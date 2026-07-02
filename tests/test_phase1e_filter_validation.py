from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED
from src.backtest.forward_returns import add_forward_returns
from src.research.auto_loop import CandidateRule
from src.research.phase1e_filter_validation import (
    PHASE_1E_FILTER_ROBUSTNESS_IMPROVED_REQUIRES_GPT_REVIEW,
    apply_phase1e_filter,
    build_filter_backtest_matrix,
    build_phase1e_filter_validation,
    calibration_gate_pass,
    deterministic_sample_split,
    holdout_gate_pass,
    phase1e_filter_family,
    phase1e_status,
    select_holdout_filters,
    write_phase1e_reports,
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


def _market_data(periods: int = 120) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for index, date in enumerate(dates):
        rows.append(_row(date, "GOOD", 20.0 + index * 0.08, 2.5))
        rows.append(_row(date, "BAD", 18.0 - index * 0.01, 1.5))
        rows.append(_row(date, "SPY", 100.0 + index * 0.03, 1.0))
    return add_forward_returns(pd.DataFrame(rows), [1, 3, 5, 10, 20])


def _diagnostics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "sample_id": 0,
                "replay_date": "2024-01-02",
                "ticker": "GOOD",
                "entry_date": "2024-01-03",
                "entry_price": 20.0,
                "reference_price": 20.0,
                "sector_or_theme": "AI / software",
                "smoke_score": 0.95,
                "volatility_20d": 0.04,
                "forward_return_1d": 0.01,
                "forward_return_3d": 0.02,
                "forward_return_5d": 0.03,
                "forward_return_10d": 0.04,
                "forward_return_20d": 0.08,
                "winner_baseline_simulation": True,
                "winner_20d": True,
                "baseline_pnl_dollars": 5.0,
                "baseline_exit_reason": "TARGET_1",
            },
            {
                "sample_id": 0,
                "replay_date": "2024-01-05",
                "ticker": "BAD",
                "entry_date": "2024-01-08",
                "entry_price": 18.0,
                "reference_price": 18.0,
                "sector_or_theme": "AI / software",
                "smoke_score": 0.70,
                "volatility_20d": 0.09,
                "forward_return_1d": -0.01,
                "forward_return_3d": -0.02,
                "forward_return_5d": -0.03,
                "forward_return_10d": -0.04,
                "forward_return_20d": -0.10,
                "winner_baseline_simulation": False,
                "winner_20d": False,
                "baseline_pnl_dollars": -6.0,
                "baseline_exit_reason": "STOP",
            },
        ]
    )


def _decisions() -> pd.DataFrame:
    rows = []
    for row in _diagnostics().to_dict("records"):
        rows.append(
            {
                "sample_id": row["sample_id"],
                "replay_date": row["replay_date"],
                "decision": "HISTORICAL_BUY_CANDIDATE",
                "ticker": row["ticker"],
                "reference_price": row["reference_price"],
                "shares_with_cash": 4,
                "estimated_total_cost": 80.0,
                "estimated_cash_remaining": 20.0,
                "smoke_score": row["smoke_score"],
                "decision_strength": 0.8,
                "relative_volume_prev20": 2.0,
                "return_5d": 0.1,
                "return_20d": 0.2,
                "distance_to_52w_high_prev": -0.1,
                "dollar_volume": 5_000_000,
                "forward_return_1d": row["forward_return_1d"],
                "forward_return_3d": row["forward_return_3d"],
                "forward_return_5d": row["forward_return_5d"],
                "forward_return_10d": row["forward_return_10d"],
                "forward_return_20d": row["forward_return_20d"],
            }
        )
    return pd.DataFrame(rows)


def _passing_row() -> pd.Series:
    return pd.Series(
        {
            "median_ending_account_value": 140.0,
            "worst_sample_ending_account_value": 110.0,
            "median_max_drawdown": -0.20,
            "worst_sample_max_drawdown": -0.30,
            "median_simulated_win_rate": 0.55,
            "minimum_buy_count": 15,
            "excluded_loser_count": 8,
            "excluded_winner_count": 2,
            "median_20d_average_return": 0.05,
            "median_profit_factor": 1.5,
            "max_top_ticker_profit_share": 0.40,
            "max_top_ticker_loss_share": 0.40,
        }
    )


def test_deterministic_sample_split():
    split = deterministic_sample_split(20)
    fallback = deterministic_sample_split(10)

    assert split["calibration"] == list(range(10))
    assert split["holdout"] == list(range(10, 20))
    assert not split["fallback_used"]
    assert fallback["calibration"] == list(range(5))
    assert fallback["holdout"] == list(range(5, 10))
    assert fallback["fallback_used"]


def test_holdout_samples_are_not_used_for_threshold_selection():
    calibration = pd.DataFrame(
        [
            {"filter_name": "cal", "worst_sample_ending_account_value": 110, "worst_sample_max_drawdown": -0.2, "median_simulated_win_rate": 0.6, "median_ending_account_value": 130, "excluded_winner_count": 1, "calibration_gate_pass": True},
            {"filter_name": "holdout_like", "worst_sample_ending_account_value": 300, "worst_sample_max_drawdown": -0.1, "median_simulated_win_rate": 0.9, "median_ending_account_value": 300, "excluded_winner_count": 0, "calibration_gate_pass": False},
        ]
    )

    selected = select_holdout_filters(calibration)

    assert selected.iloc[0]["filter_name"] == "cal"


def test_filters_use_only_pre_entry_features():
    filters = phase1e_filter_family()
    keys = set().union(*(item.keys() for item in filters))

    assert "forward_return_20d" not in keys
    assert "baseline_pnl_dollars" not in keys


def test_holdout_filters_use_frozen_thresholds():
    filter_def = {"filter_name": "fixed", "filter_description": "fixed", "kind": "vol_smoke", "volatility_20d_max": 0.05, "smoke_score_min": 0.90}
    excluded = apply_phase1e_filter(_diagnostics(), filter_def)

    assert excluded["ticker"].tolist() == ["BAD"]
    assert filter_def["volatility_20d_max"] == 0.05


def test_filtered_replay_is_chronological_and_one_position():
    matrix, _ = build_filter_backtest_matrix(
        _diagnostics(),
        _decisions(),
        _market_data(),
        AccountSettings(),
        [{"filter_name": "fixed", "filter_description": "fixed", "kind": "vol_smoke", "volatility_20d_max": 0.05, "smoke_score_min": 0.90}],
        replay_rounds=10,
        phase1_summaries={0: {"buy_count": 2, "no_trade_count": 8}},
    )

    assert matrix.iloc[0]["filtered_buy_count"] == 1
    assert matrix.iloc[0]["excluded_decision_count"] == 1


def test_calibration_and_holdout_gates():
    row = _passing_row()

    assert calibration_gate_pass(row)
    assert holdout_gate_pass(row)


def test_excluded_decision_audit_records_excluded_winners_and_losers():
    matrix, audit = build_filter_backtest_matrix(
        _diagnostics(),
        _decisions(),
        _market_data(),
        AccountSettings(),
        [{"filter_name": "all", "filter_description": "all", "kind": "vol_smoke", "volatility_20d_max": 0.0, "smoke_score_min": 1.0}],
        replay_rounds=10,
        phase1_summaries={0: {}},
    )

    assert len(audit) == 2
    assert set(audit["would_have_been_winner_baseline_simulation"].astype(bool)) == {True, False}


def test_phase1e_status_never_approves_phase2_or_execution():
    holdout = pd.DataFrame([{"phase1e_holdout_gate_pass": True}])
    status = phase1e_status(holdout, pd.DataFrame([{"calibration_gate_pass": True}]))

    assert status == PHASE_1E_FILTER_ROBUSTNESS_IMPROVED_REQUIRES_GPT_REVIEW
    assert "PHASE_2" not in status
    assert "EXECUTION" not in status


def test_phase1e_reports_are_written(tmp_path: Path):
    threshold, validation, holdout, excluded, summary_md, _ = build_phase1e_filter_validation(
        _market_data(140),
        AccountSettings(),
        _rule(),
        replay_rounds=5,
        replay_sample_count=10,
    )

    write_phase1e_reports(
        threshold,
        validation,
        holdout,
        excluded,
        summary_md,
        tmp_path / "threshold.csv",
        tmp_path / "validation.csv",
        tmp_path / "holdout.csv",
        tmp_path / "excluded.csv",
        tmp_path / "summary.md",
    )

    assert (tmp_path / "threshold.csv").exists()
    assert (tmp_path / "validation.csv").exists()
    assert (tmp_path / "holdout.csv").exists()
    assert (tmp_path / "excluded.csv").exists()
    assert (tmp_path / "summary.md").read_text(encoding="utf-8").startswith(
        "PHOENIX NANO PHASE 1E — CROSS-VALIDATED CONSERVATIVE FILTER VALIDATION"
    )
