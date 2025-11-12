from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

import requests

from tradingagents.config.defaults import DEFAULT_CONFIG
from tradingagents.config.providers import get_env_key
from tradingagents.models.types import NewsItem


class AlphaVantageNewsClient:
    """
    Very small wrapper around Alpha Vantage's NEWS_SENTIMENT endpoint.

    A dedicated class keeps request/ratelimit logic isolated from the adapter that
    shapes returned data into `NewsItem` records.
    """

    def __init__(self, api_key: str, *, base_url: str = "https://www.alphavantage.co/query"):
        self.api_key = api_key
        self.base_url = base_url

    def _call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["apikey"] = self.api_key
        resp = requests.get(self.base_url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "Note" in data:
            print("⚠️ AlphaVantage rate limit hit — skipping retry in debug mode.")
            # time.sleep(60)
            # return self._call(params)
            return {"feed": []}
        return data

    def fetch_news(self, ticker: str, *, start: date, end: date, limit: int = 50) -> List[Dict[str, Any]]:
        raw = self._call(
            {
                "function": "NEWS_SENTIMENT",
                "tickers": ticker,
                "from": start.isoformat(),
                "to": end.isoformat(),
            }
        )
        return raw.get("feed", [])[:limit]


@dataclass
class NewsGeneralAdapter:
    """
    High-level adapter that returns canonical `NewsItem` objects for downstream use.
    """

    client: AlphaVantageNewsClient
    window_days: int = DEFAULT_CONFIG["research"]["news_window_days"]

    def fetch(self, ticker: str, as_of_date: date) -> List[NewsItem]:
        start_date = as_of_date - timedelta(days=self.window_days)
        try:
            raw_items = self.client.fetch_news(ticker, start=start_date, end=as_of_date)
            parsed = [self._parse_item(rec) for rec in raw_items]
            cleaned = [item for item in parsed if item is not None]
            return cleaned or [self._no_news_item()]
        except Exception as exc:
            return [self._error_item(str(exc))]

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #

    def _parse_item(self, rec: Dict[str, Any]) -> Optional[NewsItem]:
        try:
            published = self._parse_datetime(
                rec.get("time_published") or rec.get("published_at")
            )
            title = rec.get("title") or rec.get("headline") or "Untitled"
            summary = rec.get("summary") or rec.get("snippet") or ""
            url = rec.get("url") or rec.get("link") or ""
            sentiment = rec.get("overall_sentiment_label_score") or rec.get("sentiment")
            source_name = self._extract_source(rec.get("source"))
            return NewsItem(
                headline=title,
                summary=summary,
                published_at=published,
                source=source_name,
                url=url,
                sentiment=sentiment,
            )
        except Exception:
            return None

    def _parse_datetime(self, value: Optional[str]) -> datetime:
        if not value:
            return datetime.utcnow()
        try:
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except Exception:
            return datetime.utcnow()

    def _extract_source(self, source_field: Any) -> str:
        if isinstance(source_field, dict):
            return (
                source_field.get("name")
                or source_field.get("title")
                or source_field.get("source")
                or "alphavantage"
            )
        if isinstance(source_field, str):
            return source_field or "alphavantage"
        return "alphavantage"

    def _no_news_item(self) -> NewsItem:
        return NewsItem(
            headline="No news found",
            summary="",
            published_at=datetime.utcnow(),
            source="alphavantage",
            url="",
            sentiment=None,
        )

    def _error_item(self, message: str) -> NewsItem:
        return NewsItem(
            headline="AlphaVantage API error",
            summary=message,
            published_at=datetime.utcnow(),
            source="alphavantage",
            url="",
            sentiment=None,
        )


# ------------------------------------------------------------------------- #
# Public entry point
# ------------------------------------------------------------------------- #

def fetch_news_general(ticker: str, as_of_date: date) -> List[NewsItem]:
    """
    Module-level helper retained for backward compatibility.
    """
    adapter = NewsGeneralAdapter(
        client=AlphaVantageNewsClient(api_key=get_env_key("ALPHAVANTAGE_API_KEY"))
    )
    return adapter.fetch(ticker, as_of_date)
