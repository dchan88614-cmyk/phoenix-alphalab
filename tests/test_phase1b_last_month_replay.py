from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.research.auto_loop import CandidateRule
from src.research.historical_replay import HISTORICAL_BUY_CANDIDATE, HISTORICAL_NO_TRADE
from src.research.phase1b_last_month_replay import (
    build_phase1b_last_month_replay,
    write_phase1b_last_month_reports,
)


def _rule(min_smoke_score: float = 0.5) -> CandidateRule:
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
        max_entry_price=50.0,
    )


def _row(date: pd.Timestamp, ticker: str, close: float, factor: float, return_5d: float = 0.10) -> dict:
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


def _market_data(extra_days: int = 25) -> pd.DataFrame:
    dates = list(pd.bdate_range("2026-06-01", "2026-06-30")) + list(pd.bdate_range("2026-07-01", periods=extra_days))
    rows = []
    for index, date in enumerate(dates):
        rows.append(_row(date, "GOOD", 20.0 + index * 0.5, 2.0))
        rows.append(_row(date, "FUTURE_WINNER", 15.0 + index * 2.0, 0.2, return_5d=-0.02))
        rows.append(_row(date, "SPY", 100.0 + index * 0.1, 0.5))
    return pd.DataFrame(rows)


def test_last_month_replay_outputs_one_decision_per_trading_day():
    decisions, _, summary = build_phase1b_last_month_replay(
        _market_data(),
        AccountSettings(),
        _rule(),
        "2026-06-01",
        "2026-06-30",
    )

    assert len(decisions) == len(pd.bdate_range("2026-06-01", "2026-06-30"))
    assert decisions.groupby("replay_date").size().eq(1).all()
    assert summary["total_trading_days"] == len(decisions)


def test_last_month_replay_does_not_use_future_winner_to_select():
    data = _market_data()
    data["fwd_return_20d"] = 0.0
    data.loc[data["ticker"].eq("FUTURE_WINNER"), "fwd_return_20d"] = 9.0

    decisions, _, _ = build_phase1b_last_month_replay(
        data,
        AccountSettings(),
        _rule(),
        "2026-06-01",
        "2026-06-30",
    )

    buys = decisions.loc[decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)]
    assert not buys.empty
    assert set(buys["ticker"]) == {"GOOD"}


def test_no_trade_records_up_to_five_executable_near_misses():
    dates = pd.bdate_range("2026-06-01", periods=1)
    rows = []
    for index in range(8):
        rows.append(_row(dates[0], f"NEAR{index}", 20.0 + index, 1.0, return_5d=-0.01))
    rows.append(_row(dates[0], "SPY", 100.0, 0.5))

    decisions, near_misses, _ = build_phase1b_last_month_replay(
        pd.DataFrame(rows),
        AccountSettings(),
        _rule(min_smoke_score=0.99),
        "2026-06-01",
        "2026-06-01",
    )

    assert decisions.iloc[0]["decision"] == HISTORICAL_NO_TRADE
    assert len(near_misses) == 5
    assert near_misses["replay_date"].nunique() == 1


def test_future_windows_mark_incomplete_when_data_is_missing():
    decisions, _, _ = build_phase1b_last_month_replay(
        _market_data(extra_days=2),
        AccountSettings(),
        _rule(),
        "2026-06-30",
        "2026-06-30",
    )

    row = decisions.iloc[0]
    assert row["data_complete_1d"] == True
    assert row["data_complete_3d"] == False
    assert pd.isna(row["return_3d"])


def test_phase1b_last_month_reports_are_written(tmp_path: Path):
    decisions, near_misses, summary = build_phase1b_last_month_replay(
        _market_data(),
        AccountSettings(),
        _rule(),
        "2026-06-01",
        "2026-06-30",
    )
    csv_path = tmp_path / "daily.csv"
    md_path = tmp_path / "daily.md"
    near_path = tmp_path / "near.csv"

    write_phase1b_last_month_reports(decisions, near_misses, summary, csv_path, md_path, near_path)

    assert csv_path.exists()
    assert md_path.exists()
    assert near_path.exists()
    assert "Phoenix Nano Phase 1B Last Month Daily Replay Validation" in md_path.read_text(encoding="utf-8")
