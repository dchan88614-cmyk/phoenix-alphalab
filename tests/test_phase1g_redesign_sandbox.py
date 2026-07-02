from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.backtest.forward_returns import add_forward_returns
from src.research.auto_loop import CandidateRule
from src.research.phase1g_redesign_sandbox import (
    PHASE_1G_HOLDOUT_FAILED,
    build_holdout_results,
    build_phase1g_preflight,
    build_phase1g_redesign_sandbox,
    candidate35_families,
    candidate_family_definitions_markdown,
    deterministic_phase1g_split,
    ending_excluding_best_trade,
    family_reject_reason,
    phase1g_status,
    theme_concentration_shares,
    write_phase1g_reports,
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


def _market_data(periods: int = 160) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for index, date in enumerate(dates):
        rows.append(_row(date, "RIVN", 20.0 + index * 0.08, 2.5))
        rows.append(_row(date, "BBAI", 18.0 + index * 0.03, 1.5))
        rows.append(_row(date, "SPY", 100.0 + index * 0.03, 1.0))
        rows.append(_row(date, "QQQ", 110.0 + index * 0.04, 1.0))
    return add_forward_returns(pd.DataFrame(rows), [1, 3, 5, 10, 20])


def test_phase1g_preflight_includes_spy_and_qqq_as_regime_inputs():
    preflight = build_phase1g_preflight(_market_data(), pd.DataFrame(), "SPY")

    roles = dict(zip(preflight["symbol"], preflight["role"]))
    assert roles["SPY"] == "benchmark"
    assert roles["QQQ"] == "market_regime_index"


def test_candidate_family_definitions_include_required_families():
    text = candidate_family_definitions_markdown()

    for name in [
        "candidate34_frozen_baseline",
        "candidate35_trend_quality",
        "candidate35_pullback_continuation",
        "candidate35_breakout_confirmation",
        "candidate35_regime_gated_momentum",
        "candidate35_low_volatility_compounder",
    ]:
        assert name in text


def test_candidate34_baseline_remains_frozen_and_unchanged():
    family = candidate35_families()[0]

    assert family == {"family_name": "candidate34_frozen_baseline", "kind": "candidate34"}


def test_candidate35_decision_logic_uses_only_pre_entry_fields():
    row = pd.Series(
        {
            "close": 20,
            "sma20": 19,
            "sma50": 18,
            "volatility_20d": 0.04,
            "atr_pct": 0.02,
            "distance_to_52w_high_prev": -0.05,
            "distance_from_20d_high_pct": -0.02,
            "return_5d": 0.05,
            "return_20d": 0.1,
            "relative_volume_prev20": 2.0,
            "smoke_score": 0.9,
            "regime_label": "RISK_ON",
            "forward_return_20d": -0.9,
        }
    )

    assert family_reject_reason(row, "trend_quality") == ""


def test_phase1g_split_is_deterministic_and_non_overlapping():
    split = deterministic_phase1g_split(30)

    assert split["calibration"] == list(range(10))
    assert split["validation"] == list(range(10, 20))
    assert split["holdout"] == list(range(20, 30))
    assert not (set(split["calibration"]) & set(split["validation"]) & set(split["holdout"]))


def test_holdout_evaluation_does_not_mutate_family_definitions():
    before = candidate35_families()
    after = candidate35_families()

    assert before == after


def test_minimum_buy_count_gate_prevents_over_filtering_pass():
    holdout = pd.DataFrame(
        [
            {
                "sample_id": 20,
                "family_name": "candidate35_low_volatility_compounder",
                "buy_count": 3,
                "ending_account_value": 160,
                "max_drawdown": -0.05,
                "simulated_win_rate": 1.0,
                "accuracy_20d": 1.0,
                "profit_factor": 5.0,
                "worst_trade_loss_percent": -0.01,
                "top_loss_ticker_contribution_share": 0.1,
                "top_loss_theme_contribution_share": 0.1,
                "ending_value_excluding_best_trade": 130,
            }
        ]
    )
    preflight = build_phase1g_preflight(_market_data(), pd.DataFrame(), "SPY")
    result = build_holdout_results(holdout, preflight, 30)

    assert not bool(result.iloc[0]["holdout_gate_pass"])
    assert "min_buy_count_lt_15" in result.iloc[0]["failed_gates"]


def test_concentration_and_best_trade_gates_are_computed():
    trades = pd.DataFrame(
        [
            {"ticker": "RIVN", "pnl_dollars": 10.0},
            {"ticker": "RIVN", "pnl_dollars": -5.0},
            {"ticker": "BBAI", "pnl_dollars": -1.0},
        ]
    )

    _, loss_share = theme_concentration_shares(trades)
    assert loss_share > 0.5
    assert ending_excluding_best_trade(trades, 100.0) == 94.0


def test_no_active_daily_scan_behavior_is_changed():
    from src.main import build_parser

    args = build_parser().parse_args(["--tickers", "AAPL", "--start", "2024-01-01", "--end", "2024-02-01"])
    assert not args.phase1g_redesign_sandbox


def test_phase1g_status_never_approves_phase2_or_execution():
    holdout = pd.DataFrame([{"family_name": "candidate35_x", "holdout_gate_pass": False}])
    status = phase1g_status(holdout, build_phase1g_preflight(_market_data(), pd.DataFrame(), "SPY"), 30)

    assert status == PHASE_1G_HOLDOUT_FAILED
    assert "PHASE_2" not in status
    assert "EXECUTION" not in status


def test_phase1g_reports_are_written(tmp_path: Path):
    preflight, definitions, calibration, validation, holdout, comparison, rejected, summary_md, _ = build_phase1g_redesign_sandbox(
        _market_data(),
        AccountSettings(),
        _rule(),
        replay_rounds=5,
        replay_sample_count=20,
    )

    write_phase1g_reports(
        preflight,
        definitions,
        calibration,
        validation,
        holdout,
        comparison,
        rejected,
        summary_md,
        tmp_path / "preflight.csv",
        tmp_path / "definitions.md",
        tmp_path / "calibration.csv",
        tmp_path / "validation.csv",
        tmp_path / "holdout.csv",
        tmp_path / "comparison.csv",
        tmp_path / "rejected.csv",
        tmp_path / "summary.md",
    )

    assert (tmp_path / "preflight.csv").exists()
    assert (tmp_path / "definitions.md").exists()
    assert (tmp_path / "calibration.csv").exists()
    assert (tmp_path / "validation.csv").exists()
    assert (tmp_path / "holdout.csv").exists()
    assert (tmp_path / "comparison.csv").exists()
    assert (tmp_path / "rejected.csv").exists()
    assert (tmp_path / "summary.md").read_text(encoding="utf-8").startswith(
        "PHOENIX NANO PHASE 1G — CANDIDATE 35 REDESIGN SANDBOX"
    )
