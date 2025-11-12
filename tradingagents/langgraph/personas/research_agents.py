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
