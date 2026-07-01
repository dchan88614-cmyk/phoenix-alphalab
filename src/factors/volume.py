from __future__ import annotations

import pandas as pd


def add_volume_factors(frame: pd.DataFrame, relative_window: int, change_window: int) -> pd.DataFrame:
    """Add volume-based factors with explicit EOD and prior-window timing."""
    data = frame.copy()
    grouped = data.groupby("ticker", group_keys=False)
    avg_volume_eod = grouped["volume"].transform(
        lambda series: series.rolling(relative_window, min_periods=relative_window).mean()
    )
    avg_volume_prev = grouped["volume"].transform(
        lambda series: series.shift(1).rolling(relative_window, min_periods=relative_window).mean()
    )
    data["relative_volume_eod"] = data["volume"] / avg_volume_eod
    data["relative_volume_prev20"] = data["volume"] / avg_volume_prev
    data["relative_volume"] = data["relative_volume_eod"]
    data["volume_change_20d"] = grouped["volume"].pct_change(change_window)
    data["dollar_volume"] = data["close"] * data["volume"]
    return data
