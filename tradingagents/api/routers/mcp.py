from __future__ import annotations
from fastapi import APIRouter, Query
from typing import List

from tradingagents.mcp.engine import FastMCP
from tradingagents.mcp.tools.monitor import summarize_job
from tradingagents.api.schemas.common import ApiResponse

router = APIRouter(prefix="/mcp", tags=["mcp"])
mcp = FastMCP()

@router.post("/submit", response_model=ApiResponse)
async def submit_job(tickers: List[str], as_of_date: str = Query(...)):
    """Start a multi-ticker job."""
    job_id = await mcp.submit_job(tickers, as_of_date)
    return ApiResponse(status="ok", data={"job_id": job_id})

@router.get("/status/{job_id}", response_model=ApiResponse)
async def get_job_status(job_id: str):
    job = mcp.get_job_status(job_id)
    return ApiResponse(status=job.get("status", "not_found"), data=summarize_job(job))