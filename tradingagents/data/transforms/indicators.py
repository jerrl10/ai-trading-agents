from __future__ import annotations

import pandas as pd
import numpy as np
import ta  # Technical Analysis library

from typing import Dict, Any


def compute_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute a core set of technical indicators.

    Parameters
    ----------
    df : pd.DataFrame
        Price dataframe with columns: open, high, low, close, volume.
        Must be sorted by date ascending.

    Returns
    -------
    Dict[str, Any]
        A dictionary with the latest indicator values.
    """

    # Defensive checks
    if df.empty or not {"open", "high", "low", "close", "volume"}.issubset(df.columns):
        return {}

    # -------------------------------
    # 1️⃣ Momentum: Relative Strength Index (RSI)
    # -------------------------------
    rsi_indicator = ta.momentum.RSIIndicator(close=df["close"], window=14)
    df["rsi"] = rsi_indicator.rsi()

    # -------------------------------
    # 2️⃣ Trend: Moving Averages (EMA, SMA)
    # -------------------------------
    df["ema_20"] = ta.trend.EMAIndicator(close=df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(close=df["close"], window=50).ema_indicator()
    df["sma_200"] = ta.trend.SMAIndicator(close=df["close"], window=200).sma_indicator()

    # -------------------------------
    # 3️⃣ Volatility: Average True Range (ATR)
    # -------------------------------
    atr_indicator = ta.volatility.AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=14
    )
    df["atr"] = atr_indicator.average_true_range()

    # -------------------------------
    # 4️⃣ Trend strength: MACD
    # -------------------------------
    macd_indicator = ta.trend.MACD(close=df["close"])
    df["macd"] = macd_indicator.macd()
    df["macd_signal"] = macd_indicator.macd_signal()
    df["macd_hist"] = macd_indicator.macd_diff()

    # -------------------------------
    # 5️⃣ Volatility proxy: rolling std
    # -------------------------------
    df["volatility"] = df["close"].pct_change().rolling(20).std()

    # -------------------------------
    # 6️⃣ Summarize latest values
    # -------------------------------
    latest = df.iloc[-1]

    indicators = {
        "rsi": round(latest["rsi"], 2),
        "ema_20": round(latest["ema_20"], 2),
        "ema_50": round(latest["ema_50"], 2),
        "sma_200": round(latest["sma_200"], 2),
        "macd": round(latest["macd"], 3),
        "macd_signal": round(latest["macd_signal"], 3),
        "atr": round(latest["atr"], 3),
        "volatility": round(latest["volatility"], 4),
    }

    return indicators