#!/usr/bin/env python3
"""
ClearGlass CCXT Power Bot

A safety-first CCXT command bot for market data, balances, open orders,
manual order execution, RSI signal generation, and paper/live strategy loops.

No profit is guaranteed. Live trading is disabled unless --live is explicitly set.
API credentials must come from environment variables. Do not hardcode secrets.
Withdrawals are intentionally not implemented in this bot.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import ccxt  # type: ignore

LOGGER = logging.getLogger("ccxt_power_bot")
STOP_REQUESTED = False


@dataclass(frozen=True)
class ExchangeSettings:
    exchange_id: str
    api_key: Optional[str]
    api_secret: Optional[str]
    api_password: Optional[str]
    sandbox: bool
    rate_limit: bool = True


@dataclass(frozen=True)
class RiskSettings:
    max_order_quote: Decimal
    max_base_amount: Decimal
    min_quote_balance_after_trade: Decimal
    order_cooldown_seconds: int
    max_orders_per_session: int
    allow_market_orders: bool


@dataclass(frozen=True)
class StrategySettings:
    symbol: str
    timeframe: str
    rsi_period: int
    rsi_buy: Decimal
    rsi_sell: Decimal
    quote_per_trade: Decimal
    loop_seconds: int


class BotError(RuntimeError):
    """Controlled bot failure."""


class CircuitBreaker:
    def __init__(self, max_orders: int, cooldown_seconds: int) -> None:
        self.max_orders = max_orders
        self.cooldown_seconds = cooldown_seconds
        self.orders_sent = 0
        self.last_order_ts = 0.0

    def assert_can_trade(self) -> None:
        if self.orders_sent >= self.max_orders:
            raise BotError(f"session order limit reached: {self.orders_sent}/{self.max_orders}")
        elapsed = time.time() - self.last_order_ts
        if self.last_order_ts and elapsed < self.cooldown_seconds:
            wait = self.cooldown_seconds - elapsed
            raise BotError(f"cooldown active; wait {wait:.1f}s before next order")

    def record_order(self) -> None:
        self.orders_sent += 1
        self.last_order_ts = time.time()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    logging.Formatter.converter = time.gmtime  # type: ignore[attr-defined]


def decimal_from_env(name: str, default: str) -> Decimal:
    value = os.getenv(name, default)
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise BotError(f"invalid decimal for {name}: {value}") from exc


def settings_from_env(exchange_id: str, sandbox: bool) -> ExchangeSettings:
    prefix = exchange_id.upper().replace("-", "_")
    return ExchangeSettings(
        exchange_id=exchange_id,
        api_key=os.getenv(f"{prefix}_API_KEY") or os.getenv("CCXT_API_KEY"),
        api_secret=os.getenv(f"{prefix}_API_SECRET") or os.getenv("CCXT_API_SECRET"),
        api_password=os.getenv(f"{prefix}_API_PASSWORD") or os.getenv("CCXT_API_PASSWORD"),
        sandbox=sandbox,
        rate_limit=True,
    )


def risk_from_env() -> RiskSettings:
    return RiskSettings(
        max_order_quote=decimal_from_env("CCXT_MAX_ORDER_QUOTE", "50"),
        max_base_amount=decimal_from_env("CCXT_MAX_BASE_AMOUNT", "0.01"),
        min_quote_balance_after_trade=decimal_from_env("CCXT_MIN_QUOTE_BALANCE_AFTER_TRADE", "10"),
        order_cooldown_seconds=int(os.getenv("CCXT_ORDER_COOLDOWN_SECONDS", "60")),
        max_orders_per_session=int(os.getenv("CCXT_MAX_ORDERS_PER_SESSION", "3")),
        allow_market_orders=os.getenv("CCXT_ALLOW_MARKET_ORDERS", "false").lower() == "true",
    )


def build_exchange(settings: ExchangeSettings) -> Any:
    if not hasattr(ccxt, settings.exchange_id):
        raise BotError(f"unsupported exchange id: {settings.exchange_id}")

    exchange_class = getattr(ccxt, settings.exchange_id)
    config: dict[str, Any] = {"enableRateLimit": settings.rate_limit}
    if settings.api_key:
        config["apiKey"] = settings.api_key
    if settings.api_secret:
        config["secret"] = settings.api_secret
    if settings.api_password:
        config["password"] = settings.api_password

    exchange = exchange_class(config)

    # Sandbox must be the first call after construction when supported by the exchange.
    if settings.sandbox:
        if hasattr(exchange, "set_sandbox_mode"):
            exchange.set_sandbox_mode(True)
        else:
            raise BotError(f"{settings.exchange_id} does not expose set_sandbox_mode")

    return exchange


def require_private_credentials(exchange: Any) -> None:
    if not getattr(exchange, "apiKey", None) or not getattr(exchange, "secret", None):
        raise BotError("private action requires API credentials in env vars")


def require_capability(exchange: Any, capability: str) -> None:
    value = exchange.has.get(capability) if hasattr(exchange, "has") else None
    if not value:
        raise BotError(f"exchange does not support CCXT capability: {capability}")


def safe_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def split_symbol(symbol: str) -> tuple[str, str]:
    if "/" not in symbol:
        raise BotError(f"symbol must use CCXT format like BTC/USDT, got: {symbol}")
    base, quote = symbol.split("/", 1)
    quote = quote.split(":", 1)[0]
    return base, quote


def load_and_validate_market(exchange: Any, symbol: str) -> dict[str, Any]:
    exchange.load_markets()
    if symbol not in exchange.markets:
        raise BotError(f"symbol not listed on {exchange.id}: {symbol}")
    return exchange.market(symbol)


def to_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal(default)


def current_price(exchange: Any, symbol: str) -> Decimal:
    require_capability(exchange, "fetchTicker")
    ticker = exchange.fetch_ticker(symbol)
    price = ticker.get("last") or ticker.get("close") or ticker.get("bid") or ticker.get("ask")
    if price is None:
        raise BotError(f"ticker for {symbol} has no usable price")
    return to_decimal(price)


def calculate_rsi(closes: list[Decimal], period: int) -> Optional[Decimal]:
    if period <= 1:
        raise BotError("RSI period must be greater than 1")
    if len(closes) < period + 1:
        return None

    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, Decimal("0")))
        losses.append(abs(min(delta, Decimal("0"))))

    avg_gain = sum(gains) / Decimal(period)
    avg_loss = sum(losses) / Decimal(period)

    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, Decimal("0"))
        loss = abs(min(delta, Decimal("0")))
        avg_gain = ((avg_gain * Decimal(period - 1)) + gain) / Decimal(period)
        avg_loss = ((avg_loss * Decimal(period - 1)) + loss) / Decimal(period)

    if avg_loss == 0:
        return Decimal("100")
    rs = avg_gain / avg_loss
    return Decimal("100") - (Decimal("100") / (Decimal("1") + rs))


def fetch_rsi(exchange: Any, symbol: str, timeframe: str, period: int) -> Decimal:
    require_capability(exchange, "fetchOHLCV")
    limit = max(period + 50, 100)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    closes = [to_decimal(row[4]) for row in ohlcv if len(row) >= 5]
    rsi = calculate_rsi(closes, period)
    if rsi is None:
        raise BotError(f"not enough OHLCV candles to calculate RSI({period})")
    return rsi


def print_markets(exchange: Any, limit: int) -> None:
    require_capability(exchange, "fetchMarkets")
    markets = exchange.load_markets()
    rows = []
    for symbol, market in list(markets.items())[:limit]:
        rows.append({
            "symbol": symbol,
            "base": market.get("base"),
            "quote": market.get("quote"),
            "spot": market.get("spot"),
            "swap": market.get("swap"),
            "active": market.get("active"),
        })
    print(safe_json(rows))


def print_ticker(exchange: Any, symbol: str) -> None:
    load_and_validate_market(exchange, symbol)
    require_capability(exchange, "fetchTicker")
    print(safe_json(exchange.fetch_ticker(symbol)))


def print_ohlcv(exchange: Any, symbol: str, timeframe: str, limit: int) -> None:
    load_and_validate_market(exchange, symbol)
    require_capability(exchange, "fetchOHLCV")
    print(safe_json(exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)))


def print_balance(exchange: Any) -> None:
    require_private_credentials(exchange)
    require_capability(exchange, "fetchBalance")
    balance = exchange.fetch_balance()
    compact = {
        code: amount for code, amount in balance.get("free", {}).items()
        if amount not in (None, 0, 0.0, "0")
    }
    print(safe_json({"free": compact}))


def print_open_orders(exchange: Any, symbol: Optional[str]) -> None:
    require_private_credentials(exchange)
    require_capability(exchange, "fetchOpenOrders")
    if symbol:
        load_and_validate_market(exchange, symbol)
    print(safe_json(exchange.fetch_open_orders(symbol)))


def cancel_order(exchange: Any, order_id: str, symbol: Optional[str], live: bool) -> None:
    require_private_credentials(exchange)
    require_capability(exchange, "cancelOrder")
    if not live:
        print(safe_json({"mode": "paper", "action": "cancelOrder", "id": order_id, "symbol": symbol}))
        return
    print(safe_json(exchange.cancel_order(order_id, symbol)))


def validate_order_risk(
    exchange: Any,
    risk: RiskSettings,
    symbol: str,
    side: str,
    order_type: str,
    amount: Decimal,
    price: Optional[Decimal],
) -> None:
    market = load_and_validate_market(exchange, symbol)
    if side not in {"buy", "sell"}:
        raise BotError("side must be buy or sell")
    if order_type not in {"limit", "market"}:
        raise BotError("order type must be limit or market")
    if order_type == "market" and not risk.allow_market_orders:
        raise BotError("market orders disabled; set CCXT_ALLOW_MARKET_ORDERS=true to permit")
    if amount <= 0:
        raise BotError("amount must be positive")
    if amount > risk.max_base_amount:
        raise BotError(f"amount {amount} exceeds max base amount {risk.max_base_amount}")

    px = price or current_price(exchange, symbol)
    quote_value = amount * px
    if quote_value > risk.max_order_quote:
        raise BotError(f"order value {quote_value} exceeds max quote value {risk.max_order_quote}")

    min_amount = to_decimal(market.get("limits", {}).get("amount", {}).get("min"))
    if min_amount and amount < min_amount:
        raise BotError(f"amount {amount} below exchange min amount {min_amount}")

    min_cost = to_decimal(market.get("limits", {}).get("cost", {}).get("min"))
    if min_cost and quote_value < min_cost:
        raise BotError(f"order quote value {quote_value} below exchange min cost {min_cost}")

    if side == "buy":
        require_private_credentials(exchange)
        if exchange.has.get("fetchBalance"):
            _, quote = split_symbol(symbol)
            balance = exchange.fetch_balance()
            free_quote = to_decimal(balance.get("free", {}).get(quote))
            remaining = free_quote - quote_value
            if remaining < risk.min_quote_balance_after_trade:
                raise BotError(
                    f"buy would leave {remaining} {quote}; minimum required is "
                    f"{risk.min_quote_balance_after_trade} {quote}"
                )


def create_order(
    exchange: Any,
    risk: RiskSettings,
    breaker: CircuitBreaker,
    symbol: str,
    side: str,
    order_type: str,
    amount: Decimal,
    price: Optional[Decimal],
    live: bool,
) -> None:
    require_private_credentials(exchange)
    require_capability(exchange, "createOrder")
    validate_order_risk(exchange, risk, symbol, side, order_type, amount, price)
    breaker.assert_can_trade()

    if not live:
        print(safe_json({
            "mode": "paper",
            "action": "createOrder",
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "amount": str(amount),
            "price": str(price) if price else None,
        }))
        breaker.record_order()
        return

    order_amount = float(amount)
    order_price = float(price) if price is not None else None
    result = exchange.create_order(symbol, order_type, side, order_amount, order_price)
    breaker.record_order()
    print(safe_json(result))


def run_rsi_once(
    exchange: Any,
    risk: RiskSettings,
    breaker: CircuitBreaker,
    strategy: StrategySettings,
    live: bool,
) -> None:
    load_and_validate_market(exchange, strategy.symbol)
    rsi = fetch_rsi(exchange, strategy.symbol, strategy.timeframe, strategy.rsi_period)
    px = current_price(exchange, strategy.symbol)
    amount = strategy.quote_per_trade / px

    LOGGER.info(
        "symbol=%s price=%s rsi=%s buy_below=%s sell_above=%s mode=%s",
        strategy.symbol,
        px,
        rsi.quantize(Decimal("0.01")),
        strategy.rsi_buy,
        strategy.rsi_sell,
        "live" if live else "paper",
    )

    if rsi <= strategy.rsi_buy:
        LOGGER.info("signal=BUY reason=RSI oversold")
        create_order(exchange, risk, breaker, strategy.symbol, "buy", "limit", amount, px, live)
    elif rsi >= strategy.rsi_sell:
        LOGGER.info("signal=SELL reason=RSI overbought")
        create_order(exchange, risk, breaker, strategy.symbol, "sell", "limit", amount, px, live)
    else:
        LOGGER.info("signal=HOLD reason=RSI neutral")


def run_rsi_loop(exchange: Any, risk: RiskSettings, strategy: StrategySettings, live: bool) -> None:
    breaker = CircuitBreaker(risk.max_orders_per_session, risk.order_cooldown_seconds)
    while not STOP_REQUESTED:
        try:
            run_rsi_once(exchange, risk, breaker, strategy, live)
        except (ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.DDoSProtection) as exc:
            LOGGER.warning("transient exchange failure: %s", exc)
        except BotError as exc:
            LOGGER.error("controlled stop: %s", exc)
            if live:
                break
        except ccxt.BaseError as exc:
            LOGGER.error("ccxt error: %s", exc)
            if live:
                break
        sleep_for = max(strategy.loop_seconds, 10)
        LOGGER.info("sleeping %ss", sleep_for)
        for _ in range(sleep_for):
            if STOP_REQUESTED:
                break
            time.sleep(1)


def signal_handler(signum: int, frame: Any) -> None:
    del frame
    global STOP_REQUESTED
    STOP_REQUESTED = True
    LOGGER.warning("shutdown requested by signal %s", signum)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safety-first CCXT trading and market-data bot")
    parser.add_argument("--exchange", default=os.getenv("CCXT_EXCHANGE", "kraken"))
    parser.add_argument("--sandbox", action="store_true", help="use exchange sandbox/testnet if supported")
    parser.add_argument("--live", action="store_true", help="execute real private actions; default is paper mode")
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)

    markets = sub.add_parser("markets", help="list markets")
    markets.add_argument("--limit", type=int, default=30)

    ticker = sub.add_parser("ticker", help="fetch ticker")
    ticker.add_argument("symbol")

    ohlcv = sub.add_parser("ohlcv", help="fetch candles")
    ohlcv.add_argument("symbol")
    ohlcv.add_argument("--timeframe", default="1h")
    ohlcv.add_argument("--limit", type=int, default=50)

    sub.add_parser("balance", help="fetch non-zero free balances")

    orders = sub.add_parser("open-orders", help="fetch open orders")
    orders.add_argument("--symbol")

    cancel = sub.add_parser("cancel", help="cancel an order")
    cancel.add_argument("order_id")
    cancel.add_argument("--symbol")

    order = sub.add_parser("order", help="place paper/live order")
    order.add_argument("symbol")
    order.add_argument("side", choices=["buy", "sell"])
    order.add_argument("type", choices=["limit", "market"])
    order.add_argument("amount", type=Decimal)
    order.add_argument("--price", type=Decimal)

    rsi = sub.add_parser("rsi-loop", help="run RSI paper/live strategy loop")
    rsi.add_argument("symbol")
    rsi.add_argument("--timeframe", default=os.getenv("CCXT_TIMEFRAME", "1h"))
    rsi.add_argument("--period", type=int, default=int(os.getenv("CCXT_RSI_PERIOD", "14")))
    rsi.add_argument("--buy", type=Decimal, default=decimal_from_env("CCXT_RSI_BUY", "30"))
    rsi.add_argument("--sell", type=Decimal, default=decimal_from_env("CCXT_RSI_SELL", "70"))
    rsi.add_argument("--quote-per-trade", type=Decimal, default=decimal_from_env("CCXT_QUOTE_PER_TRADE", "25"))
    rsi.add_argument("--loop-seconds", type=int, default=int(os.getenv("CCXT_LOOP_SECONDS", "900")))

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    if args.live:
        LOGGER.warning("LIVE MODE ENABLED. Real private exchange actions may execute.")
    else:
        LOGGER.info("paper mode active; no real orders or cancellations will execute")

    settings = settings_from_env(args.exchange, args.sandbox)
    risk = risk_from_env()
    exchange = build_exchange(settings)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if args.command == "markets":
            print_markets(exchange, args.limit)
        elif args.command == "ticker":
            print_ticker(exchange, args.symbol)
        elif args.command == "ohlcv":
            print_ohlcv(exchange, args.symbol, args.timeframe, args.limit)
        elif args.command == "balance":
            print_balance(exchange)
        elif args.command == "open-orders":
            print_open_orders(exchange, args.symbol)
        elif args.command == "cancel":
            cancel_order(exchange, args.order_id, args.symbol, args.live)
        elif args.command == "order":
            breaker = CircuitBreaker(risk.max_orders_per_session, risk.order_cooldown_seconds)
            create_order(exchange, risk, breaker, args.symbol, args.side, args.type, args.amount, args.price, args.live)
        elif args.command == "rsi-loop":
            strategy = StrategySettings(
                symbol=args.symbol,
                timeframe=args.timeframe,
                rsi_period=args.period,
                rsi_buy=args.buy,
                rsi_sell=args.sell,
                quote_per_trade=args.quote_per_trade,
                loop_seconds=args.loop_seconds,
            )
            run_rsi_loop(exchange, risk, strategy, args.live)
        else:
            parser.error(f"unknown command: {args.command}")
    except BotError as exc:
        LOGGER.error("%s", exc)
        return 2
    except ccxt.AuthenticationError as exc:
        LOGGER.error("authentication failed: %s", exc)
        return 3
    except ccxt.PermissionDenied as exc:
        LOGGER.error("permission denied: %s", exc)
        return 4
    except ccxt.BaseError as exc:
        LOGGER.error("ccxt failure: %s", exc)
        return 5

    return 0


if __name__ == "__main__":
    sys.exit(main())
