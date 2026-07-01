from pathlib import Path

import pandas as pd
import pytest

from src.backtest.smoke_test import build_smoke_test, summarize_smoke_test, write_smoke_test_markdown
from src.main import read_watchlist
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


def test_smoke_test_does_not_use_forward_return_for_ranking():
    frame = pd.DataFrame(
        [
            _row("2024-01-31", "SPY", 1.0, 0.01, 0.01, 0.01),
            _row("2024-01-31", "FACTOR_WINNER", 10.0, -0.5, -0.5, -0.5),
            _row("2024-01-31", "FWD_WINNER", 1.0, 2.0, 2.0, 2.0),
        ]
    )

    result = build_smoke_test(frame, benchmark_ticker="SPY", horizons=[5, 10, 20], smoke_days=1, top_n=1)

    assert result.loc[0, "ticker"] == "FACTOR_WINNER"


def test_smoke_test_selects_at_most_top_5_per_date():
    rows = [_row("2024-01-31", "SPY", 1.0, 0.01, 0.01, 0.01)]
    rows.extend(_row("2024-01-31", f"AAA{i}", float(i), 0.01, 0.01, 0.01) for i in range(10))
    frame = pd.DataFrame(rows)

    result = build_smoke_test(frame, benchmark_ticker="SPY", horizons=[5, 10, 20], smoke_days=1, top_n=5)

    assert result.groupby("date").size().max() == 5


def test_smoke_test_benchmark_excess_return_is_correct():
    frame = pd.DataFrame(
        [
            _row("2024-01-31", "SPY", 1.0, 0.03, 0.04, 0.05),
            _row("2024-01-31", "AAA", 10.0, 0.08, 0.01, -0.05),
        ]
    )

    result = build_smoke_test(frame, benchmark_ticker="SPY", horizons=[5, 10, 20], smoke_days=1, top_n=5)

    assert result.loc[0, "excess_return_5d"] == pytest.approx(0.05)
    assert result.loc[0, "excess_return_10d"] == pytest.approx(-0.03)
    assert result.loc[0, "excess_return_20d"] == pytest.approx(-0.10)


def test_smoke_test_output_files_exist(tmp_path):
    frame = pd.DataFrame(
        [
            _row("2024-01-31", "SPY", 1.0, 0.03, 0.04, 0.05),
            _row("2024-01-31", "AAA", 10.0, 0.08, 0.01, -0.05),
        ]
    )
    result = build_smoke_test(frame, benchmark_ticker="SPY", horizons=[5, 10, 20], smoke_days=1, top_n=5)
    summary = summarize_smoke_test(result, horizons=[5, 10, 20])
    csv_path = Path(tmp_path) / "smoke_test.csv"
    md_path = Path(tmp_path) / "smoke_test.md"

    write_csv(result, csv_path)
    write_smoke_test_markdown(
        result,
        summary,
        md_path,
        benchmark_ticker="SPY",
        horizons=[5, 10, 20],
        universe_ticker_count=50,
    )

    assert csv_path.exists()
    assert md_path.exists()


def test_watchlist_can_be_read(tmp_path):
    watchlist = Path(tmp_path) / "watchlist.txt"
    watchlist.write_text("aapl\nNVDA\n# comment\nsmci # inline comment\n", encoding="utf-8")

    assert read_watchlist(watchlist) == ["AAPL", "NVDA", "SMCI"]


def test_universe_count_enters_smoke_report(tmp_path):
    frame = pd.DataFrame(
        [
            _row("2024-01-31", "SPY", 1.0, 0.03, 0.04, 0.05),
            _row("2024-01-31", "AAA", 10.0, 0.08, 0.01, -0.05),
        ]
    )
    result = build_smoke_test(frame, benchmark_ticker="SPY", horizons=[5, 10, 20], smoke_days=1, top_n=5)
    summary = summarize_smoke_test(result, horizons=[5, 10, 20])
    md_path = Path(tmp_path) / "smoke_test.md"

    write_smoke_test_markdown(result, summary, md_path, "SPY", [5, 10, 20], universe_ticker_count=42)

    content = md_path.read_text(encoding="utf-8")
    assert "Universe ticker count: 42" in content


def test_small_universe_warning_enters_smoke_report(tmp_path):
    frame = pd.DataFrame(
        [
            _row("2024-01-31", "SPY", 1.0, 0.03, 0.04, 0.05),
            _row("2024-01-31", "AAA", 10.0, 0.08, 0.01, -0.05),
        ]
    )
    result = build_smoke_test(frame, benchmark_ticker="SPY", horizons=[5, 10, 20], smoke_days=1, top_n=5)
    summary = summarize_smoke_test(result, horizons=[5, 10, 20])
    md_path = Path(tmp_path) / "smoke_test.md"

    write_smoke_test_markdown(result, summary, md_path, "SPY", [5, 10, 20], universe_ticker_count=29)

    content = md_path.read_text(encoding="utf-8")
    assert "WARNING: Universe too small; smoke test is not representative." in content


def test_excluding_best_single_trade_average_outputs(tmp_path):
    frame = pd.DataFrame(
        [
            _row("2024-01-31", "SPY", 1.0, 0.0, 0.0, 0.0),
            _row("2024-01-31", "AAA", 10.0, 1.0, 1.0, 1.0),
            _row("2024-01-31", "BBB", 9.0, 0.1, 0.1, 0.1),
        ]
    )
    result = build_smoke_test(frame, benchmark_ticker="SPY", horizons=[5, 10, 20], smoke_days=1, top_n=5)
    summary = summarize_smoke_test(result, horizons=[5, 10, 20])
    md_path = Path(tmp_path) / "smoke_test.md"

    write_smoke_test_markdown(result, summary, md_path, "SPY", [5, 10, 20], universe_ticker_count=50)

    content = md_path.read_text(encoding="utf-8")
    assert "## Result Excluding Best Single Trade" in content
    assert "10.00%" in content
