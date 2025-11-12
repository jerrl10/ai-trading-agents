from fastapi import APIRouter
from datetime import datetime
from tradingagents.api.schemas.common import ApiResponse

router = APIRouter(prefix="/status", tags=["status"])

@router.get("", response_model=ApiResponse)
async def health_check():
    return ApiResponse(status="ok", data={"server_time": datetime.utcnow().isoformat()})