
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
        alerts.append("Tỷ lệ sử dụng hạn mức margin đang tiến sát/ngưỡng khẩu vị rủi ro được phê duyệt.")
    if snapshot["liquidity_buffer_x"] < 2.0:
        alerts.append("Đệm thanh khoản thấp hơn ngưỡng an toàn nội bộ, cần rà soát nguồn vốn dự phòng.")
    if snapshot["single_stock_exposure_pct"] >= 15:
        alerts.append("Tập trung tài sản bảo đảm vào một mã cổ phiếu ở mức cao, cần rà soát haircut và hạn mức mã.")
    if snapshot["top10_client_exposure_pct"] >= 25:
        alerts.append("Dư nợ top 10 khách hàng cho thấy rủi ro tập trung gia tăng.")
    if snapshot["compliance_breaches"] > 3:
        alerts.append("Ngoại lệ tuân thủ tăng, cần theo dõi khắc phục và báo cáo escalation.")
    if not alerts:
        alerts.append("Chưa ghi nhận cảnh báo rủi ro trọng yếu theo ngưỡng hiện tại.")
    return alerts


def assess_risk_appetite(df):
    out = df.copy()
    statuses = []
    utilizations = []
    for _, r in out.iterrows():
        direction = str(r["direction"]).lower()
        cur = float(r["current_value"])
        lim = float(r["approved_limit"])
        if "higher" in direction:
            utilization = lim / cur * 100 if cur else 999
            status = "Green" if cur >= lim * 1.20 else ("Yellow" if cur >= lim else "Red")
        else:
            utilization = cur / lim * 100 if lim else 0
            status = "Green" if utilization < 75 else ("Yellow" if utilization < 95 else "Red")
        utilizations.append(round(utilization, 1))
        statuses.append(status)
    out["utilization_pct"] = utilizations
    out["status"] = statuses
    return out


def force_sell_simulation(margin_df, market_shock_pct=-10, real_estate_shock_pct=None, low_liquidity_extra_haircut_pct=0):
    df = margin_df.copy()
    if real_estate_shock_pct is None:
        real_estate_shock_pct = market_shock_pct
    sector_shock = np.where(df["sector"].str.contains("Real Estate|Bất động", case=False, na=False), real_estate_shock_pct, market_shock_pct)
    liquidity_penalty = np.where(df.get("liquidity_risk", "Medium").astype(str).str.lower().eq("high"), low_liquidity_extra_haircut_pct, 0)
    df["effective_shock_pct"] = sector_shock - liquidity_penalty
    df["stressed_collateral_value"] = df["collateral_value"] * (1 + df["effective_shock_pct"] / 100)
    df["stressed_ltv_pct"] = df["loan_balance"] / df["stressed_collateral_value"] * 100
    df["collateral_shortfall"] = np.maximum(df["loan_balance"] - df["stressed_collateral_value"] * df["maintenance_ltv_pct"] / 100, 0)
    df["force_sell_flag"] = np.where(df["stressed_ltv_pct"] > df["maintenance_ltv_pct"], "Yes", "No")
    return df


def scenario_summary(stressed_df):
    forced = stressed_df[stressed_df["force_sell_flag"] == "Yes"]
    return {
        "accounts_at_risk": int(len(forced)),
        "estimated_forced_sell_value": float(forced["loan_balance"].sum()),
        "collateral_shortfall": float(stressed_df["collateral_shortfall"].sum()),
        "avg_stressed_ltv": float(stressed_df["stressed_ltv_pct"].mean()),
        "max_stressed_ltv": float(stressed_df["stressed_ltv_pct"].max()),
    }


def rule_based_recommendations(snapshot, risk_appetite, stressed, initiatives):
    recs = []
    if snapshot["margin_utilization_pct"] >= 80 and snapshot["market_volatility_pct"] >= 4:
        recs.append("Tạm giảm tốc phê duyệt margin mới, ưu tiên rà soát collateral thuộc nhóm biến động cao.")
    if snapshot["liquidity_buffer_x"] < 2.0:
        recs.append("Kích hoạt kế hoạch tăng nguồn vốn dự phòng và rà soát lịch thanh toán trong 30 ngày tới.")
    if (stressed["force_sell_flag"] == "Yes").sum() > 0:
        recs.append("Lập danh sách tài khoản có nguy cơ force-sell và yêu cầu bổ sung tài sản bảo đảm trước khi thị trường giảm sâu.")
    if (risk_appetite["status"] == "Red").any():
        red_names = ", ".join(risk_appetite.loc[risk_appetite["status"] == "Red", "risk_metric"].head(3))
        recs.append(f"Trình CEO/HĐQT phương án xử lý các ngưỡng khẩu vị rủi ro đang đỏ: {red_names}.")
    if (initiatives["health"] == "Red").any():
        recs.append("Escalate các sáng kiến chiến lược đang đỏ trong cuộc họp CEO Office/Risk & Strategy Committee gần nhất.")
    if not recs:
        recs.append("Duy trì trạng thái giám sát hiện tại; chưa cần kích hoạt biện pháp hạn chế tăng trưởng.")
    return recs
