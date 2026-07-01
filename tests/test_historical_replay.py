from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED
from src.backtest.forward_returns import add_forward_returns
from src.research.auto_loop import CandidateRule
from src.research.historical_replay import (
    HISTORICAL_BUY_CANDIDATE,
    HISTORICAL_NO_TRADE,
    build_phase1_historical_replay,
    summarize_phase1_replay,
    write_phase1_historical_replay_reports,
)


def _rule(max_entry_price: float = 50.0, min_smoke_score: float = 0.5) -> CandidateRule:
    return CandidateRule(
        candidate_id=34,
        max_buy_rate=0.30,
        min_relative_volume_prev20=1.0,
        min_smoke_score=min_smoke_score,
        min_rank_gap=0.0,
        require_return_5d_positive=True,
        require_return_20d_positive=False,
        distance_to_52w_high_prev_min=-0.35,
        dollar_volume_min=1_000_000,
        max_trades_per_ticker_per_year=None,
        max_entry_price=max_entry_price,
    )


def _market_data(periods: int = 150, include_expensive: bool = True, good_return_5d: float = 0.10) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for index, date in enumerate(dates):
        for ticker, base, factor in [
            ("GOOD", 20.0, 2.0),
            ("WEAK", 15.0, 0.2),
            ("SPY", 100.0, 0.5),
        ]:
            close = base + index * (0.10 if ticker == "GOOD" else 0.02)
            rows.append(_row(date, ticker, close, factor, good_return_5d if ticker == "GOOD" else -0.02))
        if include_expensive:
            rows.append(_row(date, "EXPENSIVE", 120.0 + index, 5.0, 0.20))
    return add_forward_returns(pd.DataFrame(rows), [1, 3, 5, 10, 20])


def _row(date: pd.Timestamp, ticker: str, close: float, factor: float, return_5d: float) -> dict:
    return {
        "date": date,
        "ticker": ticker,
        "open": close,
        "high": close * 1.02,
        "low": close * 0.98,
        "close": close,
        "volume": 1_000_000,
        "market_cap": 1_000_000_000,
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


def test_exactly_100_replay_rounds_are_generated():
    decisions, _, summary = build_phase1_historical_replay(
        _market_data(),
        AccountSettings(),
        _rule(),
        replay_rounds=100,
    )

    assert len(decisions) == 100
    assert summary["total_replay_rounds"] == 100


def test_replay_decision_does_not_use_future_return_winner():
    data = _market_data(periods=130, include_expensive=False)
    mask = data["ticker"].eq("WEAK")
    data.loc[mask, ["fwd_return_1d", "fwd_return_3d", "fwd_return_5d", "fwd_return_10d", "fwd_return_20d"]] = 9.0

    decisions, _, _ = build_phase1_historical_replay(data, AccountSettings(), _rule(), replay_rounds=1)

    assert decisions.iloc[0]["decision"] == HISTORICAL_BUY_CANDIDATE
    assert decisions.iloc[0]["ticker"] == "GOOD"


def test_non_affordable_tickers_are_rejected_before_ranking():
    decisions, near_misses, _ = build_phase1_historical_replay(
        _market_data(periods=130, include_expensive=True),
        AccountSettings(),
        _rule(),
        replay_rounds=1,
    )

    assert decisions.iloc[0]["ticker"] == "GOOD"
    rejected = near_misses.loc[near_misses["row_type"].eq("REJECTED_BEFORE_NANO_RANKING")]
    executable = near_misses.loc[near_misses["row_type"].eq("EXECUTABLE_NEAR_MISS")]
    assert "EXPENSIVE" in rejected["ticker"].tolist()
    assert "EXPENSIVE" not in executable["ticker"].tolist()


def test_forward_returns_are_labels_after_decision_not_ranking_inputs():
    data = _market_data(periods=130, include_expensive=False)
    data.loc[data["ticker"].eq("GOOD"), "fwd_return_20d"] = -0.50
    data.loc[data["ticker"].eq("WEAK"), "fwd_return_20d"] = 2.00

    decisions, _, _ = build_phase1_historical_replay(data, AccountSettings(), _rule(), replay_rounds=1)

    assert decisions.iloc[0]["ticker"] == "GOOD"
    assert decisions.iloc[0]["forward_return_20d"] == -0.50


def test_accuracy_metrics_are_computed_correctly():
    decisions = pd.DataFrame(
        [
            {
                "decision": HISTORICAL_BUY_CANDIDATE,
                "ticker": "A",
                "replay_date": "2024-01-02",
                "forward_return_1d": 0.01,
                "forward_return_3d": 0.01,
                "forward_return_5d": -0.01,
                "forward_return_10d": 0.02,
                "forward_return_20d": 0.03,
                "trade_simulation_status": EXECUTED,
                "pnl_dollars": 5.0,
                "cash_after_exit": 105.0,
                "account_return_pct": 0.05,
            },
            {
                "decision": HISTORICAL_BUY_CANDIDATE,
                "ticker": "B",
                "replay_date": "2024-01-03",
                "forward_return_1d": -0.01,
                "forward_return_3d": 0.01,
                "forward_return_5d": 0.01,
                "forward_return_10d": -0.02,
                "forward_return_20d": -0.03,
                "trade_simulation_status": EXECUTED,
                "pnl_dollars": -2.0,
                "cash_after_exit": 103.0,
                "account_return_pct": -0.019,
            },
            {
                "decision": HISTORICAL_NO_TRADE,
                "ticker": "",
                "trade_simulation_status": "",
                "pnl_dollars": pd.NA,
                "cash_after_exit": 103.0,
            },
        ]
    )

    summary = summarize_phase1_replay(decisions, AccountSettings())

    assert summary["buy_count"] == 2
    assert summary["no_trade_count"] == 1
    assert summary["accuracy_1d"] == 0.5
    assert summary["accuracy_3d"] == 1.0
    assert summary["trade_simulation_accuracy"] == 0.5
    assert summary["ending_account_value"] == 103.0
    assert summary["profit_factor"] == 2.5


def test_account_replay_respects_one_open_position_at_a_time():
    decisions, _, _ = build_phase1_historical_replay(
        _market_data(periods=130, include_expensive=False),
        AccountSettings(),
        _rule(),
        replay_rounds=20,
    )

    assert "POSITION_OPEN" in decisions["reason"].tolist()
    executed = decisions.loc[decisions["trade_simulation_status"].eq(EXECUTED)].copy()
    executed["replay_date"] = pd.to_datetime(executed["replay_date"])
    executed["exit_date"] = pd.to_datetime(executed["exit_date"])
    for previous, current in zip(executed.iloc[:-1].itertuples(), executed.iloc[1:].itertuples()):
        assert current.replay_date > previous.exit_date


def test_phase1_reports_are_written(tmp_path: Path):
    decisions, near_misses, summary = build_phase1_historical_replay(
        _market_data(periods=130, include_expensive=True),
        AccountSettings(),
        _rule(),
        replay_rounds=5,
    )

    decisions_path = tmp_path / "decisions.csv"
    summary_path = tmp_path / "summary.md"
    near_misses_path = tmp_path / "near_misses.csv"
    write_phase1_historical_replay_reports(decisions, near_misses, summary, decisions_path, summary_path, near_misses_path)

    assert decisions_path.exists()
    assert summary_path.exists()
    assert near_misses_path.exists()
    assert summary_path.read_text(encoding="utf-8").startswith(
        "PHOENIX NANO PHASE 1A — 100 HISTORICAL REPLAY ROUNDS"
    )
