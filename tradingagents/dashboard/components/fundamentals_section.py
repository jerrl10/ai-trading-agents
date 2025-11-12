import streamlit as st
import pandas as pd

def render_fundamentals_section(fund_payload: dict):
    st.subheader("Fundamentals")

    ratios = (fund_payload or {}).get("ratios", {}) or {}
    trend = (fund_payload or {}).get("trend", {}) or {}
    stance = (fund_payload or {}).get("stance", "neutral")
    rationale = (fund_payload or {}).get("rationale", "")

    c1, c2 = st.columns(2)
    with c1:
        st.write("**Valuation & Profitability**")
        if ratios:
            st.dataframe(pd.DataFrame(ratios, index=["value"]).T)
        else:
            st.caption("No ratios available.")
    with c2:
        st.write("**Trends**")
        if trend:
            st.dataframe(pd.DataFrame(trend, index=["value"]).T)
        else:
            st.caption("No trend metrics available.")

    if rationale:
        st.info(f"Analyst rationale: {rationale} (stance: {stance})")