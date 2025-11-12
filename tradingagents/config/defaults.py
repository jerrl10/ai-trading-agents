from __future__ import annotations

import os
from typing import Any, Dict

# ------------------------------------------------------------
# ENVIRONMENT-AWARE CONFIGURATION
# ------------------------------------------------------------

# The DEFAULT_CONFIG dict defines all runtime parameters used across
# the TradingAgents system. Each section represents a subsystem:
#   - llm          → model names, token limits, temperature
#   - vendors      → which data providers to use
#   - research     → default lookbacks, debate rounds, etc.
#   - risk_defaults → baseline portfolio limits
#   - cost_controls → cost caps for OpenAI or other API usage
#   - cache        → caching options
#
# The pattern is:
#     1. Start with safe, conservative defaults.
#     2. Override selectively using environment variables (.env file).
#     3. Never hardcode secrets here — only references.
#
# This approach ensures reproducibility + deployability across local, cloud,
# or container environments.

DEFAULT_CONFIG: Dict[str, Any] = {
    # --------------------------------------------------------
    # 1️⃣ LLM CONFIGURATION
    # --------------------------------------------------------
    "llm": {
        # Which models to use for "deep thinking" and "quick thinking" roles.
        # Deep = slower, more accurate (used by trader, PM).
        # Quick = cheaper, lighter (used by analysts, data summaries).
        "deep_model": os.getenv("MODEL_DEEP", "gpt-4o"),
        "quick_model": os.getenv("MODEL_QUICK", "gpt-4o-mini"),

        # Controls creativity vs determinism.
        # For trading logic, we prefer low temperature for stability.
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),

        # Maximum number of output tokens (helps control API cost).
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1500")),

        # API timeout (in seconds) to avoid hanging calls.
        "timeout": int(os.getenv("LLM_TIMEOUT", "30")),
    },

    # --------------------------------------------------------
    # 2️⃣ DATA VENDORS
    # --------------------------------------------------------
    "vendors": {
        # Which providers to use for each data domain.
        # You can later swap these with OpenRouter, Google APIs, or your own adapters.
        "prices": os.getenv("VENDOR_PRICES", "yfinance"),
        "fundamentals": os.getenv("VENDOR_FUNDAMENTALS", "alphavantage"),
        "news": os.getenv("VENDOR_NEWS", "alphavantage"),
    },

    # --------------------------------------------------------
    # 3️⃣ RESEARCH PARAMETERS
    # --------------------------------------------------------
    "research": {
        # How far back to fetch data (days).
        "lookback_days": int(os.getenv("RESEARCH_LOOKBACK_DAYS", "120")),

        # Window for relevant news around the analysis date.
        "news_window_days": int(os.getenv("RESEARCH_NEWS_WINDOW_DAYS", "7")),

        # Number of back-and-forth exchanges between bull and bear agents.
        "debate_rounds": int(os.getenv("RESEARCH_DEBATE_ROUNDS", "1")),
    },

    # --------------------------------------------------------
    # 4️⃣ RISK MANAGEMENT DEFAULTS
    # --------------------------------------------------------
    "risk_defaults": {
        # Maximum portfolio loss allowed per trade (e.g., 5%).
        "max_loss_pct": float(os.getenv("RISK_MAX_LOSS_PCT", "0.05")),

        # Maximum portfolio allocation to one position.
        "max_position_pct_nav": float(os.getenv("RISK_MAX_POSITION_PCT_NAV", "0.1")),

        # Stop distance in multiples of ATR (Average True Range).
        "atr_multiple_for_stop": float(os.getenv("RISK_ATR_MULTIPLE_FOR_STOP", "2.5")),
    },

    # --------------------------------------------------------
    # 5️⃣ COST CONTROLS
    # --------------------------------------------------------
    "cost_controls": {
        # USD cap per reasoning run (approximate).
        "max_cost_usd": float(os.getenv("COST_MAX_USD", "0.50")),

        # Token limit per agent node; keeps prompts bounded.
        "per_node_token_cap": int(os.getenv("COST_PER_NODE_TOKEN_CAP", "2000")),

        # How to truncate context: "head", "tail", or "middle".
        "truncate_strategy": os.getenv("COST_TRUNCATE_STRATEGY", "middle"),
    },

    # --------------------------------------------------------
    # 6️⃣ CACHING CONFIG
    # --------------------------------------------------------
    "cache": {
        "enabled": os.getenv("CACHE_ENABLED", "true").lower() == "true",
        "ttl_sec": int(os.getenv("CACHE_TTL_SEC", "86400")),  # 24 hours
    },
}