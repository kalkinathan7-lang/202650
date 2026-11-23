from dataclasses import asdict
import math
import pandas as pd
from .config import Settings
from .indicators import indicators

STATES = ("LONG", "SHORT", "WAIT", "NO TRADE")

def analyze(pair: str, df15: pd.DataFrame, df1h: pd.DataFrame | None, price: float, settings: Settings, equity: float = 1000.0, daily_loss: float = 0.0, consecutive_losses: int = 0, spread_pct: float | None = None, stale: bool = False):
    result = {"pair": pair, "decision": "NO TRADE", "reason": "", "conditions": {}, "trade_plan": None, "quality_score": 0, "market_regime": "UNKNOWN"}
    if stale or df15 is None or len(df15) < 40:
        result["reason"] = "Market data is stale, missing, or insufficient for indicator warm-up."; return result
    x = indicators(df15)
    if len(x) < 3 or x.iloc[-2:].isna().any().any():
        result["reason"] = "Required indicators are not available."; return result
    # Input is already completed candles, but use the latest row explicitly.
    c = x.iloc[-1]; prev2 = x.iloc[-3:-1]
    checks = {
        "adx_below_20": bool(c.adx < settings.adx_limit),
        "long_band_excursion": bool((prev2.close < prev2.bb_lower).any()),
        "long_reentry": bool(c.close > c.bb_lower),
        "long_rsi": bool(c.rsi < settings.rsi_long),
        "short_band_excursion": bool((prev2.close > prev2.bb_upper).any()),
        "short_reentry": bool(c.close < c.bb_upper),
        "short_rsi": bool(c.rsi > settings.rsi_short),
        "spread_ok": spread_pct is None or spread_pct <= settings.spread_limit_pct,
        "risk_ok": daily_loss < equity*settings.daily_loss_pct/100 and consecutive_losses < settings.max_consecutive_losses,
        "higher_tf_available": df1h is not None and len(df1h) >= 20,
    }
    result["conditions"] = checks
    result["market_regime"] = "RANGING" if c.adx < settings.adx_limit else "TRENDING"
    result["metrics"] = {k: float(c[k]) if pd.notna(c[k]) else None for k in ["close", "rsi", "adx", "atr", "bb_mid", "bb_upper", "bb_lower", "volume", "vol_avg20"]}
    if not checks["risk_ok"]: result["reason"] = "Risk limit is active."; return result
    if not checks["spread_ok"]: result["reason"] = "Spread exceeds configured limit."; return result
    if not checks["adx_below_20"]: result["reason"] = "ADX indicates a potentially strong trend; mean reversion disabled."; return result
    direction = None
    if checks["long_band_excursion"] and checks["long_reentry"] and checks["long_rsi"]: direction = "LONG"
    elif checks["short_band_excursion"] and checks["short_reentry"] and checks["short_rsi"]: direction = "SHORT"
    elif (checks["long_band_excursion"] or checks["short_band_excursion"]) and not (checks["long_reentry"] or checks["short_reentry"]):
        result["decision"] = "WAIT"; result["reason"] = "Band excursion detected; waiting for completed-candle re-entry confirmation."; return result
    else:
        result["reason"] = "Mandatory Bollinger/RSI confirmation conditions are not satisfied."; return result
    if not math.isfinite(float(c.atr)) or c.atr <= 0: result["reason"] = "ATR invalid; cannot calculate stop-loss."; return result
    excursion = df15.iloc[-3:-1]
    if direction == "LONG":
        entry = float(price); stop = float(excursion.low.min() - .2*c.atr); target = float(c.bb_mid)
        if not (stop < entry < target): result["reason"] = "Invalid long stop or target geometry."; return result
    else:
        entry = float(price); stop = float(excursion.high.max() + .2*c.atr); target = float(c.bb_mid)
        if not (target < entry < stop): result["reason"] = "Invalid short stop or target geometry."; return result
    risk_unit = abs(entry-stop); reward = abs(target-entry)
    costs = entry*(2*(settings.fee_pct_per_side+settings.slippage_pct_per_side)/100)
    net_reward = reward-costs; net_risk = risk_unit+costs
    rr = net_reward/net_risk if net_risk > 0 else 0
    if rr < settings.min_rr: result["reason"] = f"Net reward-to-risk {rr:.2f} is below minimum {settings.min_rr:.2f}."; return result
    max_loss = equity*settings.risk_pct/100
    qty = max_loss/risk_unit
    result.update(decision=direction, reason="All mandatory strategy checks passed.", quality_score=score(checks, rr, spread_pct), trade_plan={
        "entry": entry, "entry_method": "Market reference price; signal expires after configured interval", "stop_loss": stop, "take_profit": target,
        "reward_to_risk": rr, "position_size_units": qty, "estimated_notional": qty*entry, "estimated_margin_at_1x": qty*entry,
        "max_loss_before_costs": qty*risk_unit, "risk_pct_equity": settings.risk_pct, "leverage": "Not recommended/selected; use 1x for sizing reference",
        "estimated_round_trip_cost_per_unit": costs, "signal_validity_minutes": settings.signal_expiry_minutes,
        "timestamp": str(df15.index[-1]), "atr": float(c.atr), "rsi": float(c.rsi), "adx": float(c.adx),
        "bb_lower": float(c.bb_lower), "bb_mid": float(c.bb_mid), "bb_upper": float(c.bb_upper), "volume": float(c.volume),
        "warnings": ["Paper/analysis signal only; not an executable order.", "Higher timeframe is context only; incomplete/ unavailable context is disclosed."]})
    return result

def score(checks, rr, spread):
    passed = sum(bool(v) for v in checks.values())
    return max(0, min(100, int(50 + passed*3 + min(rr,3)*5 - (spread or 0)*10)))
