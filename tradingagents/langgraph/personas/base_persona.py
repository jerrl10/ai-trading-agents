from __future__ import annotations

import json
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel

from tradingagents.langgraph.state import GraphState
from tradingagents.services.llm_service import LLMService
from pathlib import Path
from tradingagents.config.logging_config import get_logger

logger = get_logger(__name__)


# ==========================================================
# 1) PersonaConfig – describes a persona's runtime profile
# ==========================================================

class PersonaConfig(BaseModel):
    """
    Configuration schema for an AI or analytical persona.
    Each persona should define a unique name and (optionally)
    a system prompt template.
    """
    name: str
    system_prompt_path: Optional[str] = None
    model: Optional[str] = "gpt-4-turbo"
    max_tokens: int = 500
    temperature: float = 0.3
    description: Optional[str] = None


# ==========================================================
# 2) BasePersona – the standard runnable node class
# ==========================================================

class BasePersona:
    """
    Base class for all personas (analysts, researchers, traders, etc).

    ✅ Key LangGraph constraint: each persona returns ONLY a unique
       top-level key — not the full state — so parallel nodes never
       collide on shared fields (like `ticker` or `data_sources`).

    Example Output:
        { "a__TechnicalAnalyst": { "stance": "bullish", "rationale": "..."} }
    """

    def __init__(self, cfg: PersonaConfig):
        self.cfg = cfg
        self.name = cfg.name
        self.system_prompt = self._load_system_prompt(cfg.system_prompt_path)
        self.model_name = cfg.model
        self.temperature = cfg.temperature
        self.max_tokens = cfg.max_tokens
        self.llm = LLMService(model=self.model_name)

    # ------------------------------------------------------
    # Required LangGraph entrypoint
    # ------------------------------------------------------
    def __call__(self, state: Union[Dict[str, Any], GraphState]) -> Dict[str, Any]:
        """
        Runs the persona node.
        Reads the current GraphState (or raw dict),
        performs analysis, and returns a single unique key.
        """
        gs = state if isinstance(state, GraphState) else GraphState(**state)

        logger.info("▶️ Persona %s started (ticker=%s)", self.name, gs.ticker)
        context = self._build_context(gs)
        analysis = self._analyze(gs, context)
        stance = analysis.get("stance", "neutral")
        confidence = analysis.get("confidence")
        logger.info(
            "✅ Persona %s finished (stance=%s, confidence=%s)",
            self.name,
            stance,
            confidence if confidence is not None else "n/a",
        )

        # 3️⃣ Return a unique top-level key (no collisions)
        return {f"a__{self.name}": analysis}

    # ------------------------------------------------------
    # Helpers: prompt loading, context building, analysis
    # ------------------------------------------------------

    def _load_system_prompt(self, path: Optional[str]) -> str:
        """
        Loads a system prompt file (if provided) or uses a default template.
        """
        if not path:
            return f"You are persona '{self.name}'. Provide your analysis concisely."
        search_paths = [
            Path(path),
            Path.cwd() / path,
            Path(__file__).resolve().parent.parent / "prompts" / path,
        ]
        for candidate in search_paths:
            if candidate.is_file():
                logger.info("loading prompts locally")
                return candidate.read_text(encoding="utf-8").strip()
        return f"System prompt not found: {path}"

    def _build_context(self, gs: GraphState) -> Dict[str, Any]:
        """
        Construct the structured context from the current GraphState
        that this persona will analyze.
        """
        ctx = {
            "ticker": gs.ticker,
            "as_of_date": gs.as_of_date,
            "data_sources": gs.data_sources,
            "analyses": gs.analyses,
        }
        return ctx

    def render_user_prompt(self, gs: GraphState, context: Optional[Dict[str, Any]] = None) -> str:
        """Subclasses override to format domain-specific prompts."""
        return json.dumps(context or {}, indent=2)

    def _analyze(self, gs: GraphState, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Default implementation: call the shared LLM service with system/user prompts
        and attempt to parse JSON output. Subclasses may override for bespoke logic.
        """
        user_prompt = self.render_user_prompt(gs, context)
        system_prompt = self._format_system_prompt(gs)
        text, usage = self.llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        analysis = self._parse_response(text)
        analysis.setdefault("persona", self.name)
        analysis.setdefault("raw_response", text)
        analysis["usage"] = usage
        return analysis

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Best-effort JSON parsing with safe fallback."""
        text = (text or "").strip()
        if not text:
            return {"stance": "neutral", "summary": "No response"}
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        return {
            "stance": "neutral",
            "summary": text,
        }

    def _format_system_prompt(self, gs: GraphState) -> str:
        template_vars = {
            "ticker": gs.ticker,
            "as_of_date": gs.as_of_date,
        }
        try:
            return self.system_prompt.format(**template_vars)
        except Exception:
            return self.system_prompt


# ==========================================================
# 3) Example Subclass Implementations
# ==========================================================

class TechnicalAnalyst(BasePersona):
    """Example persona performing technical analysis."""
    def _analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        prices = context.get("data_sources", {}).get("market", [])
        if not prices:
            stance = "neutral"
        else:
            # simple mock rule: if last change positive → bullish
            try:
                last_entry = prices[-1]["meta"]
                change = float(last_entry.get("change", 0))
                stance = "bullish" if change > 0 else "bearish"
            except Exception:
                stance = "neutral"

        return {
            "persona": self.name,
            "stance": stance,
            "decision": "buy" if stance == "bullish" else "sell" if stance == "bearish" else "hold",
            "rationale": f"{self.name} evaluated price momentum and found stance={stance}.",
        }


class ValuationAnalyst(BasePersona):
    """Example persona performing valuation-based analysis."""
    def _analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        fundamentals = context.get("data_sources", {}).get("fundamentals", [])
        pe = next((item["meta"]["value"] for item in fundamentals if "pe" in item["id"].lower()), None)
        stance = "bullish" if pe and pe < 20 else "neutral"
        return {
            "persona": self.name,
            "stance": stance,
            "decision": "buy" if stance == "bullish" else "hold",
            "rationale": f"{self.name} found P/E={pe}, stance={stance}.",
        }


# ==========================================================
# 4) Utility: pretty-print persona output
# ==========================================================

def format_persona_output(output: Dict[str, Any]) -> str:
    """
    Nicely formats persona output for CLI or logs.
    """
    try:
        return json.dumps(output, indent=2)
    except Exception:
        return str(output)
