from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.backtest.forward_returns import add_forward_returns
from src.research.auto_loop import CandidateRule
from src.research.phase1c_robustness import (
    PHASE1C_POLICIES,
    PHASE_1C_ROBUSTNESS_PROMISING_NOT_APPROVED,
    build_failure_trades,
    build_phase1c_robustness_analysis,
    build_regime_attribution,
    passes_phase1c_policy_gate,
    phase1c_status,
    simulate_phase1c_policy_trades,
    simulate_single_trade,
    write_phase1c_reports,
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


def _market_data(periods: int = 150) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for index, date in enumerate(dates):
        rows.append(_row(date, "GOOD", 20.0 + index * 0.10, 2.0, 0.10))
        rows.append(_row(date, "WEAK", 15.0 + index * 0.01, 0.2, -0.10))
        rows.append(_row(date, "SPY", 100.0 + index * 0.05, 0.5, 0.02))
    return add_forward_returns(pd.DataFrame(rows), [1, 3, 5, 10, 20])


def _row(date: pd.Timestamp, ticker: str, close: float, factor: float, return_5d: float) -> dict:
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
        "return_5d": return_5d,
        "return_10d": return_5d,
        "return_20d": return_5d,
        "distance_to_52w_high_eod": -0.10,
        "distance_to_52w_high_prev": -0.10,
        "atr": close * 0.02,
        "gap_pct": 0.0,
        "dollar_volume": 5_000_000 * factor,
    }


def _decision_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "replay_date": "2024-01-02",
                "decision": "HISTORICAL_BUY_CANDIDATE",
                "ticker": "GOOD",
                "reference_price": 10.0,
                "forward_return_1d": 0.01,
                "forward_return_3d": 0.02,
                "forward_return_5d": 0.03,
                "forward_return_10d": 0.04,
                "forward_return_20d": 0.20,
                "decision_strength": 0.9,
                "smoke_score": 0.9,
            }
        ]
    )


def _stop_data() -> pd.DataFrame:
    rows = [
        _row(pd.Timestamp("2024-01-02"), "GOOD", 10.0, 2.0, 0.10),
        _row(pd.Timestamp("2024-01-03"), "GOOD", 10.0, 2.0, 0.10),
        _row(pd.Timestamp("2024-01-04"), "GOOD", 9.6, 2.0, 0.10),
        _row(pd.Timestamp("2024-01-05"), "GOOD", 11.0, 2.0, 0.10),
    ]
    rows[0]["atr"] = 1.0
    rows[1]["open"] = 10.0
    rows[1]["low"] = 6.9
    rows[1]["close"] = 10.1
    rows[2]["open"] = 9.0
    rows[2]["low"] = 8.8
    rows[2]["close"] = 7.8
    rows[3]["open"] = 7.7
    return pd.DataFrame(rows)


def test_phase1c_sample_generation_matrix_exact_combinations():
    matrix, _, _, _, _ = build_phase1c_robustness_analysis(
        _market_data(),
        AccountSettings(),
        _rule(),
        replay_rounds=10,
        replay_sample_count=3,
    )

    assert matrix["sample_id"].nunique() == 3
    assert len(matrix) == 3 * len(PHASE1C_POLICIES)


def test_phase1c_requested_rounds_are_recorded_for_each_sample():
    matrix, _, _, _, _ = build_phase1c_robustness_analysis(
        _market_data(),
        AccountSettings(),
        _rule(),
        replay_rounds=12,
        replay_sample_count=2,
    )

    assert set(matrix["replay_rounds"]) == {12}
    assert matrix.groupby("sample_id")["policy"].nunique().eq(len(PHASE1C_POLICIES)).all()


def test_phase1c_policy_matrix_contains_every_sample_policy_pair():
    matrix, _, _, _, _ = build_phase1c_robustness_analysis(
        _market_data(),
        AccountSettings(),
        _rule(),
        replay_rounds=8,
        replay_sample_count=2,
    )

    expected = {(sample_id, policy["policy"]) for sample_id in [0, 1] for policy in PHASE1C_POLICIES}
    actual = set(zip(matrix["sample_id"], matrix["policy"]))
    assert actual == expected


def test_close_based_stop_realism_flags_intraday_breach():
    trades = simulate_phase1c_policy_trades(
        _decision_frame(),
        _stop_data(),
        AccountSettings(),
        {"policy": "close_based_stop_2_0x", "atr_multiple": 2.0, "mode": "close_stop"},
    )

    assert bool(trades.iloc[0]["intraday_stop_breached"])
    assert bool(trades.iloc[0]["same_day_recovered_above_stop"])


def test_close_confirmed_next_open_stop_exits_next_open():
    trade = simulate_single_trade(
        _stop_data().iloc[0],
        _stop_data().iloc[1:].reset_index(drop=True),
        {"policy": "close_confirmed_stop_2_0x_next_open_exit", "atr_multiple": 2.0, "mode": "close_next_open"},
    )

    assert pd.Timestamp(trade["exit_date"]).strftime("%Y-%m-%d") == "2024-01-05"
    assert trade["exit_price"] == 7.7


def test_hybrid_catastrophic_stop_exits_intraday_catastrophic_breach():
    trade = simulate_single_trade(
        _stop_data().iloc[0],
        _stop_data().iloc[1:].reset_index(drop=True),
        {"policy": "hybrid_close_stop_2_0x_intraday_catastrophic_3_0x", "atr_multiple": 2.0, "mode": "hybrid"},
    )

    assert trade["exit_reason"] == "STOP"
    assert trade["exit_price"] == 7.0


def test_failing_sample_trades_are_captured():
    trades = simulate_phase1c_policy_trades(
        _decision_frame(),
        _stop_data(),
        AccountSettings(),
        {"policy": "baseline_current", "atr_multiple": 1.5, "mode": "intraday"},
    )

    failures = build_failure_trades(3, trades, _decision_frame(), _stop_data())

    assert len(failures) == 1
    assert failures.iloc[0]["sample_id"] == 3


def test_regime_attribution_aggregates_by_period_and_policy():
    trades = simulate_phase1c_policy_trades(
        _decision_frame(),
        _stop_data(),
        AccountSettings(),
        {"policy": "baseline_current", "atr_multiple": 1.5, "mode": "intraday"},
    )

    regime = build_regime_attribution(0, trades)

    assert len(regime) == 1
    assert regime.iloc[0]["period"] == "2024-01"


def test_phase1c_status_logic_does_not_approve_phase2():
    row = {
        "ending_account_value": 150.0,
        "max_drawdown": -0.20,
        "trade_simulation_accuracy": 0.60,
        "buy_count": 25,
        "ending_value_excluding_best_trade": 120.0,
        "top_ticker_profit_share": 0.20,
    }
    assert passes_phase1c_policy_gate(row)
    matrix = pd.DataFrame([{**row, "policy": "baseline_current", "sample_id": 0, "passes_phase1c_policy_gate": True}])
    status = phase1c_status(matrix, pd.DataFrame())

    assert status == PHASE_1C_ROBUSTNESS_PROMISING_NOT_APPROVED
    assert "PHASE_2" not in status


def test_phase1c_reports_are_written(tmp_path: Path):
    matrix, failures, realism, regime, summary = build_phase1c_robustness_analysis(
        _market_data(),
        AccountSettings(),
        _rule(),
        replay_rounds=5,
        replay_sample_count=2,
    )

    write_phase1c_reports(
        matrix,
        failures,
        realism,
        regime,
        summary,
        tmp_path / "matrix.csv",
        tmp_path / "failures.csv",
        tmp_path / "realism.csv",
        tmp_path / "regime.csv",
        tmp_path / "summary.md",
    )

    assert (tmp_path / "matrix.csv").exists()
    assert (tmp_path / "failures.csv").exists()
    assert (tmp_path / "realism.csv").exists()
    assert (tmp_path / "regime.csv").exists()
    assert (tmp_path / "summary.md").read_text(encoding="utf-8").startswith(
        "PHOENIX NANO PHASE 1C — ROBUSTNESS FAILURE ANALYSIS AND CLOSE-STOP REALISM"
    )
