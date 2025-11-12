import streamlit as st
import pandas as pd
import plotly.express as px

def _try_plot_ohlcv_from_payload(price_payload: dict) -> bool:
    """
    Attempts to find and plot OHLCV data if present.
    Returns True if plotted, else False (fallback to indicators table).
    """
    # Some backends may attach raw OHLCV; if not present, return False
    ohlcv = price_payload.get("ohlcv") if isinstance(price_payload, dict) else None
    if not ohlcv or not isinstance(ohlcv, dict):
        return False

    df = pd.DataFrame(ohlcv)
    # Heuristic for common keys; Streamlit expects a datetime x-axis column
    date_col = None
    for cand in ["Date", "date", "Datetime", "datetime", "index"]:
        if cand in df.columns:
            date_col = cand
            break
    close_col = None
    for cand in ["Close", "close", "Adj Close", "adj_close"]:
        if cand in df.columns:
            close_col = cand
            break
    if date_col and close_col and not df.empty:
        fig = px.line(df, x=date_col, y=close_col, title="Price (Close)")
        st.plotly_chart(fig, use_container_width=True)
        return True
    return False

def render_price_section(price_payload: dict):
    st.subheader("Price & Indicators")

    # First, try to plot OHLCV if present (future-proof if backend adds it)
    if _try_plot_ohlcv_from_payload(price_payload):
        st.caption("Chart from cached OHLCV (if provided by backend).")

    # Always show key indicators as a table
    indicators = (price_payload or {}).get("indicators", {}) or {}
    stance = (price_payload or {}).get("stance", "neutral")
    rationale = (price_payload or {}).get("rationale", "")

    if indicators:
        st.write("**Indicators (latest):**")
        st.dataframe(pd.DataFrame(indicators, index=["value"]).T)

    if rationale:
        st.info(f"Analyst rationale: {rationale} (stance: {stance})")