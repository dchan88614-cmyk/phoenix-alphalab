from __future__ import annotations

import pandas as pd


def add_gap_factor(frame: pd.DataFrame) -> pd.DataFrame:
    """Add open-to-prior-close gap percent."""
    data = frame.copy()
    previous_close = data.groupby("ticker")["close"].shift(1)
    data["gap_pct"] = data["open"] / previous_close - 1.0
    return data


def add_all_factors(frame: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Compute all first-stage factors."""
    from src.factors.momentum import add_momentum_factors
    from src.factors.volume import add_volume_factors
    from src.factors.volatility import add_atr_factor

    factor_settings = settings.get("factors", {})
    data = add_volume_factors(
        frame,
        relative_window=int(factor_settings.get("relative_volume_window", 20)),
        change_window=int(factor_settings.get("volume_change_window", 20)),
    )
    data = add_momentum_factors(
        data,
        windows=[int(window) for window in factor_settings.get("momentum_windows", [5, 10, 20])],
        high_lookback_days=int(factor_settings.get("high_lookback_days", 252)),
    )
    data = add_atr_factor(data, window=int(factor_settings.get("atr_window", 14)))
    data = add_gap_factor(data)
    return data

