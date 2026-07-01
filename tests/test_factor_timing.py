import pandas as pd
import pytest

from src.factors.momentum import add_momentum_factors
from src.factors.volume import add_volume_factors


def test_relative_volume_prev20_excludes_current_day_volume():
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"] * 21,
            "volume": [100.0] * 20 + [1000.0],
            "close": [10.0] * 21,
        }
    )

    result = add_volume_factors(frame, relative_window=20, change_window=20)

    assert result.loc[20, "relative_volume_prev20"] == pytest.approx(10.0)
    assert result.loc[20, "relative_volume_eod"] == pytest.approx(1000.0 / 145.0)


def test_distance_to_52w_high_prev_excludes_current_day_high():
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"] * 253,
            "high": [100.0] * 252 + [200.0],
            "close": [150.0] * 253,
        }
    )

    result = add_momentum_factors(frame, windows=[5], high_lookback_days=252)

    assert result.loc[252, "distance_to_52w_high_prev"] == pytest.approx(0.5)
    assert result.loc[252, "distance_to_52w_high_eod"] == pytest.approx(-0.25)
