import pandas as pd
from src.trading.risk import position_size, risk_status
from src.trading.indicators import indicators
from src.trading.data import CoinDCXPublic
from src.trading.strategy import analyze
from src.trading.config import Settings


def test_position_size():
    p=position_size(1000,.25,100,98)
    assert p["risk_amount"] == 2.5
    assert p["units"] == 1.25


def test_risk_limit():
    assert risk_status(1000,9,0,1,3)["allowed"]
    assert not risk_status(1000,10,0,1,3)["allowed"]
    assert not risk_status(1000,0,3,1,3)["allowed"]


def test_indicator_columns_and_flat_rsi():
    idx=pd.date_range("2025-01-01", periods=80, freq="15min", tz="UTC")
    close=pd.Series(range(100,180), index=idx, dtype=float)
    df=pd.DataFrame({"open":close-1,"high":close+1,"low":close-2,"close":close,"volume":100},index=idx)
    out=indicators(df)
    for c in ["bb_mid","bb_upper","bb_lower","rsi","adx","atr"]: assert c in out
    flat=df.copy(); flat[["open","high","low","close"]]=100
    assert indicators(flat).rsi.iloc[-1] == 50


def test_exact_symbol_mapping_prevents_substring_mismatch():
    api=CoinDCXPublic()
    instruments=["B-SOL_USDT","B-1000SHIB_USDT","B-SOLX_USDT","B-BTC_USDT"]
    prices={pair:{} for pair in instruments}
    assert api.map_candidates(instruments,["SOL","SHIB","BTC"],prices)=={"SOL":"B-SOL_USDT","BTC":"B-BTC_USDT"}


def test_stale_tick_detected():
    assert CoinDCXPublic.tick_is_stale(None)
    assert CoinDCXPublic.tick_is_stale(0)


def test_data_error_never_generates_signal():
    result=analyze("B-BTC_USDT",None,None,100,Settings(),data_error="API down")
    assert result["decision"] == "NO TRADE"
    assert result["status"] == "DATA ERROR"


def test_missing_spread_blocks_signal():
    idx=pd.date_range("2025-01-01",periods=100,freq="15min",tz="UTC")
    close=pd.Series(100+pd.Series(range(100),index=idx).astype(float),index=idx)
    df=pd.DataFrame({"open":close,"high":close+1,"low":close-1,"close":close,"volume":100},index=idx)
    result=analyze("B-BTC_USDT",df,df,100,Settings(),spread_pct=None)
    assert result["decision"] == "NO TRADE"
    assert "Spread data unavailable" in result["reason"]
