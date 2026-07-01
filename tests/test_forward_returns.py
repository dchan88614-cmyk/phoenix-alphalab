import pandas as pd
import pytest

from src.backtest.forward_returns import add_forward_returns


def test_forward_returns_use_future_close_as_label():
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3),
            "ticker": ["AAA", "AAA", "AAA"],
            "close": [10.0, 11.0, 12.0],
        }
    )
    result = add_forward_returns(frame, [1])
    assert result.loc[0, "fwd_return_1d"] == pytest.approx(0.1)
    assert result.loc[1, "fwd_return_1d"] == pytest.approx(12.0 / 11.0 - 1.0)
    assert pd.isna(result.loc[2, "fwd_return_1d"])
