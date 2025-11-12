from __future__ import annotations
from fastapi import APIRouter, Query
from tradingagents.services.orchestrator import OrchestratorService
from tradingagents.api.schemas.research import ResearchResult
from tradingagents.api.schemas.common import ApiResponse

router = APIRouter(prefix="/research", tags=["research"])
orchestrator = OrchestratorService()

@router.get("/analyze", response_model=ApiResponse)
async def analyze_research(ticker: str = Query(...), as_of_date: str = Query(...)):
    """Run the full multi-agent analysis pipeline for one ticker."""
    result = await orchestrator.analyze_single(ticker, as_of_date)
    return ApiResponse(status=result.get("status", "ok"), data=result)