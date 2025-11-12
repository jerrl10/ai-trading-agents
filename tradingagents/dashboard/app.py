import streamlit as st
from datetime import date

import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from tradingagents.dashboard.utils.api_client import analyze_ticker
from tradingagents.dashboard.components.decision_card import render_decision
from tradingagents.dashboard.components.chart_section import render_price_section
from tradingagents.dashboard.components.news_section import render_news_section
from tradingagents.dashboard.components.fundamentals_section import render_fundamentals_section

st.set_page_config(page_title="TradingAgents Dashboard", layout="wide")
st.title("📊 TradingAgents Research Dashboard")

with st.sidebar:
    st.header("Settings")
    ticker = st.text_input("Ticker", "AAPL").strip().upper()
    as_of_date = st.date_input("As of date", value=date.today())
    run = st.button("Run Analysis", type="primary")

if run:
    with st.spinner("Analyzing..."):
        result = analyze_ticker(ticker, str(as_of_date))

    if not result:
        st.error("No data received from API.")
    else:
        st.success(f"Analysis complete for {ticker}")

        # Decision block
        render_decision(result.get("decision", {}), title=f"Decision for {ticker}")

        # Layout: three columns for the analysts
        a1, a2, a3 = st.columns(3)

        # Price analyst section
        with a1:
            price_payload = (result.get("analyst_outputs", {}) or {}).get("price_analyst", {}) or {}
            render_price_section(price_payload)

        # Fundamentals analyst section
        with a2:
            fund_payload = (result.get("analyst_outputs", {}) or {}).get("fundamental_analyst", {}) or {}
            render_fundamentals_section(fund_payload)

        # News analyst section
        with a3:
            news_payload = (result.get("analyst_outputs", {}) or {}).get("news_analyst", {}) or {}
            render_news_section(news_payload)

        # Research view summary (optional JSON dump)
        st.markdown("---")
        st.subheader("Aggregated Research View (raw)")
        st.json(result.get("research_view", {}))

        st.caption(f"Elapsed: {result.get('elapsed_sec','-')}s • Timestamp: {result.get('timestamp','-')}")
else:
    st.info("Enter a ticker and choose a date, then click **Run Analysis**.")