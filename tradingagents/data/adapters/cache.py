from __future__ import annotations

import os
import json
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, Callable

from tradingagents.config.defaults import DEFAULT_CONFIG

# ---------------------------------------------------------------------
# CACHE DIRECTORY CONFIGURATION
# ---------------------------------------------------------------------

CACHE_DIR = Path(os.getenv("CACHE_DIR", ".cache"))
CACHE_DIR.mkdir(exist_ok=True)


def _make_cache_key(adapter_name: str, params: Dict[str, Any]) -> str:
    """
    Create a deterministic cache key from adapter name and parameters.
    Uses SHA256 hash of the sorted parameter JSON string.
    """
    key_data = json.dumps(params, sort_keys=True)
    digest = hashlib.sha256(key_data.encode()).hexdigest()[:16]
    return f"{adapter_name}_{digest}.json"


def _get_cache_path(adapter_name: str, params: Dict[str, Any]) -> Path:
    """Return full path to cache file."""
    return CACHE_DIR / _make_cache_key(adapter_name, params)


def save_to_cache(adapter_name: str, params: Dict[str, Any], data: Dict[str, Any]) -> None:
    """
    Save adapter output (already JSON-serializable) to cache.
    """
    if not DEFAULT_CONFIG["cache"]["enabled"]:
        return

    path = _get_cache_path(adapter_name, params)
    payload = {
        "timestamp": time.time(),
        "adapter": adapter_name,
        "params": params,
        "data": data,
    }
    path.write_text(json.dumps(payload, indent=2))


def load_from_cache(adapter_name: str, params: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Attempt to load cached payload if valid and not expired.
    Returns None if not found or expired.
    """
    if not DEFAULT_CONFIG["cache"]["enabled"]:
        return None

    path = _get_cache_path(adapter_name, params)
    if not path.exists():
        return None

    ttl = DEFAULT_CONFIG["cache"]["ttl_sec"]
    payload = json.loads(path.read_text())
    age = time.time() - payload["timestamp"]
    if age > ttl:
        # Expired → remove
        try:
            path.unlink()
        except OSError:
            pass
        return None

    return payload["data"]


def cached_call(adapter_name: str, params: Dict[str, Any], fetch_func: Callable[..., Any]) -> Any:
    """
    Generic read-through cache wrapper.

    Example:
    --------
    data = cached_call("prices_yf", {"ticker": "AAPL", "as_of": "2025-11-10"},
                       lambda: fetch_prices("AAPL", date.today(), 60))
    """
    cached = load_from_cache(adapter_name, params)
    if cached is not None:
        return cached

    result = fetch_func()
    try:
        # Convert result to dict if it’s a Pydantic model
        data_dict = result.model_dump() if hasattr(result, "model_dump") else result
        save_to_cache(adapter_name, params, data_dict)
    except Exception:
        pass
    return result


def clear_cache() -> None:
    """Delete all cache files."""
    for file in CACHE_DIR.glob("*.json"):
        try:
            file.unlink()
        except OSError:
            pass