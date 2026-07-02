from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.research import phase1l_secondary_adapter as p1l


def _primary() -> pd.DataFrame:
    return pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-03"]), "ticker": ["AAPL", "AAPL"], "close": [10.0, 11.0], "volume": [100, 110], "adj_close": [10.0, 11.0]})


def test_stooq_parser_parses_normal_csv():
    text = "Date,Open,High,Low,Close,Volume\n2024-01-02,9,11,8,10,100\n"
    frame, status, reason = p1l.parse_ohlcv_text(text)

    assert status == "PASS"
    assert reason == ""
    assert len(frame) == 1


def test_stooq_parser_detects_html_block():
    frame, status, reason = p1l.parse_ohlcv_text("<html><script>verify</script></html>")

    assert frame.empty
    assert status == "HTML_OR_BLOCKED"
    assert "HTML" in reason


def test_stooq_parser_supports_bom_case_insensitive_semicolon_csv():
    text = "\ufeffdate;OPEN;High;LOW;close;Volume\n2024-01-02;9;11;8;10;100\n"
    frame, status, _ = p1l.parse_ohlcv_text(text)

    assert status == "PASS"
    assert frame.iloc[0]["close"] == 10


def test_smoke_v2_does_not_mark_global_unavailable_without_diagnostics(monkeypatch, tmp_path: Path):
    def fake_fetch(url, cache_path):
        return {
            "text": "not csv but not html",
            "url": url,
            "cache_path": str(cache_path),
            "attempted_network_fetch": True,
            "used_cache_fallback": False,
            "http_status_if_available": "200",
            "final_url_if_available": url,
            "content_type_if_available": "text/plain",
            "exception_class_if_any": "",
        }

    monkeypatch.setattr(p1l, "fetch_text", fake_fetch)
    _, smoke = p1l.build_stooq_smoke_v2("2024-01-01", "2024-01-31", tmp_path)

    assert smoke["source_level_status"].iloc[0] == "PARSER_BUG_SUSPECTED"


def test_yahoo_chart_is_transport_only_not_independent():
    row = p1l.compare_transport_fallback("AAPL", _primary(), _primary().drop(columns=["ticker"]), {"text": "{}", "used_cache_fallback": False})

    assert row["is_independent_of_primary_vendor"] is False
    assert row["transport_status"] == "TRANSPORT_MATCH"


def test_secondary_validation_v3_cannot_match_without_overlap():
    primary = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"]), "close": [10], "volume": [100], "adj_close": [10]})
    secondary = pd.DataFrame({"date": pd.to_datetime(["2024-01-03"]), "close": [10], "volume": [100]})

    row = p1l.compare_validation_v3("AAPL", primary, secondary, "aapl.us", "SMOKE_PASS", False)

    assert row["validation_status"] != "MATCH"
    assert row["overlap_trading_days"] == 0


def test_readiness_gate_fails_when_independent_coverage_zero():
    score = p1l.build_phase1l_data_readiness_scorecard(
        ["AAPL", "SPY", "QQQ"],
        pd.DataFrame({"smoke_status": ["HTML_OR_BLOCKED"] * 4}),
        pd.DataFrame({"parser_status": ["HTML_OR_BLOCKED"], "detected_payload_type": ["HTML_BLOCK"]}),
        pd.DataFrame({"ticker": ["AAPL"], "validation_status": ["GLOBAL_SOURCE_UNAVAILABLE"]}),
        pd.DataFrame({"transport_status": ["TRANSPORT_MATCH"]}),
        pd.DataFrame({"audit_status": ["FAIL"], "raw_line": ["AAPL"], "dynamic_earliest_safe_replay_date": [""], "is_trade_candidate": [True], "alias_status": ["UNCHANGED"]}),
        pd.DataFrame({"ticker": ["AAPL", "SPY", "QQQ"], "confidence": ["HIGH", "HIGH", "HIGH"]}),
        "AAPL\n",
    )

    assert score.iloc[0]["data_readiness_status"] == p1l.PHASE_1L_SECONDARY_VENDOR_BLOCKED


def test_readiness_gate_can_mark_adapter_ready_vendor_missing():
    score = p1l.build_phase1l_data_readiness_scorecard(
        ["AAPL", "SPY", "QQQ"],
        pd.DataFrame({"smoke_status": ["HTML_OR_BLOCKED"] * 4}),
        pd.DataFrame({"parser_status": ["HTML_OR_BLOCKED"], "detected_payload_type": ["HTML_BLOCK"]}),
        pd.DataFrame({"ticker": ["AAPL"], "validation_status": ["GLOBAL_SOURCE_UNAVAILABLE"]}),
        pd.DataFrame({"transport_status": ["TRANSPORT_MATCH"]}),
        pd.DataFrame({"audit_status": ["PASS"], "raw_line": ["AAPL"], "dynamic_earliest_safe_replay_date": [""], "is_trade_candidate": [True], "alias_status": ["UNCHANGED"]}),
        pd.DataFrame({"ticker": ["AAPL", "SPY", "QQQ"], "confidence": ["HIGH", "HIGH", "HIGH"]}),
        "AAPL\n",
    )
    assert score.iloc[0]["data_readiness_status"] == p1l.PHASE_1L_DATA_ADAPTER_READY_VENDOR_MISSING


def test_alias_audit_fails_blank_date_gate_comment():
    lifecycle = pd.DataFrame({"original_watchlist_ticker": ["GEV"], "canonical_current_ticker": ["GEV"], "historical_ticker": ["GEV"], "alias_status": ["UNCHANGED"]})
    audit, _ = p1l.build_alias_clean_watchlist_audit("GEV # earliest_safe_replay_date=\n", lifecycle)

    assert audit.iloc[0]["audit_status"] == "FAIL"


def test_sq_xyz_lifecycle_normalizes_effective_current_date():
    lifecycle = pd.DataFrame({"original_watchlist_ticker": ["SQ"], "canonical_current_ticker": ["XYZ"], "historical_ticker": ["SQ"], "alias_status": ["RENAMED"]})
    audit, clean = p1l.build_alias_clean_watchlist_audit("SQ # earliest_safe_replay_date=\n", lifecycle)

    assert audit.iloc[0]["canonical_current_ticker"] == "XYZ"
    assert audit.iloc[0]["dynamic_earliest_safe_replay_date"] == "2025-01-21"
    assert "earliest_safe_replay_date=2025-01-21" in clean


def test_spy_qqq_proxy_only_excluded_from_trade_candidates():
    lifecycle = pd.DataFrame(
        {
            "original_watchlist_ticker": ["SPY", "QQQ"],
            "canonical_current_ticker": ["SPY", "QQQ"],
            "historical_ticker": ["SPY", "QQQ"],
            "alias_status": ["ETF_OR_INDEX_PROXY", "ETF_OR_INDEX_PROXY"],
        }
    )
    audit, clean = p1l.build_alias_clean_watchlist_audit("SPY\nQQQ\n", lifecycle)

    assert audit["is_proxy_only"].all()
    assert "SPY" not in [line.strip() for line in clean.splitlines()]
    assert "QQQ" not in [line.strip() for line in clean.splitlines()]


def test_phase1l_reports_are_written(tmp_path: Path):
    paths = {
        "capability": tmp_path / "phase1l_secondary_source_capability_matrix.csv",
        "diagnostics": tmp_path / "phase1l_raw_response_diagnostics.csv",
        "smoke": tmp_path / "phase1l_secondary_vendor_smoke_test_v2.csv",
        "secondary": tmp_path / "phase1l_secondary_ohlcv_validation_v3.csv",
        "yahoo": tmp_path / "phase1l_yahoo_chart_transport_fallback_audit.csv",
        "alias_audit": tmp_path / "phase1l_alias_clean_watchlist_audit.csv",
        "clean_watchlist": tmp_path / "phase1l_clean_watchlist_v3_candidate.txt",
        "scorecard": tmp_path / "phase1l_data_readiness_scorecard.csv",
        "summary": tmp_path / "phase1l_data_readiness_summary.md",
    }
    frame = pd.DataFrame({"ticker": ["AAPL"]})

    p1l.write_phase1l_reports(frame, frame, frame, frame, frame, frame, "AAPL\n", frame, "PHOENIX NANO PHASE 1L — SECONDARY DATA ADAPTER HARDENING AND VENDOR DECISION GATE\n", paths)

    assert all(path.exists() for path in paths.values())
    assert paths["summary"].read_text(encoding="utf-8").startswith("PHOENIX NANO PHASE 1L")
