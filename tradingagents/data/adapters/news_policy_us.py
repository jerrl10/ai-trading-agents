# tradingagents/data/adapters/news_policy_us.py
from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta
from typing import List, Dict, Any

import requests

from tradingagents.models.types import NewsItem
from tradingagents.config.providers import get_env_key
from tradingagents.config.defaults import DEFAULT_CONFIG
from tradingagents.config.logging_config import get_logger

from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)

class NewsAPIClient:
    """
    Wrapper for NewsAPI.org to fetch U.S. policy/regulatory news.
    """
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_policy_news(self, keywords: str, from_date: date, to_date: date, page_size: int = 100) -> List[Dict[str, Any]]:
        params = {
            "q": keywords,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": self.api_key
        }
        resp = requests.get(self.BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            raise RuntimeError(f"NewsAPI error: {data.get('message')}")
        return data.get("articles", [])

def fetch_policy_news_us(as_of_date: date, keywords: str = "regulation OR bill OR legislation OR SEC OR Fed") -> List[NewsItem]:
    """
    Adapter to fetch U.S. policy / regulatory news for given date window up to as_of_date.

    Returns list of NewsItem models.
    """
    api_key = get_env_key("NEWSAPI_KEY")
    client = NewsAPIClient(api_key=api_key)
    window_days = DEFAULT_CONFIG["research"]["news_window_days"]
    from_date = as_of_date - timedelta(days=window_days)
    to_date = as_of_date

    try:
        raw_articles = client.fetch_policy_news(keywords, from_date, to_date)
        items: List[NewsItem] = []
        for rec in raw_articles:
            published_str = rec.get("publishedAt", "")
            try:
                published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except Exception:
                published = datetime.utcnow()
            summary = rec.get("description") or rec.get("content") or ""
            items.append(
                NewsItem(
                    headline=rec.get("title", "Untitled policy update"),
                    summary=summary,
                    published_at=published,
                    source=rec.get("source", {}).get("name", "newsapi"),
                    url=rec.get("url", ""),
                    sentiment=None,
                )
            )
        return items or _fallback_policy_items("No policy articles returned")
    except Exception as e:
        logger.warning("⚠️ Policy news fetch failed: %s", e)
        return _fallback_policy_items(str(e))


def _fallback_policy_items(message: str) -> List[NewsItem]:
    return [
        NewsItem(
            headline="Policy feed unavailable",
            summary=message,
            published_at=datetime.utcnow(),
            source="newsapi",
            url="",
            sentiment=None,
        ),
        NewsItem(
            headline="Fallback summary",
            summary="Using fallback policy news data",
            published_at=datetime.utcnow(),
            source="system",
            url="",
            sentiment=None,
        ),
    ]
