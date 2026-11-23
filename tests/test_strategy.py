import pandas as pd
from src.trading.risk import position_size, risk_status
from src.trading.indicators import indicators

def test_position_size():
    p=position_size(1000,.25,100,98)
    assert p["risk_amount"] == 2.5
    assert p["units"] == 1.25

def test_risk_limit():
    assert risk_status(1000, 9, 0, 1, 3)["allowed"]
    assert not risk_status(1000, 10, 0, 1, 3)["allowed"]
    assert not risk_status(1000, 0, 3, 1, 3)["allowed"]

def test_indicator_columns():
    idx=pd.date_range("2025-01-01", periods=80, freq="15min", tz="UTC")
    close=pd.Series(range(100,180), index=idx, dtype=float)
    df=pd.DataFrame({"open":close-1,"high":close+1,"low":close-2,"close":close,"volume":100},index=idx)
    out=indicators(df)
    for c in ["bb_mid","bb_upper","bb_lower","rsi","adx","atr"]: assert c in out
