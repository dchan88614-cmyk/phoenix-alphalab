from pathlib import Path

import pandas as pd
import pytest

from src.reports.csv_export import write_csv
from src.research.auto_loop import (
    RESEARCH_ONLY_NOT_TRADABLE,
    CandidateRule,
    add_rank_gap,
    build_candidate_decisions,
    build_window_smoke_results,
    evaluate_candidate,
    generate_candidate_rules,
    row_passes_candidate,
    run_auto_research_loop,
    write_auto_research_summary,
)


def _smoke_row(date, ticker="AAA", rank=1, smoke_score=0.85, fwd_20=0.1):
    return {
        "date": date,
        "rank": rank,
        "ticker": ticker,
        "smoke_score": smoke_score,
        "close": 100.0,
        "atr": 5.0,
        "relative_volume_prev20": 2.0,
        "return_5d": 0.05,
        "return_20d": 0.10,
        "distance_to_52w_high_prev": -0.10,
        "dollar_volume": 50_000_000.0,
        "fwd_return_5d": -0.9,
        "fwd_return_10d": -0.9,
        "fwd_return_20d": fwd_20,
    }


def _price_rows(start="2025-01-01", days=30, ticker="AAA", up=True, base_price=20):
    rows = []
    dates = pd.bdate_range(start, periods=days)
    for index, date in enumerate(dates):
        base = base_price + index if up else base_price
        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "ticker": ticker,
                "open": float(base),
                "high": float(base + 4),
                "low": float(base - 1),
                "close": float(base + 2),
            }
        )
        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "ticker": "SPY",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
            }
        )
    return rows


def _candidate(max_buy_rate=1.0, min_rank_gap=0.0):
    return CandidateRule(
        candidate_id=1,
        max_buy_rate=max_buy_rate,
        min_relative_volume_prev20=1.0,
        min_smoke_score=0.70,
        min_rank_gap=min_rank_gap,
        require_return_5d_positive=True,
        require_return_20d_positive=True,
        distance_to_52w_high_prev_min=-0.25,
        dollar_volume_min=20_000_000,
    )


def test_max_buy_rate_actively_reduces_trades():
    rows = [_smoke_row(f"2025-01-{day:02d}") for day in range(1, 11)]
    decisions = build_candidate_decisions(add_rank_gap(pd.DataFrame(rows)), _candidate(max_buy_rate=0.3))

    assert int(decisions["eligible_buy"].sum()) == 10
    assert int(decisions["is_buy"].sum()) == 3


def test_rank_gap_is_computed_correctly():
    smoke = pd.DataFrame(
        [
            _smoke_row("2025-01-01", ticker="AAA", rank=1, smoke_score=0.90),
            _smoke_row("2025-01-01", ticker="BBB", rank=2, smoke_score=0.82),
        ]
    )

    ranked = add_rank_gap(smoke)

    assert ranked["rank_gap"].iloc[0] == pytest.approx(0.08)


def test_buy_decision_does_not_use_forward_returns():
    row = pd.Series(_smoke_row("2025-01-01", fwd_20=-0.9))
    row["rank_gap"] = 0.10

    assert row_passes_candidate(row, _candidate())


def test_candidate_gate_uses_realized_trade_outcomes_not_forward_labels():
    smoke = pd.DataFrame([_smoke_row("2025-01-01", fwd_20=-0.99)])
    item = {
        "window_start": "2025-01-01",
        "window_end": "2025-01-31",
        "smoke_results": add_rank_gap(smoke),
        "path_data": pd.DataFrame(_price_rows()),
    }

    result, trades = evaluate_candidate(_candidate(), [item], benchmark_ticker="SPY")

    assert not trades.empty
    assert trades.iloc[0]["realized_return"] > 0
    assert "final_buy_count_lt_40" in result["fail_reasons"]
    assert result["status"] == RESEARCH_ONLY_NOT_TRADABLE


def test_auto_loop_evaluates_at_least_50_before_early_stop():
    rows = []
    for date in pd.bdate_range("2025-01-01", periods=5):
        rows.append(_smoke_row(date.strftime("%Y-%m-%d"), ticker="AAA"))
        rows.append(_smoke_row(date.strftime("%Y-%m-%d"), ticker="SPY"))
    data = pd.DataFrame(rows + _price_rows(days=30))

    results, summary, _ = run_auto_research_loop(
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

    assert len({candidate.max_buy_rate for candidate in candidates}) > 1
    assert len({candidate.min_relative_volume_prev20 for candidate in candidates}) > 1
    assert len({candidate.min_smoke_score for candidate in candidates}) > 1
    assert len({candidate.min_rank_gap for candidate in candidates}) > 1
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


def test_auto_loop_writes_csv_and_markdown_outputs(tmp_path):
    data = pd.DataFrame([*_price_rows(days=30), _smoke_row("2025-01-01"), _smoke_row("2025-01-01", ticker="SPY")])
    results, summary, trades = run_auto_research_loop(
        data,
        benchmark_ticker="SPY",
        horizons=[5, 10, 20],
        windows=[("2025-01-01", "2025-01-31")],
        max_candidates=2,
        min_candidates_before_early_stop=1,
        no_improvement_limit=2,
    )
    csv_path = Path(tmp_path) / "auto_research_generations.csv"
    trades_path = Path(tmp_path) / "trade_simulation_trades.csv"
    md_path = Path(tmp_path) / "auto_research_summary.md"

    write_csv(results, csv_path)
    write_csv(trades, trades_path)
    write_auto_research_summary(results, summary, md_path)

    assert csv_path.exists()
    assert trades_path.exists()
    assert md_path.exists()
    assert "Common Fail Reasons" in md_path.read_text(encoding="utf-8")
