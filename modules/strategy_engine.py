import pandas as pd


def initiative_health(row):
    if row["progress_pct"] < row["expected_progress_pct"] - 15 or row["execution_risk"] == "High":
        return "Red"
    if row["progress_pct"] < row["expected_progress_pct"] - 5 or row["execution_risk"] == "Medium":
        return "Yellow"
    return "Green"


def summarize_initiatives(df):
    out = df.copy()
    out["health"] = out.apply(initiative_health, axis=1)
    return out


def board_narrative(risk_status, top_alerts, initiatives):
    red_count = (initiatives["health"] == "Red").sum()
    yellow_count = (initiatives["health"] == "Yellow").sum()
    return (
        f"Overall enterprise risk status is {risk_status}. "
        f"Key alerts include: {'; '.join(top_alerts[:3])}. "
        f"Strategic execution review identifies {red_count} red initiatives and {yellow_count} yellow initiatives. "
        "Management should focus on risk appetite discipline, margin concentration, liquidity buffer, and overdue transformation actions."
    )
