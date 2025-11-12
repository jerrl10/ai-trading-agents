from __future__ import annotations
from typing import Any, Dict, Union

from tradingagents.langgraph.state import GraphState


def consolidate_state(state: Union[Dict[str, Any], GraphState]) -> Dict[str, Any]:
    """
    Consolidates ephemeral node outputs into canonical keys for LangGraph.

    - Mappers (m__*) → data_sources[<type>]
    - Personas (a__*) → analyses[<persona_name>]

    This function is called as a final node in the pipeline to avoid
    concurrent write conflicts. It must return only a small clean dict
    with merged results.
    """
    # ✅ handle both dict and Pydantic model cases
    if isinstance(state, GraphState):
        state = state.model_dump()

    data_sources: Dict[str, Any] = {}
    analyses: Dict[str, Any] = {}
    usage_accumulator = {
        "prompt": int(state.get("token_usage", {}).get("prompt", 0)),
        "completion": int(state.get("token_usage", {}).get("completion", 0)),
    }

    for k, v in state.items():
        if k.startswith("m__"):
            subtype = k.split("__", 1)[1]  # e.g. "market"
            data_sources[subtype] = v
        elif k.startswith("a__"):
            persona = k.split("__", 1)[1]  # e.g. "TechnicalAnalyst"
            analyses[persona] = v
            usage = v.get("usage") if isinstance(v, dict) else None
            if usage:
                usage_accumulator["prompt"] += int(usage.get("prompt_tokens", 0))
                usage_accumulator["completion"] += int(usage.get("completion_tokens", 0))

    result: Dict[str, Any] = {}
    if data_sources:
        result["data_sources"] = data_sources
    if analyses:
        result["analyses"] = analyses
    result["token_usage"] = usage_accumulator

    return result


def finalize_decision(state: Union[Dict[str, Any], GraphState]) -> Dict[str, Any]:
    """
    Build a normalized decision payload from the latest governance personas.
    """
    gs = state if isinstance(state, GraphState) else GraphState(**state)

    analyses = dict(gs.analyses)
    # Fallback to raw persona payloads when consolidate_state has not run yet.
    for key in ["TechnicalAnalyst", "ValuationAnalyst", "EventAnalyst", "MacroAnalyst", "FlowAnalyst",
                "BullResearcher", "BearResearcher", "ResearchReferee", "RiskManager", "Trader", "RiskJudge"]:
        raw_key = f"a__{key}"
        if key not in analyses and hasattr(gs, raw_key):
            data = getattr(gs, raw_key)
            if data:
                analyses[key] = data

    risk_judge = analyses.get("RiskJudge") or {}
    trader = analyses.get("Trader") or {}
    referee = analyses.get("ResearchReferee") or {}

    source = risk_judge or trader or referee

    decision = {
        "ticker": gs.ticker,
        "stance": source.get("stance", "neutral"),
        "decision": source.get("final_action") or source.get("decision", "hold"),
        "rationale": source.get("rationale") or source.get("summary", ""),
        "confidence": source.get("confidence", referee.get("confidence", 0.0)),
        "source_persona": "RiskJudge" if risk_judge else "Trader" if trader else "ResearchReferee",
    }

    return {"decision": decision}
