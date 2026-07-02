from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.research.phase1c_continuous_account import (
    build_phase1c_continuous_account_backtest,
    write_phase1c_continuous_account_reports,
)


def _row(date: pd.Timestamp, ticker: str, close: float, *, strong: bool = True) -> dict:
    factor = 2.0 if strong else 0.4
    return {
        "date": date,
        "ticker": ticker,
        "open": close * 0.99,
        "high": close * (1.35 if ticker == "GOOD" else 1.02),
        "low": close * 0.98,
        "close": close,
        "volume": 2_000_000,
        "market_cap": 1_000_000_000,
        "relative_volume_eod": factor,
        "relative_volume_prev20": factor,
        "volume_change_20d": factor,
        "return_5d": 0.08 if strong else -0.02,
        "return_10d": 0.10 if strong else -0.02,
        "return_20d": 0.12 if strong else -0.02,
        "distance_to_52w_high_eod": -0.10,
        "distance_to_52w_high_prev": -0.10,
        "atr": close * 0.04,
        "gap_pct": 0.0,
        "dollar_volume": 50_000_000 if strong else 5_000_000,
    }


def _market_data(periods: int = 45) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for index, date in enumerate(dates):
        rows.append(_row(date, "GOOD", 20.0 + index * 0.05, strong=True))
        rows.append(_row(date, "WEAK", 18.0 + index * 0.01, strong=False))
        rows.append(_row(date, "SPY", 100.0 + index * 0.10, strong=True))
        rows.append(_row(date, "QQQ", 120.0 + index * 0.10, strong=True))
    return pd.DataFrame(rows)


def test_continuous_account_uses_one_starting_capital_and_can_grow():
    trades, equity, summary = build_phase1c_continuous_account_backtest(
        _market_data(),
        AccountSettings(slippage_bps=0),
        "2024-01-02",
        "2024-02-15",
    )

    assert not trades.empty
    assert trades.iloc[0]["cash_before"] == 100.0
    assert summary["ending_account_value"] > 100.0
    assert equity.iloc[0]["event"] == "START"


def test_continuous_account_keeps_one_open_position_at_a_time():
    trades, _, _ = build_phase1c_continuous_account_backtest(
        _market_data(),
        AccountSettings(slippage_bps=0),
        "2024-01-02",
        "2024-02-15",
    )

    entries = pd.to_datetime(trades["entry_date"])
    previous_exits = pd.to_datetime(trades["exit_date"]).shift(1)
    assert (entries.iloc[1:].reset_index(drop=True) > previous_exits.iloc[1:].reset_index(drop=True)).all()


def test_filter_rejects_future_winner_with_weak_signal_inputs():
    data = _market_data()
    data.loc[data["ticker"].eq("WEAK"), "future_return_that_must_not_be_used"] = 9.0

    trades, _, _ = build_phase1c_continuous_account_backtest(
        data,
        AccountSettings(slippage_bps=0),
        "2024-01-02",
        "2024-02-15",
    )

    assert set(trades["ticker"]) == {"GOOD"}


def test_block_counter_reports_dominant_filter():
    _, _, summary = build_phase1c_continuous_account_backtest(
        _market_data(),
        AccountSettings(slippage_bps=0),
        "2024-01-02",
        "2024-01-12",
    )

    assert summary["top_block_rule"]
    assert summary["top_block_rule_count"] > 0


def test_phase1c_continuous_reports_are_written(tmp_path: Path):
    trades, equity, summary = build_phase1c_continuous_account_backtest(
        _market_data(),
        AccountSettings(slippage_bps=0),
        "2024-01-02",
        "2024-02-15",
    )
    trades_path = tmp_path / "trades.csv"
    equity_path = tmp_path / "equity.csv"
    summary_path = tmp_path / "summary.md"

    write_phase1c_continuous_account_reports(trades, equity, summary, trades_path, equity_path, summary_path)

    assert trades_path.exists()
    assert equity_path.exists()
    assert summary_path.exists()
    assert "Continuous Account Growth Backtest" in summary_path.read_text(encoding="utf-8")
