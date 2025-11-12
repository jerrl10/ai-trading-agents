import streamlit as st
from tradingagents.dashboard.utils.formatters import stance_color, decision_color

def render_decision(decision: dict, title: str = "Decision"):
    stance = (decision or {}).get("stance", "neutral")
    choice = (decision or {}).get("decision", "hold")
    rationale = (decision or {}).get("rationale", "")

    st.markdown(f"### {title}")
    st.markdown(
        f"""
        <div style="
            padding:14px;border-radius:12px;border:1px solid #e5e7eb;
            background:#fafafa;">
            <div style="font-size:22px;margin-bottom:8px;">
                Overall Stance:
                <b style="color:{stance_color(stance)}">{stance.upper()}</b>
            </div>
            <div style="font-size:18px;margin-bottom:8px;">
                Action:
                <b style="color:{decision_color(choice)}">{choice.upper()}</b>
            </div>
            <div style="color:#374151">{rationale}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )