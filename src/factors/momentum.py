from __future__ import annotations

import pandas as pd


def add_momentum_factors(frame: pd.DataFrame, windows: list[int], high_lookback_days: int) -> pd.DataFrame:
    """Add trailing return and 52-week high distance factors."""
    data = frame.copy()
    grouped = data.groupby("ticker", group_keys=False)

    for window in windows:
        data[f"return_{window}d"] = grouped["close"].pct_change(window)

    rolling_high = grouped["high"].transform(
        lambda series: series.rolling(high_lookback_days, min_periods=min(60, high_lookback_days)).max()
    )
    data["distance_to_52w_high"] = data["close"] / rolling_high - 1.0
    return data

