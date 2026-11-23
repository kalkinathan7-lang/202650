import numpy as np, pandas as pd

def demo_candles(seed=7, periods=240, freq="15min"):
    rng=np.random.default_rng(seed); t=pd.date_range(end=pd.Timestamp.now(tz="UTC").floor(freq), periods=periods, freq=freq)
    close=100+np.cumsum(rng.normal(0,.45,periods)); op=np.r_[close[0],close[:-1]]
    high=np.maximum(op,close)+rng.uniform(.05,.4,periods); low=np.minimum(op,close)-rng.uniform(.05,.4,periods)
    return pd.DataFrame({"open":op,"high":high,"low":low,"close":close,"volume":rng.uniform(1000,5000,periods)},index=t)
