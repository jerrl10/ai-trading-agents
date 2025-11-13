from __future__ import annotations
from typing import Any, Dict, Optional
from tradingagents.langgraph.state import GraphState
from tradingagents.langgraph.personas.base_persona import BasePersona, PersonaConfig


# ──────────────────────────────────────────────
# Risk Assessment
# ──────────────────────────────────────────────
class RiskAssessment(BasePersona):
    """
    Evaluates portfolio and instrument-specific risks, sizing positions based on
    thesis confidence, volatility, and time horizon.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        synthesis = gs.analyses.get("Synthesis", {})
        conf = synthesis.get("confidence", 0.0)
        stance_score = synthesis.get("stance_score", 0.0)
        # Derive simple volatility proxy (from market data)
        price_data = gs.data_sources.get("market", [])
        vol = len(price_data) and abs(price_data[0]["meta"].get("change", 0.02)) or 0.02

        horizon_sizing = {
            "short": "Size for quick tactical moves with tighter stops (e.g., 0.5-1.0x base size).",
            "medium": "Size for sustained trends with moderate stops (e.g., 0.75-1.5x base size).",
            "long": "Size for strategic positioning with wider stops (e.g., 0.5-2.0x base size)."
        }.get(gs.time_horizon, "")

        return (
            f"You are a professional Risk Manager reviewing {gs.ticker}.\n"
            f"As of {gs.as_of_date}.\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_sizing}\n"
            f"Thesis confidence: {conf:.2f}, stance_score: {stance_score:.2f}, "
            f"estimated volatility: {vol:.2%}.\n\n"
            "Estimate a normalized risk_score (0=low risk, 1=high risk) and suggest sizing_band "
            "(e.g., 0.25x, 0.5x, 1.0x) with rationale and guardrails. "
            "Guardrails should include items like max drawdown %, max slippage bps, and stop_loss guidance."
        )


# ──────────────────────────────────────────────
# Execution Plan
# ──────────────────────────────────────────────
class ExecutionPlan(BasePersona):
    """
    Converts synthesis and risk assessment into concrete execution playbook.
    Produces actionable trade plan with entry, exit, and sizing parameters.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        synthesis = gs.analyses.get("Synthesis", {})
        risk = gs.analyses.get("RiskAssessment", {})

        horizon_execution = {
            "short": "Plan for quick execution with tight stops, intraday to weekly timeframe.",
            "medium": "Plan for phased entry/exit over 1-6 months with moderate stops.",
            "long": "Plan for strategic accumulation/distribution over 1+ years with wide stops."
        }.get(gs.time_horizon, "")

        return (
            f"You are a senior Trader creating an execution plan for {gs.ticker}.\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_execution}\n"
            f"Thesis: {synthesis.get('summary','')}\n"
            f"Confidence: {synthesis.get('confidence',0):.2f}, stance_score: {synthesis.get('stance_score',0):.2f}\n"
            f"Risk profile: {risk.get('risk_score',0):.2f}, sizing_band={risk.get('sizing_band','N/A')}.\n\n"
            "Decide the appropriate action (buy/sell/hold). "
            "Provide rationale, key entry level, invalidation/stop level, and expected horizon. "
            "Output structured JSON with stance, action, rationale, and confidence."
        )


# ──────────────────────────────────────────────
# Final Oversight
# ──────────────────────────────────────────────
class FinalOversight(BasePersona):
    """
    Final governance layer ensuring the trade respects risk discipline and compliance.
    May override the execution plan if guardrails are violated.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        execution = gs.analyses.get("ExecutionPlan", {})
        risk = gs.analyses.get("RiskAssessment", {})
        return (
            f"You are a Chief Risk Officer reviewing a proposed trade for {gs.ticker}.\n"
            f"Time Horizon: {gs.time_horizon.upper()}\n"
            f"Proposed action: {execution.get('action','N/A')} ({execution.get('stance','neutral')}).\n"
            f"Risk score: {risk.get('risk_score',0):.2f}, guardrails={risk.get('guardrails',{})}.\n\n"
            "Approve or override the decision based on whether risk_score > 0.7 or confidence < 0.4. "
            "If you override, explain why and propose a safer alternative (e.g., downgrade to HOLD). "
            "Return structured JSON with fields: final_action, stance, rationale, and override_reason."
        )


# ──────────────────────────────────────────────
# Factory for easy orchestration
# ──────────────────────────────────────────────
def build_execution_personas() -> Dict[str, BasePersona]:
    """
    Create execution and risk personas with consistent configuration.
    Returns personas for risk assessment, execution planning, and final oversight.
    """
    return {
        "RiskAssessment": RiskAssessment(PersonaConfig(
            name="RiskAssessment",
            system_prompt_path="risk_assessment.txt",
            temperature=0.2,
            max_tokens=400,
        )),
        "ExecutionPlan": ExecutionPlan(PersonaConfig(
            name="ExecutionPlan",
            system_prompt_path="execution_plan.txt",
            temperature=0.2,
            max_tokens=500,
        )),
        "FinalOversight": FinalOversight(PersonaConfig(
            name="FinalOversight",
            system_prompt_path="final_oversight.txt",
            temperature=0.2,
            max_tokens=400,
        )),
    }


# Legacy alias for backwards compatibility
def build_trader_personas() -> Dict[str, BasePersona]:
    """Deprecated: Use build_execution_personas() instead."""
    return build_execution_personas()
