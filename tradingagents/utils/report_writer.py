from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from textwrap import indent
from typing import Dict, Any, List

from tradingagents.config.logging_config import get_logger
from tradingagents.utils.report_paths import get_reports_base

REPORTS_BASE = get_reports_base()

logger = get_logger(__name__)


# ───────────────────────────────────────────────
# Utility
# ───────────────────────────────────────────────
def _safe_filename(s: str) -> str:
    return "".join(c for c in s if c.isalnum() or c in ("-", "_"))


# ───────────────────────────────────────────────
# Main async function
# ───────────────────────────────────────────────
async def save_report(payload: Dict[str, Any]) -> None:
    """
    Persist a research/trading analysis result as JSON + Markdown.

    Parameters
    ----------
    payload : dict
        Output from OrchestratorService.analyze_single()
    """
    ticker = _safe_filename(payload.get("ticker", "UNKNOWN"))
    as_of_date = payload.get("as_of_date") or datetime.utcnow().date().isoformat()

    base_dir = REPORTS_BASE / ticker
    base_dir.mkdir(parents=True, exist_ok=True)

    # File paths
    json_path = base_dir / f"{as_of_date}.json"
    md_path = base_dir / f"{as_of_date}.md"

    # ───────────── Save JSON ─────────────
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=_json_default)

    # ───────────── Generate Markdown ─────────────
    md_text = render_markdown_report(payload)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    logger.info("📝 Report saved (json=%s, md=%s)", json_path, md_path)


# ───────────────────────────────────────────────
# Markdown rendering
# ───────────────────────────────────────────────
def render_markdown_report(data: Dict[str, Any]) -> str:
    ticker = data.get("ticker", "N/A")
    as_of_date = data.get("as_of_date", "N/A")
    decision = data.get("decision", {})
    analyses = data.get("analyses", {})
    data_sources = data.get("data_sources", {})
    telemetry = data.get("token_usage", {})
    notes = data.get("notes", [])

    # --- Header ---
    md = [
        f"# Trading Report — {ticker}",
        f"**Date:** {as_of_date}",
        "",
        f"**Final Decision:** {decision.get('decision', 'N/A').upper()} ({decision.get('stance', 'neutral')})",
        "",
        f"> {decision.get('rationale', 'No summary available.')}",
        "",
        "### 📊 Telemetry",
        f"- Tokens (prompt): {telemetry.get('prompt', 0)}",
        f"- Tokens (completion): {telemetry.get('completion', 0)}",
        f"- Est. cost (USD): {data.get('cost_usd', 0.0):.4f}",
        "",
        "---",
        "## 🧩 Analyses Summary",
    ]

    # --- Analyst details ---
    for name, result in analyses.items():
        stance = result.get("stance", "neutral")
        conf = result.get("confidence", "N/A")
        summary = result.get("summary", "")
        reasons = result.get("reasons", [])
        refs = result.get("evidence_refs", [])
        section = [
            f"### {name}",
            f"**Stance:** {stance}  |  **Confidence:** {conf}",
            "",
            f"**Summary:** {summary}",
        ]
        if reasons:
            section += ["", "**Reasons:**", indent("\n".join(f"- {r}" for r in reasons), "  ")]
        if refs:
            section += ["", "**Evidence Refs:**", indent(", ".join(refs), "  ")]
        md += ["\n".join(section), ""]
    md += ["---", "## 📰 Data Sources Overview"]

    # --- Data sources summary ---
    for src_type, items in data_sources.items():
        md.append(f"### {src_type.capitalize()} ({len(items)})")
        for s in items[:5]:
            title = s.get("title") or "(no title)"
            meta = s.get("meta", {})
        md.append(f"- {title} — {meta}")
        md.append("")

    # --- Execution notes ---
    if notes:
        md += ["---", "## 🗒 Execution Notes"]
        md += [f"- {line}" for line in notes]

    # --- Step artifacts ---
    steps = _list_step_files(ticker, as_of_date)
    if steps:
        md += ["---", "## 🧱 Step Artifacts"]
        md += ["The following JSON files capture each node output in execution order:"]
        md += [f"- `{step}`" for step in steps]

    md += ["---", f"_Generated automatically at {datetime.utcnow().isoformat()} UTC_"]

    return "\n".join(md)


def _list_step_files(ticker: str, as_of_date: str) -> List[str]:
    """Return relative step filenames for the ticker/date run."""
    steps_dir = REPORTS_BASE / _safe_filename(ticker) / _safe_filename(as_of_date) / "steps"
    if not steps_dir.exists():
        return []
    return [f"steps/{p.name}" for p in sorted(steps_dir.iterdir()) if p.is_file()]


def _json_default(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)
