from __future__ import annotations

"""Autoload project .env files for every Python process (tests, CLI, LangGraph)."""

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    """
    Ensure tracing/API keys are available even when third-party tools spawn Python.
    """
    root = Path(__file__).resolve().parent
    env_files = [root / ".env", root / ".env.local"]
    loaded = False
    for env_path in env_files:
        if env_path.is_file():
            load_dotenv(env_path, override=False)
            loaded = True
    if loaded and os.getenv("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGCHAIN_API_KEY", os.environ["LANGSMITH_API_KEY"])
        os.environ.setdefault("LANGSMITH_TRACING_V2", "true")


_load_env()
