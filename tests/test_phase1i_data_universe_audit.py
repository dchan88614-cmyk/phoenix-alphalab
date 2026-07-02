from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.backtest.forward_returns import add_forward_returns
from src.research.auto_loop import CandidateRule
from src.research.phase1i_data_universe_audit import (
    PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH,
    build_data_gap_incident_log,
    build_phase1i_data_universe_audit,
    build_symbol_data_quality_audit,
    build_universe_variant_holdout_results,
    build_universe_variants,
    build_vendor_validation_matrix,
    phase1i_status,
    theme_balanced_selection,
    write_phase1i_reports,
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
        rows.append(_row(date, "BBAI", 18.0 + index * 0.04, 1.8))
        rows.append(_row(date, "SPY", 100.0 + index * 0.03, 1.0))
        rows.append(_row(date, "QQQ", 110.0 + index * 0.04, 1.0))
    return add_forward_returns(pd.DataFrame(rows), [1, 3, 5, 10, 20])


def _universe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "RIVN", "quote_type": "EQUITY", "exchange": "NYSE", "short_name": "Rivian", "long_name": "Rivian", "market_cap": 1.0, "pass_universe": True, "reason": "pass"},
            {"ticker": "BBAI", "quote_type": "EQUITY", "exchange": "NYSE", "short_name": "BigBear", "long_name": "BigBear", "market_cap": 1.0, "pass_universe": True, "reason": "pass"},
            {"ticker": "BITF", "quote_type": None, "exchange": None, "short_name": None, "long_name": None, "market_cap": None, "pass_universe": False, "reason": "metadata_incomplete"},
        ]
    )


def test_cli_dispatch_flag_exists():
    from src.main import build_parser

    args = build_parser().parse_args(["--tickers", "AAPL", "--start", "2024-01-01", "--end", "2024-02-01", "--phase1i-data-universe-audit"])

    assert args.phase1i_data_universe_audit


def test_symbol_data_quality_grading_is_deterministic():
    quality = build_symbol_data_quality_audit(_market_data(), ["RIVN", "BITF", "SPY", "QQQ"], _universe(), pd.DataFrame({"ticker": ["BITF"], "reason": ["metadata_incomplete"]}), "2024-01-02", "2024-09-01")

    grades = set(quality["data_quality_grade"])
    assert grades <= {"PASS", "WARN", "FAIL"}
    assert quality.loc[quality["ticker"].eq("BITF"), "data_quality_grade"].iloc[0] == "FAIL"


def test_metadata_rejected_and_download_failed_symbols_are_logged():
    quality = build_symbol_data_quality_audit(_market_data(), ["BITF"], _universe(), pd.DataFrame({"ticker": ["BITF"], "reason": ["metadata_incomplete"]}), "2024-01-02", "2024-09-01")
    incidents = build_data_gap_incident_log(quality, pd.DataFrame())

    assert "METADATA_REJECTED" in set(incidents["incident_type"])
    assert "YFINANCE_404" in set(incidents["incident_type"])


def test_vendor_validation_handles_missing_secondary_source():
    vendor = build_vendor_validation_matrix(_market_data(), ["RIVN"])

    assert vendor.iloc[0]["validation_status"] == "NO_SECOND_SOURCE"


def test_universe_variants_use_predeclared_non_future_criteria():
    quality = build_symbol_data_quality_audit(_market_data(), ["RIVN", "BBAI", "BITF"], _universe(), pd.DataFrame({"ticker": ["BITF"], "reason": ["metadata_incomplete"]}), "2024-01-02", "2024-09-01")
    variants = build_universe_variants(quality, _market_data(), ["RIVN", "BBAI", "BITF"])

    assert "BITF" not in variants["data_quality_pass_only"]
    assert "forward_return_20d" not in quality.columns


def test_theme_balanced_selection_does_not_use_future_returns_or_pnl():
    quality = pd.DataFrame(
        {
            "ticker": ["RIVN", "F", "BBAI"],
            "data_quality_grade": ["WARN", "WARN", "WARN"],
            "avg_dollar_volume_20d": [10, 20, 5],
            "forward_return_20d": [99, -99, 88],
            "pnl_dollars": [-1, 100, -5],
        }
    )

    selected = theme_balanced_selection(quality, max_per_theme=1)

    assert "F" in selected
    assert "RIVN" not in selected


def test_holdout_results_include_required_metrics():
    matrix = pd.DataFrame(
        [
            {
                "universe_variant": "current_watchlist_full",
                "strategy_name": "candidate35_trend_quality_frozen",
                "sample_id": 20,
                "split_name": "holdout",
                "universe_size": 2,
                "buy_count": 50,
                "ending_account_value": 150,
                "max_drawdown": -0.1,
                "simulated_win_rate": 0.6,
                "accuracy_20d": 0.6,
                "profit_factor": 1.5,
                "worst_trade_loss_percent": -0.02,
                "top_loss_ticker_contribution_share": 0.1,
                "top_loss_theme_contribution_share": 0.1,
                "median_ending_value_excluding_best_trade": 130,
            }
        ]
    )
    holdout = build_universe_variant_holdout_results(matrix, 30)

    assert "median_holdout_profit_factor" in holdout.columns
    assert "failed_gates" in holdout.columns


def test_phase1i_status_cannot_approve_execution():
    quality = pd.DataFrame({"data_quality_grade": ["FAIL", "WARN"]})
    vendor = pd.DataFrame({"validation_status": ["NO_SECOND_SOURCE", "NO_SECOND_SOURCE"]})
    incidents = pd.DataFrame({"severity": ["HIGH"]})

    status = phase1i_status(quality, vendor, incidents, pd.DataFrame(), 30)

    assert status == PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH
    assert "LIVE" not in status
    assert "PAPER" not in status


def test_phase1i_reports_are_written(tmp_path: Path):
    quality, vendor, composition, matrix, holdout, incidents, rejected, attribution, summary_md, _ = build_phase1i_data_universe_audit(
        _market_data(),
        AccountSettings(),
        _rule(),
        ["RIVN", "BBAI", "BITF"],
        _universe(),
        pd.DataFrame({"ticker": ["BITF"], "reason": ["metadata_incomplete"]}),
        "2024-01-02",
        "2024-09-01",
        replay_rounds=5,
        replay_sample_count=20,
    )
    paths = {
        "quality": tmp_path / "quality.csv",
        "vendor": tmp_path / "vendor.csv",
        "composition": tmp_path / "composition.csv",
        "matrix": tmp_path / "matrix.csv",
        "holdout": tmp_path / "holdout.csv",
        "incidents": tmp_path / "incidents.csv",
        "rejected": tmp_path / "rejected.csv",
        "attribution": tmp_path / "attribution.csv",
        "summary": tmp_path / "summary.md",
    }

    write_phase1i_reports(quality, vendor, composition, matrix, holdout, incidents, rejected, attribution, summary_md, paths)

    assert paths["quality"].exists()
    assert paths["holdout"].exists()
    assert paths["summary"].read_text(encoding="utf-8").startswith(
        "PHOENIX NANO PHASE 1I — DATA QUALITY, VENDOR VALIDATION, AND UNIVERSE DESIGN AUDIT"
    )
