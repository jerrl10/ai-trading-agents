from __future__ import annotations
from fastapi import APIRouter, Path, Query
from tradingagents.services.orchestrator import OrchestratorService
from tradingagents.api.schemas.decisions import DecisionResult
from tradingagents.api.schemas.common import ApiResponse

router = APIRouter(prefix="/decisions", tags=["decisions"])
orchestrator = OrchestratorService()

@router.get("/ticker/{ticker}", response_model=ApiResponse)
async def get_decision(
    ticker: str = Path(...),
    as_of_date: str = Query(...)
):
    """Return the trading decision only (simplified)."""
    result = await orchestrator.analyze_single(ticker, as_of_date)
    decision = result.get("decision", {})
    return ApiResponse(status=result.get("status", "ok"), data={"ticker": ticker, "decision": decision})