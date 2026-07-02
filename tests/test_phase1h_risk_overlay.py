from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.backtest.forward_returns import add_forward_returns
from src.research.auto_loop import CandidateRule
from src.research.phase1h_risk_overlay import (
    PHASE_1H_OVERFILTERED,
    TREND_BASELINE,
    build_index_feature_lookup,
    build_phase1h_holdout_results,
    build_phase1h_risk_overlay_sandbox,
    deterministic_phase1h_split,
    overlay_definitions,
    overlay_skip_reason,
    phase1h_status,
    write_phase1h_reports,
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
        "low": close * 0.98,
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


def _market_data(periods: int = 180) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for index, date in enumerate(dates):
        rows.append(_row(date, "RIVN", 20.0 + index * 0.08, 2.5))
        rows.append(_row(date, "BBAI", 18.0 + index * 0.05, 1.8))
        rows.append(_row(date, "SPY", 100.0 + index * 0.03, 1.0))
        rows.append(_row(date, "QQQ", 110.0 + index * 0.04, 1.0))
    return add_forward_returns(pd.DataFrame(rows), [1, 3, 5, 10, 20])


def test_candidate34_and_candidate35_baselines_are_frozen_names():
    names = {overlay["overlay_name"] for overlay in overlay_definitions()}

    assert "overlay_market_regime_risk_off_skip" in names
    assert "overlay_high_volatility_tail_skip" in names
    assert TREND_BASELINE == "candidate35_trend_quality_frozen"


def test_market_regime_overlay_uses_replay_date_index_features_not_future_returns():
    data = _market_data()
    lookup = build_index_feature_lookup(data)
    overlay = {"overlay_name": "overlay_market_regime_risk_off_skip", "kind": "market_regime"}
    decision = pd.Series(
        {
            "decision": "HISTORICAL_BUY_CANDIDATE",
            "replay_date": data["date"].max().strftime("%Y-%m-%d"),
            "ticker": "RIVN",
            "forward_return_20d": -0.99,
        }
    )

    skip, _ = overlay_skip_reason(decision, overlay, lookup, {}, 0)

    assert isinstance(skip, bool)


def test_cooldown_overlay_only_uses_prior_closed_state():
    overlay = {"overlay_name": "overlay_ticker_loss_cooldown_5pct_5", "kind": "ticker_cooldown", "loss_threshold": -0.05, "cooldown_decisions": 5}
    decision = pd.Series({"decision": "HISTORICAL_BUY_CANDIDATE", "ticker": "RIVN", "replay_date": "2024-02-01"})

    before_skip, _ = overlay_skip_reason(decision, overlay, {}, {}, 2)
    after_skip, _ = overlay_skip_reason(decision, overlay, {}, {"RIVN": 7}, 2)

    assert before_skip is False
    assert after_skip is True


def test_phase1h_split_is_deterministic_and_non_overlapping():
    split = deterministic_phase1h_split(30)

    assert split["calibration"] == list(range(10))
    assert split["validation"] == list(range(10, 20))
    assert split["holdout"] == list(range(20, 30))
    assert not set(split["calibration"]) & set(split["validation"])
    assert not set(split["validation"]) & set(split["holdout"])


def test_holdout_parameters_are_fixed_policy_names_after_validation():
    definitions_before = overlay_definitions()
    definitions_after = overlay_definitions()

    assert definitions_before == definitions_after


def test_overfiltering_is_detected_when_buy_count_falls_below_gate():
    holdout = pd.DataFrame(
        [
            {
                "policy_name": "overlay_x",
                "split_name": "holdout",
                "sample_count": 10,
                "total_buy_count": 10,
                "median_buy_count": 2,
                "minimum_buy_count": 1,
                "median_ending_account_value": 150,
                "worst_sample_ending_value": 140,
                "worst_max_drawdown": -0.05,
                "median_simulated_win_rate": 1.0,
                "median_accuracy_20d": 1.0,
                "median_profit_factor": 3.0,
                "worst_trade_loss_percent": -0.01,
                "max_top_ticker_loss_share": 0.1,
                "max_top_theme_loss_share": 0.1,
                "median_ending_value_excluding_best_trade": 130,
                "holdout_gate_pass": False,
            }
        ]
    )
    preflight = pd.DataFrame({"symbol": ["SPY", "QQQ"], "bar_count": [100, 100], "warnings": ["", ""]})

    assert phase1h_status(holdout, preflight, 30) == PHASE_1H_OVERFILTERED


def test_phase1h_reports_are_written(tmp_path: Path):
    definitions, calibration, validation, holdout, comparison, drawdown, theme, counter, _, summary_md, _ = build_phase1h_risk_overlay_sandbox(
        _market_data(),
        AccountSettings(),
        _rule(),
        replay_rounds=5,
        replay_sample_count=20,
    )

    write_phase1h_reports(
        definitions,
        calibration,
        validation,
        holdout,
        comparison,
        drawdown,
        theme,
        counter,
        summary_md,
        tmp_path / "definitions.md",
        tmp_path / "calibration.csv",
        tmp_path / "validation.csv",
        tmp_path / "holdout.csv",
        tmp_path / "comparison.csv",
        tmp_path / "drawdown.csv",
        tmp_path / "theme.csv",
        tmp_path / "counter.csv",
        tmp_path / "summary.md",
    )

    assert (tmp_path / "counter.csv").exists()
    assert (tmp_path / "drawdown.csv").exists()
    assert (tmp_path / "theme.csv").exists()
    assert (tmp_path / "summary.md").read_text(encoding="utf-8").startswith(
        "PHOENIX NANO PHASE 1H — TREND-QUALITY RISK OVERLAY AND DRAWDOWN COMPRESSION"
    )


def test_holdout_results_include_excluded_trade_counterfactual_gate():
    preflight = pd.DataFrame({"symbol": ["SPY", "QQQ"], "bar_count": [100, 100], "warnings": ["", ""]})
    holdout = pd.DataFrame(
        [
            {
                "sample_id": 20,
                "policy_name": "overlay_x",
                "buy_count": 50,
                "no_trade_count": 50,
                "buy_rate": 0.5,
                "ending_account_value": 150,
                "max_drawdown": -0.1,
                "simulated_win_rate": 0.6,
                "accuracy_1d": 0.6,
                "accuracy_3d": 0.6,
                "accuracy_5d": 0.6,
                "accuracy_10d": 0.6,
                "accuracy_20d": 0.6,
                "profit_factor": 1.5,
                "worst_trade_loss_percent": -0.02,
                "top_loss_ticker_contribution_share": 0.1,
                "top_loss_theme_contribution_share": 0.1,
                "ending_value_excluding_best_trade": 130,
                "number_of_trades_excluded_by_overlay": 1,
                "excluded_loser_count": 0,
                "excluded_winner_count": 1,
                "excluded_loser_dollars_avoided": 0,
                "excluded_winner_dollars_missed": 5,
                "overlay_false_positive_rate": 1.0,
                "overlay_false_negative_rate": 0.1,
            }
        ]
    )
    counter = pd.DataFrame({"overlay_name": ["overlay_x"], "simulated_pnl_if_taken_with_baseline_exit": [5.0]})

    result = build_phase1h_holdout_results(holdout, counter, preflight, 30)

    assert "excluded_winners_missed_gte_losers_avoided" in result.iloc[0]["failed_gates"]
