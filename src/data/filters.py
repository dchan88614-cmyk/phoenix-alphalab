from __future__ import annotations

import pandas as pd


def apply_price_liquidity_filters(prices: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Filter rows by close price, dollar volume, and optional market cap.

    These filters use only same-day or trailing historical data columns.
    """
    if prices.empty:
        return prices

    filters = settings.get("filters", {})
    min_close = float(filters.get("min_close_price", 1.0))
    min_dollar_volume = float(filters.get("min_avg_dollar_volume_20d", 0) or 0)
    min_market_cap = filters.get("min_market_cap")
    max_market_cap = filters.get("max_market_cap")

    frame = prices.copy()
    frame["dollar_volume"] = frame["close"] * frame["volume"]
    frame["avg_dollar_volume_20d"] = (
        frame.groupby("ticker")["dollar_volume"]
        .transform(lambda series: series.rolling(20, min_periods=20).mean())
    )

    mask = frame["close"].ge(min_close)
    if min_dollar_volume > 0:
        mask &= frame["avg_dollar_volume_20d"].ge(min_dollar_volume)

    if "market_cap" in frame.columns:
        if min_market_cap is not None:
            mask &= frame["market_cap"].ge(float(min_market_cap))
        if max_market_cap is not None:
            mask &= frame["market_cap"].le(float(max_market_cap))

    return frame.loc[mask].copy()

