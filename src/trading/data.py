import time
import requests
import pandas as pd
from typing import Any

BASE = "https://api.coindcx.com"
PUBLIC = "https://public.coindcx.com"
TIMEOUT = 12

class DataError(RuntimeError): pass

class CoinDCXPublic:
    def __init__(self): self.session = requests.Session()

    def get_json(self, url: str, params: dict | None = None):
        r = self.session.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    def active_instruments(self):
        url = f"{BASE}/exchange/v1/derivatives/futures/data/active_instruments"
        data = self.get_json(url, params={"margin_currency_short_name[]": "USDT"})
        if not isinstance(data, list): raise DataError("Unexpected active-instruments response")
        return data

    def current_prices(self):
        data = self.get_json(f"{PUBLIC}/market_data/v3/current_prices/futures/rt")
        if not isinstance(data, dict) or not isinstance(data.get("prices"), dict): raise DataError("Unexpected futures current-prices response")
        return data

    def candles(self, pair: str, resolution: str, minutes: int = 300):
        now = int(time.time())
        params = {"pair": pair, "from": now - minutes*60, "to": now, "resolution": resolution, "pcode": "f"}
        data = self.get_json(f"{PUBLIC}/market_data/candlesticks", params=params)
        if isinstance(data, dict):
            if data.get("s") not in (None, "ok"): raise DataError(f"Candle API status: {data.get('s')}")
            data = data.get("data", [])
        if not isinstance(data, list) or not data: raise DataError("No candle data returned")
        df = pd.DataFrame(data)
        required = {"open", "high", "low", "close", "volume", "time"}
        if not required.issubset(df.columns): raise DataError("Candle response missing required fields")
        df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
        for c in ["open", "high", "low", "close", "volume"]: df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna().sort_values("time").drop_duplicates("time").set_index("time")
        return df

    def candles_15m(self, pair: str, lookback_minutes: int = 1800):
        # Official futures REST docs list 5m, 1h and 1D. Build 15m from 5m bars.
        five = self.candles(pair, "5", lookback_minutes)
        agg = five.resample("15min", label="left", closed="left").agg({"open":"first", "high":"max", "low":"min", "close":"last", "volume":"sum"}).dropna()
        # Keep only candles whose full 15-minute window has elapsed.
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=15)
        return agg[agg.index + pd.Timedelta(minutes=15) <= cutoff]

    def candles_1h(self, pair: str, lookback_minutes: int = 3600):
        df = self.candles(pair, "60", lookback_minutes)
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=1)
        return df[df.index + pd.Timedelta(hours=1) <= cutoff]
