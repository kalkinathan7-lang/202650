"""CoinDCX public futures data client with strict market and candle validation."""
from __future__ import annotations
import time
import requests
import pandas as pd
from typing import Any

BASE = "https://api.coindcx.com"
PUBLIC = "https://public.coindcx.com"
TIMEOUT = 12

class DataError(RuntimeError):
    """Raised when exchange data cannot be safely used."""

class CoinDCXPublic:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "202650-Trading-Intelligence/2.0"})

    def get_json(self, url: str, params: dict | None = None):
        last_error = None
        for attempt in range(3):
            try:
                response = self.session.get(url, params=params, timeout=TIMEOUT)
                if response.status_code == 429:
                    raise DataError("CoinDCX rate limit reached (HTTP 429). Retry later.")
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
        raise DataError(f"Request failed after retries: {last_error}")

    def active_instruments(self):
        data = self.get_json(f"{BASE}/exchange/v1/derivatives/futures/data/active_instruments", params={"margin_currency_short_name[]": "USDT"})
        if not isinstance(data, list):
            raise DataError("Unexpected active-instruments response")
        return [x for x in data if isinstance(x, str) and x.endswith("_USDT") and x.startswith("B-")]

    def current_prices(self):
        data = self.get_json(f"{PUBLIC}/market_data/v3/current_prices/futures/rt")
        if not isinstance(data, dict) or not isinstance(data.get("prices"), dict):
            raise DataError("Unexpected futures current-prices response")
        return data

    @staticmethod
    def base_ticker(pair: str) -> str:
        """Extract exact contract base from B-BASE_USDT; do not substring-match."""
        if not isinstance(pair, str) or not pair.startswith("B-") or not pair.endswith("_USDT"):
            return ""
        return pair[2:-5]

    def map_candidates(self, instruments: list[str], candidates: list[str], price_map: dict) -> dict[str, str]:
        by_base = {}
        for pair in instruments:
            base = self.base_ticker(pair)
            if base and pair in price_map:
                by_base.setdefault(base, pair)
        return {ticker: by_base[ticker] for ticker in candidates if ticker in by_base}

    def orderbook(self, pair: str, depth: int = 20):
        if depth not in (10, 20, 50):
            raise ValueError("Orderbook depth must be 10, 20 or 50")
        data = self.get_json(f"{PUBLIC}/market_data/v3/orderbook/{pair}-futures/{depth}")
        if not isinstance(data, dict) or not isinstance(data.get("bids"), dict) or not isinstance(data.get("asks"), dict):
            raise DataError("Unexpected orderbook response")
        bids = [(float(p), float(q)) for p, q in data["bids"].items() if float(p) > 0 and float(q) > 0]
        asks = [(float(p), float(q)) for p, q in data["asks"].items() if float(p) > 0 and float(q) > 0]
        if not bids or not asks:
            raise DataError("Orderbook has no valid bid/ask levels")
        bid, ask = max(p for p, _ in bids), min(p for p, _ in asks)
        if ask <= bid:
            raise DataError("Orderbook is crossed or invalid")
        mid = (bid + ask) / 2
        return {"best_bid": bid, "best_ask": ask, "spread_pct": (ask-bid)/mid*100,
                "bid_depth": sum(q for _, q in bids), "ask_depth": sum(q for _, q in asks),
                "timestamp_ms": data.get("ts")}

    def candles(self, pair: str, resolution: str, minutes: int = 3000):
        now = int(time.time())
        params = {"pair": pair, "from": now-minutes*60, "to": now, "resolution": resolution, "pcode": "f"}
        data = self.get_json(f"{PUBLIC}/market_data/candlesticks", params=params)
        if isinstance(data, dict):
            if data.get("s") not in (None, "ok"):
                raise DataError(f"Candle API status: {data.get('s')}")
            data = data.get("data", [])
        if not isinstance(data, list) or not data:
            raise DataError("No candle data returned")
        df = pd.DataFrame(data)
        required = {"open", "high", "low", "close", "volume", "time"}
        if not required.issubset(df.columns):
            raise DataError(f"Candle response missing fields: {sorted(required-set(df.columns))}")
        df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna().sort_values("time").drop_duplicates("time").set_index("time")
        if (df[["open", "high", "low", "close"]] <= 0).any().any() or (df.volume < 0).any():
            raise DataError("Candle data contains invalid prices or volume")
        if (df.high < df[["open", "close", "low"]].max(axis=1)).any() or (df.low > df[["open", "close", "high"]].min(axis=1)).any():
            raise DataError("Candle OHLC consistency validation failed")
        return df

    def candles_15m(self, pair: str, lookback_minutes: int = 3000):
        five = self.candles(pair, "5", lookback_minutes)
        agg = five.resample("15min", label="left", closed="left").agg({"open":"first", "high":"max", "low":"min", "close":"last", "volume":"sum"})
        counts = five["close"].resample("15min", label="left", closed="left").count()
        agg = agg[counts == 3].dropna()
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=15)
        agg = agg[agg.index + pd.Timedelta(minutes=15) <= cutoff]
        if len(agg) >= 2:
            gaps = agg.index.to_series().diff().dropna()
            if (gaps > pd.Timedelta(minutes=30)).any():
                raise DataError("15-minute candle history contains gaps; refusing to analyze incomplete history")
        return agg

    def candles_1h(self, pair: str, lookback_minutes: int = 6000):
        df = self.candles(pair, "60", lookback_minutes)
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=1)
        df = df[df.index + pd.Timedelta(hours=1) <= cutoff]
        if len(df) >= 2 and (df.index.to_series().diff().dropna() > pd.Timedelta(hours=2)).any():
            raise DataError("Hourly candle history contains gaps")
        return df

    @staticmethod
    def timestamp_to_seconds(timestamp: Any) -> float | None:
        """Normalize common Unix timestamp units (s, ms, us, ns) to seconds.

        CoinDCX payload fields can differ in naming and unit. Magnitude-based
        normalization avoids treating a valid millisecond timestamp as stale
        or a nanosecond timestamp as a far-future value.
        """
        if timestamp is None:
            return None
        try:
            # Accept ISO-8601 strings as well as numeric epoch values.
            if isinstance(timestamp, str) and not timestamp.strip().replace(".", "", 1).isdigit():
                parsed = pd.Timestamp(timestamp)
                if parsed.tzinfo is None:
                    parsed = parsed.tz_localize("UTC")
                return float(parsed.timestamp())

            value = float(timestamp)
            if not pd.notna(value) or value <= 0:
                return None
            magnitude = abs(value)
            if magnitude >= 1e17:       # nanoseconds
                return value / 1_000_000_000
            if magnitude >= 1e14:       # microseconds
                return value / 1_000_000
            if magnitude >= 1e11:       # milliseconds
                return value / 1_000
            if magnitude >= 1e9:        # seconds
                return value
            return None
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def tick_is_stale(timestamp: Any, max_age_seconds: int = 120) -> bool:
        epoch_seconds = CoinDCXPublic.timestamp_to_seconds(timestamp)
        if epoch_seconds is None:
            return True
        age = time.time() - epoch_seconds
        return age < -30 or age > max_age_seconds
