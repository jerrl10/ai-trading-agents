from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, Field, ConfigDict


class GraphState(BaseModel):
    """
    LangGraph shared state object.

    Why Pydantic here?
    - Strong typing → catches mistakes early (missing keys, wrong shapes).
    - JSON-serializable → easy to log, persist to reports.
    - Schema as documentation → every persona knows what exists.

    Design rules:
    1) Inputs & raw data are separated from reasoning outputs.
    2) Persona outputs are stored under `analyses[persona_name]` to keep provenance.
    3) Telemetry (tokens/cost) is part of the state for end-to-end accounting.
    """

    model_config = ConfigDict(extra="allow")

    # ---- Inputs (immutable during a run) -----------------------------------
    ticker: str = Field(..., frozen=True)
    as_of_date: str  # ISO date string "YYYY-MM-DD" to avoid tz headaches
    time_horizon: str = Field(
        default="medium",
        description="Trading time horizon: 'short' (days-weeks), 'medium' (1-6 months), 'long' (1+ years)"
    )

    # ---- Raw sources (populated by the data-loading node) ------------------
    # Store as plain dict/list so state is trivially serializable to JSON.
    price_snapshot: Dict[str, Any] = Field(default_factory=dict)
    fundamentals: Dict[str, Any] = Field(default_factory=dict)
    news_general: List[Dict[str, Any]] = Field(default_factory=list)
    news_policy: List[Dict[str, Any]] = Field(default_factory=list)
    data_sources: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)

    # ---- Ephemeral mapper outputs (fan-in helpers) -------------------------
    m__market: List[Dict[str, Any]] = Field(default_factory=list)
    m__fundamentals: List[Dict[str, Any]] = Field(default_factory=list)
    m__news: List[Dict[str, Any]] = Field(default_factory=list)
    m__macro: List[Dict[str, Any]] = Field(default_factory=list)

    # ---- Persona outputs (LLM or rule-based summaries) ---------------------
    # Key by persona name for analyses dict consolidation
    analyses: Dict[str, Any] = Field(default_factory=dict)

    # Analysis stage personas
    a__TechnicalAnalyst: Dict[str, Any] = Field(default_factory=dict)
    a__FundamentalAnalyst: Dict[str, Any] = Field(default_factory=dict)
    a__SentimentAnalyst: Dict[str, Any] = Field(default_factory=dict)
    a__MacroAnalyst: Dict[str, Any] = Field(default_factory=dict)
    a__FlowAnalyst: Dict[str, Any] = Field(default_factory=dict)

    # Synthesis & execution personas
    a__Synthesis: Dict[str, Any] = Field(default_factory=dict)
    a__RiskAssessment: Dict[str, Any] = Field(default_factory=dict)
    a__ExecutionPlan: Dict[str, Any] = Field(default_factory=dict)
    a__FinalOversight: Dict[str, Any] = Field(default_factory=dict)

    # ---- Aggregation & final action ----------------------------------------
    research_view: Dict[str, Any] = Field(default_factory=dict)  # synthesized thesis, confidence, key drivers
    decision: Dict[str, Any] = Field(default_factory=dict)       # stance, action, rationale (for UI/API)

    # ---- Telemetry & notes --------------------------------------------------
    token_usage: Dict[str, int] = Field(
        default_factory=lambda: {"prompt": 0, "completion": 0}
    )  # cumulative token counts across personas
    cost_usd: float = 0.0                                          # cumulative cost across personas
    notes: List[str] = Field(default_factory=list)                  # free-form execution notes

    # ---- Convenience helpers (optional but handy) --------------------------
    def add_usage(self, prompt_tokens: int = 0, completion_tokens: int = 0, cost: float = 0.0) -> None:
        """Accumulate LLM usage/cost in a single, safe place."""
        self.token_usage["prompt"] = int(self.token_usage.get("prompt", 0)) + int(prompt_tokens)
        self.token_usage["completion"] = int(self.token_usage.get("completion", 0)) + int(completion_tokens)
        self.cost_usd = float(self.cost_usd) + float(cost)

    def add_analysis(self, persona: str, content: Any) -> None:
        """Record a persona’s output under a consistent key."""
        self.analyses[persona] = content

    def set_research_view(self, view: Dict[str, Any]) -> None:
        """Set the synthesized research view (thesis, confidence, drivers)."""
        self.research_view = view or {}

    def set_decision(self, payload: Dict[str, Any]) -> None:
        """Set the final trading decision payload."""
        self.decision = payload or {}

    def log(self, message: str) -> None:
        """Append an execution note (useful for debugging/audit)."""
        self.notes.append(message)
