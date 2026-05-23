import pandas as pd
import numpy as np


def traffic_light(value, yellow, red, high_is_bad=True):
    if pd.isna(value):
        return "Grey"
    if high_is_bad:
        if value >= red:
            return "Red"
        if value >= yellow:
            return "Yellow"
        return "Green"
    if value <= red:
        return "Red"
    if value <= yellow:
        return "Yellow"
    return "Green"


def latest_row(df, date_col="date"):
    if date_col in df.columns:
        return df.sort_values(date_col).iloc[-1]
    return df.iloc[-1]


def enterprise_risk_score(snapshot):
    weights = {
        "margin_utilization_pct": 0.25,
        "liquidity_buffer_x": 0.20,
        "top10_client_exposure_pct": 0.15,
        "single_stock_exposure_pct": 0.15,
        "compliance_breaches": 0.10,
        "market_volatility_pct": 0.15,
    }
    score = 0
    score += min(snapshot["margin_utilization_pct"] / 100, 1.2) * 100 * weights["margin_utilization_pct"]
    score += max(0, min((4 - snapshot["liquidity_buffer_x"]) / 4, 1.2)) * 100 * weights["liquidity_buffer_x"]
    score += min(snapshot["top10_client_exposure_pct"] / 35, 1.2) * 100 * weights["top10_client_exposure_pct"]
    score += min(snapshot["single_stock_exposure_pct"] / 20, 1.2) * 100 * weights["single_stock_exposure_pct"]
    score += min(snapshot["compliance_breaches"] / 8, 1.2) * 100 * weights["compliance_breaches"]
    score += min(snapshot["market_volatility_pct"] / 6, 1.2) * 100 * weights["market_volatility_pct"]
    return round(score, 1)


def status_from_score(score):
    if score >= 70:
        return "Red"
    if score >= 45:
        return "Yellow"
    return "Green"


def build_alerts(snapshot):
    alerts = []
    if snapshot["margin_utilization_pct"] >= 80:
        alerts.append("Margin utilization is approaching approved risk appetite limit.")
    if snapshot["liquidity_buffer_x"] < 2.0:
        alerts.append("Liquidity buffer is below internal comfort level.")
    if snapshot["single_stock_exposure_pct"] >= 15:
        alerts.append("Single-stock concentration requires immediate risk review.")
    if snapshot["top10_client_exposure_pct"] >= 25:
        alerts.append("Top-10 client exposure indicates elevated concentration risk.")
    if snapshot["compliance_breaches"] > 3:
        alerts.append("Compliance exceptions are increasing and require remediation tracking.")
    if not alerts:
        alerts.append("No critical enterprise risk alert based on current synthetic thresholds.")
    return alerts


def force_sell_simulation(margin_df, market_shock_pct):
    df = margin_df.copy()
    df["stressed_collateral_value"] = df["collateral_value"] * (1 + market_shock_pct / 100)
    df["stressed_ltv_pct"] = df["loan_balance"] / df["stressed_collateral_value"] * 100
    df["force_sell_flag"] = np.where(df["stressed_ltv_pct"] > df["maintenance_ltv_pct"], "Yes", "No")
    return df
