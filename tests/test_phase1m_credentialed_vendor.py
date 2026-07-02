from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.research import phase1m_credentialed_vendor as p1m


def _primary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "ticker": ["AAPL", "AAPL"],
            "close": [10.0, 11.0],
            "adj_close": [10.0, 11.0],
            "volume": [1000, 1100],
        }
    )


def test_missing_credentials_are_reported_without_network_calls(monkeypatch):
    for key in ["TIINGO_API_TOKEN", "POLYGON_API_KEY", "MASSIVE_API_KEY", "ALPHAVANTAGE_API_KEY"]:
        monkeypatch.delenv(key, raising=False)

    credentials = p1m.build_credentials_status()
    capability = p1m.build_vendor_capability_matrix(credentials)
    smoke, errors, vendor_status = p1m.build_vendor_smoke_tests("2024-01-01", "2024-01-31", credentials, Path("/tmp/no-cache-needed"))

    assert credentials["format_hint_status"].eq("MISSING").all()
    assert set(vendor_status.values()) == {"CREDENTIAL_MISSING"}
    assert smoke["attempted_network_fetch"].eq(False).all()
    assert capability.loc[capability["source_name"].eq("yahoo_chart_api"), "allowed_for_execution_grade_secondary_validation"].iloc[0] == False
    assert not errors.empty


def test_credentials_status_redacts_present_values(monkeypatch):
    monkeypatch.setenv("TIINGO_API_TOKEN", "dummy-redacted-value")
    credentials = p1m.build_credentials_status()
    row = credentials.loc[credentials["env_var_name"].eq("TIINGO_API_TOKEN")].iloc[0]

    assert row["format_hint_status"] == "PRESENT_REDACTED"
    assert row["value_redacted"] == True
    assert "dummy-redacted-value" not in credentials.to_csv(index=False)


def test_vendor_smoke_status_requires_core_symbols_and_five_passes():
    rows = pd.DataFrame({"ticker": ["AAPL", "MSFT", "SPY", "QQQ", "GEV", "SQ", "RDDT"], "smoke_status": ["PASS", "PASS", "PASS", "PASS", "PASS", "NO_DATA_FOR_SYMBOL", "NO_DATA_FOR_SYMBOL"]})

    assert p1m.vendor_smoke_status(rows) == "SMOKE_PASS"


def test_parse_tiingo_adjusted_json():
    text = '[{"date":"2024-01-02T00:00:00.000Z","open":9,"high":11,"low":8,"close":10,"volume":100,"adjClose":10,"adjOpen":9,"adjHigh":11,"adjLow":8,"adjVolume":100}]'
    frame, status, reason = p1m.parse_vendor_json("tiingo_eod", text)

    assert status == "PASS"
    assert reason == ""
    assert frame.iloc[0]["adj_close"] == 10


def test_compare_secondary_match_thresholds():
    vendor = {"source_name": "tiingo_eod", "source_family": "tiingo"}
    secondary = pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-03"]), "adj_close": [10.0, 11.0], "close": [10.0, 11.0], "volume": [1000, 1100]})

    row = p1m.compare_secondary("AAPL", vendor, {}, _primary(), secondary, {"parse_status": "PASS", "parse_reason": ""})

    assert row["validation_status"] == "MATCH"
    assert row["overlap_trading_days"] == 2


def test_compare_secondary_fails_large_price_diff():
    vendor = {"source_name": "tiingo_eod", "source_family": "tiingo"}
    secondary = pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-03"]), "adj_close": [20.0, 22.0], "close": [20.0, 22.0], "volume": [1000, 1100]})

    row = p1m.compare_secondary("AAPL", vendor, {}, _primary(), secondary, {"parse_status": "PASS", "parse_reason": ""})

    assert row["validation_status"] == "FAIL"


def test_yahoo_chart_capability_is_transport_only(monkeypatch):
    for key in ["TIINGO_API_TOKEN", "POLYGON_API_KEY", "MASSIVE_API_KEY", "ALPHAVANTAGE_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    capability = p1m.build_vendor_capability_matrix(p1m.build_credentials_status())
    row = capability.loc[capability["source_name"].eq("yahoo_chart_api")].iloc[0]

    assert row["is_independent_of_primary_vendor"] == False
    assert row["allowed_for_transport_fallback_only"] == True


def test_scorecard_missing_credentials_status(monkeypatch):
    for key in ["TIINGO_API_TOKEN", "POLYGON_API_KEY", "MASSIVE_API_KEY", "ALPHAVANTAGE_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    credentials = p1m.build_credentials_status()
    capability = p1m.build_vendor_capability_matrix(credentials)
    smoke = pd.DataFrame({"smoke_status": ["CREDENTIAL_MISSING"], "ticker": ["AAPL"]})
    secondary = pd.DataFrame({"validation_status": ["CREDENTIAL_MISSING"]})
    coverage = pd.DataFrame({"is_trade_candidate": [True], "is_proxy_only": [False], "covered_by_any_independent_vendor": [False]})
    adjustment = pd.DataFrame({"detected_mismatch": [False]})
    errors = pd.DataFrame({"error_type": ["CREDENTIAL_MISSING"]})
    alias = pd.DataFrame({"audit_status": ["PASS"], "raw_line": ["AAPL"], "dynamic_earliest_safe_replay_date": [""], "is_trade_candidate": [True], "alias_status": ["UNCHANGED"]})

    score = p1m.build_phase1m_scorecard(["AAPL"], credentials, capability, smoke, secondary, coverage, adjustment, errors, alias, "")

    assert score.iloc[0]["data_readiness_status"] == p1m.PHASE_1M_CREDENTIAL_MISSING


def test_clean_watchlist_v4_requires_independent_coverage():
    clean_v3 = "AAPL\nMSFT\n"
    coverage = pd.DataFrame({"ticker": ["AAPL", "MSFT"], "covered_by_any_independent_vendor": [True, False]})
    alias = pd.DataFrame({"ticker": ["AAPL", "MSFT"], "audit_status": ["PASS", "PASS"]})

    text = p1m.build_clean_watchlist_v4(clean_v3, coverage, alias)

    assert "AAPL" in text
    assert "MSFT" not in text


def test_phase1m_reports_are_written(tmp_path: Path):
    paths = {
        "capability": tmp_path / "phase1m_vendor_capability_matrix.csv",
        "credentials": tmp_path / "phase1m_credentials_status.csv",
        "smoke": tmp_path / "phase1m_vendor_smoke_tests.csv",
        "secondary": tmp_path / "phase1m_secondary_ohlcv_validation.csv",
        "coverage": tmp_path / "phase1m_coverage_by_symbol.csv",
        "adjustment": tmp_path / "phase1m_adjustment_consistency_audit.csv",
        "errors": tmp_path / "phase1m_rate_limit_and_error_audit.csv",
        "clean_watchlist": tmp_path / "phase1m_clean_watchlist_v4_candidate.txt",
        "scorecard": tmp_path / "phase1m_data_readiness_scorecard.csv",
        "summary": tmp_path / "phase1m_data_readiness_summary.md",
    }
    frame = pd.DataFrame({"ticker": ["AAPL"]})

    p1m.write_phase1m_reports(frame, frame, frame, frame, frame, frame, frame, "AAPL\n", frame, "PHOENIX NANO PHASE 1M — CREDENTIALED INDEPENDENT VENDOR INTEGRATION AND DATA READINESS GATE\n", paths)

    assert all(path.exists() for path in paths.values())
    assert paths["summary"].read_text(encoding="utf-8").startswith("PHOENIX NANO PHASE 1M")
