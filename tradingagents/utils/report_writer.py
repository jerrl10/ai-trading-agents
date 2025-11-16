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

    # Calculate total cost from telemetry
    total_cost = data.get("cost_usd", 0.0)
    if total_cost == 0.0:
        # Fallback: calculate from token usage if not set
        prompt_tokens = telemetry.get("prompt", 0)
        completion_tokens = telemetry.get("completion", 0)
        # Rough estimate: $0.015/1K input, $0.06/1K output for gpt-4o-mini
        total_cost = (prompt_tokens * 0.000015) + (completion_tokens * 0.00006)

    # --- Header ---
    md = [
        f"# Trading Analysis Report: {ticker}",
        f"**Analysis Date:** {as_of_date}  |  **Time Horizon:** {data.get('time_horizon', 'medium').capitalize()}",
        "",
        "## Executive Summary",
        "",
        f"**Recommendation:** {decision.get('decision', 'HOLD').upper()}",
        f"**Conviction:** {decision.get('stance', 'neutral').capitalize()} (Confidence: {decision.get('confidence', 0.0):.0%})",
        "",
        _format_rationale(decision.get('rationale', 'No analysis summary available.')),
        "",
        "---",
        "",
        "## Analysis Overview",
        "",
        _render_analysis_summary(analyses),
        "",
        "### 📊 Analysis Metrics",
        f"- **Total Tokens Used:** {telemetry.get('prompt', 0):,} input + {telemetry.get('completion', 0):,} output",
        f"- **Estimated Cost:** ${total_cost:.4f} USD",
        "",
        "---",
        "",
        "## Detailed Analysis",
        "",
    ]

    # --- Analyst details ---
    analyst_order = [
        "TechnicalAnalyst",
        "FundamentalAnalyst",
        "SentimentAnalyst",
        "MacroAnalyst",
        "FlowAnalyst",
        "Synthesis",
        "RiskAssessment",
        "ExecutionPlan",
        "FinalOversight"
    ]

    # Render in priority order
    for name in analyst_order:
        if name in analyses:
            md += _format_analyst_section(name, analyses[name])

    # Render any remaining analysts not in the order
    for name, result in analyses.items():
        if name not in analyst_order:
            md += _format_analyst_section(name, result)

    # --- Data sources summary ---
    if data_sources:
        md += ["", "---", "", "## Data Sources", ""]
        md += _render_data_sources(data_sources)

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


# ───────────────────────────────────────────────
# Formatting helpers
# ───────────────────────────────────────────────

def _format_rationale(rationale: str) -> str:
    """Format the decision rationale with proper wrapping."""
    if not rationale or rationale.strip() == "":
        return "> *No detailed rationale provided.*"
    return f"> {rationale}"


def _render_analysis_summary(analyses: Dict[str, Any]) -> str:
    """Render a high-level summary table of all analyses."""
    if not analyses:
        return "*No analysis data available.*"

    lines = ["| Analyst | Stance | Confidence | Key Insight |", "|---------|---------|------------|-------------|"]

    analyst_order = [
        ("TechnicalAnalyst", "Technical"),
        ("FundamentalAnalyst", "Fundamental"),
        ("SentimentAnalyst", "Sentiment"),
        ("MacroAnalyst", "Macro"),
        ("FlowAnalyst", "Flow"),
        ("Synthesis", "Synthesis"),
    ]

    for key, display_name in analyst_order:
        if key in analyses:
            result = analyses[key]
            stance = result.get("stance", "neutral").capitalize()
            conf = result.get("confidence", 0.0)
            conf_pct = f"{conf:.0%}" if isinstance(conf, (int, float)) else str(conf)
            summary = result.get("summary", "")
            # Extract first sentence as key insight
            key_insight = summary.split(".")[0][:80] + "..." if len(summary) > 80 else summary.split(".")[0]
            lines.append(f"| {display_name} | {stance} | {conf_pct} | {key_insight} |")

    return "\n".join(lines)


def _format_analyst_section(name: str, result: Dict[str, Any]) -> List[str]:
    """Format a single analyst section with clean, readable output."""
    # Map persona names to friendly display names
    display_names = {
        "TechnicalAnalyst": "📈 Technical Analysis",
        "FundamentalAnalyst": "💰 Fundamental Analysis",
        "SentimentAnalyst": "📰 Sentiment Analysis",
        "MacroAnalyst": "🌍 Macro Analysis",
        "FlowAnalyst": "🔄 Flow & Positioning",
        "Synthesis": "🎯 Strategic Synthesis",
        "RiskAssessment": "⚠️ Risk Assessment",
        "ExecutionPlan": "📋 Execution Plan",
        "FinalOversight": "✅ Final Oversight"
    }

    display_name = display_names.get(name, name)
    stance = result.get("stance", "neutral").capitalize()
    conf = result.get("confidence", 0.0)

    # Format confidence properly
    if isinstance(conf, (int, float)):
        conf_display = f"{conf:.0%}" if conf > 0 else "N/A"
    else:
        conf_display = str(conf)

    # Get summary/rationale (FinalOversight uses 'rationale' instead of 'summary')
    summary = result.get("summary") or result.get("rationale", "*No summary provided.*")
    if not summary or summary.strip() == "":
        summary = "*No detailed analysis provided.*"

    reasons = result.get("reasons", [])
    refs = result.get("evidence_refs", [])

    # Special handling for FinalOversight
    if name == "FinalOversight":
        final_action = result.get("final_action", "N/A")
        override = result.get("override_reason", "")

        section = [
            f"### {display_name}",
            "",
            f"**Final Action:** {final_action.upper()}  |  **Stance:** {stance}",
            "",
            f"{summary}",
            "",
        ]

        if override and override.strip():
            section.append(f"**Override Reason:** {override}")
            section.append("")

        return section

    # Standard analyst format
    section = [
        f"### {display_name}",
        "",
        f"**Stance:** {stance}  |  **Confidence:** {conf_display}",
        "",
        f"{summary}",
        "",
    ]

    # Format reasons as clean bullet points
    if reasons:
        section.append("**Key Points:**")
        for reason in reasons:
            if isinstance(reason, dict):
                claim = reason.get("claim", str(reason))
                section.append(f"- {claim}")
            else:
                section.append(f"- {reason}")
        section.append("")

    # Add evidence references if available
    if refs and len(refs) > 0:
        section.append(f"*Evidence: {', '.join(refs)}*")
        section.append("")

    return section


def _render_data_sources(data_sources: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """Render data sources in a clean, readable format."""
    lines = []

    source_order = ["market", "fundamentals", "news", "macro"]

    for src_type in source_order:
        if src_type not in data_sources:
            continue

        items = data_sources[src_type]
        if not items:
            continue

        # Display name mapping
        display_names = {
            "market": "📊 Market Data",
            "fundamentals": "💼 Fundamentals",
            "news": "📰 News & Events",
            "macro": "🌐 Macroeconomic Indicators"
        }

        lines.append(f"### {display_names.get(src_type, src_type.capitalize())}")
        lines.append("")

        # Show first 5 items with clean formatting
        for item in items[:5]:
            formatted = _format_data_item(src_type, item)
            if formatted:
                lines.append(formatted)

        if len(items) > 5:
            lines.append(f"*...and {len(items) - 5} more {src_type} items*")

        lines.append("")

    return lines


def _format_data_item(src_type: str, item: Dict[str, Any]) -> str:
    """Format a single data source item based on its type."""
    meta = item.get("meta", {})

    if src_type == "market":
        date = meta.get("date", "")[:10]  # YYYY-MM-DD only
        close = meta.get("close", 0)
        change = meta.get("change", 0)
        volume = meta.get("volume", 0)
        return f"- **{date}**: ${close:.2f} ({change:+.1%}), Volume: {volume:,}"

    elif src_type == "fundamentals":
        title = item.get("title", "")
        category = meta.get("category", "")
        return f"- {title} ({category})"

    elif src_type == "news":
        headline = meta.get("headline", item.get("title", ""))
        published = meta.get("published_at", "")
        if isinstance(published, str):
            published = published[:10]  # Date only
        source = meta.get("source", "")
        if headline and headline != "No news found":
            return f"- **{headline}** ({source}, {published})"
        return None

    elif src_type == "macro":
        indicator = meta.get("indicator", "")
        value = meta.get("value", 0)
        unit = meta.get("unit", "")
        return f"- **{indicator}**: {value} {unit}"

    return f"- {item.get('title', str(item))}"
