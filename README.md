# 202650 — Crypto Trading Intelligence

Streamlit application for CoinDCX futures market analysis using the Bollinger Bands Mean Reversion V1 specification. This project is **analysis-first**; it does not place live futures orders.

## Important API limitation
CoinDCX's public documentation currently states that futures trading is not available through Public APIs. This app therefore provides public market analysis and a clearly labelled paper-trading scaffold only. Do not add live execution or credentials to this build. CoinDCX futures candle resolutions documented include 1, 5, 60 and 1D; 15-minute candles are aggregated from completed 5-minute candles. Confirm this remains supported before relying on the data.

## Run locally
1. Install Python 3.10+.
2. `python -m venv .venv`
3. Activate it (Windows: `.venv\\Scripts\\activate`; macOS/Linux: `source .venv/bin/activate`).
4. `pip install -r requirements.txt`
5. `streamlit run app.py`

## Deploy on Streamlit Community Cloud
Push this folder to a GitHub repository. In Streamlit Cloud, create an app, choose the repository, branch, and `app.py` as the main file. No API secrets are needed for public market data.

## Modes
- **Live public data**: calls CoinDCX public endpoints. If an endpoint is unavailable, scanner reports data errors and does not signal.
- **Demo mode**: synthetic data for UI/testing only, clearly labelled; it must not be treated as market signals.

## Strategy
See `src/trading/strategy.py`. Uses completed candles only; mandatory strategy rules are deterministic. The system returns LONG/SHORT only if all checks pass, otherwise WAIT or NO TRADE. Strategy quality score is not a probability of profit.

## Tests
`pytest -q`

## Limitations / not verified
- No authenticated account access or live order execution.
- Fees, funding and slippage are configurable estimates, not account-specific values.
- Contract details and instrument naming can change. The app checks active instruments at runtime and displays data availability.
- Public API reachability and response shape depend on CoinDCX; this repository's tests are offline unit tests, not a live API certification.
- News integration is not included; the dashboard states NEWS DATA UNAVAILABLE.
