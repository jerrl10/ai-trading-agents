from __future__ import annotations
from typing import Any, Dict, Optional

from tradingagents.langgraph.state import GraphState
from tradingagents.langgraph.personas.base_persona import BasePersona, PersonaConfig


# ──────────────────────────────────────────────────────────────
# Utility: build concise analyst summary for prompt
# ──────────────────────────────────────────────────────────────

def _analyst_digest(gs: GraphState) -> str:
    """Summarize all domain analyst outputs for context."""
    if not gs.analyses:
        return "No analyst outputs available."
    lines = []
    for name, a in gs.analyses.items():
        stance = a.get("stance", "neutral")
        conf = a.get("confidence", 0.0)
        summary = a.get("summary", "")[:160]
        lines.append(f"{name}: {stance} ({conf:.2f}) → {summary}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# Synthesis Persona (Replaces Bull/Bear/Referee debate)
# ──────────────────────────────────────────────────────────────

class Synthesis(BasePersona):
    """
    Synthesizes all domain analyst outputs into a coherent investment thesis.
    Weights technical, fundamental, sentiment, macro, and flow perspectives to
    produce a balanced view with confidence and stance.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        digest = _analyst_digest(gs)

        horizon_focus = {
            "short": "Prioritize technical and sentiment signals for near-term price action.",
            "medium": "Balance fundamental valuation with technical trends and sentiment over 1-6 months.",
            "long": "Focus on fundamental moats, structural trends, and long-term macro environment."
        }.get(gs.time_horizon, "")

        return (
            f"You are a senior Research Strategist synthesizing multi-disciplinary analysis for {gs.ticker}.\n"
            f"As of {gs.as_of_date}, Time Horizon: {gs.time_horizon.upper()}\n"
            f"{horizon_focus}\n\n"
            f"Analyst Inputs:\n{digest}\n\n"
            "Synthesize these views into a coherent thesis. Weigh each analyst's input by their confidence and relevance to the time horizon. "
            "Produce a final stance (bullish/neutral/bearish), stance_score (-1 to +1), overall confidence (0-1), "
            "and a concise summary with 3-5 key drivers. Include evidence_refs from analysts."
        )


# ──────────────────────────────────────────────────────────────
# Bull and Bear researchers
# ──────────────────────────────────────────────────────────────

class BullResearcher(BasePersona):
    """Constructs the strongest bullish case using all analyst evidence."""
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        digest = _analyst_digest(gs)
        return (
            f"You are a senior research analyst arguing the **BULLISH** case for {gs.ticker}.\n"
            f"As of {gs.as_of_date}, here is the analyst summary:\n{digest}\n\n"
            "Build the most compelling bullish thesis possible using evidence from the analyses above. "
            "Cite specific evidence_refs and include 3–5 key reasons. "
            "Be realistic but optimistic; discuss valuation, momentum, sentiment, and macro context."
        )


class BearResearcher(BasePersona):
    """Constructs the strongest bearish or risk-focused case."""
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        digest = _analyst_digest(gs)
        return (
            f"You are a senior research analyst arguing the **BEARISH** case for {gs.ticker}.\n"
            f"As of {gs.as_of_date}, here is the analyst summary:\n{digest}\n\n"
            "Build the most compelling bearish thesis possible using evidence from the analyses above. "
            "Highlight downside risks, overvaluation, weak fundamentals, or macro threats. "
            "Return JSON with stance, stance_score (-1..1), confidence, reasons, and evidence_refs."
        )


# ──────────────────────────────────────────────────────────────
# Referee (consensus builder)
# ──────────────────────────────────────────────────────────────

class ResearchReferee(BasePersona):
    """
    Reconciles Bull and Bear researchers into a weighted, balanced thesis.
    Weights are based on each researcher's confidence and evidence depth.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        bull = gs.analyses.get("BullResearcher", {})
        bear = gs.analyses.get("BearResearcher", {})
        return (
            f"You are a neutral Research Referee combining two opposing theses for {gs.ticker}.\n"
            f"---\nBULLISH CASE:\n{bull.get('summary','')}\n\n"
            f"---\nBEARISH CASE:\n{bear.get('summary','')}\n\n"
            "Evaluate both objectively. Determine which side has stronger evidence and higher confidence. "
            "Produce a weighted final thesis and numeric score from -1 (bear) to +1 (bull). "
            "Include an overall confidence 0–1 and list 3–5 synthesized reasons with evidence_refs."
        )
