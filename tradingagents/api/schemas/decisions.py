from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel


class DecisionResult(BaseModel):
    ticker: str
    stance: str
    avg_score: float
    decision: str
    rationale: str