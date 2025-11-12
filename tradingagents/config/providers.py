# tradingagents/config/providers.py
from __future__ import annotations

import os
from typing import Any, Dict

from pydantic import BaseModel

from .defaults import DEFAULT_CONFIG


# ------------------------------------------------------------
#  PROVIDER REGISTRY MODEL
# ------------------------------------------------------------

class ProviderRegistry(BaseModel):
    """
    Registry object containing instantiated clients and adapters.

    Theory:
        This acts as a lightweight dependency container.
        Agents can request the resources they need (LLM client, data adapter)
        without caring about how they were created or configured.

    Example:
        registry.llm_clients["deep"]
        registry.data_adapters["prices"]
    """
    llm_clients: Dict[str, Any]
    data_adapters: Dict[str, Any]


# ------------------------------------------------------------
#  ENVIRONMENT UTILITIES
# ------------------------------------------------------------

def get_env_key(name: str) -> str:
    """
    Fetch an environment variable, ensuring it exists.

    Why:
        - Centralized validation for sensitive credentials.
        - Makes missing keys explicit early (fail fast principle).
    """
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return value


# ------------------------------------------------------------
#  LLM PROVIDER FACTORY
# ------------------------------------------------------------

def make_llm_providers() -> Dict[str, Any]:
    """
    Create logical 'handles' for LLM providers.

    Why:
        - Keeps agents independent from specific API implementations.
        - Allows swapping between OpenAI, Anthropic, Gemini, or local models.

    For now:
        This returns *stub identifiers* (strings). In Step 4,
        you’ll replace these with real LLM client objects
        that expose `.complete()` and `.structured()` methods.
    """
    cfg = DEFAULT_CONFIG["llm"]

    return {
        "deep": {
            "model": cfg["deep_model"],
            "temperature": cfg["temperature"],
            "max_tokens": cfg["max_tokens"],
        },
        "quick": {
            "model": cfg["quick_model"],
            "temperature": cfg["temperature"],
            "max_tokens": cfg["max_tokens"],
        },
    }


# ------------------------------------------------------------
#  DATA ADAPTER FACTORY
# ------------------------------------------------------------

def make_data_adapters() -> Dict[str, Any]:
    """
    Return references to data vendor configurations.

    Why:
        - Abstracts vendor-specific implementation details.
        - Lets you easily extend to new sources (e.g., Polygon, Tiingo, custom DB).

    For now:
        The adapters are just string placeholders. Later, you’ll replace these
        with actual callable adapter classes in the `data/adapters/` folder.
    """
    vendors = DEFAULT_CONFIG["vendors"]

    return {
        "prices": vendors["prices"],
        "fundamentals": vendors["fundamentals"],
        "news": vendors["news"],
    }


# ------------------------------------------------------------
#  REGISTRY BUILDER
# ------------------------------------------------------------

def build_provider_registry() -> ProviderRegistry:
    """
    Assemble and return a ProviderRegistry instance.

    Why:
        - Centralizes initialization logic.
        - Keeps startup predictable and testable.

    Usage:
        registry = build_provider_registry()
        print(registry.llm_clients["quick"])
    """
    registry = ProviderRegistry(
        llm_clients=make_llm_providers(),
        data_adapters=make_data_adapters(),
    )
    return registry