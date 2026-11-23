from dataclasses import dataclass

CANDIDATES = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "LINK", "AVAX", "SUI", "LTC", "DOT", "TRX", "NEAR", "APT", "UNI", "BCH", "ETC", "FIL", "ATOM"]

@dataclass
class Settings:
    risk_pct: float = 0.25
    daily_loss_pct: float = 1.0
    max_consecutive_losses: int = 3
    max_positions: int = 1
    min_rr: float = 1.5
    fee_pct_per_side: float = 0.05
    slippage_pct_per_side: float = 0.03
    spread_limit_pct: float = 0.15
    min_quote_volume: float = 0.0
    adx_limit: float = 20.0
    rsi_long: float = 35.0
    rsi_short: float = 65.0
    signal_expiry_minutes: int = 15
