from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.backtest.nano_daily_scan import (
    MANUAL_REVIEW_CANDIDATE,
    MANUAL_VERIFY_ONLY_NOT_TRADE_SIGNAL,
    NO_TRADE_MANUAL_REVIEW,
    STALE_DATA,
    append_scan_history,
    extract_candidate_34_rule,
    expected_latest_trading_date,
    build_nano_daily_scan,
    write_candidate_34_frozen_rules,
    write_nano_daily_scan_reports,
)
from src.research.auto_loop import CandidateRule


def _rule(max_entry_price: float = 50.0) -> CandidateRule:
    return CandidateRule(
        candidate_id=34,
        max_buy_rate=0.30,
        min_relative_volume_prev20=1.5,
        min_smoke_score=0.85,
        min_rank_gap=0.0,
        require_return_5d_positive=True,
        require_return_20d_positive=False,
        distance_to_52w_high_prev_min=-0.35,
        dollar_volume_min=20_000_000,
        max_trades_per_ticker_per_year=None,
        max_entry_price=max_entry_price,
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


def _candidate_csv(path: Path, rows: list[dict] | None = None) -> Path:
    base = {
        "candidate_id": 34,
        "nano_status": "NANO_RESEARCH_QUALIFIED_NOT_LIVE",
        "max_buy_rate": 0.30,
        "min_relative_volume_prev20": 1.5,
        "min_smoke_score": 0.85,
        "min_rank_gap": 0.0,
        "require_return_5d_positive": True,
        "require_return_20d_positive": False,
        "distance_to_52w_high_prev_min": -0.35,
        "dollar_volume_min": 20_000_000,
        "max_trades_per_ticker_per_year": pd.NA,
        "max_entry_price": 75.0,
        "nano_max_entry_price": 50.0,
        "executed_trade_count": 27,
        "ending_equity": 164.06,
        "max_drawdown": -0.3129,
        "profit_factor": 1.3075,
        "win_rate": 0.4815,
        "worst_account_trade_loss": -0.1178,
    }
    pd.DataFrame(rows or [base]).to_csv(path, index=False)
    return path


def test_candidate_34_extraction_returns_one_qualified_configuration(tmp_path: Path):
    csv_path = _candidate_csv(tmp_path / "auto_research_generations.csv")

    rule, row = extract_candidate_34_rule(csv_path)

    assert rule.candidate_id == 34
    assert rule.max_entry_price == 50.0
    assert row["nano_status"] == "NANO_RESEARCH_QUALIFIED_NOT_LIVE"


def test_daily_scan_outputs_exactly_one_action():
    data = pd.DataFrame([_row("2026-06-30", "GOOD", 40.0, 2.0), _row("2026-06-30", "WEAK", 30.0, 0.5)])

    scan, _ = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())

    assert len(scan) == 1
    assert scan["action"].isin([MANUAL_REVIEW_CANDIDATE, NO_TRADE_MANUAL_REVIEW]).sum() == 1


def test_daily_scan_rejects_stock_above_100_for_whole_share_account():
    data = pd.DataFrame([_row("2026-06-30", "EXPENSIVE", 120.0, 2.0), _row("2026-06-30", "WEAK", 30.0, 0.5)])

    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule(max_entry_price=150.0))

    assert scan.iloc[0]["action"] == NO_TRADE_MANUAL_REVIEW
    assert "EXPENSIVE" not in metadata["top_candidates"]["ticker"].tolist()
    rejected = metadata["rejected_candidates"].set_index("ticker")
    assert "EXPENSIVE" in rejected.index
    assert not bool(rejected.loc["EXPENSIVE", "affordability_pass"])


def test_daily_scan_rejects_stock_above_candidate_34_max_entry_price():
    data = pd.DataFrame([_row("2026-06-30", "TOO_HIGH", 60.0, 2.0), _row("2026-06-30", "WEAK", 30.0, 0.5)])

    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())

    assert scan.iloc[0]["action"] == NO_TRADE_MANUAL_REVIEW
    assert "TOO_HIGH" not in metadata["top_candidates"]["ticker"].tolist()
    rejected = metadata["rejected_candidates"].set_index("ticker")
    assert "TOO_HIGH" in rejected.index
    assert not bool(rejected.loc["TOO_HIGH", "max_entry_price_pass"])
    assert bool(rejected.loc["TOO_HIGH", "affordability_pass"])


def test_daily_scan_affordable_candidate_can_produce_manual_review_candidate():
    data = pd.DataFrame([_row("2026-06-30", "GOOD", 40.0, 2.0), _row("2026-06-30", "WEAK", 30.0, 0.5)])

    scan, _ = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())

    result = scan.iloc[0]
    assert result["action"] == MANUAL_REVIEW_CANDIDATE
    assert result["status"] == MANUAL_VERIFY_ONLY_NOT_TRADE_SIGNAL
    assert result["ticker"] == "GOOD"
    assert result["shares_with_100"] >= 1
    assert result["estimated_total_cost"] <= 100.0


def test_daily_scan_stale_data_outputs_no_trade():
    data = pd.DataFrame([_row("2024-01-02", "GOOD", 40.0, 2.0), _row("2024-01-02", "WEAK", 30.0, 0.5)])

    scan, _ = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())

    assert scan.iloc[0]["action"] == NO_TRADE_MANUAL_REVIEW
    assert scan.iloc[0]["reason"] == STALE_DATA
    assert bool(scan.iloc[0]["is_stale"])


def test_daily_scan_does_not_use_forward_returns_or_realized_outcomes():
    data = pd.DataFrame(
        [
            {**_row("2026-06-30", "GOOD", 40.0, 2.0), "fwd_return_20d": -0.90, "realized_return": -0.90},
            {**_row("2026-06-30", "FUTURE_WINNER", 20.0, 0.5), "fwd_return_20d": 9.00, "realized_return": 9.00},
        ]
    )

    scan, _ = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())

    assert scan.iloc[0]["action"] == MANUAL_REVIEW_CANDIDATE
    assert scan.iloc[0]["ticker"] == "GOOD"


def test_near_miss_table_contains_only_executable_stocks():
    data = pd.DataFrame(
        [
            _row("2026-06-30", "EXPENSIVE", 120.0, 2.0),
            _row("2026-06-30", "TOO_HIGH", 60.0, 1.9),
            _row("2026-06-30", "NEAR", 40.0, 1.0),
        ]
    )

    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())

    assert scan.iloc[0]["action"] == NO_TRADE_MANUAL_REVIEW
    assert metadata["top_candidates"]["ticker"].tolist() == ["NEAR"]
    assert metadata["top_candidates"]["affordability_pass"].all()
    assert metadata["top_candidates"]["max_entry_price_pass"].all()
    assert metadata["top_candidates"]["failed_checks"].astype(str).str.len().gt(0).all()


def test_rejected_high_priced_names_appear_only_in_rejected_summary(tmp_path: Path):
    data = pd.DataFrame(
        [
            _row("2026-06-30", "AMAT", 723.0, 2.0),
            _row("2026-06-30", "NEAR", 40.0, 1.0),
        ]
    )
    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())
    md_path = tmp_path / "nano_daily_scan.md"

    write_nano_daily_scan_reports(scan, metadata, tmp_path / "nano_daily_scan.csv", md_path)
    text = md_path.read_text(encoding="utf-8")

    near_miss_section = text.split("## Rejected Before Nano Ranking", 1)[0]
    rejected_section = text.split("## Rejected Before Nano Ranking", 1)[1]
    assert "AMAT" not in near_miss_section
    assert "AMAT" in rejected_section
    assert "Top 5 Scanned Candidates" not in text


def test_daily_scan_does_not_hardcode_a_ticker():
    data = pd.DataFrame([_row("2026-06-30", "XYZQ", 40.0, 2.0), _row("2026-06-30", "ABCD", 30.0, 0.5)])

    scan, _ = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())

    assert scan.iloc[0]["action"] == MANUAL_REVIEW_CANDIDATE
    assert scan.iloc[0]["ticker"] == "XYZQ"


def test_daily_report_contains_manual_verify_status_for_candidate(tmp_path: Path):
    data = pd.DataFrame([_row("2026-06-30", "GOOD", 40.0, 2.0), _row("2026-06-30", "WEAK", 30.0, 0.5)])
    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())
    csv_path = tmp_path / "nano_daily_scan.csv"
    md_path = tmp_path / "nano_daily_scan.md"

    write_nano_daily_scan_reports(scan, metadata, csv_path, md_path)

    assert "Status: MANUAL_VERIFY_ONLY_NOT_TRADE_SIGNAL" in md_path.read_text(encoding="utf-8")


def test_daily_report_does_not_contain_live_tradable_or_unconditional_buy_language(tmp_path: Path):
    data = pd.DataFrame([_row("2026-06-30", "GOOD", 40.0, 2.0), _row("2026-06-30", "WEAK", 30.0, 0.5)])
    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())
    md_path = tmp_path / "nano_daily_scan.md"

    write_nano_daily_scan_reports(scan, metadata, tmp_path / "nano_daily_scan.csv", md_path)
    text = md_path.read_text(encoding="utf-8")

    assert "live-tradable" not in text
    assert "Action: BUY" not in text


def test_daily_scan_reports_are_written(tmp_path: Path):
    data = pd.DataFrame([_row("2026-06-30", "GOOD", 40.0, 2.0), _row("2026-06-30", "WEAK", 30.0, 0.5)])
    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())
    csv_path = tmp_path / "nano_daily_scan.csv"
    md_path = tmp_path / "nano_daily_scan.md"
    rules_path = tmp_path / "nano_daily_candidate_34_frozen_rules.md"

    write_nano_daily_scan_reports(scan, metadata, csv_path, md_path)
    write_candidate_34_frozen_rules(rules_path, _rule(), _settings(), source_row=pd.Series({"candidate_id": 34}))

    assert csv_path.exists()
    assert md_path.exists()
    assert rules_path.exists()
    assert "PHOENIX NANO DAILY SCAN" in md_path.read_text(encoding="utf-8")


def test_daily_scan_csv_uses_required_row_types(tmp_path: Path):
    data = pd.DataFrame(
        [
            _row("2026-06-30", "AMAT", 723.0, 2.0),
            _row("2026-06-30", "NEAR", 40.0, 1.0),
        ]
    )
    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())
    csv_path = tmp_path / "nano_daily_scan.csv"

    write_nano_daily_scan_reports(scan, metadata, csv_path, tmp_path / "nano_daily_scan.md")
    rows = pd.read_csv(csv_path)

    assert {
        "row_type",
        "ticker",
        "action",
        "reference_price",
        "shares_with_100",
        "estimated_total_cost",
        "estimated_cash_remaining",
        "affordability_pass",
        "max_entry_price_pass",
        "signal_rule_pass",
        "full_rule_pass",
        "failed_checks",
    }.issubset(rows.columns)
    assert rows["row_type"].tolist() == [
        "FINAL",
        "EXECUTABLE_NEAR_MISS",
        "REJECTED_BEFORE_NANO_RANKING",
    ]
    near = rows.loc[rows["row_type"].eq("EXECUTABLE_NEAR_MISS")].iloc[0]
    assert bool(near["affordability_pass"])
    assert bool(near["max_entry_price_pass"])
    assert isinstance(near["failed_checks"], str) and near["failed_checks"]


def test_diagnostic_csv_includes_scan_metadata_columns(tmp_path: Path):
    data = pd.DataFrame([_row("2026-06-30", "GOOD", 40.0, 2.0), _row("2026-06-30", "NEAR", 30.0, 1.0)])
    scan, metadata = build_nano_daily_scan(
        data,
        _settings(),
        requested_end="2026-07-01",
        rule=_rule(),
        data_source="unit",
        scan_timestamp_utc="2026-07-01T12:00:00+00:00",
    )
    csv_path = tmp_path / "nano_daily_scan.csv"

    write_nano_daily_scan_reports(scan, metadata, csv_path, tmp_path / "nano_daily_scan.md")
    rows = pd.read_csv(csv_path)

    assert {
        "scan_timestamp_utc",
        "latest_data_date",
        "expected_latest_trading_date",
        "is_stale",
        "data_source",
        "status",
        "smoke_score",
        "decision_strength",
        "relative_volume_prev20",
        "return_5d",
        "return_20d",
        "distance_to_52w_high_prev",
        "dollar_volume",
        "rejection_reason",
    }.issubset(rows.columns)


def test_history_csv_is_created_and_idempotent(tmp_path: Path):
    data = pd.DataFrame([_row("2026-06-30", "GOOD", 40.0, 2.0), _row("2026-06-30", "NEAR", 30.0, 1.0)])
    scan, metadata = build_nano_daily_scan(
        data,
        _settings(),
        requested_end="2026-07-01",
        rule=_rule(),
        scan_timestamp_utc="2026-07-01T12:00:00+00:00",
    )
    csv_path = tmp_path / "nano_daily_scan.csv"
    history_path = tmp_path / "nano_daily_scan_history.csv"

    write_nano_daily_scan_reports(scan, metadata, csv_path, tmp_path / "nano_daily_scan.md", history_path)
    first = pd.read_csv(history_path)
    write_nano_daily_scan_reports(scan, metadata, csv_path, tmp_path / "nano_daily_scan.md", history_path)
    second = pd.read_csv(history_path)

    assert history_path.exists()
    assert len(first) == len(second)


def test_history_appends_new_scan_when_timestamp_changes(tmp_path: Path):
    data = pd.DataFrame([_row("2026-06-30", "GOOD", 40.0, 2.0), _row("2026-06-30", "NEAR", 30.0, 1.0)])
    history_path = tmp_path / "nano_daily_scan_history.csv"
    for timestamp in ["2026-07-01T12:00:00+00:00", "2026-07-01T13:00:00+00:00"]:
        scan, metadata = build_nano_daily_scan(
            data,
            _settings(),
            requested_end="2026-07-01",
            rule=_rule(),
            scan_timestamp_utc=timestamp,
        )
        write_nano_daily_scan_reports(
            scan,
            metadata,
            tmp_path / "nano_daily_scan.csv",
            tmp_path / "nano_daily_scan.md",
            history_path,
        )

    history = pd.read_csv(history_path)
    assert history["scan_timestamp_utc"].nunique() == 2
    assert set(history["scan_timestamp_utc"]) == {
        "2026-07-01T12:00:00+00:00",
        "2026-07-01T13:00:00+00:00",
    }


def test_daily_report_includes_history_total_row_count(tmp_path: Path):
    data = pd.DataFrame([_row("2026-06-30", "GOOD", 40.0, 2.0), _row("2026-06-30", "NEAR", 30.0, 1.0)])
    scan, metadata = build_nano_daily_scan(
        data,
        _settings(),
        requested_end="2026-07-01",
        rule=_rule(),
        scan_timestamp_utc="2026-07-01T12:00:00+00:00",
    )
    md_path = tmp_path / "nano_daily_scan.md"

    write_nano_daily_scan_reports(
        scan,
        metadata,
        tmp_path / "nano_daily_scan.csv",
        md_path,
        tmp_path / "nano_daily_scan_history.csv",
    )

    assert "History total row count:" in md_path.read_text(encoding="utf-8")


def test_weekend_and_holiday_use_prior_market_trading_day():
    assert expected_latest_trading_date("2026-07-06").strftime("%Y-%m-%d") == "2026-07-02"
    assert expected_latest_trading_date("2026-07-05").strftime("%Y-%m-%d") == "2026-07-02"


def test_stale_data_older_than_expected_trading_date_outputs_stale():
    data = pd.DataFrame([_row("2026-06-29", "GOOD", 40.0, 2.0), _row("2026-06-29", "NEAR", 30.0, 1.0)])

    scan, metadata = build_nano_daily_scan(data, _settings(), requested_end="2026-07-01", rule=_rule())

    assert scan.iloc[0]["action"] == NO_TRADE_MANUAL_REVIEW
    assert scan.iloc[0]["reason"] == STALE_DATA
    assert bool(scan.iloc[0]["is_stale"])
    assert metadata["expected_latest_trading_date"] == "2026-06-30"
