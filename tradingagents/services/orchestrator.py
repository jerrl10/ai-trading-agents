from __future__ import annotations
import os
import asyncio
from datetime import date
from typing import Any, Dict

from tradingagents.langgraph.runner_langgraph import run_langgraph_pipeline
from tradingagents.config.logging_config import get_logger, setup_logging


logger = get_logger(__name__)


class OrchestratorService:
    """
    Main coordinator for full research and trading analysis.

    Responsibilities:
    - Switch between LangGraph and SimpleGraph execution
    - Validate inputs
    - Run async end-to-end workflow
    - Normalize output for API / dashboard / report
    """

    def __init__(self):
        setup_logging(os.getenv("LOG_LEVEL", "INFO"))

        logger.info("🔧 Orchestrator initialized (LangGraph pipeline)")

    # ─────────────────────────────────────────────────────────────
    # MAIN ENTRYPOINT
    # ─────────────────────────────────────────────────────────────
    async def analyze_single(self, ticker: str, as_of_date: str | None = None) -> Dict[str, Any]:
        """
        Execute the full analysis pipeline for one ticker.

        Parameters
        ----------
        ticker : str
            Stock ticker symbol, e.g., 'AAPL'
        as_of_date : str | None
            ISO date string (YYYY-MM-DD), defaults to today's date.

        Returns
        -------
        Dict[str, Any]
            {
              "status": "ok",
              "ticker": "AAPL",
              "as_of_date": "2025-11-11",
              "decision": {...},
              "analyses": {...},
              "data_sources": {...}
            }
        """
        if not as_of_date:
            as_of_date = date.today().isoformat()

        logger.info(f"🚀 Starting analysis for {ticker} @ {as_of_date}")

        try:
            result = await run_langgraph_pipeline(ticker, as_of_date)
        except Exception as e:
            logger.exception(f"❌ Pipeline failed for {ticker}: {e}")
            return {"status": "error", "ticker": ticker, "message": str(e)}

        # Normalize outputs
        decision = result.get("decision", {})
        analyses = result.get("analyses", {})
        data_sources = result.get("data_sources", {})

        decision_text = f"{decision.get('decision', 'N/A')} ({decision.get('stance', 'neutral')})"
        logger.info(f"✅ Final decision for {ticker}: {decision_text}")

        output = {
            "status": "ok",
            "ticker": ticker,
            "as_of_date": as_of_date,
            "decision": decision,
            "analyses": analyses,
            "data_sources": data_sources,
        }

        # ─────────────────────────────────────────────
        # Optional: automatic report saving
        # ─────────────────────────────────────────────
        if os.getenv("AUTO_SAVE_REPORTS", "false").lower() == "true":
            try:
                from tradingagents.utils.report_writer import save_report
                await save_report(output)
                logger.info(f"📝 Report auto-saved for {ticker}")
            except Exception as e:
                logger.warning(f"⚠️ Report save failed for {ticker}: {e}")

        return output


# ─────────────────────────────────────────────────────────────
# CLI ENTRY (for testing outside FastAPI)
# ─────────────────────────────────────────────────────────────
async def _run_from_cli():
    """
    Run orchestrator from CLI for debugging:
    $ poetry run python -m tradingagents.services.orchestrator AAPL
    """
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    orchestrator = OrchestratorService()
    result = await orchestrator.analyze_single(ticker)
    print(result.get("decision", {}))


if __name__ == "__main__":
    asyncio.run(_run_from_cli())
