import pandas as pd
import numpy as np

def indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    close, high, low = x.close, x.high, x.low
    x["bb_mid"] = close.rolling(20, min_periods=20).mean()
    sd = close.rolling(20, min_periods=20).std(ddof=0)
    x["bb_upper"] = x.bb_mid + 2*sd
    x["bb_lower"] = x.bb_mid - 2*sd
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    x["rsi"] = 100 - 100/(1+rs)
    tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    up, down = high.diff(), -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    atr = x.atr.replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean()/atr
    minus_di = 100 * minus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean()/atr
    dx = 100*(plus_di-minus_di).abs()/(plus_di+minus_di).replace(0,np.nan)
    x["adx"] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    x["vol_avg20"] = x.volume.rolling(20, min_periods=20).mean()
    x["bb_width"] = (x.bb_upper-x.bb_lower)/x.bb_mid
    return x
