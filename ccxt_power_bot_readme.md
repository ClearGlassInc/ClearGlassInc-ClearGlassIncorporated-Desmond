# ClearGlass CCXT Power Bot

A safety-first CCXT command bot for exchange market data, balances, open orders, controlled order execution, RSI signal generation, and paper/live strategy loops.

This bot is designed for disciplined experimentation and controlled execution. It does not guarantee profit. Markets are adversarial, volatile, and fee-sensitive. Live trading should start with tiny size, sandbox mode where supported, and strict API permissions.

---

## What It Can Do

- Load CCXT-supported exchanges
- Use exchange rate limiting
- Use sandbox/testnet mode where supported
- Fetch markets
- Fetch tickers
- Fetch OHLCV candles
- Calculate RSI without pandas
- Fetch balances
- Fetch open orders
- Cancel orders
- Create paper orders
- Create live orders only with `--live`
- Run a controlled RSI loop
- Enforce risk limits
- Enforce order cooldowns
- Enforce max orders per session
- Block market orders unless explicitly enabled
- Avoid hardcoded secrets
- Avoid auto-withdrawal logic

---

## Install

```bash
python -m pip install ccxt
```

Optional isolated environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip ccxt
```

---

## Environment Variables

Use exchange-specific variables or generic CCXT variables.

```bash
export CCXT_EXCHANGE=kraken
export CCXT_API_KEY="your_api_key"
export CCXT_API_SECRET="your_api_secret"
```

For exchanges requiring a password/passphrase:

```bash
export CCXT_API_PASSWORD="your_passphrase"
```

Risk controls:

```bash
export CCXT_MAX_ORDER_QUOTE=50
export CCXT_MAX_BASE_AMOUNT=0.01
export CCXT_MIN_QUOTE_BALANCE_AFTER_TRADE=10
export CCXT_ORDER_COOLDOWN_SECONDS=60
export CCXT_MAX_ORDERS_PER_SESSION=3
export CCXT_ALLOW_MARKET_ORDERS=false
```

Strategy controls:

```bash
export CCXT_TIMEFRAME=1h
export CCXT_RSI_PERIOD=14
export CCXT_RSI_BUY=30
export CCXT_RSI_SELL=70
export CCXT_QUOTE_PER_TRADE=25
export CCXT_LOOP_SECONDS=900
```

---

## Commands

List markets:

```bash
python bots/ccxt_power_bot.py --exchange kraken markets --limit 20
```

Fetch ticker:

```bash
python bots/ccxt_power_bot.py --exchange kraken ticker BTC/USDT
```

Fetch candles:

```bash
python bots/ccxt_power_bot.py --exchange kraken ohlcv BTC/USDT --timeframe 1h --limit 50
```

Fetch balance:

```bash
python bots/ccxt_power_bot.py --exchange kraken balance
```

Fetch open orders:

```bash
python bots/ccxt_power_bot.py --exchange kraken open-orders --symbol BTC/USDT
```

Paper order:

```bash
python bots/ccxt_power_bot.py --exchange kraken order BTC/USDT buy limit 0.0005 --price 65000
```

Live order:

```bash
python bots/ccxt_power_bot.py --exchange kraken --live order BTC/USDT buy limit 0.0005 --price 65000
```

RSI paper loop:

```bash
python bots/ccxt_power_bot.py --exchange kraken rsi-loop BTC/USDT --timeframe 1h --quote-per-trade 25
```

RSI live loop:

```bash
python bots/ccxt_power_bot.py --exchange kraken --live rsi-loop BTC/USDT --timeframe 1h --quote-per-trade 25
```

Sandbox mode where supported:

```bash
python bots/ccxt_power_bot.py --exchange binance --sandbox rsi-loop BTC/USDT
```

---

## Security Rules

- Do not hardcode API keys.
- Do not commit `.env` files.
- Disable withdrawal permissions on API keys.
- Use IP allowlists where the exchange supports them.
- Start with read-only keys for market data.
- Use sandbox/testnet before live trading.
- Use tiny order size first.
- Confirm exchange symbol formats before live execution.
- Check maker/taker fees before assuming strategy profitability.

---

## Why Auto-Withdrawal Is Not Included

Auto-withdrawal is intentionally excluded. A production trading bot should not automatically move funds without separate custody controls, manual approval, withdrawal allowlists, multi-factor confirmation, and exchange-side security policies.

The correct operating model is:

1. Trade with restricted API keys.
2. Keep withdrawal permissions disabled.
3. Move funds manually or through a separate custody-controlled process.

---

## Production Hardening Roadmap

- Add structured JSON logs
- Add SQLite/Postgres trade journal
- Add backtesting harness
- Add fee-aware position accounting
- Add stop-loss and take-profit logic
- Add portfolio exposure limits
- Add volatility filter
- Add exchange-specific symbol validation
- Add Prometheus metrics
- Add Telegram/Slack alerting
- Add Dockerfile and systemd service
- Add unit tests for RSI and risk checks
- Add integration tests in sandbox mode
