from pathlib import Path

import pandas as pd
import pytest

from src.reports.csv_export import write_csv
from src.research.auto_loop import (
    RESEARCH_ONLY_NOT_TRADABLE,
    RESEARCH_QUALIFIED_NOT_LIVE,
    CandidateRule,
    add_path_diagnostics,
    build_window_smoke_results,
    evaluate_candidate,
    generate_candidate_rules,
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
        "close": 100.0,
        "atr": 5.0,
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


def test_auto_loop_evaluates_at_least_50_before_early_stop():
    data = pd.DataFrame(_smoke_row("2025-01-01") for _ in range(2))
    data["ticker"] = ["SPY", "AAA"]

    results, summary = run_auto_research_loop(
        data,
        benchmark_ticker="SPY",
        horizons=[5, 10, 20],
        windows=[("2025-01-01", "2025-01-31")],
        max_candidates=60,
        min_candidates_before_early_stop=50,
        no_improvement_limit=1,
    )

    assert len(results) >= 50
    assert summary["total_candidates_evaluated"] >= 50


def test_first_20_candidate_rules_are_diverse():
    candidates = generate_candidate_rules(20)

    assert len({candidate.smoke_score_threshold for candidate in candidates}) > 1
    assert len({candidate.max_buy_rate for candidate in candidates}) > 1
    assert len({candidate.distance_to_52w_high_prev_min for candidate in candidates}) > 1
    assert len({candidate.dollar_volume_min for candidate in candidates}) > 1
    assert len({candidate.require_return_5d_positive for candidate in candidates}) > 1
    assert len({candidate.require_return_20d_positive for candidate in candidates}) > 1


def test_warmup_data_does_not_create_signals_before_research_start():
    rows = []
    for date in ["2023-12-28", "2024-01-03", "2024-01-04"]:
        rows.append(_smoke_row(date, ticker="SPY"))
        rows.append(_smoke_row(date, ticker="AAA"))
    window_results = build_window_smoke_results(
        pd.DataFrame(rows),
        benchmark_ticker="SPY",
        horizons=[5, 10, 20],
        windows=[("2024-01-01", "2024-01-31")],
    )

    smoke = window_results[0]["smoke_results"]
    assert not smoke.empty
    assert pd.to_datetime(smoke["date"]).min() >= pd.Timestamp("2024-01-01")


def test_path_diagnostics_do_not_control_buy_decisions():
    smoke = pd.DataFrame([_smoke_row("2025-01-01", ticker="AAA")])
    path_data = pd.DataFrame(
        [
            {"date": "2025-01-01", "ticker": "AAA", "high": 101.0, "low": 99.0},
            {"date": "2025-01-02", "ticker": "AAA", "high": 102.0, "low": 91.0},
        ]
    )
    item = {"window_start": "2025-01-01", "window_end": "2025-01-31", "smoke_results": smoke, "path_data": path_data}

    with_stop_hit = evaluate_candidate(_candidate(), [item])

    no_stop_path = path_data.copy()
    no_stop_path.loc[1, "low"] = 99.0
    item_without_stop = {
        "window_start": "2025-01-01",
        "window_end": "2025-01-31",
        "smoke_results": smoke,
        "path_data": no_stop_path,
    }
    without_stop_hit = evaluate_candidate(_candidate(), [item_without_stop])

    assert with_stop_hit["buy_count"] == without_stop_hit["buy_count"] == 1
    assert with_stop_hit["stop_hit_rate_20d"] == pytest.approx(1.0)
    assert without_stop_hit["stop_hit_rate_20d"] == pytest.approx(0.0)


def test_add_path_diagnostics_calculates_target_hits():
    decisions = pd.DataFrame([_smoke_row("2025-01-01", ticker="AAA")])
    decisions["is_buy"] = True
    path_data = pd.DataFrame(
        [
            {"date": "2025-01-01", "ticker": "AAA", "high": 100.0, "low": 100.0},
            {"date": "2025-01-02", "ticker": "AAA", "high": 111.0, "low": 99.0},
            {"date": "2025-01-03", "ticker": "AAA", "high": 116.0, "low": 98.0},
        ]
    )

    diagnosed = add_path_diagnostics(decisions, path_data)

    assert diagnosed.loc[0, "target_1_hit_20d"]
    assert diagnosed.loc[0, "target_2_hit_20d"]


def test_auto_research_summary_includes_common_fail_reasons(tmp_path):
    results = pd.DataFrame(
        [
            {
                "candidate_id": 1,
                "status": RESEARCH_ONLY_NOT_TRADABLE,
                "risk_adjusted_score": 1.0,
                "smoke_score_threshold": 0.7,
                "require_return_5d_positive": True,
                "require_return_20d_positive": True,
                "distance_to_52w_high_prev_min": -0.25,
                "dollar_volume_min": 20_000_000,
                "max_buy_rate": 1.0,
                "buy_count": 1,
                "overall_buy_rate": 0.5,
                "overall_20d_avg_excess": 0.01,
                "overall_20d_win_rate": 0.5,
                "worst_20d_return": -0.7,
                "avg_excess_excluding_best_buy_20d": 0.0,
                "stop_hit_rate_20d": 1.0,
                "target_1_hit_rate_20d": 0.0,
                "target_2_hit_rate_20d": 0.0,
                "fail_reasons": "worst_20d_return_lte_minus_60pct",
            }
        ]
    )
    summary = {
        "total_candidates_available": 1,
        "total_candidates_tested": 1,
        "total_candidates_evaluated": 1,
        "candidates_passed_gate": 0,
        "candidates_failed_gate": 1,
        "early_stop_reason": "test",
    }
    md_path = Path(tmp_path) / "auto_research_summary.md"

    write_auto_research_summary(results, summary, md_path)

    assert "Common Fail Reasons" in md_path.read_text(encoding="utf-8")
