# tradingagents/data/adapters/macro_av.py
from __future__ import annotations

import time
from datetime import date, datetime
from typing import List, Dict, Any, Optional

import requests
from pydantic import BaseModel

from tradingagents.config.providers import get_env_key
from tradingagents.config.logging_config import get_logger

logger = get_logger(__name__)


class MacroIndicator(BaseModel):
    """
    A single macro economic indicator data point.
    """
    indicator: str  # e.g., "CPI", "GDP", "UNEMPLOYMENT"
    value: float
    date: str
    unit: str  # e.g., "percent", "index", "billions"
    interval: str  # e.g., "monthly", "quarterly", "annual"


class AlphaVantageMacroClient:
    """
    Wrapper for Alpha Vantage economic indicators endpoint.

    Supported functions:
    - REAL_GDP: Real GDP (quarterly)
    - REAL_GDP_PER_CAPITA: Real GDP per capita (quarterly)
    - TREASURY_YIELD: Treasury yield (daily/monthly)
    - FEDERAL_FUNDS_RATE: Federal funds rate (daily/monthly)
    - CPI: Consumer Price Index (monthly)
    - INFLATION: Inflation rate (annual)
    - RETAIL_SALES: Retail sales (monthly)
    - DURABLES: Durable goods orders (monthly)
    - UNEMPLOYMENT: Unemployment rate (monthly)
    - NONFARM_PAYROLL: Nonfarm payroll (monthly)
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API call with rate limit handling."""
        params["apikey"] = self.api_key
        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # Handle rate limiting
            if "Note" in data:
                logger.warning("⚠️ Alpha Vantage rate limit hit, waiting 60s...")
                time.sleep(60)
                return self._call(params)

            # Handle API errors
            if "Error Message" in data:
                logger.error("❌ Alpha Vantage error: %s", data["Error Message"])
                return {}

            return data
        except Exception as e:
            logger.error("❌ Macro API call failed: %s", e)
            return {}

    def fetch_indicator(
        self,
        function: str,
        interval: str = "monthly",
        maturity: Optional[str] = None
    ) -> List[MacroIndicator]:
        """
        Fetch a single economic indicator.

        Args:
            function: Alpha Vantage function name (e.g., "CPI", "UNEMPLOYMENT")
            interval: Data interval (monthly, quarterly, annual)
            maturity: For treasury yields (e.g., "10year")
        """
        params = {
            "function": function,
            "interval": interval,
        }

        # Treasury yield requires maturity parameter
        if function == "TREASURY_YIELD" and maturity:
            params["maturity"] = maturity

        raw = self._call(params)

        if not raw or "data" not in raw:
            logger.warning("⚠️ No data returned for %s", function)
            return []

        items: List[MacroIndicator] = []
        data_key = "data"

        for record in raw.get(data_key, [])[:12]:  # Last 12 data points
            try:
                value_str = record.get("value", "")
                if not value_str or value_str == ".":
                    continue

                items.append(
                    MacroIndicator(
                        indicator=function,
                        value=float(value_str),
                        date=record.get("date", ""),
                        unit=raw.get("unit", "unknown"),
                        interval=interval,
                    )
                )
            except (ValueError, TypeError) as e:
                logger.debug("Skipping invalid macro data point: %s", e)
                continue

        return items


def fetch_macro_indicators(as_of_date: date) -> List[MacroIndicator]:
    """
    Fetch key macro economic indicators relevant for equity trading.

    Returns consolidated list of recent macro data points across:
    - Inflation (CPI)
    - Interest rates (Federal Funds Rate, 10Y Treasury)
    - Growth (GDP)
    - Employment (Unemployment, Nonfarm Payroll)
    - Consumer activity (Retail Sales)

    Args:
        as_of_date: Reference date for data lookback

    Returns:
        List of MacroIndicator objects
    """
    api_key = get_env_key("ALPHAVANTAGE_API_KEY")
    client = AlphaVantageMacroClient(api_key=api_key)

    all_indicators: List[MacroIndicator] = []

    # Define indicators to fetch with their configurations
    indicators_config = [
        ("CPI", "monthly", None),
        ("INFLATION", "annual", None),
        ("FEDERAL_FUNDS_RATE", "monthly", None),
        ("TREASURY_YIELD", "monthly", "10year"),
        ("UNEMPLOYMENT", "monthly", None),
        ("REAL_GDP", "quarterly", None),
        ("RETAIL_SALES", "monthly", None),
    ]

    for function, interval, maturity in indicators_config:
        try:
            logger.info("🔹 Fetching macro indicator: %s", function)
            indicators = client.fetch_indicator(function, interval, maturity)
            if indicators:
                # Only keep the most recent data point
                all_indicators.append(indicators[0])
                logger.info("✅ Fetched %s: %.2f", function, indicators[0].value)
            else:
                logger.warning("⚠️ No data for %s", function)
        except Exception as e:
            logger.error("❌ Failed to fetch %s: %s", function, e)
            continue

    # If we couldn't fetch any real data, return fallback indicators
    if not all_indicators:
        logger.warning("⚠️ All macro API calls failed, using fallback data")
        all_indicators = _get_fallback_macro_data()

    return all_indicators


def _get_fallback_macro_data() -> List[MacroIndicator]:
    """
    Fallback macro data when API is unavailable.
    Uses realistic recent values for offline/testing mode.
    """
    return [
        MacroIndicator(
            indicator="CPI",
            value=314.0,
            date=datetime.now().strftime("%Y-%m-%d"),
            unit="index",
            interval="monthly",
        ),
        MacroIndicator(
            indicator="INFLATION",
            value=3.1,
            date=datetime.now().strftime("%Y-%m-%d"),
            unit="percent",
            interval="annual",
        ),
        MacroIndicator(
            indicator="FEDERAL_FUNDS_RATE",
            value=5.33,
            date=datetime.now().strftime("%Y-%m-%d"),
            unit="percent",
            interval="monthly",
        ),
        MacroIndicator(
            indicator="TREASURY_YIELD",
            value=4.25,
            date=datetime.now().strftime("%Y-%m-%d"),
            unit="percent",
            interval="monthly",
        ),
        MacroIndicator(
            indicator="UNEMPLOYMENT",
            value=3.7,
            date=datetime.now().strftime("%Y-%m-%d"),
            unit="percent",
            interval="monthly",
        ),
        MacroIndicator(
            indicator="REAL_GDP",
            value=22000.0,
            date=datetime.now().strftime("%Y-%m-%d"),
            unit="billions",
            interval="quarterly",
        ),
    ]
