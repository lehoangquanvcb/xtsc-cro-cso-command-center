# XTSC CRO/CSO Enterprise Governance Platform

**Author: Le Hoang Quan**

Prototype Streamlit cho vai trò **Giám đốc Quản trị Rủi ro kiêm Chiến lược** tại Công ty Chứng khoán Xuân Thiện.

## Điểm mới v3

- Việt hoá giao diện và báo cáo điều hành.
- Hiển thị `Author: Le Hoang Quan` trên đầu dashboard.
- Connector `vnstock` để lấy VNINDEX tự động, có fallback sang dữ liệu mẫu nếu lỗi môi trường.
- Module **Risk Appetite Framework**: hạn mức, ngưỡng sử dụng, trạng thái xanh/vàng/đỏ.
- Module **Margin Stress Test**: shock thị trường chung, shock nhóm bất động sản, penalty thanh khoản thấp, forced-sell, collateral shortfall.
- Module **CSO Strategic Execution Tracker**: sáng kiến chiến lược, owner, tiến độ, blocker, action.
- Module **Board Pack Generator**: tóm tắt điều hành, top risk alerts, risk appetite, stress test, execution status và khuyến nghị.
- Rule-based recommendation engine, có thể nâng cấp lên LLM/AI assistant.

## Chạy local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy Streamlit Cloud

- Repository: `xtsc-cro-cso-command-center`
- Branch: `main`
- Main file path: `app.py`

## Ghi chú dữ liệu

Dữ liệu margin, khẩu vị rủi ro, compliance và sáng kiến chiến lược hiện là dữ liệu mẫu để demo phỏng vấn. VNINDEX có thể lấy live qua `vnstock`; khi Streamlit Cloud lỗi thư viện/API, app tự fallback về dữ liệu mẫu để không bị crash.
