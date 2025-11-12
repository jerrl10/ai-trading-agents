from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field

from .types import Inputs, AnalystReport, ResearchView, TradePlan


# ------------------------------------------------------------
# RISK AND PORTFOLIO GOVERNANCE MODELS
# ------------------------------------------------------------

class RiskCheck(BaseModel):
    """
    Quantitative validation of a proposed TradePlan.

    Why:
        - Allows deterministic risk controls independent of the LLM.
        - Ensures all trade decisions pass through a reproducible compliance gate.
    """
    ok: bool = Field(..., description="Whether the plan passes all risk thresholds.")
    reasons: List[str] = Field(
        default_factory=list, description="List of any failed checks or warnings."
    )
    limits: Dict[str, float] = Field(
        default_factory=dict,
        description="Numeric thresholds applied during the check (e.g., max_loss_pct).",
    )


class PMDecision(BaseModel):
    """
    Final approval step, representing the portfolio manager’s discretion.

    Why:
        - Acts as the governance layer after risk validation.
        - Separates 'quantitative pass' from 'strategic approval'.
    """
    approved: bool = Field(..., description="Whether the trade is approved for execution.")
    notes: str = Field(
        default="",
        description="Optional qualitative reasoning or rejection rationale.",
    )


# ------------------------------------------------------------
# FINAL DECISION MODEL
# ------------------------------------------------------------

class Decision(BaseModel):
    """
    Aggregate object representing the complete reasoning trace and outcome
    for one asset as of a given date.

    Why:
        - This is the canonical artifact that downstream consumers (API, MCP,
          backtesting engine) will use.
        - It ensures reproducibility and explainability by including audit logs,
          cost tracking, and all intermediate reasoning results.
    """
    inputs: Inputs = Field(..., description="Original analysis inputs.")
    reports: List[AnalystReport] = Field(
        default_factory=list,
        description="Individual analyst reports (fundamental, technical, etc.).",
    )
    views: List[ResearchView] = Field(
        default_factory=list,
        description="Bull/Bear research arguments and confidence scores.",
    )
    plan: TradePlan = Field(..., description="Proposed trading plan.")
    risk: RiskCheck = Field(..., description="Quantitative risk validation results.")
    pm: PMDecision = Field(..., description="Final approval or rejection.")
    audit_log: List[str] = Field(
        default_factory=list,
        description="Chronological record of agent execution and key messages.",
    )
    costs: Dict[str, float] = Field(
        default_factory=dict,
        description="Resource usage metrics (tokens, API calls, cost in USD).",
    )

    class Config:
        """Ensures consistent JSON export and immutability."""
        frozen = True