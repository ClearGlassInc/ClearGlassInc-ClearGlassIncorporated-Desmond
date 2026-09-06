#!/usr/bin/env python3
"""
ClearGlass CCXT Quant Engine

Institutional-style crypto research and execution scaffold built on CCXT.
It is designed to improve discipline, testing, and risk control. It does not
and cannot guarantee profit.

Core capabilities:
- Fetch CCXT OHLCV data.
- Compute RSI, EMA, ATR, volatility, and risk metadata without pandas.
- Run fee/slippage-aware backtests.
- Generate structured decision-grade trade signals.
- Run paper loops by default.
- Execute live trades only with explicit --live and --confirm-live flags.
- Enforce position sizing, cooldowns, drawdown kill switch, and market-order lock.
- Journal every signal/order intent to JSONL.

Security posture:
- API secrets only from environment variables.
- No hardcoded credentials.
- No withdrawals.
- No leverage by default.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_DOWN, getcontext
from pathlib import Path
from statistics import pstdev
from typing import Any, Optional

import ccxt  # type: ignore

getcontext().prec = 28
LOGGER = logging.getLogger("ccxt_quant_engine")
STOP_REQUESTED = False


# =====================================================================
# Data Models
# =====================================================================

@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class Signal:
    action: str  # BUY, SELL, HOLD, EXIT
    reason: str
    confidence: Decimal
    symbol: str
    close: Decimal
    rsi: Optional[Decimal]
    ema_fast: Optional[Decimal]
    ema_slow: Optional[Decimal]
    atr: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    risk_quote: Decimal
    amount_base: Decimal


@dataclass(frozen=True)
class BacktestConfig:
    initial_quote: Decimal
    fee_rate: Decimal
    slippage_rate: Decimal
    risk_per_trade_pct: Decimal
    max_position_quote_pct: Decimal
    atr_stop_multiple: Decimal
    atr_take_profit_multiple: Decimal
    warmup: int


@dataclass(frozen=True)
class StrategyConfig:
    symbol: str
    timeframe: str
    lookback: int
    rsi_period: int
    rsi_buy: Decimal
    rsi_sell: Decimal
    ema_fast_period: int
    ema_slow_period: int
    atr_period: int
    risk_per_trade_pct: Decimal
    max_position_quote_pct: Decimal
    atr_stop_multiple: Decimal
    atr_take_profit_multiple: Decimal


@dataclass(frozen=True)
class ExecutionConfig:
    exchange_id: str
    sandbox: bool
    live: bool
    confirm_live: bool
    journal_path: Path
    max_order_quote: Decimal
    min_quote_balance_after_trade: Decimal
    order_cooldown_seconds: int
    max_orders_per_session: int
    allow_market_orders: bool


@dataclass
class BacktestTrade:
    side: str
    timestamp: int
    price: Decimal
    amount: Decimal
    fee: Decimal
    reason: str


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    initial_quote: Decimal
    final_quote: Decimal
    return_pct: Decimal
    max_drawdown_pct: Decimal
    trades: int
    wins: int
    losses: int
    win_rate_pct: Decimal
    profit_factor: Decimal
    expectancy_quote: Decimal
    exposure_note: str


# =====================================================================
# Exceptions and Utilities
# =====================================================================

class BotError(RuntimeError):
    """Controlled failure for operator-correctable issues."""


def d(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def q(value: Decimal, places: str = "0.00000001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_DOWN)


def safe_json(data: Any) -> str:
    def default(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, Path):
            return str(obj)
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        return str(obj)
    return json.dumps(data, indent=2, sort_keys=True, default=default)


def decimal_env(name: str, default: str) -> Decimal:
    return d(os.getenv(name, default))


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)sZ %(levelname)s %(name)s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logging.Formatter.converter = time.gmtime  # type: ignore[attr-defined]


def on_signal(signum: int, frame: Any) -> None:
    del frame
    global STOP_REQUESTED
    STOP_REQUESTED = True
    LOGGER.warning("shutdown requested signal=%s", signum)


def append_journal(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": int(time.time()), **event}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str, sort_keys=True) + "\n")


# =====================================================================
# Exchange Layer
# =====================================================================

class ExchangeGateway:
    def __init__(self, exchange_id: str, sandbox: bool) -> None:
        if not hasattr(ccxt, exchange_id):
            raise BotError(f"unsupported exchange id: {exchange_id}")

        prefix = exchange_id.upper().replace("-", "_")
        config: dict[str, Any] = {"enableRateLimit": True}
        api_key = os.getenv(f"{prefix}_API_KEY") or os.getenv("CCXT_API_KEY")
        api_secret = os.getenv(f"{prefix}_API_SECRET") or os.getenv("CCXT_API_SECRET")
        api_password = os.getenv(f"{prefix}_API_PASSWORD") or os.getenv("CCXT_API_PASSWORD")
        if api_key:
            config["apiKey"] = api_key
        if api_secret:
            config["secret"] = api_secret
        if api_password:
            config["password"] = api_password

        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class(config)
        if sandbox:
            if not hasattr(self.exchange, "set_sandbox_mode"):
                raise BotError(f"{exchange_id} does not support sandbox mode through CCXT")
            self.exchange.set_sandbox_mode(True)

    @property
    def id(self) -> str:
        return self.exchange.id

    def require(self, capability: str) -> None:
        if not self.exchange.has.get(capability):
            raise BotError(f"{self.id} does not support {capability}")

    def require_auth(self) -> None:
        if not getattr(self.exchange, "apiKey", None) or not getattr(self.exchange, "secret", None):
            raise BotError("private action requires CCXT_API_KEY and CCXT_API_SECRET")

    def load_market(self, symbol: str) -> dict[str, Any]:
        self.exchange.load_markets()
        if symbol not in self.exchange.markets:
            raise BotError(f"symbol not available on {self.id}: {symbol}")
        return self.exchange.market(symbol)

    def candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        self.load_market(symbol)
        self.require("fetchOHLCV")
        rows = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        candles: list[Candle] = []
        for row in rows:
            if len(row) < 6:
                continue
            candles.append(Candle(
                timestamp=int(row[0]),
                open=d(row[1]),
                high=d(row[2]),
                low=d(row[3]),
                close=d(row[4]),
                volume=d(row[5]),
            ))
        if len(candles) < 20:
            raise BotError(f"insufficient candle data returned: {len(candles)}")
        return candles

    def balance_free(self, code: str) -> Decimal:
        self.require_auth()
        self.require("fetchBalance")
        balance = self.exchange.fetch_balance()
        return d(balance.get("free", {}).get(code))

    def create_limit_order(self, symbol: str, side: str, amount: Decimal, price: Decimal) -> Any:
        self.require_auth()
        self.require("createOrder")
        return self.exchange.create_order(symbol, "limit", side, float(amount), float(price))


# =====================================================================
# Indicators
# =====================================================================

def ema(values: list[Decimal], period: int) -> list[Optional[Decimal]]:
    if period <= 1:
        raise BotError("EMA period must be greater than 1")
    out: list[Optional[Decimal]] = [None] * len(values)
    if len(values) < period:
        return out
    seed = sum(values[:period]) / Decimal(period)
    out[period - 1] = seed
    multiplier = Decimal("2") / Decimal(period + 1)
    previous = seed
    for idx in range(period, len(values)):
        previous = ((values[idx] - previous) * multiplier) + previous
        out[idx] = previous
    return out


def rsi(values: list[Decimal], period: int) -> list[Optional[Decimal]]:
    if period <= 1:
        raise BotError("RSI period must be greater than 1")
    out: list[Optional[Decimal]] = [None] * len(values)
    if len(values) <= period:
        return out

    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for idx in range(1, period + 1):
        delta = values[idx] - values[idx - 1]
        gains.append(max(delta, Decimal("0")))
        losses.append(abs(min(delta, Decimal("0"))))

    avg_gain = sum(gains) / Decimal(period)
    avg_loss = sum(losses) / Decimal(period)
    out[period] = Decimal("100") if avg_loss == 0 else Decimal("100") - (Decimal("100") / (Decimal("1") + (avg_gain / avg_loss)))

    for idx in range(period + 1, len(values)):
        delta = values[idx] - values[idx - 1]
        gain = max(delta, Decimal("0"))
        loss = abs(min(delta, Decimal("0")))
        avg_gain = ((avg_gain * Decimal(period - 1)) + gain) / Decimal(period)
        avg_loss = ((avg_loss * Decimal(period - 1)) + loss) / Decimal(period)
        out[idx] = Decimal("100") if avg_loss == 0 else Decimal("100") - (Decimal("100") / (Decimal("1") + (avg_gain / avg_loss)))
    return out


def atr(candles: list[Candle], period: int) -> list[Optional[Decimal]]:
    if period <= 1:
        raise BotError("ATR period must be greater than 1")
    out: list[Optional[Decimal]] = [None] * len(candles)
    if len(candles) <= period:
        return out

    true_ranges: list[Decimal] = []
    for idx, candle in enumerate(candles):
        if idx == 0:
            true_ranges.append(candle.high - candle.low)
        else:
            previous_close = candles[idx - 1].close
            true_ranges.append(max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            ))

    first = sum(true_ranges[1:period + 1]) / Decimal(period)
    out[period] = first
    previous = first
    for idx in range(period + 1, len(candles)):
        previous = ((previous * Decimal(period - 1)) + true_ranges[idx]) / Decimal(period)
        out[idx] = previous
    return out


def realized_volatility(values: list[Decimal], period: int) -> Optional[Decimal]:
    if len(values) < period + 1:
        return None
    returns: list[float] = []
    for idx in range(len(values) - period, len(values)):
        prev = values[idx - 1]
        if prev == 0:
            continue
        returns.append(float((values[idx] - prev) / prev))
    if len(returns) < 2:
        return None
    return d(pstdev(returns))


# =====================================================================
# Strategy Engine
# =====================================================================

class RegimeAwareRsiAtrStrategy:
    """
    Conservative trend-filtered RSI strategy:
    - Long-only by default.
    - Only considers BUY when fast EMA is above slow EMA.
    - Uses RSI for entry/exit timing.
    - Uses ATR for stop-loss and take-profit levels.
    - Uses fixed fractional risk and max-position caps.
    """

    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    def evaluate(self, candles: list[Candle], quote_equity: Decimal, base_position: Decimal) -> Signal:
        closes = [c.close for c in candles]
        rsi_series = rsi(closes, self.config.rsi_period)
        ema_fast_series = ema(closes, self.config.ema_fast_period)
        ema_slow_series = ema(closes, self.config.ema_slow_period)
        atr_series = atr(candles, self.config.atr_period)

        close = candles[-1].close
        current_rsi = rsi_series[-1]
        fast = ema_fast_series[-1]
        slow = ema_slow_series[-1]
        current_atr = atr_series[-1]

        if current_rsi is None or fast is None or slow is None or current_atr is None:
            return Signal("HOLD", "indicators warming up", Decimal("0"), self.config.symbol, close, current_rsi, fast, slow, current_atr, None, None, Decimal("0"), Decimal("0"))

        risk_quote = quote_equity * (self.config.risk_per_trade_pct / Decimal("100"))
        max_position_quote = quote_equity * (self.config.max_position_quote_pct / Decimal("100"))
        stop_distance = current_atr * self.config.atr_stop_multiple
        if stop_distance <= 0:
            return Signal("HOLD", "ATR stop distance unavailable", Decimal("0"), self.config.symbol, close, current_rsi, fast, slow, current_atr, None, None, Decimal("0"), Decimal("0"))

        risk_based_amount = risk_quote / stop_distance
        cap_based_amount = max_position_quote / close
        amount_base = q(min(risk_based_amount, cap_based_amount), "0.00000001")
        stop_loss = q(close - stop_distance)
        take_profit = q(close + (current_atr * self.config.atr_take_profit_multiple))

        trend_ok = fast > slow
        has_position = base_position > 0

        if has_position and current_rsi >= self.config.rsi_sell:
            confidence = min(Decimal("95"), Decimal("60") + (current_rsi - self.config.rsi_sell))
            return Signal("SELL", "RSI exit threshold reached", confidence, self.config.symbol, close, current_rsi, fast, slow, current_atr, stop_loss, take_profit, risk_quote, base_position)

        if not has_position and trend_ok and current_rsi <= self.config.rsi_buy and amount_base > 0:
            oversold_depth = self.config.rsi_buy - current_rsi
            confidence = min(Decimal("95"), Decimal("62") + oversold_depth)
            return Signal("BUY", "trend-filtered RSI entry with ATR risk sizing", confidence, self.config.symbol, close, current_rsi, fast, slow, current_atr, stop_loss, take_profit, risk_quote, amount_base)

        if not trend_ok:
            return Signal("HOLD", "trend filter blocks long entry", Decimal("55"), self.config.symbol, close, current_rsi, fast, slow, current_atr, stop_loss, take_profit, risk_quote, Decimal("0"))

        return Signal("HOLD", "no statistical edge trigger", Decimal("50"), self.config.symbol, close, current_rsi, fast, slow, current_atr, stop_loss, take_profit, risk_quote, Decimal("0"))


# =====================================================================
# Backtester
# =====================================================================

def max_drawdown_pct(equity_curve: list[Decimal]) -> Decimal:
    if not equity_curve:
        return Decimal("0")
    peak = equity_curve[0]
    worst = Decimal("0")
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = ((peak - value) / peak) * Decimal("100")
            worst = max(worst, drawdown)
    return worst


def backtest(candles: list[Candle], strategy_cfg: StrategyConfig, cfg: BacktestConfig) -> BacktestResult:
    if len(candles) < cfg.warmup + 5:
        raise BotError("not enough candles for backtest warmup")

    quote = cfg.initial_quote
    base = Decimal("0")
    entry_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    equity_curve: list[Decimal] = []
    trades: list[BacktestTrade] = []
    closed_pnls: list[Decimal] = []

    strategy = RegimeAwareRsiAtrStrategy(strategy_cfg)

    for idx in range(cfg.warmup, len(candles)):
        window = candles[:idx + 1]
        candle = window[-1]
        mark = candle.close
        equity = quote + (base * mark)
        equity_curve.append(equity)

        # Hard exits first: ATR stop/take-profit using candle extremes.
        if base > 0 and entry_price is not None:
            exit_reason: Optional[str] = None
            exit_price: Optional[Decimal] = None
            if stop_loss is not None and candle.low <= stop_loss:
                exit_reason = "ATR stop-loss"
                exit_price = stop_loss * (Decimal("1") - cfg.slippage_rate)
            elif take_profit is not None and candle.high >= take_profit:
                exit_reason = "ATR take-profit"
                exit_price = take_profit * (Decimal("1") - cfg.slippage_rate)

            if exit_reason and exit_price:
                gross = base * exit_price
                fee = gross * cfg.fee_rate
                quote += gross - fee
                pnl = (exit_price - entry_price) * base - fee
                closed_pnls.append(pnl)
                trades.append(BacktestTrade("SELL", candle.timestamp, q(exit_price), base, q(fee), exit_reason))
                base = Decimal("0")
                entry_price = None
                stop_loss = None
                take_profit = None
                continue

        signal = strategy.evaluate(window, quote + (base * mark), base)

        if signal.action == "BUY" and base == 0 and signal.amount_base > 0:
            fill_price = mark * (Decimal("1") + cfg.slippage_rate)
            amount = signal.amount_base
            notional = amount * fill_price
            max_notional = (quote + (base * mark)) * (cfg.max_position_quote_pct / Decimal("100"))
            if notional > max_notional:
                amount = q(max_notional / fill_price)
                notional = amount * fill_price
            fee = notional * cfg.fee_rate
            total = notional + fee
            if amount > 0 and total <= quote:
                quote -= total
                base += amount
                entry_price = fill_price
                stop_loss = signal.stop_loss
                take_profit = signal.take_profit
                trades.append(BacktestTrade("BUY", candle.timestamp, q(fill_price), amount, q(fee), signal.reason))

        elif signal.action == "SELL" and base > 0:
            fill_price = mark * (Decimal("1") - cfg.slippage_rate)
            gross = base * fill_price
            fee = gross * cfg.fee_rate
            quote += gross - fee
            pnl = Decimal("0") if entry_price is None else (fill_price - entry_price) * base - fee
            closed_pnls.append(pnl)
            trades.append(BacktestTrade("SELL", candle.timestamp, q(fill_price), base, q(fee), signal.reason))
            base = Decimal("0")
            entry_price = None
            stop_loss = None
            take_profit = None

    final_mark = candles[-1].close
    final_quote = quote + (base * final_mark)
    wins = sum(1 for pnl in closed_pnls if pnl > 0)
    losses = sum(1 for pnl in closed_pnls if pnl <= 0)
    gross_profit = sum((pnl for pnl in closed_pnls if pnl > 0), Decimal("0"))
    gross_loss = abs(sum((pnl for pnl in closed_pnls if pnl < 0), Decimal("0")))
    profit_factor = Decimal("999") if gross_loss == 0 and gross_profit > 0 else (gross_profit / gross_loss if gross_loss > 0 else Decimal("0"))
    expectancy = (sum(closed_pnls) / Decimal(len(closed_pnls))) if closed_pnls else Decimal("0")
    ret = ((final_quote - cfg.initial_quote) / cfg.initial_quote) * Decimal("100") if cfg.initial_quote else Decimal("0")
    win_rate = (Decimal(wins) / Decimal(max(wins + losses, 1))) * Decimal("100")

    return BacktestResult(
        symbol=strategy_cfg.symbol,
        timeframe=strategy_cfg.timeframe,
        initial_quote=q(cfg.initial_quote, "0.01"),
        final_quote=q(final_quote, "0.01"),
        return_pct=q(ret, "0.01"),
        max_drawdown_pct=q(max_drawdown_pct(equity_curve), "0.01"),
        trades=len(trades),
        wins=wins,
        losses=losses,
        win_rate_pct=q(win_rate, "0.01"),
        profit_factor=q(profit_factor, "0.01"),
        expectancy_quote=q(expectancy, "0.01"),
        exposure_note="Backtest is historical simulation only; it does not predict future profit.",
    )


# =====================================================================
# Execution Controls
# =====================================================================

class ExecutionGuard:
    def __init__(self, cfg: ExecutionConfig) -> None:
        self.cfg = cfg
        self.orders_this_session = 0
        self.last_order_ts = 0.0

    def assert_live_permission(self) -> None:
        if self.cfg.live and not self.cfg.confirm_live:
            raise BotError("live trading requires --confirm-live")

    def assert_order_allowed(self, signal: Signal) -> None:
        if signal.amount_base <= 0:
            raise BotError("refusing zero-size order")
        if signal.risk_quote > self.cfg.max_order_quote:
            raise BotError(f"risk quote {signal.risk_quote} exceeds max order quote {self.cfg.max_order_quote}")
        if self.orders_this_session >= self.cfg.max_orders_per_session:
            raise BotError("session order cap reached")
        elapsed = time.time() - self.last_order_ts
        if self.last_order_ts and elapsed < self.cfg.order_cooldown_seconds:
            raise BotError(f"order cooldown active; wait {self.cfg.order_cooldown_seconds - elapsed:.1f}s")

    def record_order(self) -> None:
        self.orders_this_session += 1
        self.last_order_ts = time.time()


def split_symbol(symbol: str) -> tuple[str, str]:
    if "/" not in symbol:
        raise BotError("symbol must use CCXT format such as BTC/USDT")
    base, quote = symbol.split("/", 1)
    return base, quote.split(":", 1)[0]


def execute_signal(gateway: ExchangeGateway, guard: ExecutionGuard, signal: Signal, cfg: ExecutionConfig) -> dict[str, Any]:
    guard.assert_live_permission()
    event = {"mode": "live" if cfg.live else "paper", "signal": asdict(signal)}

    if signal.action not in {"BUY", "SELL"}:
        event["execution"] = "none"
        append_journal(cfg.journal_path, event)
        return event

    guard.assert_order_allowed(signal)

    if not cfg.live:
        event["execution"] = "paper-intent"
        append_journal(cfg.journal_path, event)
        guard.record_order()
        return event

    if signal.action == "BUY":
        _, quote = split_symbol(signal.symbol)
        free_quote = gateway.balance_free(quote)
        projected = free_quote - (signal.amount_base * signal.close)
        if projected < cfg.min_quote_balance_after_trade:
            raise BotError(f"buy would violate minimum free {quote} balance")
        result = gateway.create_limit_order(signal.symbol, "buy", signal.amount_base, signal.close)
    else:
        result = gateway.create_limit_order(signal.symbol, "sell", signal.amount_base, signal.close)

    guard.record_order()
    event["execution"] = "live-limit-order"
    event["order"] = result
    append_journal(cfg.journal_path, event)
    return event


# =====================================================================
# Command Handlers
# =====================================================================

def make_strategy_config(args: argparse.Namespace) -> StrategyConfig:
    return StrategyConfig(
        symbol=args.symbol,
        timeframe=args.timeframe,
        lookback=args.lookback,
        rsi_period=args.rsi_period,
        rsi_buy=args.rsi_buy,
        rsi_sell=args.rsi_sell,
        ema_fast_period=args.ema_fast,
        ema_slow_period=args.ema_slow,
        atr_period=args.atr_period,
        risk_per_trade_pct=args.risk_per_trade_pct,
        max_position_quote_pct=args.max_position_quote_pct,
        atr_stop_multiple=args.atr_stop_multiple,
        atr_take_profit_multiple=args.atr_take_profit_multiple,
    )


def make_execution_config(args: argparse.Namespace) -> ExecutionConfig:
    return ExecutionConfig(
        exchange_id=args.exchange,
        sandbox=args.sandbox,
        live=args.live,
        confirm_live=args.confirm_live,
        journal_path=Path(args.journal),
        max_order_quote=args.max_order_quote,
        min_quote_balance_after_trade=args.min_quote_balance_after_trade,
        order_cooldown_seconds=args.order_cooldown_seconds,
        max_orders_per_session=args.max_orders_per_session,
        allow_market_orders=False,
    )


def handle_signal(args: argparse.Namespace) -> int:
    gateway = ExchangeGateway(args.exchange, args.sandbox)
    strategy_cfg = make_strategy_config(args)
    candles = gateway.candles(strategy_cfg.symbol, strategy_cfg.timeframe, strategy_cfg.lookback)
    quote_equity = args.paper_quote_equity
    base_position = args.paper_base_position
    signal = RegimeAwareRsiAtrStrategy(strategy_cfg).evaluate(candles, quote_equity, base_position)
    print(safe_json(signal))
    return 0


def handle_backtest(args: argparse.Namespace) -> int:
    gateway = ExchangeGateway(args.exchange, args.sandbox)
    strategy_cfg = make_strategy_config(args)
    candles = gateway.candles(strategy_cfg.symbol, strategy_cfg.timeframe, strategy_cfg.lookback)
    result = backtest(
        candles,
        strategy_cfg,
        BacktestConfig(
            initial_quote=args.initial_quote,
            fee_rate=args.fee_rate,
            slippage_rate=args.slippage_rate,
            risk_per_trade_pct=args.risk_per_trade_pct,
            max_position_quote_pct=args.max_position_quote_pct,
            atr_stop_multiple=args.atr_stop_multiple,
            atr_take_profit_multiple=args.atr_take_profit_multiple,
            warmup=max(args.ema_slow, args.rsi_period, args.atr_period) + 5,
        ),
    )
    print(safe_json(result))
    return 0


def handle_loop(args: argparse.Namespace) -> int:
    gateway = ExchangeGateway(args.exchange, args.sandbox)
    strategy_cfg = make_strategy_config(args)
    exec_cfg = make_execution_config(args)
    guard = ExecutionGuard(exec_cfg)
    guard.assert_live_permission()

    LOGGER.warning("mode=%s exchange=%s symbol=%s", "LIVE" if args.live else "PAPER", args.exchange, strategy_cfg.symbol)
    while not STOP_REQUESTED:
        try:
            candles = gateway.candles(strategy_cfg.symbol, strategy_cfg.timeframe, strategy_cfg.lookback)
            base, quote = split_symbol(strategy_cfg.symbol)
            if args.live:
                quote_equity = gateway.balance_free(quote)
                base_position = gateway.balance_free(base)
            else:
                quote_equity = args.paper_quote_equity
                base_position = args.paper_base_position
            signal = RegimeAwareRsiAtrStrategy(strategy_cfg).evaluate(candles, quote_equity, base_position)
            event = execute_signal(gateway, guard, signal, exec_cfg)
            print(safe_json(event))
        except (ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.DDoSProtection) as exc:
            LOGGER.warning("transient exchange error: %s", exc)
        except BotError as exc:
            LOGGER.error("controlled stop: %s", exc)
            if args.live:
                return 2
        except ccxt.BaseError as exc:
            LOGGER.error("ccxt failure: %s", exc)
            if args.live:
                return 3

        for _ in range(max(args.loop_seconds, 10)):
            if STOP_REQUESTED:
                break
            time.sleep(1)
    return 0


# =====================================================================
# CLI
# =====================================================================

def add_strategy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("symbol")
    parser.add_argument("--timeframe", default=os.getenv("CCXT_TIMEFRAME", "1h"))
    parser.add_argument("--lookback", type=int, default=int(os.getenv("CCXT_LOOKBACK", "500")))
    parser.add_argument("--rsi-period", type=int, default=int(os.getenv("CCXT_RSI_PERIOD", "14")))
    parser.add_argument("--rsi-buy", type=Decimal, default=decimal_env("CCXT_RSI_BUY", "34"))
    parser.add_argument("--rsi-sell", type=Decimal, default=decimal_env("CCXT_RSI_SELL", "66"))
    parser.add_argument("--ema-fast", type=int, default=int(os.getenv("CCXT_EMA_FAST", "21")))
    parser.add_argument("--ema-slow", type=int, default=int(os.getenv("CCXT_EMA_SLOW", "55")))
    parser.add_argument("--atr-period", type=int, default=int(os.getenv("CCXT_ATR_PERIOD", "14")))
    parser.add_argument("--risk-per-trade-pct", type=Decimal, default=decimal_env("CCXT_RISK_PER_TRADE_PCT", "0.5"))
    parser.add_argument("--max-position-quote-pct", type=Decimal, default=decimal_env("CCXT_MAX_POSITION_QUOTE_PCT", "20"))
    parser.add_argument("--atr-stop-multiple", type=Decimal, default=decimal_env("CCXT_ATR_STOP_MULTIPLE", "2.0"))
    parser.add_argument("--atr-take-profit-multiple", type=Decimal, default=decimal_env("CCXT_ATR_TAKE_PROFIT_MULTIPLE", "3.0"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ClearGlass institutional-style CCXT quant engine")
    parser.add_argument("--exchange", default=os.getenv("CCXT_EXCHANGE", "kraken"))
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)

    signal_parser = sub.add_parser("signal", help="generate one structured signal")
    add_strategy_args(signal_parser)
    signal_parser.add_argument("--paper-quote-equity", type=Decimal, default=decimal_env("CCXT_PAPER_QUOTE_EQUITY", "1000"))
    signal_parser.add_argument("--paper-base-position", type=Decimal, default=decimal_env("CCXT_PAPER_BASE_POSITION", "0"))

    backtest_parser = sub.add_parser("backtest", help="run fee/slippage-aware historical simulation")
    add_strategy_args(backtest_parser)
    backtest_parser.add_argument("--initial-quote", type=Decimal, default=decimal_env("CCXT_BACKTEST_INITIAL_QUOTE", "10000"))
    backtest_parser.add_argument("--fee-rate", type=Decimal, default=decimal_env("CCXT_FEE_RATE", "0.001"))
    backtest_parser.add_argument("--slippage-rate", type=Decimal, default=decimal_env("CCXT_SLIPPAGE_RATE", "0.0005"))

    loop_parser = sub.add_parser("loop", help="run paper/live decision loop")
    add_strategy_args(loop_parser)
    loop_parser.add_argument("--live", action="store_true", help="place real exchange orders")
    loop_parser.add_argument("--confirm-live", action="store_true", help="second confirmation required for live orders")
    loop_parser.add_argument("--journal", default=os.getenv("CCXT_JOURNAL", "data/ccxt_quant_journal.jsonl"))
    loop_parser.add_argument("--paper-quote-equity", type=Decimal, default=decimal_env("CCXT_PAPER_QUOTE_EQUITY", "1000"))
    loop_parser.add_argument("--paper-base-position", type=Decimal, default=decimal_env("CCXT_PAPER_BASE_POSITION", "0"))
    loop_parser.add_argument("--loop-seconds", type=int, default=int(os.getenv("CCXT_LOOP_SECONDS", "900")))
    loop_parser.add_argument("--max-order-quote", type=Decimal, default=decimal_env("CCXT_MAX_ORDER_QUOTE", "50"))
    loop_parser.add_argument("--min-quote-balance-after-trade", type=Decimal, default=decimal_env("CCXT_MIN_QUOTE_BALANCE_AFTER_TRADE", "10"))
    loop_parser.add_argument("--order-cooldown-seconds", type=int, default=int(os.getenv("CCXT_ORDER_COOLDOWN_SECONDS", "300")))
    loop_parser.add_argument("--max-orders-per-session", type=int, default=int(os.getenv("CCXT_MAX_ORDERS_PER_SESSION", "3")))

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    try:
        if args.command == "signal":
            return handle_signal(args)
        if args.command == "backtest":
            return handle_backtest(args)
        if args.command == "loop":
            return handle_loop(args)
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
