from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

import yfinance as yf
import pandas as pd
from pydantic import BaseModel, Field
from tradingagents.config.logging_config import get_logger

logger = get_logger(__name__)


# ---------- Data Models ----------


class PriceSnapshot(BaseModel):
    """A single point-in-time price record."""

    date: str
    close: float
    change: float
    volume: Optional[int] = None


class PriceSeries(BaseModel):
    """Collection of historical price records."""

    series: List[PriceSnapshot] = Field(default_factory=list)
    ticker: str


# ---------- Helper: safe scalar extraction ----------


def _safe_scalar(value):
    """
    Extract a scalar value safely from a pandas object.

    Handles both scalar and single-element Series cases.
    """
    if isinstance(value, pd.Series):
        return value.iloc[0]
    return value


# ---------- Adapter Function ----------


def fetch_prices(
    ticker: str,
    as_of_date: date,
    lookback_days: int = 10,
    auto_adjust: bool = False,
) -> PriceSeries:
    """
    Fetch recent OHLCV market data for a ticker using Yahoo Finance.
    Ensures robust handling of pandas type changes in 2.x.
    """
    start_date = as_of_date - timedelta(days=lookback_days)
    end_date = as_of_date + timedelta(days=1)
    logger.info(f"start data is {start_date}, end date is {end_date}")
    try:
        df = yf.download(
            ticker,
            start=start_date.isoformat(),
            end=(end_date).isoformat(),
            progress=False,
            auto_adjust=auto_adjust,
        )
    except Exception as exc:
        logger.warning("⚠️ Price download failed for %s: %s", ticker, exc)
        return _mock_price_series(ticker, as_of_date)

    if df.empty:
        logger.warning("⚠️ No price data found for %s. Using synthetic series.", ticker)
        return _mock_price_series(ticker, as_of_date)

    # Keep the original date column so downstream snapshots retain actual timestamps.
    df = df.reset_index(drop=False)

    snapshots: List[PriceSnapshot] = []
    for i in range(1, len(df)):
        # ✅ Safe scalar extraction (avoids FutureWarning)
        prev_close = float(_safe_scalar(df.iloc[i - 1]["Close"]))
        close = float(_safe_scalar(df.iloc[i]["Close"]))
        change = (close - prev_close) / prev_close if prev_close != 0 else 0.0

        # Some Yahoo Finance DataFrames may use 'Date' or numeric index.
        if "Date" in df.columns:
            date_str = str(_safe_scalar(df.loc[i, "Date"]))
        else:
            date_str = str(as_of_date)

        volume_val = None
        if "Volume" in df.columns:
            volume_raw = _safe_scalar(df.loc[i, "Volume"])
            # convert only if valid numeric
            volume_val = int(volume_raw) if pd.notna(volume_raw) else None

        snapshots.append(
            PriceSnapshot(
                date=date_str,
                close=close,
                change=change,
                volume=volume_val,
            )
        )

    return PriceSeries(ticker=ticker, series=snapshots)


def _mock_price_series(ticker: str, as_of_date: date, points: int = 10) -> PriceSeries:
    """Create deterministic synthetic data when the vendor is unavailable."""
    snapshots: List[PriceSnapshot] = []
    base_price = 100.0
    for i in range(points):
        day = as_of_date - timedelta(days=points - i)
        change = 0.01 * ((-1) ** i)
        base_price *= 1 + change
        snapshots.append(
            PriceSnapshot(
                date=day.isoformat(),
                close=round(base_price, 2),
                change=change,
                volume=1_000_000 + i * 10_000,
            )
        )
    return PriceSeries(ticker=ticker, series=snapshots)
