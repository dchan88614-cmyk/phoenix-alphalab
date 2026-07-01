from __future__ import annotations

import pandas as pd


def add_volume_factors(frame: pd.DataFrame, relative_window: int, change_window: int) -> pd.DataFrame:
    """Add volume-based factors using trailing windows only."""
    data = frame.copy()
    grouped = data.groupby("ticker", group_keys=False)
    avg_volume = grouped["volume"].transform(
        lambda series: series.rolling(relative_window, min_periods=relative_window).mean()
    )
    data["relative_volume"] = data["volume"] / avg_volume
    data["volume_change_20d"] = grouped["volume"].pct_change(change_window)
    data["dollar_volume"] = data["close"] * data["volume"]
    return data

