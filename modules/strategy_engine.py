
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
    out["gap_pct"] = out["progress_pct"] - out["expected_progress_pct"]
    return out


def board_narrative(risk_status, top_alerts, initiatives, appetite=None, stress=None):
    red_count = int((initiatives["health"] == "Red").sum())
    yellow_count = int((initiatives["health"] == "Yellow").sum())
    red_appetite = int((appetite["status"] == "Red").sum()) if appetite is not None else 0
    forced_accounts = int(stress.get("accounts_at_risk", 0)) if stress else 0
    return (
        f"Trạng thái rủi ro tổng thể hiện ở mức {risk_status}. "
        f"Các cảnh báo chính gồm: {'; '.join(top_alerts[:3])}. "
        f"Khẩu vị rủi ro có {red_appetite} chỉ tiêu vượt ngưỡng đỏ. "
        f"Stress test margin ghi nhận {forced_accounts} tài khoản có nguy cơ force-sell trong kịch bản hiện tại. "
        f"Rà soát thực thi chiến lược xác định {red_count} sáng kiến đỏ và {yellow_count} sáng kiến vàng. "
        "Ban lãnh đạo nên ưu tiên kỷ luật khẩu vị rủi ro, kiểm soát tập trung margin, duy trì đệm thanh khoản và xử lý các điểm nghẽn chiến lược."
    )
