def risk_status(equity: float, daily_loss: float, consecutive_losses: int, daily_loss_pct: float, max_consecutive: int):
    max_loss = equity * daily_loss_pct / 100
    return {"allowed": daily_loss < max_loss and consecutive_losses < max_consecutive, "daily_loss_limit": max_loss, "daily_loss_remaining": max(0, max_loss-daily_loss), "reason": "Risk limits clear" if daily_loss < max_loss and consecutive_losses < max_consecutive else "Daily loss or consecutive-loss limit reached"}

def position_size(equity: float, risk_pct: float, entry: float, stop: float):
    distance=abs(entry-stop)
    if distance <= 0: raise ValueError("Stop distance must be positive")
    risk=equity*risk_pct/100
    return {"risk_amount":risk,"units":risk/distance,"notional":risk/distance*entry}
