from __future__ import annotations
import asyncio
import logging
import uuid
from typing import Dict, Any, List
from datetime import datetime

from tradingagents.services.orchestrator import OrchestratorService

logger = logging.getLogger(__name__)

class FastMCP:
    """
    Lightweight multi-control-plane to orchestrate many concurrent analysis tasks.
    Designed to scale horizontally and to manage job metadata.
    """

    def __init__(self):
        self._orchestrator = OrchestratorService()
        self._jobs: Dict[str, Dict[str, Any]] = {}

    async def submit_job(self, tickers: List[str], as_of_date: str) -> str:
        """Register and asynchronously start a multi-ticker analysis job."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {"tickers": tickers, "as_of_date": as_of_date, "status": "running"}
        logger.info(f"[FastMCP] Job {job_id} started for {len(tickers)} tickers")

        asyncio.create_task(self._run_job(job_id, tickers, as_of_date))
        return job_id

    async def _run_job(self, job_id: str, tickers: List[str], as_of_date: str) -> None:
        try:
            results = await self._orchestrator.analyze_batch(tickers, as_of_date)
            self._jobs[job_id].update({
                "status": "completed",
                "results": results,
                "finished_at": datetime.utcnow().isoformat()
            })
            logger.info(f"[FastMCP] Job {job_id} completed.")
        except Exception as e:
            logger.exception(f"[FastMCP] Job {job_id} failed: {e}")
            self._jobs[job_id]["status"] = "error"
            self._jobs[job_id]["error"] = str(e)

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Return current metadata and results if finished."""
        return self._jobs.get(job_id, {"status": "not_found"})