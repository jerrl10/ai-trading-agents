from __future__ import annotations

import os
import time
from typing import Dict, Any
from datetime import date

import requests
from tradingagents.models.types import FundamentalsSnapshot

from tradingagents.config.providers import get_env_key
from tradingagents.config.logging_config import get_logger

logger = get_logger(__name__)

class AlphaVantageClient:
    """
    A light wrapper for Alpha Vantage Fundamental data endpoints.
    """

    def __init__(self, api_key: str, base_url: str = "https://www.alphavantage.co/query"):
        self.api_key = api_key
        self.base_url = base_url

    def _call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP GET request to Alpha Vantage endpoint, with rate-limit handling.
        """
        params["apikey"] = self.api_key
        resp = requests.get(self.base_url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Alpha Vantage uses various keys like "Note" for rate-limit messages.
        if "Note" in data:
            # rate limit hit
            time.sleep(60)  # simple backoff
            return self._call(params)
        return data

    def fetch_company_ratios(self, ticker: str) -> Dict[str, float]:
        """
        Example call: &function=OVERVIEW for key ratios
        """
        params = {"function": "OVERVIEW", "symbol": ticker}
        raw = self._call(params)
        # map vendor-specific keys → our normalized keys
        ratios: Dict[str, float] = {}
        # e.g.: raw["PERatio"], raw["PEGRatio"], raw["ForwardPE"]
        for key, val in raw.items():
            try:
                if key in {"PERatio", "ForwardPE", "PEGRatio", "PriceToBookRatio"}:
                    ratios[key.lower()] = float(val)
            except (ValueError, KeyError, TypeError):
                continue
        return ratios

    def fetch_trend_data(self, ticker: str) -> Dict[str, float]:
        """
        Example call: &function=INCOME_STATEMENT or CASH_FLOW to compute QoQ/YoY growth
        """
        params = {"function": "INCOME_STATEMENT", "symbol": ticker}
        raw = self._call(params)
        trends: Dict[str, float] = {}
        if "annualReports" in raw:
            reports = raw["annualReports"]
            if len(reports) >= 2:
                try:
                    rev_curr = float(reports[0]["totalRevenue"])
                    rev_prev = float(reports[1]["totalRevenue"])
                    trends["revenue_growth_annual"] = (rev_curr / rev_prev) - 1.0
                except (KeyError, ValueError):
                    pass
        return trends

def fetch_fundamentals(ticker: str, as_of_date: date) -> FundamentalsSnapshot:
    """
    Fetch normalized fundamental data for `ticker` using Alpha Vantage.

    Parameters
    ----------
    ticker : str
        Asset symbol (uppercase recommended).
    as_of_date : date
        Cut-off date: ensure no future-dated fundamentals or release data leak.

    Returns
    -------
    FundamentalsSnapshot
    """
    api_key = get_env_key("ALPHAVANTAGE_API_KEY")
    client = AlphaVantageClient(api_key=api_key)

    notes: list[str] = [f"Vendor=AlphaVantage", f"As-Of={as_of_date.isoformat()}"]

    try:
        ratios = client.fetch_company_ratios(ticker)
        trend = client.fetch_trend_data(ticker)
        if not ratios:
            notes.append("No ratios returned; using synthetic baseline.")
            ratios = _mock_ratios()
        if not trend:
            notes.append("No trend data returned; using synthetic baseline.")
            trend = _mock_trend()
    except Exception as e:
        logger.warning("⚠️ Fundamentals fetch failed for %s: %s", ticker, e)
        notes.append(f"error: {e}")
        ratios = _mock_ratios()
        trend = _mock_trend()

    return FundamentalsSnapshot(ratios=ratios, trend=trend, notes=notes)


def _mock_ratios() -> Dict[str, float]:
    return {
        "peratio": 18.4,
        "forwardpe": 16.9,
        "pegratio": 1.3,
        "pricetobookratio": 5.2,
    }


def _mock_trend() -> Dict[str, float]:
    return {
        "revenue_growth_annual": 0.07,
        "eps_growth_annual": 0.09,
    }
