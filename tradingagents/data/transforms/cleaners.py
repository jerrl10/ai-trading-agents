from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Tuple

def clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize and clean OHLCV data.

    - Lowercase column names
    - Remove duplicates and NaNs
    - Sort by date
    - Forward-fill small gaps (1-2 days)
    """
    if df.empty:
        return df

    df = df.rename(columns=str.lower)
    df = df.drop_duplicates()
    df = df.dropna(subset=["close"])
    df = df.sort_index()

    # fill small missing gaps
    df = df.ffill(limit=2)
    return df

def detect_outliers_zscore(df: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.DataFrame:
    """
    Flag rows where the specified column has z-score > threshold.
    Returns dataframe with added 'is_outlier' boolean column.
    """
    if column not in df.columns:
        df["is_outlier"] = False
        return df

    mean, std = df[column].mean(), df[column].std()
    df["is_outlier"] = (np.abs((df[column] - mean) / std) > threshold)
    return df

def normalize_volume(df: pd.DataFrame) -> pd.DataFrame:
    """
    Scale volume to millions for readability / model stability.
    """
    if "volume" in df.columns:
        df["volume_millions"] = df["volume"] / 1e6
    return df