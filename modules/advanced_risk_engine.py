
import pandas as pd

def dynamic_haircut(volatility_pct, liquidity_score, event_risk=False):
    base = 15
    vol_penalty = volatility_pct * 1.5
    liq_penalty = (100 - liquidity_score) * 0.1
    event_penalty = 10 if event_risk else 0
    return round(base + vol_penalty + liq_penalty + event_penalty, 2)

def trading_book_var(position_value, volatility_pct, confidence=0.99):
    z = 2.33 if confidence >= 0.99 else 1.65
    return round(position_value * (volatility_pct/100) * z, 2)

def stress_loss(position_value, shock_pct):
    return round(position_value * abs(shock_pct)/100, 2)

def build_competitor_snapshot():
    return pd.DataFrame([
        ["SSI", 10.8, 26500, 18.5],
        ["VND", 7.2, 18200, 14.1],
        ["HCM", 5.8, 12100, 11.8],
        ["MBS", 5.2, 9800, 10.3],
        ["SHS", 4.4, 8700, 9.5],
    ], columns=["Company","MarketSharePct","MarginBalanceBn","ROE"])
