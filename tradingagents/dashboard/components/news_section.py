import streamlit as st

def render_news_section(news_payload: dict):
    st.subheader("News & Policy")

    articles = (news_payload or {}).get("articles", 0)
    stance = (news_payload or {}).get("stance", "neutral")
    rationale = (news_payload or {}).get("rationale", "")

    # Optional: if backend later includes headlines list
    headlines = (news_payload or {}).get("headlines")  # list[str] optional

    st.write(f"**Articles counted:** {articles}")
    st.write(f"**Stance:** {stance}")
    if rationale:
        st.info(rationale)

    if headlines and isinstance(headlines, list):
        st.write("**Recent headlines:**")
        for h in headlines[:10]:
            st.markdown(f"- {h}")