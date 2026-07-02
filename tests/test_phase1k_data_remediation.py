from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.research import phase1k_data_remediation as p1k


def _prices() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=140)
    rows = []
    for ticker in ["AAPL", "MSFT", "SPY", "QQQ", "GEV", "SQ"]:
        start = 100 if ticker == "GEV" else 0
        for index, date in enumerate(dates[start:]):
            rows.append({"date": date, "ticker": ticker, "close": 10 + index, "volume": 1000 + index, "adj_close": 10 + index})
    return pd.DataFrame(rows)


def _phase1j_quarantine() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "AAPL", "quarantine_status": "ALLOW_RESEARCH", "quarantine_reason": "clean_research_symbol", "suggested_action": "KEEP_WITH_WARNING", "earliest_safe_replay_date": ""},
            {"ticker": "GEV", "quarantine_status": "RESEARCH_WARN", "quarantine_reason": "recent_listing_requires_earliest_safe_replay_date", "suggested_action": "ALLOW_AFTER_DATE", "earliest_safe_replay_date": "2024-05-21"},
            {"ticker": "SQ", "quarantine_status": "QUARANTINE", "quarantine_reason": "symbol_master_status:UNKNOWN", "suggested_action": "DROP_FROM_RESEARCH", "earliest_safe_replay_date": ""},
            {"ticker": "BITF", "quarantine_status": "QUARANTINE", "quarantine_reason": "symbol_master_status:UNKNOWN", "suggested_action": "DROP_FROM_RESEARCH", "earliest_safe_replay_date": ""},
            {"ticker": "SPY", "quarantine_status": "ALLOW_RESEARCH", "quarantine_reason": "clean_research_symbol", "suggested_action": "KEEP_WITH_WARNING", "earliest_safe_replay_date": ""},
            {"ticker": "QQQ", "quarantine_status": "ALLOW_RESEARCH", "quarantine_reason": "clean_research_symbol", "suggested_action": "KEEP_WITH_WARNING", "earliest_safe_replay_date": ""},
        ]
    )


def _symbol_master() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "AAPL", "symbol_master_status": "ACTIVE_LISTED_EQUITY"},
            {"ticker": "GEV", "symbol_master_status": "ACTIVE_LISTED_EQUITY"},
            {"ticker": "SQ", "symbol_master_status": "UNKNOWN"},
            {"ticker": "BITF", "symbol_master_status": "UNKNOWN"},
            {"ticker": "SPY", "symbol_master_status": "ETF_OR_INDEX_PROXY"},
            {"ticker": "QQQ", "symbol_master_status": "ETF_OR_INDEX_PROXY"},
        ]
    )


def _taxonomy() -> pd.DataFrame:
    return p1k.build_taxonomy_resolution_v2(
        pd.DataFrame(
            {
                "ticker": ["AAPL", "GEV", "SQ", "BITF", "SPY", "QQQ"],
                "prior_theme": ["x"] * 6,
                "resolved_theme": ["x"] * 6,
                "resolved_subtheme": ["x"] * 6,
                "confidence": ["HIGH", "HIGH", "LOW", "LOW", "LOW", "LOW"],
                "evidence_source": ["test"] * 6,
                "notes": [""] * 6,
            }
        ),
        ["AAPL", "GEV", "SQ", "BITF", "SPY", "QQQ"],
        p1k.build_taxonomy_static_overrides(),
    )


def test_secondary_vendor_smoke_distinguishes_global_from_symbol_no_data(monkeypatch, tmp_path: Path):
    def fake_fetch(ticker, start, end, cache_dir, smoke=False):
        status = "PASS" if ticker == "AAPL" else "NO_DATA_FOR_SYMBOL"
        return pd.DataFrame({"date": pd.to_datetime(["2024-01-02"]), "close": [1], "volume": [1]}) if status == "PASS" else pd.DataFrame(), {
            "source_name": "stooq",
            "ticker": ticker,
            "lookup_symbol": f"{ticker.lower()}.us",
            "url_or_cache_key": "cache",
            "attempted_network_fetch": True,
            "used_cache_fallback": False,
            "http_status_if_available": "200",
            "exception_class_if_any": "",
            "response_bytes": 10,
            "parsed_rows": 1 if status == "PASS" else 0,
            "first_date": "2024-01-02" if status == "PASS" else "",
            "last_date": "2024-01-02" if status == "PASS" else "",
            "required_start_date": start,
            "required_end_date": end,
            "smoke_status": status,
            "smoke_reason": status,
            "_fetch_status": status,
        }

    monkeypatch.setattr(p1k, "fetch_stooq_for_report", fake_fetch)
    smoke = p1k.build_secondary_vendor_smoke_test("2024-01-01", "2024-01-31", tmp_path)

    assert "PASS" in set(smoke["smoke_status"])
    assert "NO_DATA_FOR_SYMBOL" in set(smoke["smoke_status"])
    assert "GLOBAL_SOURCE_UNAVAILABLE" not in set(smoke["smoke_status"])


def test_secondary_validation_never_matches_without_overlap_days_and_diffs():
    primary = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"]), "close": [10], "volume": [100], "adj_close": [10]})
    secondary = pd.DataFrame({"date": pd.to_datetime(["2024-01-03"]), "close": [10], "volume": [100]})
    report = {"_fetch_status": "AVAILABLE", "used_cache_fallback": False, "smoke_reason": ""}

    row = p1k.compare_ohlcv_v2("AAPL", primary, secondary, "AVAILABLE_OR_CACHED", report)

    assert row["validation_status"] != "MATCH"
    assert row["overlap_trading_days"] == 0


def test_cached_secondary_data_is_labeled_as_cache_based():
    primary = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"]), "close": [10], "volume": [100], "adj_close": [10]})
    secondary = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"]), "close": [10], "volume": [100]})
    report = {"_fetch_status": "CACHE_ONLY_AVAILABLE", "used_cache_fallback": True, "smoke_reason": ""}

    row = p1k.compare_ohlcv_v2("AAPL", primary, secondary, "AVAILABLE_OR_CACHED", report)

    assert row["validation_status"] == "CACHE_ONLY_MATCH"


def test_sq_xyz_lifecycle_alias_has_no_future_eligibility_leak():
    lifecycle = p1k.build_symbol_lifecycle_alias_map(["SQ"], _symbol_master())
    row = lifecycle.iloc[0]

    assert row["canonical_current_ticker"] == "XYZ"
    assert row["historical_ticker"] == "SQ"
    assert row["effective_end_date"] == "2025-01-20"
    assert row["replay_handling"] == "USE_HISTORICAL_THEN_CURRENT_ALIAS"


def test_spy_qqq_taxonomy_are_proxies_and_excluded_from_trade_candidates():
    taxonomy = _taxonomy()
    clean = p1k.build_clean_watchlist_v2_candidate(_phase1j_quarantine(), pd.DataFrame(), taxonomy)

    assert taxonomy.loc[taxonomy["ticker"].eq("SPY"), "phase1k_resolved_theme"].iloc[0] == "ETF / index proxy"
    assert taxonomy.loc[taxonomy["ticker"].eq("QQQ"), "phase1k_resolved_theme"].iloc[0] == "ETF / index proxy"
    assert "SPY" not in clean
    assert "QQQ" not in clean


def test_static_taxonomy_overrides_fix_targeted_low_and_wrong_medium_rows():
    overrides = p1k.build_taxonomy_static_overrides()
    taxonomy = p1k.build_taxonomy_resolution_v2(pd.DataFrame(), ["BITF", "ASTS", "SOUN", "TTD"], overrides)

    assert taxonomy["confidence"].eq("LOW").sum() == 0
    assert taxonomy.loc[taxonomy["ticker"].eq("BITF"), "phase1k_resolved_subtheme"].iloc[0] == "bitcoin mining"
    assert taxonomy.loc[taxonomy["ticker"].eq("SOUN"), "phase1k_resolved_theme"].iloc[0] == "AI / software"


def test_recent_listing_can_be_dynamic_allow_after_date():
    secondary = pd.DataFrame({"ticker": ["GEV"], "validation_status": ["GLOBAL_SOURCE_UNAVAILABLE"]})
    lifecycle = p1k.build_symbol_lifecycle_alias_map(["GEV"], _symbol_master())
    remediation = p1k.build_quarantine_remediation_audit(_prices(), _phase1j_quarantine(), _symbol_master(), secondary, lifecycle, _taxonomy(), "2024-01-01", "2024-07-01")
    row = remediation.loc[remediation["ticker"].eq("GEV")].iloc[0]

    assert row["remediation_class"] == "DYNAMIC_ALLOW_AFTER_DATE"
    assert row["phase1k_recommended_research_action"] == "ALLOW_DYNAMIC_DATE_GATED"


def test_permanent_drops_and_unresolved_aliases_do_not_appear_in_clean_watchlist():
    remediation = pd.DataFrame(
        [
            {"ticker": "AAPL", "phase1k_recommended_research_action": "ALLOW_WITH_WARNING", "remediation_class": "KEEP_WITH_WARNING", "dynamic_earliest_safe_replay_date": ""},
            {"ticker": "BITF", "phase1k_recommended_research_action": "MANUAL_REVIEW", "remediation_class": "MANUAL_REVIEW_REQUIRED", "dynamic_earliest_safe_replay_date": ""},
        ]
    )
    clean = p1k.build_clean_watchlist_v2_candidate(_phase1j_quarantine(), remediation, _taxonomy())

    assert "AAPL" in clean
    assert "BITF" not in clean


def test_phase1k_readiness_statuses_follow_gates():
    symbols = ["AAPL", "SPY", "QQQ"]
    smoke = pd.DataFrame({"smoke_status": ["GLOBAL_SOURCE_UNAVAILABLE"] * 4})
    secondary = pd.DataFrame({"ticker": symbols, "validation_status": ["GLOBAL_SOURCE_UNAVAILABLE"] * 3})
    lifecycle = p1k.build_symbol_lifecycle_alias_map(symbols, _symbol_master())
    remediation = pd.DataFrame({"ticker": ["AAPL"], "phase1k_recommended_research_action": ["ALLOW_WITH_WARNING"], "remediation_class": ["KEEP_WITH_WARNING"]})
    taxonomy = _taxonomy().loc[lambda frame: frame["ticker"].isin(symbols)]
    clean = "AAPL\n"

    scorecard = p1k.build_phase1k_data_readiness_scorecard(symbols, _phase1j_quarantine(), smoke, secondary, lifecycle, remediation, taxonomy, clean)

    assert scorecard.iloc[0]["data_readiness_status"] == p1k.PHASE_1K_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING


def test_phase1k_cli_writer_writes_all_required_outputs(tmp_path: Path):
    paths = {
        "smoke": tmp_path / "phase1k_secondary_vendor_smoke_test.csv",
        "secondary": tmp_path / "phase1k_secondary_ohlcv_validation.csv",
        "lifecycle": tmp_path / "phase1k_symbol_lifecycle_alias_map.csv",
        "remediation": tmp_path / "phase1k_quarantine_remediation_audit.csv",
        "overrides": tmp_path / "phase1k_taxonomy_static_overrides.csv",
        "taxonomy": tmp_path / "phase1k_taxonomy_resolution_v2.csv",
        "clean_watchlist": tmp_path / "phase1k_clean_watchlist_v2_candidate.txt",
        "scorecard": tmp_path / "phase1k_data_readiness_scorecard.csv",
        "summary": tmp_path / "phase1k_data_readiness_summary.md",
    }
    frame = pd.DataFrame({"ticker": ["AAPL"]})

    p1k.write_phase1k_reports(frame, frame, frame, frame, frame, frame, "AAPL\n", frame, "PHOENIX NANO PHASE 1K — DATA REMEDIATION, TICKER LIFECYCLE, AND SECONDARY VENDOR SMOKE TESTS\n", paths)

    assert all(path.exists() for path in paths.values())
    assert paths["summary"].read_text(encoding="utf-8").startswith("PHOENIX NANO PHASE 1K")
