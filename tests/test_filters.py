import pandas as pd

from src.data.filters import apply_price_liquidity_filters


def test_apply_price_liquidity_filters_removes_low_price_and_low_dollar_volume():
    dates = pd.date_range("2024-01-01", periods=20)
    frame = pd.DataFrame(
        {
            "date": list(dates) * 3,
            "ticker": ["LOWPRICE"] * 20 + ["LOWDV"] * 20 + ["PASS"] * 20,
            "close": [0.5] * 20 + [10.0] * 20 + [10.0] * 20,
            "volume": [1_000_000] * 20 + [10_000] * 20 + [200_000] * 20,
        }
    )
    settings = {
        "filters": {
            "min_close_price": 1.0,
            "min_avg_dollar_volume_20d": 1_000_000,
            "min_market_cap": None,
            "max_market_cap": None,
        }
    }

    result = apply_price_liquidity_filters(frame, settings)

    assert set(result["ticker"]) == {"PASS"}
