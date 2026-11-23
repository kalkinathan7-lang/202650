# 202650 Master Project Specification & Implementation Status

This document preserves the full scope and rules of the requested project. The current ZIP is a runnable **initial analysis prototype**, not a completed implementation of every requirement. Status is shown honestly.

## Identity, objective, and branding
- Name: **202650**; type: AI-powered cryptocurrency futures trading intelligence and scanner.
- Primary exchange: CoinDCX; market: futures; currency: USDT; execution timeframe: 15 minutes; context timeframe: 1 hour; target: responsive Streamlit web app.
- Brand: “202650 CRYPTO TRADING INTELLIGENCE”; description: intelligent cryptocurrency analysis using systematic strategies, risk controls, real-time data, transparent decisions.
- Priorities: capital protection, accurate data, valid setups, strict strategy adherence, no fabricated signals, transparent explanations, reliable calculations, risk controls, scanner efficiency, honest performance reporting.
- Never force a trade. NO TRADE can be the outcome all day. No profit guarantees.

## Exchange/data scope
- Official CoinDCX APIs only where supported; verify endpoint, symbols, intervals, formats, contract details, precision and limits.
- Desired fields: price, futures price, active instruments, OHLCV, 24h volume/change, liquidity, bid/ask, order book, funding, mark price, contract specifications, availability, min quantity and precision.
- Validate response, freshness, missing/duplicate candles, abnormal prices; retry/backoff, cache, handle rate limits and errors. No fabricated data; invalid feed => DATA ERROR/NO TRADE.
- Public futures data endpoints are used in this prototype. The documented futures candle resolutions include 5m and 60m; the app aggregates completed 5m candles to 15m. Check current official docs before depending on it.
- Official docs currently state futures trading is not available through public APIs. This build therefore has no live order execution, account API, or credential storage.

## Scanner universe
Candidate tickers: BTC, ETH, SOL, XRP, BNB, DOGE, ADA, LINK, AVAX, SUI, LTC, DOT, TRX, NEAR, APT, UNI, BCH, ETC, FIL, ATOM.
- Candidate list is not a guarantee of active futures. Runtime active-contract matching is required.
- Exclude unavailable/inactive, low liquidity, excessive spread, unsuitable volatility, unreliable data or strategy-incompatible contracts.
- Prioritize availability, liquidity, volume, spread, volatility, data reliability and strategy fit. Any universe change should be transparent/configurable.

## Primary strategy: Bollinger Bands Mean Reversion V1
- BB period 20, standard deviation 2; RSI 14; ADX 14; ATR 14.
- Primary 15m completed candles; context 1h completed candles. No repainting, look-ahead or future data.
- LONG mandatory: ADX < 20; at least one of prior two completed candles closed below lower BB; latest completed candle closes back above lower BB; RSI < 35; valid/current/complete feed; valid stop; net R:R >= 1.5 after fees/slippage; risk restrictions clear; liquidity/spread filters pass; no duplicate same-market/same-candle signal.
- SHORT mandatory: ADX < 20; at least one of prior two completed candles closed above upper BB; latest completed candle closes back below upper BB; RSI > 65; all same data/stop/net R:R/risk/liquidity/duplicate checks pass.
- Any failed mandatory rule prevents signal.
- Decision exactly one of LONG, SHORT, WAIT, NO TRADE for each coin.
- WAIT: potential setup, missing confirmation, unclosed candle or threshold approaching; explain missing conditions and do not imply entry permission.
- NO TRADE: unsuitable/invalid setup, trend, R:R, spread/liquidity, volatility, stale/missing data, risk limit, unavailable contract, missing indicators, failed rules; explain why.

## Trade-plan fields
For qualified signals: coin/pair, direction, timestamp, timeframe, entry and method, stop, target, R:R, position size, estimated margin, max loss, risk %, leverage guidance, RSI/ADX/ATR/BB values, volume, regime, expiry, fees, slippage, explanation, passed conditions, warnings and freshness. Signals expire; reject unrealistic stale entry prices.

## Stop, target, risk, size
- LONG stop: relevant excursion low minus 0.2 ATR. SHORT stop: relevant excursion high plus 0.2 ATR. Define excursion/confirmation window; do not widen stop after entry.
- Target: BB middle/20-period mean. Compute gross/net profit, fees, slippage, stop distance and R:R. Reject if net R:R below 1.5; never move target artificially.
- Default risk per trade 0.25% equity; max daily loss 1% of starting daily equity; max 3 consecutive losses/day; max 1 simultaneous position; daily trade cap configurable.
- No martingale, averaging down, adding to losing positions, revenge trading, or sizing/leverage escalation. Risk engine is deterministic and cannot be overridden by AI.
- Size = maximum loss / stop distance per unit. Account for contract multiplier/specs, min quantity/precision, margin, leverage, fees, slippage, funding and exchange restrictions. Show maximum loss. Leverage is not a sizing substitute.

## Filters/regimes/timeframes/volume/BTC
- Filters: volume, spread, book liquidity when available, abnormal volatility, availability, funding, slippage, mark price, BTC condition, sudden movement. Reject unsuitable execution.
- Regimes: RANGING, TRENDING UP, TRENDING DOWN, HIGH VOLATILITY, LOW VOLATILITY, UNSTABLE, UNKNOWN; use measurable ADX plus EMA slope, ATR relative history, BB width, structure, volume, higher timeframe. Disable mean-reversion when unsuitable; unclear => NO TRADE.
- 15m entries; 1h context; optional future 4h. Do not fabricate higher-timeframe confirmation; disclose incomplete data.
- Volume inputs: current, average, spike, abnormal, relative, confirmation volume; configurable. Volume cannot override mandatory rules or be called buy/sell pressure without supporting data.
- BTC risk: volatility, trend, abrupt moves, alt correlation, liquidation events where reliable; optionally block alt trades with transparent deterministic rule.
- News/event filter: macro announcements, Fed, inflation, crypto regulation, exchange/security incidents, blockchain events. If unavailable, display **NEWS DATA UNAVAILABLE**. Not mandatory unless configured.

## Scanner/dashboard/ranking/explanation/confidence
- Scanner dashboard: total/active, LONG/SHORT/WAIT/NO TRADE, errors, timestamp, qualified setups, regime, health. Expandable details: price, change, volume, RSI/ADX/ATR/BB, regime, decision/reasons, entry/stop/target/R:R/risk/data time.
- Ranking factors: liquidity, spread, R:R, setup completeness, confirmation candle, volume, stability, freshness. Mandatory rules cannot be overridden; never auto-open every signal; max one position.
- Explanation layer: simple English based only on computed data; explain price/indicators/regime/entry/stop/target/risks. WAIT explains passed/missing/change condition; NO TRADE explains failed/unsuitable and potential change. No fabricated rationale.
- Quality score is measurable and is **not** win probability; no “90% chance” without statistical validation. Mandatory rules remain mandatory.

## Notifications, history, audit
- Optional notifications: new LONG/SHORT, expiry, stop/target, daily/consecutive risk limits, API/data/scanner failures and risk shutdown; deduplicate; include coin, decision, timestamp and reason.
- Store each evaluation: time, pair, price, indicators, regime, decision, passed/failed conditions, plan, R:R, expiry, quality, data quality, strategy version.
- Execution history if future execution exists: order ID, request/fill price, quantity, fees, slippage, status, exit reason, realized P/L. Export history.

## Backtesting
Historical OHLCV, indicator calculation, realistic signal timing, next-candle execution assumptions, fees, slippage, funding, sizing, stop/target, daily limits, loss streaks, no look-ahead/repainting/future leakage. Report trade count, win rate, gross/net P&L, profit factor, drawdown, avg win/loss, R:R, expectancy, costs, funding, loss streaks, long/short, coin and regime breakdown. Separate train/test periods; avoid overfitting; do not claim profitability without evidence.

## Paper trading
Use real market data; simulate fills, fees, slippage, positions, equity, risk, limits, signals and reports. Label PAPER TRADING clearly. It must not pretend to execute real orders.

## Real execution (future, separately authorized)
- Not enabled. Before implementation, verify official order endpoints, permissions, order types, position/margin modes, leverage limits, quantity precision/minimums, stops/targets, cancel/close, rate limits.
- Never assume public data API can execute orders. No withdrawal permissions. Secrets only in environment/secure storage, never code/log/frontend/screenshots/errors/repository.
- Emergency shutdown, position/order verification, duplicate prevention, API failure protection, execution monitoring, stop verification, daily loss protection. No order success claim without exchange confirmation.

## Security/architecture/UI/error handling/testing/development
- Secure architecture: secret management, validation, rate limiting, safe logs, authentication for public deployment, safe permissions. Public market data should not need credentials.
- Modular services: market data, universe, indicators, strategy, regime, liquidity, risk, signals, ranking, scanner, explanations, notifications, history, backtest, paper, execution (future), dashboard, config.
- AI cannot override deterministic engine.
- Pages: Dashboard, Scanner, Signal Details, Market Analysis, Strategy Config, Risk, Backtest, Paper, History, Settings, API status. Premium clean responsive mobile/desktop UI; readable state colors.
- Handle internet/API/rate-limit/response/candle/indicator/database/calculation/exchange/crash errors. Critical failure disables signals.
- Automated tests: indicators, BB/RSI/ADX/ATR, LONG/SHORT/WAIT/NO TRADE, stops/targets/sizing/R:R/daily limits/duplicates/data validation/API failures/expiry/edge cases. Invalid setups never signal.
- Inspect existing code before upgrades; preserve working functions; don't replace real data with mock without labeling; don't claim integrations/deployments/profitability; no placeholder buttons; fix bugs; clean modular code; README, dependencies, sample env, tests and startup instructions.

## Future upgrades (independent evaluation)
Additional strategies; regime selection; strategy comparisons; advanced liquidity; liquidation data; funding; orderbook imbalance; multi-timeframe; BTC correlation; news sentiment; AI explanations; optimization; automation; portfolio risk; analytics. Add only when data reliable and value measurable.

## Operating principles
Never fabricate data/signals; never force trades; never ignore failed rules or risk controls; never promise profit; never use future data/repainting; never silently alter strategy; never hide API failure; never claim unconfirmed execution; never expose secrets; explain decisions; respect NO TRADE; prioritize capital preservation, accuracy, transparency, testing; live trading requires explicit authorization.

## Status in this ZIP
**Implemented in prototype:** Streamlit app shell, candidate list, public CoinDCX active-instrument/current-price/futures-candle retrieval, 5m-to-completed-15m aggregation, 1h candle retrieval, BB/RSI/ADX/ATR calculations, core rule checks, simple stop/target/R:R sizing estimate, risk controls for analysis, scan CSV export, demo mode, offline unit tests, README and deployment instructions.

**Partial / not complete:** ticker-to-contract matching, freshness checks, liquidity/spread filters, higher-timeframe regime checks, opportunity scoring, signal expiry tracking, audit persistence, notifications, BTC correlation, volume quality filters, market-wide risk detection, detailed contract constraints.

**Not implemented:** production-grade backtesting, paper-trade simulator, persistent trade history, news/event feed, account balance integration, authenticated order execution, full API health/rate-limit/backoff/cache strategy, portfolio tracking, real exchange order verification.

**Tested here:** Python compilation and 3 offline unit tests. No live CoinDCX API test, Streamlit deployment test, or trading profitability test was performed. See README.

## V2 implementation notes (2026-11-23)
- Exact base-symbol matching is used for candidate markets; ticker substring matches are rejected.
- Public futures orderbook is used to estimate bid/ask spread. Signal approval is blocked when spread cannot be measured or exceeds the configured threshold.
- OHLCV values are validated; complete 15-minute aggregates require three 5-minute bars; gaps in the candle series are rejected.
- Ticker and completed-candle freshness checks are applied.
- Scanner results distinguish `DATA ERROR` status from strategy `NO TRADE` decisions.
- Daily realized loss and consecutive-loss input values are passed to the deterministic risk gate.
- Indicator RSI edge cases are covered by tests.
- The app remains analysis-only; backtesting, persistent paper trading, order execution, funding-aware sizing, contract precision and other future features remain unimplemented.
