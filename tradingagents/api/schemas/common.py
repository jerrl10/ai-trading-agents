from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ApiResponse(BaseModel):
    status: str
    timestamp: datetime = datetime.utcnow()
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None