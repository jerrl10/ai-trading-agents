from __future__ import annotations
import os
import json
from typing import Any, Dict, Optional


class LLMUsage:
    """Lightweight container for token and cost tracking."""
    def __init__(self, prompt_tokens=0, completion_tokens=0, cost_usd=0.0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_usd = cost_usd

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": self.cost_usd,
        }


class LLMService:
    """
    Provider-agnostic LLM client.

    best practices built in:
    - reads model/key from environment variables so nothing hard-coded
    - mock mode (no API key) for deterministic offline runs
    - returns both text and usage dict for GraphState accounting
    - minimal dependency footprint (plain requests)
    """

    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.mock = not bool(self.api_key)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> tuple[str, Dict[str, Any]]:
        """Return (text, usage_dict)."""

        # ---------- mock mode for dev/CI ----------
        if self.mock:
            text = f"[MOCK:{self.model}] {user_prompt[:200]}"
            usage = LLMUsage(
                prompt_tokens=len(user_prompt) // 4,
                completion_tokens=len(text) // 4,
                cost_usd=0.0,
            )
            return text, usage.to_dict()

        # ---------- real API call ----------
        import requests

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            # fall back to deterministic mock so offline runs don't crash
            text = f"[LLM-OFFLINE:{exc.__class__.__name__}] {user_prompt[:200]}"
            usage = LLMUsage(
                prompt_tokens=len(user_prompt) // 4,
                completion_tokens=len(text) // 4,
                cost_usd=0.0,
            )
            return text, usage.to_dict()

        data = response.json()

        message = data.get("choices", [{}])[0].get("message", {})
        text = (message.get("content") or "").strip()

        usage_raw = data.get("usage") or {}
        usage = LLMUsage(
            prompt_tokens=int(usage_raw.get("prompt_tokens", 0)),
            completion_tokens=int(usage_raw.get("completion_tokens", 0)),
            cost_usd=0.0,  # you can compute cost later from a model-pricing map
        )
        return text, usage.to_dict()
