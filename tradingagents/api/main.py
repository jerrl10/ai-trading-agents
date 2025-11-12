from __future__ import annotations
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tradingagents.api.routers import research, decisions, status, mcp
from tradingagents.config.logging_config import setup_logging

# Initialize app
app = FastAPI(
    title="TradingAgents API",
    description="Multi-agent trading research and decision system",
    version="1.0.0",
)

# Setup logging
setup_logging(os.getenv("LOG_LEVEL", "INFO"))

# Enable CORS (for frontend dashboards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(research.router)
app.include_router(decisions.router)
app.include_router(status.router)
app.include_router(mcp.router)

@app.on_event("startup")
async def startup_event():
    logging.getLogger(__name__).info("✅ TradingAgents FastAPI service started successfully.")