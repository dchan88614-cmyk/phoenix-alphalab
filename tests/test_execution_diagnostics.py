from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED
from src.backtest.forward_returns import add_forward_returns
from src.research.auto_loop import CandidateRule
from src.research.execution_diagnostics import (
    POLICIES,
    build_phase1b_execution_diagnostics,
    build_ticker_risk_attribution,
    build_trade_diagnostics,
    compare_exit_policies,
    simulate_policy_trades,
    write_phase1b_reports,
)
from src.research.historical_replay import HISTORICAL_BUY_CANDIDATE, build_phase1_historical_replay, sample_replay_dates


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
        good_close = 20.0 + index * 0.10
        weak_close = 15.0 + index * 0.01
        rows.append(_row(date, "GOOD", good_close, 2.0, 0.10))
        rows.append(_row(date, "WEAK", weak_close, 0.2, -0.10))
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


def _single_buy_decision() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "replay_date": "2024-01-02",
                "decision": HISTORICAL_BUY_CANDIDATE,
                "ticker": "GOOD",
                "reference_price": 10.0,
                "entry_date": "2024-01-03",
                "exit_date": "2024-01-03",
                "exit_reason": "STOP",
                "pnl_dollars": -5.0,
                "trade_return_pct": -0.05,
                "account_return_pct": -0.05,
                "forward_return_1d": 0.01,
                "forward_return_3d": 0.02,
                "forward_return_5d": 0.03,
                "forward_return_10d": 0.04,
                "forward_return_20d": 0.20,
            }
        ]
    )


def _gap_data() -> pd.DataFrame:
    rows = [
        _row(pd.Timestamp("2024-01-02"), "GOOD", 10.0, 2.0, 0.10),
        _row(pd.Timestamp("2024-01-03"), "GOOD", 11.0, 2.0, 0.10),
        _row(pd.Timestamp("2024-01-04"), "GOOD", 12.0, 2.0, 0.10),
    ]
    rows[1]["open"] = 11.0
    rows[1]["low"] = 9.0
    rows[2]["high"] = 15.0
    return pd.DataFrame(rows)


def test_execution_diagnostics_do_not_change_selected_decisions():
    data = _market_data()
    decisions, _, _ = build_phase1_historical_replay(data, AccountSettings(), _rule(), replay_rounds=10)

    diagnostics = build_trade_diagnostics(decisions, data)

    expected = decisions.loc[decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE), ["replay_date", "ticker"]].reset_index(drop=True)
    actual = diagnostics[["replay_date", "ticker"]].reset_index(drop=True)
    pd.testing.assert_frame_equal(actual, expected)


def test_future_data_does_not_affect_phase1b_selection():
    data = _market_data()
    data.loc[data["ticker"].eq("WEAK"), ["fwd_return_1d", "fwd_return_3d", "fwd_return_5d", "fwd_return_10d", "fwd_return_20d"]] = 9.0

    diagnostics, _, _, _ = build_phase1b_execution_diagnostics(data, AccountSettings(), _rule(), replay_rounds=5)

    assert diagnostics.iloc[0]["ticker"] == "GOOD"


def test_entry_gap_is_computed_correctly():
    diagnostics = build_trade_diagnostics(_single_buy_decision(), _gap_data())

    assert round(float(diagnostics.iloc[0]["entry_gap_pct"]), 6) == 0.1


def test_stopped_out_then_20d_positive_detection_is_correct():
    diagnostics = build_trade_diagnostics(_single_buy_decision(), _gap_data())

    assert bool(diagnostics.iloc[0]["stopped_out_then_20d_positive"])


def test_exit_policy_comparison_computes_core_metrics():
    decisions = _single_buy_decision()
    comparison = compare_exit_policies(decisions, _gap_data(), AccountSettings())

    baseline = comparison.loc[comparison["policy"].eq("baseline_current")].iloc[0]
    assert baseline["buy_count"] == 1
    assert baseline["executed_count"] == 1
    assert "profit_factor" in baseline.index
    assert "ending_account_value" in baseline.index
    assert "max_drawdown" in baseline.index


def test_policy_account_replay_respects_one_open_position_at_a_time():
    decisions = pd.concat([_single_buy_decision(), _single_buy_decision().assign(replay_date="2024-01-03")], ignore_index=True)
    trades = simulate_policy_trades(decisions, _gap_data(), AccountSettings(), POLICIES[-3])

    assert "SKIPPED_POSITION_OPEN" in trades["status"].tolist()


def test_ticker_risk_attribution_identifies_concentration():
    trades = pd.DataFrame(
        [
            {"ticker": "A", "pnl_dollars": 10.0, "account_return_pct": 0.10, "replay_date": "2024-01-02", "status": EXECUTED},
            {"ticker": "A", "pnl_dollars": 5.0, "account_return_pct": 0.05, "replay_date": "2024-01-03", "status": EXECUTED},
            {"ticker": "B", "pnl_dollars": -3.0, "account_return_pct": -0.03, "replay_date": "2024-01-04", "status": EXECUTED},
        ]
    )

    attribution = build_ticker_risk_attribution(trades)

    assert attribution.iloc[0]["ticker"] == "A"
    assert attribution.iloc[0]["contribution_to_total_profit_pct"] == 1.0


def test_sample_offsets_are_deterministic_and_exact_count():
    data = _market_data()

    first = sample_replay_dates(data, 20, replay_sample_offset=2)
    second = sample_replay_dates(data, 20, replay_sample_offset=2)
    different = sample_replay_dates(data, 20, replay_sample_offset=3)

    assert first == second
    assert len(first) == 20
    assert len(different) == 20
    assert first != different


def test_phase1b_reports_are_written(tmp_path: Path):
    diagnostics, comparison, attribution, summary = build_phase1b_execution_diagnostics(
        _market_data(),
        AccountSettings(),
        _rule(),
        replay_rounds=5,
        replay_sample_count=2,
    )

    write_phase1b_reports(
        diagnostics,
        comparison,
        attribution,
        summary,
        tmp_path / "diagnostics.csv",
        tmp_path / "summary.md",
        tmp_path / "comparison.csv",
        tmp_path / "attribution.csv",
    )

    assert (tmp_path / "diagnostics.csv").exists()
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "comparison.csv").exists()
    assert (tmp_path / "attribution.csv").exists()
    assert (tmp_path / "summary.md").read_text(encoding="utf-8").startswith(
        "PHOENIX NANO PHASE 1B — EXECUTION RISK AND DRAWDOWN DIAGNOSTICS"
    )
