from __future__ import annotations

import pandas as pd


def add_forward_returns(frame: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    """Add future close-to-close returns used as validation labels."""
    data = frame.copy()
    grouped = data.groupby("ticker", group_keys=False)
    for horizon in horizons:
        future_close = grouped["close"].shift(-horizon)
        data[f"fwd_return_{horizon}d"] = future_close / data["close"] - 1.0
    return data

