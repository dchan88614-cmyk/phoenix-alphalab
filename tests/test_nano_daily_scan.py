from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.backtest.nano_daily_scan import (
    MANUAL_REVIEW_CANDIDATE,
    NO_TRADE_MANUAL_REVIEW,
    STALE_DATA,
    build_nano_daily_scan,
    write_nano_daily_scan_reports,
)


def _row(
    date: str,
    ticker: str,
    close: float,
    factor_value: float,
    *,
    return_5d: float | None = None,
    return_20d: float | None = None,
) -> dict:
    return {
        "date": date,
        "ticker": ticker,
        "open": close,
        "high": close * 1.02,
        "low": close * 0.98,
        "close": close,
        "volume": 1_000_000,
        "atr": close * 0.04,
        "relative_volume_prev20": factor_value,
        "return_5d": factor_value if return_5d is None else return_5d,
        "return_20d": factor_value if return_20d is None else return_20d,
        "distance_to_52w_high_prev": -0.10,
        "dollar_volume": 50_000_000 * factor_value,
    }


def _settings() -> AccountSettings:
    return AccountSettings(starting_capital=100.0, fractional_shares=False, slippage_bps=10.0)


def test_daily_scan_outputs_exactly_one_action():
    data = pd.DataFrame(
        [
            _row("2026-06-30", "GOOD", 40.0, 2.0),
            _row("2026-06-30", "WEAK", 30.0, 0.5),
        ]
    )

    scan, _ = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01")

    assert len(scan) == 1
    assert scan["action"].isin([MANUAL_REVIEW_CANDIDATE, NO_TRADE_MANUAL_REVIEW]).sum() == 1


def test_daily_scan_rejects_stock_above_100_for_whole_share_account():
    data = pd.DataFrame(
        [
            _row("2026-06-30", "EXPENSIVE", 120.0, 2.0),
            _row("2026-06-30", "WEAK", 30.0, 0.5),
        ]
    )

    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01")

    assert scan.iloc[0]["action"] == NO_TRADE_MANUAL_REVIEW
    top = metadata["top_candidates"].iloc[0]
    assert top["ticker"] == "EXPENSIVE"
    assert not bool(top["affordability_pass"])


def test_daily_scan_affordable_candidate_can_produce_manual_review_candidate():
    data = pd.DataFrame(
        [
            _row("2026-06-30", "GOOD", 40.0, 2.0),
            _row("2026-06-30", "WEAK", 30.0, 0.5),
        ]
    )

    scan, _ = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01")

    result = scan.iloc[0]
    assert result["action"] == MANUAL_REVIEW_CANDIDATE
    assert result["ticker"] == "GOOD"
    assert result["shares_with_100"] >= 1
    assert result["estimated_total_cost"] <= 100.0


def test_daily_scan_stale_data_outputs_no_trade():
    data = pd.DataFrame(
        [
            _row("2024-01-02", "GOOD", 40.0, 2.0),
            _row("2024-01-02", "WEAK", 30.0, 0.5),
        ]
    )

    scan, _ = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01")

    assert scan.iloc[0]["action"] == NO_TRADE_MANUAL_REVIEW
    assert scan.iloc[0]["reason"] == STALE_DATA
    assert bool(scan.iloc[0]["is_stale"])


def test_daily_scan_does_not_use_forward_returns_or_realized_outcomes():
    data = pd.DataFrame(
        [
            {
                **_row("2026-06-30", "GOOD", 40.0, 2.0),
                "fwd_return_20d": -0.90,
                "realized_return": -0.90,
            },
            {
                **_row("2026-06-30", "FUTURE_WINNER", 20.0, 0.5),
                "fwd_return_20d": 9.00,
                "realized_return": 9.00,
            },
        ]
    )

    scan, _ = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01")

    assert scan.iloc[0]["action"] == MANUAL_REVIEW_CANDIDATE
    assert scan.iloc[0]["ticker"] == "GOOD"


def test_daily_scan_reports_are_written(tmp_path: Path):
    data = pd.DataFrame(
        [
            _row("2026-06-30", "GOOD", 40.0, 2.0),
            _row("2026-06-30", "WEAK", 30.0, 0.5),
        ]
    )
    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01")
    csv_path = tmp_path / "nano_daily_scan.csv"
    md_path = tmp_path / "nano_daily_scan.md"

    write_nano_daily_scan_reports(scan, metadata, csv_path, md_path)

    assert csv_path.exists()
    assert md_path.exists()
    assert "PHOENIX NANO DAILY SCAN" in md_path.read_text(encoding="utf-8")
