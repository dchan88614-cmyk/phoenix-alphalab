from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED
from src.backtest.forward_returns import add_forward_returns
from src.research.auto_loop import CandidateRule
from src.research.phase1d_entry_rules import (
    PHASE_1D_ROBUSTNESS_IMPROVED_BUT_REQUIRES_GPT_REVIEW,
    apply_candidate_filter,
    build_entry_rule_diagnostics,
    build_filter_backtest_matrix,
    build_loser_feature_attribution,
    build_phase1d_entry_rule_analysis,
    candidate_filters_from_diagnostics,
    phase1d_status,
    write_phase1d_reports,
)


def _rule() -> CandidateRule:
    return CandidateRule(
        candidate_id=34,
        max_buy_rate=0.30,
        min_relative_volume_prev20=1.0,
        min_smoke_score=0.5,
        min_rank_gap=0.0,
        require_return_5d_positive=True,
        require_return_20d_positive=False,
        distance_to_52w_high_prev_min=-0.35,
        dollar_volume_min=1_000_000,
        max_trades_per_ticker_per_year=None,
        max_entry_price=50.0,
    )


def _row(date: pd.Timestamp, ticker: str, close: float, factor: float = 2.0) -> dict:
    return {
        "date": date,
        "ticker": ticker,
        "open": close,
        "high": close * 1.03,
        "low": close * 0.99,
        "close": close,
        "volume": 1_000_000,
        "relative_volume_eod": factor,
        "relative_volume_prev20": factor,
        "volume_change_20d": factor,
        "return_5d": 0.10,
        "return_10d": 0.10,
        "return_20d": 0.10,
        "distance_to_52w_high_eod": -0.10,
        "distance_to_52w_high_prev": -0.10,
        "atr": close * 0.02,
        "gap_pct": 0.0,
        "dollar_volume": 5_000_000 * factor,
    }


def _market_data(periods: int = 80) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for index, date in enumerate(dates):
        rows.append(_row(date, "GOOD", 20.0 + index * 0.10, 2.5))
        rows.append(_row(date, "BAD", 18.0 - index * 0.02, 1.5))
        rows.append(_row(date, "SPY", 100.0 + index * 0.03, 1.0))
    return add_forward_returns(pd.DataFrame(rows), [1, 3, 5, 10, 20])


def _decisions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "sample_id": 0,
                "replay_date": "2024-02-01",
                "decision": "HISTORICAL_BUY_CANDIDATE",
                "ticker": "GOOD",
                "reference_price": 22.0,
                "shares_with_cash": 4,
                "estimated_total_cost": 88.0,
                "estimated_cash_remaining": 12.0,
                "smoke_score": 0.9,
                "decision_strength": 0.8,
                "relative_volume_prev20": 2.0,
                "return_5d": 0.1,
                "return_20d": 0.2,
                "distance_to_52w_high_prev": -0.1,
                "dollar_volume": 5_000_000,
                "forward_return_1d": 0.01,
                "forward_return_3d": 0.02,
                "forward_return_5d": 0.03,
                "forward_return_10d": 0.04,
                "forward_return_20d": 0.10,
            },
            {
                "sample_id": 0,
                "replay_date": "2024-02-15",
                "decision": "HISTORICAL_BUY_CANDIDATE",
                "ticker": "BAD",
                "reference_price": 17.0,
                "shares_with_cash": 5,
                "estimated_total_cost": 85.0,
                "estimated_cash_remaining": 15.0,
                "smoke_score": 0.6,
                "decision_strength": 0.2,
                "relative_volume_prev20": 1.1,
                "return_5d": 0.2,
                "return_20d": 0.3,
                "distance_to_52w_high_prev": -0.3,
                "dollar_volume": 3_000_000,
                "forward_return_1d": -0.01,
                "forward_return_3d": -0.02,
                "forward_return_5d": -0.03,
                "forward_return_10d": -0.04,
                "forward_return_20d": -0.10,
            },
        ]
    )


def _baseline_trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "policy": "baseline_current",
                "replay_date": "2024-02-01",
                "ticker": "GOOD",
                "entry_date": "2024-02-02",
                "entry_price": 22.1,
                "exit_date": "2024-02-10",
                "exit_reason": "TARGET_1",
                "stop_loss": 20.0,
                "target_1": 26.0,
                "target_2": 30.0,
                "pnl_dollars": 10.0,
                "trade_return_pct": 0.1,
                "account_return_pct": 0.1,
                "intraday_stop_breached": False,
                "status": EXECUTED,
                "cash_after_exit": 110.0,
            },
            {
                "policy": "baseline_current",
                "replay_date": "2024-02-15",
                "ticker": "BAD",
                "entry_date": "2024-02-16",
                "entry_price": 17.1,
                "exit_date": "2024-02-20",
                "exit_reason": "STOP",
                "stop_loss": 15.0,
                "target_1": 21.0,
                "target_2": 25.0,
                "pnl_dollars": -8.0,
                "trade_return_pct": -0.08,
                "account_return_pct": -0.08,
                "intraday_stop_breached": True,
                "status": EXECUTED,
                "cash_after_exit": 102.0,
            },
        ]
    )


def test_phase1d_feature_snapshots_do_not_use_future_data():
    data = _market_data()
    first = build_entry_rule_diagnostics(0, _decisions().head(1), _baseline_trades().head(1), data, _rule())
    changed = data.copy()
    changed.loc[changed["date"].gt(pd.Timestamp("2024-02-01")) & changed["ticker"].eq("GOOD"), "close"] = 999.0
    second = build_entry_rule_diagnostics(0, _decisions().head(1), _baseline_trades().head(1), changed, _rule())

    assert first.iloc[0]["close_vs_sma20_pct"] == second.iloc[0]["close_vs_sma20_pct"]
    assert first.iloc[0]["volatility_20d"] == second.iloc[0]["volatility_20d"]


def test_winner_loser_attribution_computes_expected_separation_metrics():
    diagnostics = build_entry_rule_diagnostics(0, _decisions(), _baseline_trades(), _market_data(), _rule())
    attribution = build_loser_feature_attribution(diagnostics)
    row = attribution.loc[(attribution["sample_id"].eq("ALL")) & (attribution["feature_name"].eq("decision_strength"))].iloc[0]

    assert row["winner_count"] == 1
    assert row["loser_count"] == 1
    assert row["loser_minus_winner_mean"] < 0
    assert row["simple_separation_score"] > 0


def test_candidate_filters_use_only_pre_entry_feature_columns():
    diagnostics = build_entry_rule_diagnostics(0, _decisions(), _baseline_trades(), _market_data(), _rule())
    filters = candidate_filters_from_diagnostics(diagnostics, _rule())
    threshold_columns = {item["column"] for item in filters if item.get("kind") == "threshold"}

    assert "forward_return_20d" not in threshold_columns
    assert "baseline_pnl_dollars" not in threshold_columns


def test_filtered_replay_is_chronological_and_respects_one_open_position():
    diagnostics = build_entry_rule_diagnostics(0, _decisions(), _baseline_trades(), _market_data(), _rule())
    filters = [{"filter_name": "none", "filter_description": "No exclusions", "kind": "threshold", "column": "atr_pct", "operator": "le", "threshold": 999.0}]
    matrix, _ = build_filter_backtest_matrix(
        diagnostics,
        _decisions(),
        _market_data(),
        AccountSettings(),
        filters,
        replay_rounds=10,
        phase1_summaries={0: {"buy_count": 2, "no_trade_count": 8}},
    )

    assert matrix.iloc[0]["filtered_buy_count"] <= 2
    assert matrix.iloc[0]["filtered_buy_count"] == matrix.iloc[0]["original_buy_count"]


def test_filter_backtest_matrix_contains_every_sample_filter_combination():
    diagnostics = build_entry_rule_diagnostics(0, _decisions(), _baseline_trades(), _market_data(), _rule())
    diagnostics2 = diagnostics.copy()
    diagnostics2["sample_id"] = 1
    all_diag = pd.concat([diagnostics, diagnostics2], ignore_index=True)
    decisions = pd.concat([_decisions(), _decisions().assign(sample_id=1)], ignore_index=True)
    filters = [
        {"filter_name": "a", "filter_description": "A", "kind": "threshold", "column": "atr_pct", "operator": "le", "threshold": 999.0},
        {"filter_name": "b", "filter_description": "B", "kind": "threshold", "column": "atr_pct", "operator": "le", "threshold": 0.0},
    ]

    matrix, _ = build_filter_backtest_matrix(all_diag, decisions, _market_data(), AccountSettings(), filters, 10, {0: {}, 1: {}})

    assert set(zip(matrix["sample_id"], matrix["filter_name"])) == {(0, "a"), (0, "b"), (1, "a"), (1, "b")}


def test_excluded_decision_audit_records_excluded_winners_and_losers():
    diagnostics = build_entry_rule_diagnostics(0, _decisions(), _baseline_trades(), _market_data(), _rule())
    filter_def = {"filter_name": "all", "filter_description": "Exclude all", "kind": "threshold", "column": "atr_pct", "operator": "le", "threshold": 0.0}
    excluded = apply_candidate_filter(diagnostics, filter_def)

    assert len(excluded) == 2
    assert set(excluded["winner_baseline_simulation"].astype(bool)) == {True, False}


def test_phase1d_status_logic_never_approves_phase2():
    matrix = pd.DataFrame(
        [
            {
                "filter_name": "promising",
                "ending_account_value": 150.0,
                "filtered_buy_count": 20,
                "max_drawdown": -0.20,
                "trade_simulation_accuracy": 0.60,
                "ending_value_excluding_best_decision": 120.0,
                "top_ticker_profit_share": 0.20,
                "excluded_loser_count": 5,
                "excluded_winner_count": 1,
                "average_return_20d": 0.05,
                "passes_phase1d_diagnostic_gate": True,
            }
        ]
    )

    status = phase1d_status(matrix)

    assert status == PHASE_1D_ROBUSTNESS_IMPROVED_BUT_REQUIRES_GPT_REVIEW
    assert "PHASE_2" not in status


def test_phase1d_reports_are_written(tmp_path: Path):
    diagnostics, attribution, matrix, excluded, candidate_md, summary = build_phase1d_entry_rule_analysis(
        _market_data(100),
        AccountSettings(),
        _rule(),
        replay_rounds=5,
        replay_sample_count=2,
    )

    write_phase1d_reports(
        diagnostics,
        attribution,
        matrix,
        excluded,
        candidate_md,
        summary,
        tmp_path / "diagnostics.csv",
        tmp_path / "attribution.csv",
        tmp_path / "matrix.csv",
        tmp_path / "excluded.csv",
        tmp_path / "filters.md",
        tmp_path / "summary.md",
    )

    assert (tmp_path / "diagnostics.csv").exists()
    assert (tmp_path / "attribution.csv").exists()
    assert (tmp_path / "matrix.csv").exists()
    assert (tmp_path / "excluded.csv").exists()
    assert (tmp_path / "filters.md").exists()
    assert (tmp_path / "summary.md").read_text(encoding="utf-8").startswith(
        "PHOENIX NANO PHASE 1D — ENTRY-RULE FAILURE DIAGNOSTICS"
    )
