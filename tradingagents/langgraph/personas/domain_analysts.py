from __future__ import annotations

from typing import Any, Dict, List, Optional

from tradingagents.langgraph.personas.base_persona import BasePersona, PersonaConfig
from tradingagents.langgraph.state import GraphState

# ──────────────────────────────────────────────────────────────
# Utility to select top evidence snippets for prompting
# ──────────────────────────────────────────────────────────────


def _sample_sources(
    gs: GraphState, source_key: str, n: int = 3
) -> List[Dict[str, Any]]:
    """Return up to n readable snippets from gs.data_sources[source_key]."""
    items = gs.data_sources.get(source_key, [])[:n]
    return [f"- {src.get('title') or src.get('content','')[:150]}" for src in items]


# ──────────────────────────────────────────────────────────────
# Domain-specific analyst personas
# ──────────────────────────────────────────────────────────────


class TechnicalAnalyst(BasePersona):
    """
    Examines market price action & volatility patterns.
    Looks at indicators, trend direction, and momentum.
    """

    def render_user_prompt(
        self, gs: GraphState, context: Optional[Dict[str, Any]] = None
    ) -> str:
        snippets = "\n".join(_sample_sources(gs, "market"))
        horizon_context = {
            "short": "Focus on near-term price action (days to weeks): momentum, volatility, support/resistance.",
            "medium": "Focus on intermediate trends (1-6 months): sustained momentum, trend strength, pattern breakouts.",
            "long": "Focus on long-term positioning (1+ years): major trend direction, structural levels, cyclical patterns."
        }.get(gs.time_horizon, "")

        return (
            f"You are a seasoned Technical Analyst evaluating {gs.ticker}.\n"
            f"Today: {gs.as_of_date}.\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_context}\n"
            f"Recent market data:\n{snippets}\n\n"
            "Identify trend direction, key signals (momentum, support/resistance), "
            "and return your stance with confidence. Support each claim with one evidence_ref "
            "from market data."
        )


class FundamentalAnalyst(BasePersona):
    """
    Evaluates fundamental valuation, growth metrics, and financial health.
    """

    def render_user_prompt(
        self, gs: GraphState, context: Optional[Dict[str, Any]] = None
    ) -> str:
        snippets = "\n".join(_sample_sources(gs, "fundamentals"))
        horizon_context = {
            "short": "Focus on near-term earnings catalysts, guidance, and valuation gaps.",
            "medium": "Focus on sustainable growth, margin trends, and competitive positioning over 1-6 months.",
            "long": "Focus on structural moats, long-term growth trajectory, and strategic position for 1+ years."
        }.get(gs.time_horizon, "")

        return (
            f"You are a Fundamental Analyst assessing {gs.ticker}.\n"
            f"As of {gs.as_of_date}, recent fundamental ratios:\n{snippets}\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_context}\n\n"
            "Determine if the company appears undervalued or overvalued relative to history "
            "and peers. Provide stance, key metrics, and confidence."
        )


class SentimentAnalyst(BasePersona):
    """
    Analyzes news & policy events for sentiment impact across different time horizons.
    """

    def render_user_prompt(
        self, gs: GraphState, context: Optional[Dict[str, Any]] = None
    ) -> str:
        news = "\n".join(_sample_sources(gs, "news"))
        horizon_context = {
            "short": "Focus on immediate sentiment shocks, headline reactions, and near-term narrative shifts.",
            "medium": "Focus on evolving themes, sector trends, and sustained narrative changes over 1-6 months.",
            "long": "Focus on structural regulatory changes, secular trends, and long-term sentiment drivers."
        }.get(gs.time_horizon, "")

        return (
            f"You are a Sentiment Analyst covering {gs.ticker}.\n"
            f"Relevant company, sector, and policy news:\n{news}\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_context}\n\n"
            "Summarize how these events might affect investor sentiment and price direction. "
            "Return structured JSON with stance, reasons, and evidence_refs."
        )


class MacroAnalyst(BasePersona):
    """
    Reviews macroeconomic indicators and global context.
    """

    def render_user_prompt(
        self, gs: GraphState, context: Optional[Dict[str, Any]] = None
    ) -> str:
        snippets = "\n".join(_sample_sources(gs, "macro"))
        horizon_context = {
            "short": "Focus on immediate rate decisions, data surprises, and near-term policy shifts.",
            "medium": "Focus on evolving monetary/fiscal policy, growth trajectory, and inflation trends over 1-6 months.",
            "long": "Focus on structural economic cycles, regime changes, and long-term policy direction."
        }.get(gs.time_horizon, "")

        return (
            f"You are a Macro Analyst.\n"
            f"Latest macro context:\n{snippets}\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_context}\n\n"
            f"Explain how macro trends could influence {gs.ticker}'s sector or index exposure. "
            "State whether the macro environment is supportive, neutral, or hostile for the stock."
        )


class FlowAnalyst(BasePersona):
    """
    Observes positioning, flow, and market microstructure.
    """

    def render_user_prompt(
        self, gs: GraphState, context: Optional[Dict[str, Any]] = None
    ) -> str:
        snippets = "\n".join(_sample_sources(gs, "market"))
        horizon_context = {
            "short": "Focus on intraday/weekly flows, liquidity, and positioning imbalances.",
            "medium": "Focus on institutional flow trends, sentiment extremes, and positioning over 1-6 months.",
            "long": "Focus on structural changes in ownership, long-term capital allocation trends."
        }.get(gs.time_horizon, "")

        return (
            f"You are a Flow & Positioning Analyst for {gs.ticker}.\n"
            f"Recent market flow data:\n{snippets}\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_context}\n\n"
            "Estimate whether current positioning is crowded long, neutral, or short. "
            "Support claims with reasoning and confidence."
        )


# ──────────────────────────────────────────────────────────────
# Factory for easy graph construction
# ──────────────────────────────────────────────────────────────


def build_domain_analysts() -> Dict[str, BasePersona]:
    """
    Create all domain analysts with consistent config.
    Returns analysts keyed by their role names for easy graph construction.
    """
    return {
        "technical": TechnicalAnalyst(
            PersonaConfig(
                name="TechnicalAnalyst",
                system_prompt_path="technical_analyst.txt",
                temperature=0.2,
                max_tokens=400,
            )
        ),
        "fundamental": FundamentalAnalyst(
            PersonaConfig(
                name="FundamentalAnalyst",
                system_prompt_path="fundamental_analyst.txt",
                temperature=0.2,
                max_tokens=400,
            )
        ),
        "sentiment": SentimentAnalyst(
            PersonaConfig(
                name="SentimentAnalyst",
                system_prompt_path="sentiment_analyst.txt",
                temperature=0.2,
                max_tokens=500,
            )
        ),
        "macro": MacroAnalyst(
            PersonaConfig(
                name="MacroAnalyst",
                system_prompt_path="macro_analyst.txt",
                temperature=0.2,
                max_tokens=400,
            )
        ),
        "flow": FlowAnalyst(
            PersonaConfig(
                name="FlowAnalyst",
                system_prompt_path="flow_analyst.txt",
                temperature=0.2,
                max_tokens=400,
            )
        ),
    }
