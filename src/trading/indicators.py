"""Indicator calculations. Uses closed-candle inputs and Wilder-style smoothing."""
import pandas as pd
import numpy as np

def _wilder(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

def indicators(df: pd.DataFrame) -> pd.DataFrame:
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing OHLCV columns: {sorted(required-set(df.columns))}")
    x = df.copy()
    close, high, low = x.close, x.high, x.low
    x["bb_mid"] = close.rolling(20, min_periods=20).mean()
    sd = close.rolling(20, min_periods=20).std(ddof=0)
    x["bb_upper"] = x.bb_mid + 2*sd
    x["bb_lower"] = x.bb_mid - 2*sd
    delta = close.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain, avg_loss = _wilder(gain, 14), _wilder(loss, 14)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    x["rsi"] = 100 - 100/(1+rs)
    x.loc[(avg_loss == 0) & (avg_gain > 0), "rsi"] = 100
    x.loc[(avg_gain == 0) & (avg_loss > 0), "rsi"] = 0
    x.loc[(avg_gain == 0) & (avg_loss == 0), "rsi"] = 50
    tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    x["atr"] = _wilder(tr, 14)
    up, down = high.diff(), -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    plus_di = 100*_wilder(plus_dm,14)/x.atr.replace(0,np.nan)
    minus_di = 100*_wilder(minus_dm,14)/x.atr.replace(0,np.nan)
    dx = 100*(plus_di-minus_di).abs()/(plus_di+minus_di).replace(0,np.nan)
    x["adx"] = _wilder(dx,14)
    x["vol_avg20"] = x.volume.rolling(20,min_periods=20).mean()
    x["bb_width"] = (x.bb_upper-x.bb_lower)/x.bb_mid.replace(0,np.nan)
    return x
