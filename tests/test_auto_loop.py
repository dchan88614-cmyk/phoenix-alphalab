from pathlib import Path

import pandas as pd
import pytest

from src.reports.csv_export import write_csv
from src.research.auto_loop import (
    RESEARCH_ONLY_NOT_TRADABLE,
    RESEARCH_QUALIFIED_NOT_LIVE,
    CandidateRule,
    evaluate_candidate,
    row_passes_candidate,
    run_auto_research_loop,
    score_candidate,
    write_auto_research_summary,
)


def _smoke_row(date, ticker="AAA", fwd_20=0.1, excess_20=0.05, smoke_score=0.8):
    return {
        "date": date,
        "rank": 1,
        "ticker": ticker,
        "smoke_score": smoke_score,
        "relative_volume_prev20": 1.5,
        "return_5d": 0.05,
        "return_20d": 0.10,
        "distance_to_52w_high_prev": -0.10,
        "dollar_volume": 50_000_000.0,
        "fwd_return_5d": 0.02,
        "fwd_return_10d": 0.04,
        "fwd_return_20d": fwd_20,
        "excess_return_5d": 0.01,
        "excess_return_10d": 0.02,
        "excess_return_20d": excess_20,
    }


def _candidate(max_buy_rate=1.0):
    return CandidateRule(
        candidate_id=1,
        smoke_score_threshold=0.70,
        require_return_5d_positive=True,
        require_return_20d_positive=True,
        distance_to_52w_high_prev_min=-0.25,
        dollar_volume_min=20_000_000,
        max_buy_rate=max_buy_rate,
    )


def _window_items(window_count=8, rows_per_window=5, excess_20=0.05):
    items = []
    for window_index in range(window_count):
        start = f"2025-{window_index + 1:02d}-01"
        end = f"2025-{window_index + 1:02d}-28"
        rows = [
            _smoke_row(f"2025-{window_index + 1:02d}-{day + 1:02d}", excess_20=excess_20)
            for day in range(rows_per_window)
        ]
        items.append({"window_start": start, "window_end": end, "smoke_results": pd.DataFrame(rows)})
    return items


def test_candidate_failing_buy_count_gate_is_not_tradable():
    result = evaluate_candidate(_candidate(), _window_items(window_count=1, rows_per_window=1))

    assert result["status"] == RESEARCH_ONLY_NOT_TRADABLE
    assert "buy_count_lt_40" in result["fail_reasons"]


def test_candidate_passing_all_gates_is_research_qualified():
    result = evaluate_candidate(_candidate(), _window_items(window_count=8, rows_per_window=5))

    assert result["status"] == RESEARCH_QUALIFIED_NOT_LIVE


def test_removing_best_buy_is_included_in_gate_logic():
    items = _window_items(window_count=8, rows_per_window=5, excess_20=-0.01)
    items[0]["smoke_results"].loc[0, "excess_return_20d"] = 4.0
    items[0]["smoke_results"].loc[0, "fwd_return_20d"] = 4.0

    result = evaluate_candidate(_candidate(), items)

    assert "without_best_20d_avg_excess_not_positive" in result["fail_reasons"]


def test_auto_loop_writes_csv_and_markdown_outputs(tmp_path):
    data = pd.DataFrame(_smoke_row("2025-01-01") for _ in range(2))
    data["ticker"] = ["SPY", "AAA"]
    results, summary = run_auto_research_loop(
        data,
        benchmark_ticker="SPY",
        horizons=[5, 10, 20],
        windows=[("2025-01-01", "2025-01-31")],
        max_candidates=2,
        no_improvement_limit=2,
    )
    csv_path = Path(tmp_path) / "auto_research_generations.csv"
    md_path = Path(tmp_path) / "auto_research_summary.md"

    write_csv(results, csv_path)
    write_auto_research_summary(results, summary, md_path)

    assert csv_path.exists()
    assert md_path.exists()


def test_candidate_scoring_is_deterministic():
    result = evaluate_candidate(_candidate(), _window_items(window_count=8, rows_per_window=5))

    assert score_candidate(result) == pytest.approx(score_candidate(result))


def test_auto_loop_buy_decision_does_not_use_forward_returns():
    row = pd.Series(_smoke_row("2025-01-01", fwd_20=-0.9, excess_20=-0.9))

    assert row_passes_candidate(row, _candidate())
