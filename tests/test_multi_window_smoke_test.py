from pathlib import Path

import pandas as pd
import pytest

from src.backtest.multi_window_smoke_test import (
    DEFAULT_MULTI_WINDOW_SMOKE_WINDOWS,
    build_multi_window_smoke_test,
    validate_non_overlapping_windows,
    write_multi_window_smoke_markdown,
)
from src.reports.csv_export import write_csv


def _row(date, ticker, factor_value, fwd_5=0.0, fwd_10=0.0, fwd_20=0.0):
    return {
        "date": date,
        "ticker": ticker,
        "relative_volume_prev20": factor_value,
        "return_5d": factor_value,
        "return_20d": factor_value,
        "distance_to_52w_high_prev": factor_value,
        "dollar_volume": factor_value,
        "fwd_return_5d": fwd_5,
        "fwd_return_10d": fwd_10,
        "fwd_return_20d": fwd_20,
    }


def test_multi_window_stats_are_independent_per_window():
    frame = pd.DataFrame(
        [
            _row("2024-01-10", "SPY", 1.0, 0.0, 0.0, 0.0),
            _row("2024-01-10", "AAA", 10.0, 0.1, 0.1, 0.1),
            _row("2024-04-10", "SPY", 1.0, 0.0, 0.0, 0.0),
            _row("2024-04-10", "AAA", 10.0, -0.2, -0.2, -0.2),
        ]
    )

    result = build_multi_window_smoke_test(
        frame,
        benchmark_ticker="SPY",
        horizons=[5, 10, 20],
        universe_ticker_count=50,
        windows=[("2024-01-01", "2024-03-31"), ("2024-04-01", "2024-06-30")],
    )

    assert result.loc[0, "avg_return_20d"] == pytest.approx(0.1)
    assert result.loc[1, "avg_return_20d"] == pytest.approx(-0.2)


def test_multi_window_windows_do_not_overlap():
    validate_non_overlapping_windows(DEFAULT_MULTI_WINDOW_SMOKE_WINDOWS)
    with pytest.raises(ValueError, match="overlap"):
        validate_non_overlapping_windows([("2024-01-01", "2024-03-31"), ("2024-03-01", "2024-04-30")])


def test_multi_window_output_files_exist(tmp_path):
    frame = pd.DataFrame(
        [
            _row("2024-01-10", "SPY", 1.0, 0.0, 0.0, 0.0),
            _row("2024-01-10", "AAA", 10.0, 0.1, 0.1, 0.1),
        ]
    )
    result = build_multi_window_smoke_test(
        frame,
        benchmark_ticker="SPY",
        horizons=[5, 10, 20],
        universe_ticker_count=50,
        windows=[("2024-01-01", "2024-03-31")],
    )
    csv_path = Path(tmp_path) / "multi_window_smoke_test.csv"
    md_path = Path(tmp_path) / "multi_window_smoke_test.md"

    write_csv(result, csv_path)
    write_multi_window_smoke_markdown(result, md_path, benchmark_ticker="SPY")

    assert csv_path.exists()
    assert md_path.exists()


def test_multi_window_marks_insufficient_data():
    frame = pd.DataFrame(
        [
            _row("2024-01-10", "SPY", 1.0, 0.0, 0.0, 0.0),
            _row("2024-01-10", "AAA", 10.0, 0.1, 0.1, 0.1),
        ]
    )

    result = build_multi_window_smoke_test(
        frame,
        benchmark_ticker="SPY",
        horizons=[5, 10, 20],
        universe_ticker_count=50,
        windows=[("2024-01-01", "2024-03-31"), ("2024-04-01", "2024-06-30")],
    )

    assert result.loc[0, "status"] == "ok"
    assert result.loc[1, "status"] == "insufficient_data"
