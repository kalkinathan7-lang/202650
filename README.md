# 202650 — Crypto Trading Intelligence V2

Streamlit analysis application for CoinDCX USDT futures market data. The build is analysis-only and does not place orders.

## V2 improvements
- Exact futures-symbol matching (no ticker substring selection)
- Public current-price, candle, and orderbook retrieval
- Orderbook-derived spread check; signal approval is blocked if spread is unavailable or above the configured limit
- OHLCV validation, duplicate removal, candle-completeness filtering, and gap rejection
- Stale ticker/candle checks
- RSI edge-case handling (flat series, zero-loss and zero-gain series)
- Condition-by-condition signal checks and data-error status
- Risk input for daily realized loss and consecutive losses
- Strict four decision states: LONG, SHORT, WAIT, NO TRADE
- Seven automated tests

## Run locally
1. Extract the ZIP.
2. Open a terminal in this folder.
3. `python -m pip install -r requirements.txt`
4. `streamlit run app.py`

## Deploy to Streamlit Cloud
- Push the project files to a GitHub repository.
- Select `app.py` as the main file.
- Streamlit Cloud installs dependencies from `requirements.txt`.

## Modes
- **Live public CoinDCX data:** fetches public futures data, exact active symbols, current prices, candle history, and orderbook.
- **Synthetic demo data:** artificial data for UI/testing only; never treat it as a market signal.

## Safety / limitations
- This is market analysis, not order execution. CoinDCX's official documentation currently says futures execution is not available through public APIs.
- No private account balances, actual fills, contract-aware quantity rounding, funding costs, news/event feed, persistent audit database, backtesting engine, paper trading engine, or BTC-correlation risk block are implemented in this build.
- A spread/orderbook API failure blocks signal approval. A missing or stale market feed is reported as DATA ERROR and cannot create a signal.
- Quality score is not a win probability.
- All signals expire conceptually after the configured interval; automated expiry monitoring is not yet implemented.
- API behavior and availability can change. Live endpoint connectivity was not tested during packaging.

## Tests
Run: `python -m pytest -q`

## Files
- `app.py`: Streamlit interface
- `src/trading/data.py`: CoinDCX public data client and validation
- `src/trading/indicators.py`: BB, RSI, ADX, ATR calculations
- `src/trading/strategy.py`: deterministic strategy and signal validation
- `src/trading/config.py`: candidate universe and configuration
- `src/trading/risk.py`: risk helpers
- `src/trading/demo.py`: synthetic demo candle generator
- `tests/`: automated tests
- `PROJECT_SPECIFICATION.md`: full original project scope
