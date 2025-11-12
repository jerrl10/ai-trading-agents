from __future__ import annotations
from typing import Dict, Any, List
from pydantic import BaseModel


class ResearchResult(BaseModel):
    ticker: str
    analyst_outputs: Dict[str, Dict[str, Any]]
    research_view: Dict[str, Any]
    decision: Dict[str, Any]
    elapsed_sec: float
    status: str