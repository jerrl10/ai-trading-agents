from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import date, datetime

from tradingagents.config.logging_config import get_logger
from tradingagents.utils.report_paths import get_reports_base

logger = get_logger(__name__)


class StepTracker:
    """
    Persists each node's output (and the final state) to disk for auditing.
    """

    def __init__(self, ticker: str, as_of_date: str):
        self.ticker = _safe(ticker)
        self.as_of_date = _safe(as_of_date)
        self.base_dir = get_reports_base() / self.ticker / self.as_of_date
        self.steps_dir = self.base_dir / "steps"
        if self.steps_dir.exists():
            for artifact in self.steps_dir.glob("*.json"):
                try:
                    artifact.unlink()
                except OSError:
                    pass
        else:
            self.steps_dir.mkdir(parents=True, exist_ok=True)
        self._counter = 0
        logger.info("📂 StepTracker initialized at %s", self.base_dir)

    def record_step(self, node_name: str, payload: Any) -> None:
        """
        Persist one node's output to <reports>/<ticker>/<date>/steps/<n>_<node>.json
        """
        data = _coerce_dict(payload)
        if data is None:
            return

        self._counter += 1
        filename = f"{self._counter:02d}_{_safe(node_name)}.json"
        path = self.steps_dir / filename
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=_json_default),
            encoding="utf-8",
        )
        logger.debug("🧾 Saved step %s → %s", node_name, path)

    def record_final_state(self, state: Any) -> None:
        """Persist the final graph state for convenience."""
        data = _coerce_dict(state)
        if data is None:
            return
        path = self.base_dir / "final_state.json"
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=_json_default),
            encoding="utf-8",
        )
        logger.info("📦 Final state saved: %s", path)


def _safe(value: str) -> str:
    return "".join(c for c in value if c.isalnum() or c in ("-", "_"))


def _coerce_dict(value: Any) -> dict | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            pass
    if isinstance(value, dict):
        return value
    return None


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)
