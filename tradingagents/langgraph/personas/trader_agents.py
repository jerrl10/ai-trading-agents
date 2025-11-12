from __future__ import annotations
from typing import Any, Dict, Optional
from tradingagents.langgraph.state import GraphState
from tradingagents.langgraph.personas.base_persona import BasePersona, PersonaConfig


# ──────────────────────────────────────────────
# Risk Manager
# ──────────────────────────────────────────────
class RiskManager(BasePersona):
    """
    Evaluates portfolio and instrument-specific risks.
    Uses confidence, volatility, and liquidity to adjust sizing.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        ref = gs.analyses.get("ResearchReferee", {})
        conf = ref.get("confidence", 0.0)
        stance_score = ref.get("stance_score", 0.0)
        # Derive simple volatility proxy (from market data)
        price_data = gs.data_sources.get("market", [])
        vol = len(price_data) and abs(price_data[0]["meta"].get("change", 0.02)) or 0.02
        return (
            f"You are a professional Risk Manager reviewing {gs.ticker}.\n"
            f"As of {gs.as_of_date}.\n"
            f"Research confidence: {conf:.2f}, stance_score: {stance_score:.2f}, "
            f"estimated volatility: {vol:.2%}.\n\n"
            "Estimate a normalized risk_score (0=low risk, 1=high risk) and suggest sizing_band "
            "(e.g., 0.25x, 0.5x, 1.0x) with rationale and guardrails. "
            "Guardrails should include items like max drawdown %, max slippage bps, and stop_loss guidance."
        )


# ──────────────────────────────────────────────
# Trader
# ──────────────────────────────────────────────
class Trader(BasePersona):
    """
    Converts research and risk assessments into concrete trade decisions.
    Produces a playbook-style output.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        ref = gs.analyses.get("ResearchReferee", {})
        risk = gs.analyses.get("RiskManager", {})
        return (
            f"You are a senior Trader implementing {gs.ticker} strategy.\n"
            f"Thesis: {ref.get('summary','')}\n"
            f"Confidence: {ref.get('confidence',0):.2f}, stance_score: {ref.get('stance_score',0):.2f}\n"
            f"Risk profile: {risk.get('risk_score',0):.2f}, sizing_band={risk.get('sizing_band','N/A')}.\n\n"
            "Decide the appropriate action (buy/sell/hold). "
            "Provide rationale, key entry level, invalidation/stop level, and expected horizon. "
            "Output structured JSON with stance, decision, rationale, and confidence."
        )


# ──────────────────────────────────────────────
# Risk Judge
# ──────────────────────────────────────────────
class RiskJudge(BasePersona):
    """
    Final oversight persona ensuring that the trade respects risk discipline.
    May override the trader’s decision if guardrails are violated.
    """
    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        trader = gs.analyses.get("Trader", {})
        risk = gs.analyses.get("RiskManager", {})
        return (
            f"You are a Chief Risk Officer reviewing a proposed trade for {gs.ticker}.\n"
            f"Trader decision: {trader.get('decision','N/A')} ({trader.get('stance','neutral')}).\n"
            f"Risk score: {risk.get('risk_score',0):.2f}, guardrails={risk.get('guardrails',{})}.\n\n"
            "Approve or override the decision based on whether risk_score > 0.7 or confidence < 0.4. "
            "If you override, explain why and propose a safer alternative (e.g., downgrade to HOLD). "
            "Return structured JSON with fields: final_action, stance, rationale, and override_reason."
        )


# ──────────────────────────────────────────────
# Factory for easy orchestration
# ──────────────────────────────────────────────
def build_trader_personas() -> Dict[str, BasePersona]:
    """
    Create execution and risk personas with consistent configuration.
    """
    return {
        "RiskManager": RiskManager(PersonaConfig(
            name="RiskManager",
            system_prompt_path="risk_manager.txt",
            temperature=0.2,
            max_tokens=400,
        )),
        "Trader": Trader(PersonaConfig(
            name="Trader",
            system_prompt_path="trader.txt",
            temperature=0.2,
            max_tokens=500,
        )),
        "RiskJudge": RiskJudge(PersonaConfig(
            name="RiskJudge",
            system_prompt_path="risk_judge.txt",
            temperature=0.2,
            max_tokens=400,
        )),
    }
