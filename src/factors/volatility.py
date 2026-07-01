from __future__ import annotations

import pandas as pd


def add_atr_factor(frame: pd.DataFrame, window: int) -> pd.DataFrame:
    """Add ATR and ATR percent using current and prior OHLC data."""
    data = frame.copy()
    previous_close = data.groupby("ticker")["close"].shift(1)
    high_low = data["high"] - data["low"]
    high_prev_close = (data["high"] - previous_close).abs()
    low_prev_close = (data["low"] - previous_close).abs()

    data["true_range"] = pd.concat(
        [high_low, high_prev_close, low_prev_close],
        axis=1,
    ).max(axis=1)
    data["atr"] = data.groupby("ticker")["true_range"].transform(
        lambda series: series.rolling(window, min_periods=window).mean()
    )
    data["atr_pct"] = data["atr"] / data["close"]
    return data

