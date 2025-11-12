from __future__ import annotations
from typing import Dict, Any
from datetime import datetime

def summarize_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a concise snapshot for API responses or dashboards.
    """
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "tickers": job.get("tickers", []),
        "as_of_date": job.get("as_of_date"),
        "finished_at": job.get("finished_at"),
        "results_count": len(job.get("results", [])) if "results" in job else 0,
        "timestamp": datetime.utcnow().isoformat(),
    }