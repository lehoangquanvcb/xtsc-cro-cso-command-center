import streamlit as st
import pandas as pd
import plotly.express as px
from modules.risk_engine import latest_row, enterprise_risk_score, status_from_score, build_alerts, force_sell_simulation, traffic_light
from modules.strategy_engine import summarize_initiatives, board_narrative

st.set_page_config(page_title="XTSC Risk & Strategy Command Center", layout="wide")

@st.cache_data
def load_data():
    return {
        "snapshot": pd.read_csv("data/executive_snapshot.csv", parse_dates=["date"]),
        "margin": pd.read_csv("data/margin_book.csv"),
        "initiatives": pd.read_csv("data/strategic_initiatives.csv"),
        "compliance": pd.read_csv("data/compliance_calendar.csv"),
        "macro": pd.read_csv("data/macro_market.csv", parse_dates=["date"]),
    }

def status_badge(status):
    return {"Green":"🟢 Green", "Yellow":"🟡 Yellow", "Red":"🔴 Red", "Grey":"⚪ Grey"}.get(status,status)

def money_bn(x):
    return f"{x/1e9:,.1f} bn VND"

D = load_data()
snapshot = D["snapshot"]
margin = D["margin"]
initiatives = summarize_initiatives(D["initiatives"])
compliance = D["compliance"]
macro = D["macro"]
latest = latest_row(snapshot)
risk_score = enterprise_risk_score(latest)
risk_status = status_from_score(risk_score)
alerts = build_alerts(latest)

st.sidebar.title("XTSC Command Center")
st.sidebar.caption("CRO + CSO demo system for Xuan Thien Securities")
mobile = st.sidebar.radio("Interface", ["Boardroom", "Mobile friendly"], index=0) == "Mobile friendly"
shock = st.sidebar.slider("Market shock for margin stress test", -30, 0, -10, 1)

st.title("XTSC Risk & Strategy Command Center")
st.caption("Enterprise risk governance, strategic execution, compliance oversight and CEO/Board reporting prototype")

if mobile:
    st.info("Mobile friendly mode is on: use tabs and compact tables for interview demo.")

tabs = st.tabs([
    "1. Executive Cockpit",
    "2. Margin & Trading Risk",
    "3. Strategy Governance",
    "4. Compliance Hub",
    "5. Macro & Market Risk",
    "6. Board Pack"
])

with tabs[0]:
    st.subheader("Executive Risk & Strategy Snapshot")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Enterprise Risk Score", f"{risk_score}/100", status_badge(risk_status))
    c2.metric("Margin Utilization", f"{latest['margin_utilization_pct']:.1f}%", status_badge(traffic_light(latest['margin_utilization_pct'],75,85)))
    c3.metric("Liquidity Buffer", f"{latest['liquidity_buffer_x']:.2f}x", status_badge(traffic_light(latest['liquidity_buffer_x'],2.5,1.8,high_is_bad=False)))
    c4.metric("Compliance Breaches", int(latest['compliance_breaches']), status_badge(traffic_light(latest['compliance_breaches'],3,5)))

    st.markdown("### Strategic Alerts")
    for a in alerts:
        st.warning(a) if risk_status != "Green" else st.success(a)

    col1,col2 = st.columns(2)
    with col1:
        fig = px.line(snapshot, x="date", y=["margin_utilization_pct","top10_client_exposure_pct","single_stock_exposure_pct"], title="Risk Appetite Utilization Trend")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        heat = pd.DataFrame({
            "Risk Area":["Margin", "Liquidity", "Concentration", "Compliance", "Market Volatility"],
            "Score":[latest['margin_utilization_pct'], max(0,100-latest['liquidity_buffer_x']*25), latest['top10_client_exposure_pct']*3, latest['compliance_breaches']*15, latest['market_volatility_pct']*12]
        })
        fig = px.bar(heat, x="Risk Area", y="Score", title="Enterprise Risk Heatmap Proxy", range_y=[0,100])
        st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.subheader("Margin & Trading Risk Center")
    stressed = force_sell_simulation(margin, shock)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Margin Loan", money_bn(margin['loan_balance'].sum()))
    c2.metric("Collateral Value", money_bn(margin['collateral_value'].sum()))
    c3.metric("Accounts at Force-sell Risk", int((stressed['force_sell_flag']=="Yes").sum()))
    c4.metric("Avg Stressed LTV", f"{stressed['stressed_ltv_pct'].mean():.1f}%")

    col1,col2 = st.columns(2)
    with col1:
        by_sector = margin.groupby('sector', as_index=False)['loan_balance'].sum()
        fig = px.pie(by_sector, names='sector', values='loan_balance', title='Margin Loan by Sector')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        by_stock = margin.groupby('stock', as_index=False)['loan_balance'].sum().sort_values('loan_balance', ascending=False).head(10)
        fig = px.bar(by_stock, x='stock', y='loan_balance', title='Top 10 Stock Exposure')
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Stressed Client Book")
    st.dataframe(stressed.sort_values('stressed_ltv_pct', ascending=False), use_container_width=True)

with tabs[2]:
    st.subheader("Strategic Execution Governance")
    c1,c2,c3 = st.columns(3)
    c1.metric("Red initiatives", int((initiatives['health']=="Red").sum()))
    c2.metric("Yellow initiatives", int((initiatives['health']=="Yellow").sum()))
    c3.metric("Average progress", f"{initiatives['progress_pct'].mean():.1f}%")
    fig = px.bar(initiatives, x='initiative', y=['progress_pct','expected_progress_pct'], title='Strategic Initiative Progress')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(initiatives, use_container_width=True)

with tabs[3]:
    st.subheader("Regulatory & Compliance Hub")
    status_counts = compliance['status'].value_counts().reset_index()
    status_counts.columns = ['status','count']
    fig = px.bar(status_counts, x='status', y='count', title='Compliance Reporting Status')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(compliance, use_container_width=True)
    st.markdown("### Suggested Governance Calendar")
    st.write("Monthly: risk dashboard, margin concentration review, liquidity stress review, compliance exceptions, SSC/HOSE/HNX reporting status.")
    st.write("Quarterly: risk appetite review, policy updates, risk committee meeting, strategic execution review.")

with tabs[4]:
    st.subheader("Macro & Market Risk Engine")
    col1,col2 = st.columns(2)
    with col1:
        fig = px.line(macro, x='date', y='vnindex', title='VNINDEX Proxy')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.line(macro, x='date', y=['usd_vnd','foreign_flow_bn_vnd'], title='FX and Foreign Flow Proxy')
        st.plotly_chart(fig, use_container_width=True)
    fig = px.line(macro, x='date', y=['policy_rate_pct','bond_yield_10y_pct'], title='Interest Rate and Bond Yield Proxy')
    st.plotly_chart(fig, use_container_width=True)

with tabs[5]:
    st.subheader("CEO / Board Pack Generator")
    narrative = board_narrative(risk_status, alerts, initiatives)
    st.markdown("### Executive Narrative")
    st.info(narrative)
    st.markdown("### Board-level Recommendations")
    st.write("1. Approve and cascade the risk appetite framework across business lines.")
    st.write("2. Prioritize margin concentration limits and single-stock exposure control.")
    st.write("3. Establish a monthly Risk & Strategy Committee chaired by CEO/Chairman.")
    st.write("4. Automate early warning dashboards for margin, liquidity, compliance and strategic execution.")
    st.write("5. Build a three-lines-of-defense model with clear escalation authority.")
