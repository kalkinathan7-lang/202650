from __future__ import annotations
import math
import pandas as pd
from .config import Settings
from .indicators import indicators

STATES = ("LONG", "SHORT", "WAIT", "NO TRADE")

def analyze(pair: str, df15: pd.DataFrame, df1h: pd.DataFrame | None, price: float, settings: Settings,
            equity: float = 1000.0, daily_loss: float = 0.0, consecutive_losses: int = 0,
            spread_pct: float | None = None, stale: bool = False, data_error: str | None = None,
            orderbook: dict | None = None):
    result = {"pair": pair, "decision": "NO TRADE", "reason": "", "conditions": {}, "trade_plan": None,
              "quality_score": 0, "market_regime": "UNKNOWN", "status": "OK", "warnings": []}
    if data_error:
        result.update(status="DATA ERROR", reason=data_error)
        return result
    if stale or df15 is None or len(df15) < 50 or not math.isfinite(price) or price <= 0:
        result.update(status="DATA ERROR", reason="Market data is stale, missing, or insufficient for indicator warm-up.")
        return result
    try:
        x = indicators(df15)
    except Exception as exc:
        result.update(status="DATA ERROR", reason=f"Indicator calculation failed: {exc}")
        return result
    required = ["bb_mid", "bb_upper", "bb_lower", "rsi", "adx", "atr"]
    c = x.iloc[-1]
    if any(pd.isna(c[k]) for k in required) or not math.isfinite(float(c.atr)) or c.atr <= 0:
        result.update(status="DATA ERROR", reason="Latest completed candle has missing or invalid indicator values.")
        return
    previous = x.iloc[-3:-1]
    if len(previous) != 2:
        result.update(status="DATA ERROR", reason="Insufficient prior candles for excursion check.")
        return
    long_excursion = bool((previous.close < previous.bb_lower).any())
    short_excursion = bool((previous.close > previous.bb_upper).any())
    # Orderbook-derived spread is mandatory for signal approval; unavailable means no signal.
    checks = {
        "adx_below_20": bool(c.adx < settings.adx_limit),
        "long_band_excursion_previous_2": long_excursion,
        "long_confirmation_close_above_lower_band": bool(c.close > c.bb_lower),
        "long_rsi_below_threshold": bool(c.rsi < settings.rsi_long),
        "short_band_excursion_previous_2": short_excursion,
        "short_confirmation_close_below_upper_band": bool(c.close < c.bb_upper),
        "short_rsi_above_threshold": bool(c.rsi > settings.rsi_short),
        "spread_measured": spread_pct is not None,
        "spread_within_limit": spread_pct is not None and spread_pct <= settings.spread_limit_pct,
        "risk_limits_clear": daily_loss < equity*settings.daily_loss_pct/100 and consecutive_losses < settings.max_consecutive_losses,
        "higher_timeframe_available": df1h is not None and len(df1h) >= 20,
    }
    result["conditions"] = checks
    result["metrics"] = {k: float(c[k]) if pd.notna(c[k]) else None for k in ["close","rsi","adx","atr","bb_mid","bb_upper","bb_lower","volume","vol_avg20","bb_width"]}
    result["spread_pct"] = spread_pct
    result["market_regime"] = "RANGING" if c.adx < settings.adx_limit else "TRENDING"
    if df1h is None or len(df1h) < 20:
        result["warnings"].append("1-hour context unavailable or incomplete; no higher-timeframe confirmation claimed.")
    if orderbook is None:
        result["warnings"].append("Order-book liquidity data unavailable; signal approval blocked.")
    if not checks["risk_limits_clear"]:
        result["reason"] = "Risk restriction active: daily loss or consecutive-loss limit reached."
        return result
    if spread_pct is None:
        result.update(status="DATA ERROR", reason="Spread data unavailable; refusing to approve a signal without execution-cost screening.")
        return result
    if not checks["spread_within_limit"]:
        result["reason"] = f"Spread {spread_pct:.4f}% exceeds configured limit {settings.spread_limit_pct:.4f}%."
        return result
    if not checks["adx_below_20"]:
        result["reason"] = f"ADX {c.adx:.2f} is at or above {settings.adx_limit:.2f}; mean-reversion strategy disabled."
        return result
    direction = None
    long_valid = long_excursion and checks["long_confirmation_close_above_lower_band"] and checks["long_rsi_below_threshold"]
    short_valid = short_excursion and checks["short_confirmation_close_below_upper_band"] and checks["short_rsi_above_threshold"]
    if long_valid: direction = "LONG"
    elif short_valid: direction = "SHORT"
    elif long_excursion and not checks["long_confirmation_close_above_lower_band"]:
        result.update(decision="WAIT", reason="Lower-band excursion occurred; waiting for a completed candle to close back above the lower band.")
        return result
    elif short_excursion and not checks["short_confirmation_close_below_upper_band"]:
        result.update(decision="WAIT", reason="Upper-band excursion occurred; waiting for a completed candle to close back below the upper band.")
        return result
    else:
        result["reason"] = "Mandatory Bollinger Band excursion, re-entry, and RSI confirmation conditions are not all satisfied."
        return result
    excursion_window = x.iloc[-3:]  # two excursion candidates plus the confirmation candle
    if direction == "LONG":
        entry = float(price); stop = float(excursion_window.low.min() - .2*c.atr); target = float(c.bb_mid)
        if not stop < entry < target:
            result["reason"] = "Long stop/target geometry invalid; target is not above entry or stop is not below entry."
            return result
    else:
        entry = float(price); stop = float(excursion_window.high.max() + .2*c.atr); target = float(c.bb_mid)
        if not target < entry < stop:
            result["reason"] = "Short stop/target geometry invalid; target is not below entry or stop is not above entry."
            return result
    distance = abs(entry-stop)
    if distance <= 0:
        result["reason"] = "Stop-loss distance is zero or invalid."
        return result
    cost_per_unit = entry*2*(settings.fee_pct_per_side+settings.slippage_pct_per_side)/100
    net_reward = abs(target-entry)-cost_per_unit
    net_risk = distance+cost_per_unit
    rr = net_reward/net_risk if net_risk > 0 else 0
    if rr < settings.min_rr:
        result["reason"] = f"Net reward-to-risk {rr:.2f} is below required {settings.min_rr:.2f}; target not adjusted."
        return result
    risk_amount = equity*settings.risk_pct/100
    qty = risk_amount/distance
    result.update(decision=direction, reason="All deterministic strategy conditions passed; spread and risk checks passed.",
                  quality_score=score(checks, rr, spread_pct), trade_plan={
        "entry": entry, "entry_method": "Reference price; confirm executable price before any manual trade",
        "stop_loss": stop, "take_profit": target, "reward_to_risk": rr,
        "position_size_units": qty, "estimated_notional": qty*entry,
        "estimated_margin_at_1x": qty*entry, "max_loss_before_costs": qty*distance,
        "risk_pct_equity": settings.risk_pct, "leverage": "Not calculated; leverage is not a substitute for risk sizing",
        "estimated_round_trip_cost_per_unit": cost_per_unit, "signal_validity_minutes": settings.signal_expiry_minutes,
        "timestamp": str(df15.index[-1]), "atr": float(c.atr), "rsi": float(c.rsi), "adx": float(c.adx),
        "bb_lower": float(c.bb_lower), "bb_mid": float(c.bb_mid), "bb_upper": float(c.bb_upper), "volume": float(c.volume),
        "estimated_gross_reward_per_unit": abs(target-entry), "estimated_net_reward_per_unit": net_reward,
        "estimated_net_risk_per_unit": net_risk, "warnings": ["Analysis only; not an executable order.", "Contract multiplier, exchange quantity precision, funding and margin constraints are not verified."]})
    return result

def score(checks, rr, spread):
    passed = sum(bool(v) for v in checks.values())
    return max(0, min(100, int(50 + passed*3 + min(rr,3)*5 - (spread or 0)*10)))
