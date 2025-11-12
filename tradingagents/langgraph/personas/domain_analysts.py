from __future__ import annotations
from typing import Any, Dict, List, Optional

from tradingagents.langgraph.state import GraphState
from tradingagents.langgraph.personas.base_persona import BasePersona, PersonaConfig


# ──────────────────────────────────────────────────────────────
# Utility to select top evidence snippets for prompting
# ──────────────────────────────────────────────────────────────

def _sample_sources(gs: GraphState, source_key: str, n: int = 3) -> List[Dict[str, Any]]:
    """Return up to n readable snippets from gs.data_sources[source_key]."""
    items = gs.data_sources.get(source_key, [])[:n]
    return [
        f"- {src.get('title') or src.get('content','')[:150]}" for src in items
    ]


# ──────────────────────────────────────────────────────────────
# Domain-specific analyst personas
# ──────────────────────────────────────────────────────────────

class TechnicalAnalyst(BasePersona):
    """
    Examines market price action & volatility patterns.
    Looks at indicators, trend direction, and momentum.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        snippets = "\n".join(_sample_sources(gs, "market"))
        return (
            f"You are a seasoned Technical Analyst evaluating {gs.ticker}.\n"
            f"Today: {gs.as_of_date}.\n"
            f"Recent market data:\n{snippets}\n\n"
            "Identify trend direction, key signals (momentum, support/resistance), "
            "and return your stance with confidence. Support each claim with one evidence_ref "
            "from market data."
        )


class ValuationAnalyst(BasePersona):
    """
    Evaluates fundamental valuation & growth metrics.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        snippets = "\n".join(_sample_sources(gs, "fundamentals"))
        return (
            f"You are a Valuation Analyst assessing {gs.ticker}.\n"
            f"As of {gs.as_of_date}, recent fundamental ratios:\n{snippets}\n\n"
            "Determine if the company appears undervalued or overvalued relative to history "
            "and peers. Provide stance, key metrics, and confidence."
        )


class EventAnalyst(BasePersona):
    """
    Analyzes news & policy events for sentiment impact.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        general = "\n".join(_sample_sources(gs, "news"))
        policy = "\n".join(_sample_sources(gs, "policy"))
        return (
            f"You are a News & Event Analyst covering {gs.ticker}.\n"
            f"Relevant company or sector news:\n{general}\n\n"
            f"Recent policy developments:\n{policy}\n\n"
            "Summarize how these events might affect investor sentiment and near-term price "
            "direction. Return structured JSON with stance, reasons, and evidence_refs."
        )


class MacroAnalyst(BasePersona):
    """
    Reviews macroeconomic indicators and global context.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        snippets = "\n".join(_sample_sources(gs, "macro"))
        return (
            f"You are a Macro Analyst.\n"
            f"Latest macro context:\n{snippets}\n\n"
            f"Explain how macro trends could influence {gs.ticker}'s sector or index exposure. "
            "State whether the macro environment is supportive, neutral, or hostile for the stock."
        )


class FlowAnalyst(BasePersona):
    """
    Observes positioning and flow (optional extension).
    You can connect to CFTC or options data in Step 8.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        # For now just echo market context as placeholder.
        snippets = "\n".join(_sample_sources(gs, "market"))
        return (
            f"You are a Flow & Positioning Analyst for {gs.ticker}.\n"
            f"Recent market flow data:\n{snippets}\n\n"
            "Estimate whether current positioning is crowded long, neutral, or short. "
            "Support claims with reasoning and confidence."
        )


# ──────────────────────────────────────────────────────────────
# Factory for easy graph construction
# ──────────────────────────────────────────────────────────────

def build_domain_analysts() -> Dict[str, BasePersona]:
    """
    Create all domain analysts with consistent config.
    """
    return {
        "technical": TechnicalAnalyst(PersonaConfig(
            name="TechnicalAnalyst",
            system_prompt_path="technical_analyst.txt",
            temperature=0.2,
            max_tokens=400,
        )),
        "valuation": ValuationAnalyst(PersonaConfig(
            name="ValuationAnalyst",
            system_prompt_path="valuation_analyst.txt",
            temperature=0.2,
            max_tokens=400,
        )),
        "event": EventAnalyst(PersonaConfig(
            name="EventAnalyst",
            system_prompt_path="event_analyst.txt",
            temperature=0.2,
            max_tokens=500,
        )),
        "macro": MacroAnalyst(PersonaConfig(
            name="MacroAnalyst",
            system_prompt_path="macro_analyst.txt",
            temperature=0.2,
            max_tokens=400,
        )),
        "flow": FlowAnalyst(PersonaConfig(
            name="FlowAnalyst",
            system_prompt_path="flow_analyst.txt",
            temperature=0.2,
            max_tokens=400,
        )),
    }
