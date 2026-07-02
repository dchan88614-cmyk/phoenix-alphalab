from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.backtest.forward_returns import add_forward_returns
from src.research.auto_loop import CandidateRule
from src.research.phase1f_failure_audit import (
    PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN,
    build_data_quality_audit,
    build_failure_ledger_for_sample,
    build_market_regime_lookup,
    build_phase1f_failure_audit,
    build_theme_taxonomy,
    phase1f_status,
    write_phase1f_reports,
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


def _row(date: pd.Timestamp, ticker: str, close: float, factor: float = 2.0, volume: int = 1_000_000) -> dict:
    return {
        "date": date,
        "ticker": ticker,
        "open": close,
        "high": close * 1.03,
        "low": close * 0.99,
        "close": close,
        "volume": volume,
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


def _market_data(periods: int = 140) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for index, date in enumerate(dates):
        rows.append(_row(date, "RIVN", 20.0 + index * 0.08, 2.5))
        rows.append(_row(date, "BBAI", 18.0 - index * 0.01, 1.5))
        rows.append(_row(date, "SPY", 100.0 + index * 0.03, 1.0))
    return add_forward_returns(pd.DataFrame(rows), [1, 3, 5, 10, 20])


def _diagnostics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "sample_id": 0,
                "replay_date": "2024-02-01",
                "ticker": "RIVN",
                "theme": "EV / mobility",
                "subtheme": "EV OEM",
                "reference_price": 20.0,
                "entry_price": 20.2,
                "entry_gap_pct": 0.01,
                "shares_with_100": 4,
                "estimated_total_cost": 80.8,
                "decision_strength": 0.8,
                "smoke_score": 0.9,
                "volatility_20d": 0.04,
                "atr_pct": 0.02,
                "distance_from_52w_high_pct": -0.1,
                "relative_volume_prev20": 2.0,
                "return_5d_prior": 0.05,
                "return_10d_prior": 0.08,
                "forward_return_20d": -0.05,
                "stopped_out_then_20d_positive": False,
                "baseline_exit_reason": "STOP",
                "baseline_pnl_dollars": -5.0,
                "baseline_trade_return_pct": -0.05,
            },
            {
                "sample_id": 0,
                "replay_date": "2024-02-05",
                "ticker": "BBAI",
                "theme": "AI / software",
                "subtheme": "defense AI",
                "reference_price": 18.0,
                "entry_price": 18.1,
                "entry_gap_pct": 0.005,
                "shares_with_100": 5,
                "estimated_total_cost": 90.5,
                "decision_strength": 0.7,
                "smoke_score": 0.88,
                "volatility_20d": 0.08,
                "atr_pct": 0.05,
                "distance_from_52w_high_pct": -0.2,
                "relative_volume_prev20": 1.5,
                "return_5d_prior": 0.10,
                "return_10d_prior": 0.15,
                "forward_return_20d": 0.04,
                "stopped_out_then_20d_positive": True,
                "baseline_exit_reason": "TARGET_1",
                "baseline_pnl_dollars": 4.0,
                "baseline_trade_return_pct": 0.04,
            },
        ]
    )


def _decisions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"sample_id": 0, "replay_date": "2024-02-01", "decision": "HISTORICAL_BUY_CANDIDATE", "ticker": "RIVN"},
            {"sample_id": 0, "replay_date": "2024-02-05", "decision": "HISTORICAL_BUY_CANDIDATE", "ticker": "BBAI"},
        ]
    )


def _trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"replay_date": "2024-02-01", "ticker": "RIVN", "status": "EXECUTED", "cash_before": 100.0, "cash_after_exit": 95.0, "exit_reason": "STOP", "pnl_dollars": -5.0, "trade_return_pct": -0.05},
            {"replay_date": "2024-02-05", "ticker": "BBAI", "status": "EXECUTED", "cash_before": 95.0, "cash_after_exit": 99.0, "exit_reason": "TARGET_1", "pnl_dollars": 4.0, "trade_return_pct": 0.04},
        ]
    )


def test_failure_ledger_contains_all_accepted_historical_candidates():
    ledger = build_failure_ledger_for_sample(0, _decisions(), _diagnostics(), _trades(), _market_data())

    assert len(ledger) == 2
    assert set(ledger["ticker"]) == {"RIVN", "BBAI"}


def test_failure_ledger_uses_only_pre_entry_features_for_decision_side():
    data = _market_data()
    first = build_failure_ledger_for_sample(0, _decisions(), _diagnostics(), _trades(), data)
    changed = data.copy()
    changed.loc[changed["date"].gt(pd.Timestamp("2024-02-01")) & changed["ticker"].eq("SPY"), "close"] = 999.0
    second = build_failure_ledger_for_sample(0, _decisions(), _diagnostics(), _trades(), changed)

    assert first.loc[first["ticker"].eq("RIVN"), "market_regime_label"].iloc[0] == second.loc[second["ticker"].eq("RIVN"), "market_regime_label"].iloc[0]


def test_theme_taxonomy_eliminates_avoidable_unmapped_values():
    taxonomy = build_theme_taxonomy(pd.DataFrame({"ticker": ["RIVN", "BBAI", "UNKNOWNX"]}))

    assert taxonomy.loc[taxonomy["ticker"].eq("RIVN"), "theme"].iloc[0] == "EV / mobility"
    assert taxonomy.loc[taxonomy["ticker"].eq("UNKNOWNX"), "theme"].iloc[0] == "UNMAPPED_LOW_CONFIDENCE"
    assert "UNMAPPED_LOW_CONFIDENCE" in taxonomy.loc[taxonomy["ticker"].eq("UNKNOWNX"), "notes"].iloc[0]


def test_market_regime_labels_use_only_data_on_or_before_replay_date():
    data = _market_data()
    first = build_market_regime_lookup(data)
    changed = data.copy()
    changed.loc[changed["date"].gt(pd.Timestamp("2024-03-01")) & changed["ticker"].eq("SPY"), "close"] = 1.0
    second = build_market_regime_lookup(changed)

    assert first["2024-03-01"]["spy_trend_label"] == second["2024-03-01"]["spy_trend_label"]


def test_data_quality_audit_catches_missing_and_abnormal_cases():
    data = _market_data(40)
    data = data.loc[~((data["ticker"].eq("RIVN")) & (data["date"].eq(data["date"].iloc[3])))]
    data.loc[data["ticker"].eq("BBAI"), "volume"] = 0
    quality = build_data_quality_audit(data, pd.DataFrame(), pd.DataFrame([{"ticker": "BITF", "reason": "metadata_incomplete"}]), "SPY")

    assert "metadata_rejected_symbol" in set(quality["issue_type"])
    assert quality.loc[quality["issue_type"].eq("zero_volume_days"), "issue_count"].sum() > 0


def test_no_active_scan_behavior_is_changed():
    from src.main import build_parser

    args = build_parser().parse_args(["--tickers", "AAPL", "--start", "2024-01-01", "--end", "2024-02-01"])
    assert not args.phase1f_failure_audit


def test_phase1f_status_never_approves_phase2_or_deployment():
    status = phase1f_status(False, 0.10, 0.10, 0.0, 100.0)

    assert status == PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN
    assert "PHASE_2" not in status
    assert "DEPLOY" not in status


def test_phase1f_reports_are_written(tmp_path: Path):
    ledger, taxonomy, drawdown, regime, quality, summary = build_phase1f_failure_audit(
        _market_data(),
        AccountSettings(),
        _rule(),
        replay_rounds=5,
        replay_sample_count=2,
    )

    write_phase1f_reports(
        ledger,
        taxonomy,
        drawdown,
        regime,
        quality,
        summary,
        tmp_path / "ledger.csv",
        tmp_path / "taxonomy.csv",
        tmp_path / "drawdown.csv",
        tmp_path / "regime.csv",
        tmp_path / "quality.csv",
        tmp_path / "summary.md",
    )

    assert (tmp_path / "ledger.csv").exists()
    assert (tmp_path / "taxonomy.csv").exists()
    assert (tmp_path / "drawdown.csv").exists()
    assert (tmp_path / "regime.csv").exists()
    assert (tmp_path / "quality.csv").exists()
    assert (tmp_path / "summary.md").read_text(encoding="utf-8").startswith(
        "PHOENIX NANO PHASE 1F — FAILURE ATTRIBUTION, TAXONOMY, AND DATA QUALITY AUDIT"
    )
