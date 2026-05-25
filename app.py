import streamlit as st
import pandas as pd
import plotly.express as px
from modules.risk_engine import (
    latest_row,
    enterprise_risk_score,
    status_from_score,
    build_alerts,
    force_sell_simulation,
    traffic_light,
    assess_risk_appetite,
    scenario_summary,
    rule_based_recommendations,
)
from modules.strategy_engine import summarize_initiatives, board_narrative
from modules.vnstock_connector import enrich_macro_with_vnstock
from modules.advanced_risk_engine import (
    dynamic_haircut,
    trading_book_var,
    stress_loss,
    build_competitor_snapshot,
)

st.set_page_config(page_title="XTSC CRO/CSO Enterprise Governance Platform", layout="wide")

@st.cache_data(ttl=1800)
def load_data(use_live_vnstock: bool = True, vnstock_source: str = "VCI"):
    local_macro = pd.read_csv("data/macro_market.csv", parse_dates=["date"])
    macro, data_source, data_note = enrich_macro_with_vnstock(local_macro, use_live=use_live_vnstock, source=vnstock_source)
    return {
        "snapshot": pd.read_csv("data/executive_snapshot.csv", parse_dates=["date"]),
        "margin": pd.read_csv("data/margin_book.csv"),
        "initiatives": pd.read_csv("data/strategic_initiatives.csv"),
        "compliance": pd.read_csv("data/compliance_calendar.csv"),
        "macro": macro,
        "appetite": pd.read_csv("data/risk_appetite.csv"),
        "collateral": pd.read_csv("data/collateral_universe.csv"),
        "data_source": data_source,
        "data_note": data_note,
    }

def status_badge(status):
    return {"Green":"🟢 Xanh", "Yellow":"🟡 Vàng", "Red":"🔴 Đỏ", "Grey":"⚪ Chưa đủ dữ liệu"}.get(status,status)

def money_bn(x):
    return f"{x/1e9:,.1f} tỷ đồng"

def vi_flag(x):
    return "Có" if str(x).lower() == "yes" else "Không"

def vi_status(x):
    return {"Green":"Xanh", "Yellow":"Vàng", "Red":"Đỏ", "Grey":"Thiếu dữ liệu"}.get(x, x)

st.sidebar.title("XTSC Governance Platform")
st.sidebar.caption("Mô hình CRO + CSO cho Công ty Chứng khoán Xuân Thiện")
use_live_vnstock = st.sidebar.toggle("Tự động lấy VNINDEX từ vnstock", value=True)
vnstock_source = st.sidebar.selectbox("Nguồn vnstock", ["VCI", "TCBS", "KBS"], index=0)
mobile = st.sidebar.radio("Giao diện", ["Phòng họp HĐQT", "Mobile friendly"], index=0) == "Mobile friendly"
st.sidebar.markdown("### Kịch bản stress test")
shock = st.sidebar.slider("VNINDEX / thị trường chung", -30, 0, -10, 1)
real_estate_shock = st.sidebar.slider("Nhóm bất động sản", -40, 0, -15, 1)
liquidity_penalty = st.sidebar.slider("Phạt thêm cho mã thanh khoản thấp", 0, 20, 5, 1)

D = load_data(use_live_vnstock, vnstock_source)
snapshot = D["snapshot"]
margin = D["margin"]
initiatives = summarize_initiatives(D["initiatives"])
compliance = D["compliance"]
macro = D["macro"]
risk_appetite = assess_risk_appetite(D["appetite"])
collateral = D["collateral"]
latest = latest_row(snapshot)
risk_score = enterprise_risk_score(latest)
risk_status = status_from_score(risk_score)
alerts = build_alerts(latest)
stressed = force_sell_simulation(margin, shock, real_estate_shock, liquidity_penalty)
stress = scenario_summary(stressed)
recommendations = rule_based_recommendations(latest, risk_appetite, stressed, initiatives)

st.markdown("**Author: Le Hoang Quan**")
st.title("XTSC CRO/CSO Enterprise Governance Platform")
st.caption("Trung tâm điều hành Quản trị rủi ro, Tuân thủ, Chiến lược, Stress Test và Báo cáo Ban lãnh đạo/HĐQT")
st.info("📌 Lưu ý: Dashboard này có 7 tab chức năng. Anh/chị vui lòng click lần lượt vào các tab được đánh số từ 1 đến 7 bên dưới để xem đầy đủ các module")

if "vnstock live" in D["data_source"]:
    st.success(f"Nguồn dữ liệu thị trường: {D['data_source']}. {D['data_note']}")
else:
    st.warning(f"Nguồn dữ liệu thị trường: {D['data_source']}. {D['data_note']}")

if mobile:
    st.info("Đang bật giao diện mobile friendly: bảng và biểu đồ được giữ gọn để demo trên điện thoại.")

tabs = st.tabs([
    "1. Tổng quan",
    "2. Khẩu vị rủi ro",
    "3. Margin Stress Test",
    "4. CSO Execution Tracker",
    "5. Tuân thủ & Regulator",
    "6. Vĩ mô & Thị trường",
    "7. Trình HĐQT",
])

with tabs[0]:
    st.subheader("Tổng quan rủi ro & chiến lược cho Ban lãnh đạo")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Điểm rủi ro tổng thể", f"{risk_score}/100", status_badge(risk_status))
    c2.metric("Sử dụng hạn mức margin", f"{latest['margin_utilization_pct']:.1f}%", status_badge(traffic_light(latest['margin_utilization_pct'],75,85)))
    c3.metric("Đệm thanh khoản", f"{latest['liquidity_buffer_x']:.2f}x", status_badge(traffic_light(latest['liquidity_buffer_x'],2.5,1.8,high_is_bad=False)))
    c4.metric("Tài khoản nguy cơ force-sell", stress["accounts_at_risk"], f"Shock {shock}%")

    st.markdown("### Cảnh báo trọng yếu")
    for a in alerts:
        if risk_status != "Green":
            st.warning(a)
        else:
            st.success(a)

    st.markdown("### Khuyến nghị tự động cho CEO/CRO")
    for rec in recommendations[:5]:
        st.info("• " + rec)

    col1,col2 = st.columns(2)
    with col1:
        fig = px.line(snapshot, x="date", y=["margin_utilization_pct","top10_client_exposure_pct","single_stock_exposure_pct"], title="Xu hướng sử dụng khẩu vị rủi ro")
        fig.update_layout(legend_title_text="Chỉ tiêu")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        heat = pd.DataFrame({
            "Nhóm rủi ro":["Margin", "Thanh khoản", "Tập trung", "Tuân thủ", "Biến động thị trường"],
            "Điểm rủi ro":[latest['margin_utilization_pct'], max(0,100-latest['liquidity_buffer_x']*25), latest['top10_client_exposure_pct']*3, latest['compliance_breaches']*15, latest['market_volatility_pct']*12]
        })
        fig = px.bar(heat, x="Nhóm rủi ro", y="Điểm rủi ro", title="Bản đồ nhiệt rủi ro doanh nghiệp", range_y=[0,100])
        st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.subheader("Khung khẩu vị rủi ro và hạn mức kiểm soát")
    c1,c2,c3 = st.columns(3)
    c1.metric("Chỉ tiêu Đỏ", int((risk_appetite["status"] == "Red").sum()))
    c2.metric("Chỉ tiêu Vàng", int((risk_appetite["status"] == "Yellow").sum()))
    c3.metric("Chỉ tiêu Xanh", int((risk_appetite["status"] == "Green").sum()))
    view = risk_appetite.copy()
    view["status_vi"] = view["status"].map(vi_status)
    st.dataframe(view, use_container_width=True)
    fig = px.bar(view, x="risk_metric", y="utilization_pct", color="status_vi", title="Mức sử dụng khẩu vị rủi ro / hạn mức phê duyệt")
    st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("Stress Test rủi ro margin & giao dịch")
    stressed_display = stressed.copy()
    stressed_display["force_sell_flag_vi"] = stressed_display["force_sell_flag"].apply(vi_flag)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Tổng dư nợ margin", money_bn(margin['loan_balance'].sum()))
    c2.metric("Forced-sell ước tính", money_bn(stress['estimated_forced_sell_value']))
    c3.metric("Thiếu hụt collateral", money_bn(stress['collateral_shortfall']))
    c4.metric("LTV bình quân sau stress", f"{stress['avg_stressed_ltv']:.1f}%")

    col1,col2 = st.columns(2)
    with col1:
        by_sector = margin.groupby('sector', as_index=False)['loan_balance'].sum()
        fig = px.pie(by_sector, names='sector', values='loan_balance', title='Dư nợ margin theo ngành')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        by_stock = margin.groupby('stock', as_index=False)['loan_balance'].sum().sort_values('loan_balance', ascending=False).head(10)
        fig = px.bar(by_stock, x='stock', y='loan_balance', title='Top 10 mã cổ phiếu theo dư nợ')
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Sổ margin sau kịch bản stress")
    st.dataframe(stressed_display.sort_values('stressed_ltv_pct', ascending=False), use_container_width=True)

    st.markdown("### Danh mục collateral mẫu lấy từ thị trường")
    st.dataframe(collateral, use_container_width=True)

with tabs[3]:
    st.subheader("CSO Strategic Execution Tracker")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Sáng kiến Đỏ", int((initiatives['health']=="Red").sum()))
    c2.metric("Sáng kiến Vàng", int((initiatives['health']=="Yellow").sum()))
    c3.metric("Tiến độ bình quân", f"{initiatives['progress_pct'].mean():.1f}%")
    c4.metric("Khoảng cách tiến độ", f"{initiatives['gap_pct'].mean():.1f} điểm %")
    fig = px.bar(initiatives, x='initiative', y=['progress_pct','expected_progress_pct'], color_discrete_sequence=None, title='Tiến độ sáng kiến chiến lược so với kế hoạch')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(initiatives, use_container_width=True)

with tabs[4]:
    st.subheader("Trung tâm tuân thủ & làm việc với cơ quan quản lý")
    status_counts = compliance['status'].value_counts().reset_index()
    status_counts.columns = ['Trạng thái','Số lượng']
    fig = px.bar(status_counts, x='Trạng thái', y='Số lượng', title='Trạng thái báo cáo/đầu việc tuân thủ')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(compliance, use_container_width=True)
    st.markdown("### Lịch quản trị đề xuất")
    st.write("Hàng tháng: dashboard rủi ro, rà soát tập trung margin, stress test thanh khoản, ngoại lệ tuân thủ, tình trạng báo cáo UBCK/HOSE/HNX.")
    st.write("Hàng quý: rà soát khẩu vị rủi ro, cập nhật chính sách, họp Ủy ban Rủi ro, rà soát thực thi chiến lược.")

with tabs[5]:
    st.subheader("Động cơ rủi ro vĩ mô & thị trường")
    col1,col2 = st.columns(2)
    with col1:
        fig = px.line(macro, x='date', y='vnindex', title='VNINDEX từ vnstock hoặc dữ liệu mẫu')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.line(macro, x='date', y=['usd_vnd','foreign_flow_bn_vnd'], title='Tỷ giá USD/VND và dòng vốn ngoại proxy')
        st.plotly_chart(fig, use_container_width=True)
    if 'market_volatility_pct' in macro.columns:
        fig = px.line(macro, x='date', y='market_volatility_pct', title='Biến động thị trường ước tính từ VNINDEX')
        st.plotly_chart(fig, use_container_width=True)
    fig = px.line(macro, x='date', y=['policy_rate_pct','bond_yield_10y_pct'], title='Lãi suất chính sách và lợi suất TPCP 10 năm proxy')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Competitor Intelligence")
    
    competitors = build_competitor_snapshot()
    
    st.dataframe(competitors, use_container_width=True)
    
with tabs[6]:
    st.subheader("Board Pack Generator - Báo cáo CRO/CSO tự động")
    narrative = board_narrative(risk_status, alerts, initiatives, risk_appetite, stress)
    st.markdown("### 1. Executive Summary")
    st.info(narrative)
    st.markdown("### 2. Top Risk Alerts")
    for i, a in enumerate(alerts[:5], 1):
        st.write(f"{i}. {a}")
    st.markdown("### 3. Risk Appetite Status")
    st.dataframe(risk_appetite[["risk_metric", "approved_limit", "current_value", "utilization_pct", "status"]], use_container_width=True)
    st.markdown("### 4. Margin Stress Test Result")
    st.write(f"Kịch bản: thị trường chung {shock}%, bất động sản {real_estate_shock}%, phạt thanh khoản thấp {liquidity_penalty} điểm %.")
    st.write(f"Tài khoản có nguy cơ force-sell: **{stress['accounts_at_risk']}**; giá trị forced-sell ước tính: **{money_bn(stress['estimated_forced_sell_value'])}**; thiếu hụt collateral: **{money_bn(stress['collateral_shortfall'])}**.")
    st.markdown("### 5. Strategic Execution Status")
    st.dataframe(initiatives[["initiative", "owner", "progress_pct", "expected_progress_pct", "execution_risk", "health", "recommended_action"]], use_container_width=True)
    st.markdown("### 6. Khuyến nghị cấp HĐQT/Ban lãnh đạo")
    for i, rec in enumerate(recommendations, 1):
        st.write(f"{i}. {rec}")
    st.download_button(
        "Tải nội dung Board Pack dạng Markdown",
        data=("# XTSC CRO/CSO Board Pack\n\n" + narrative + "\n\n## Recommendations\n" + "\n".join([f"- {r}" for r in recommendations])),
        file_name="XTSC_CRO_CSO_Board_Pack.md",
        mime="text/markdown",
    )
