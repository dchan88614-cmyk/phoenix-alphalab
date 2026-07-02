from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.research.phase1j_data_readiness import (
    PHASE_1J_DATA_BLOCKED,
    build_clean_watchlist_candidate,
    build_data_readiness_scorecard,
    build_listing_validation_matrix,
    build_quarantine_list,
    build_symbol_master,
    build_taxonomy_resolution,
    compare_ohlcv,
    write_phase1j_reports,
)


def _prices() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=140)
    rows = []
    for ticker in ["AAPL", "BITF", "GEV", "SPY", "QQQ"]:
        start_index = 100 if ticker == "GEV" else 0
        for index, date in enumerate(dates[start_index:]):
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": 10 + index,
                    "high": 11 + index,
                    "low": 9 + index,
                    "close": 10 + index,
                    "adj_close": 10 + index,
                    "volume": 1_000_000,
                }
            )
    return pd.DataFrame(rows)


def _universe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "AAPL", "quote_type": "EQUITY", "exchange": "NMS", "short_name": "Apple Inc.", "long_name": "Apple Inc.", "pass_universe": True, "reason": "pass"},
            {"ticker": "BITF", "quote_type": None, "exchange": None, "short_name": None, "long_name": None, "pass_universe": False, "reason": "metadata_incomplete"},
            {"ticker": "GEV", "quote_type": "EQUITY", "exchange": "NYQ", "short_name": "GE Vernova", "long_name": "GE Vernova", "pass_universe": True, "reason": "pass"},
        ]
    )


def _listing_sources() -> dict:
    return {
        "nasdaq_trader_nasdaq": pd.DataFrame({"Symbol": ["AAPL"], "Security Name": ["Apple Inc."], "Test Issue": ["N"], "ETF": ["N"]}),
        "nasdaq_trader_other": pd.DataFrame({"ACT Symbol": ["BITF", "GEV"], "Security Name": ["Bitfarms Ltd.", "GE Vernova Inc."], "Exchange": ["N", "N"], "Test Issue": ["N", "N"], "ETF": ["N", "N"]}),
    }


def test_symbol_master_includes_watchlist_plus_spy_qqq():
    master = build_symbol_master(_prices(), ["AAPL", "SPY", "QQQ"], {"AAPL": 1}, _universe(), pd.DataFrame(), _listing_sources(), "2024-01-01", "2024-07-01", "SPY")

    assert set(master["ticker"]) == {"AAPL", "SPY", "QQQ"}


def test_listing_validation_distinguishes_source_unavailable_from_fail():
    master = pd.DataFrame(
        [
            {
                "ticker": "XXX",
                "symbol_master_status": "SOURCE_UNAVAILABLE",
                "validation_sources_used": "",
                "security_name": "",
                "listing_exchange": "",
                "asset_type": "",
            }
        ]
    )
    listing = build_listing_validation_matrix(master, pd.DataFrame(), pd.DataFrame(), {})

    assert listing.iloc[0]["validation_status"] == "SOURCE_UNAVAILABLE"


def test_metadata_rejection_alone_does_not_force_quarantine_when_listing_validates():
    master = build_symbol_master(
        _prices(),
        ["BITF"],
        {"BITF": 1},
        _universe(),
        pd.DataFrame({"ticker": ["BITF"], "reason": ["metadata_incomplete"]}),
        _listing_sources(),
        "2024-01-01",
        "2024-07-01",
        "SPY",
    )
    listing = build_listing_validation_matrix(master, _universe(), pd.DataFrame({"ticker": ["BITF"], "reason": ["metadata_incomplete"]}), _listing_sources())
    secondary = pd.DataFrame({"ticker": ["BITF"], "validation_status": ["NO_SECOND_SOURCE"]})
    quarantine = build_quarantine_list(master, listing, secondary)

    assert quarantine.iloc[0]["quarantine_status"] != "QUARANTINE"


def test_bitf_style_no_ohlcv_is_quarantined():
    master = build_symbol_master(
        _prices().loc[lambda frame: ~frame["ticker"].eq("BITF")],
        ["BITF"],
        {"BITF": 1},
        _universe(),
        pd.DataFrame({"ticker": ["BITF"], "reason": ["metadata_incomplete"]}),
        {"nasdaq_trader_nasdaq": None, "nasdaq_trader_other": None},
        "2024-01-01",
        "2024-07-01",
        "SPY",
    )
    listing = build_listing_validation_matrix(master, _universe(), pd.DataFrame({"ticker": ["BITF"], "reason": ["metadata_incomplete"]}), {})
    secondary = pd.DataFrame({"ticker": ["BITF"], "validation_status": ["NO_SECOND_SOURCE"]})
    quarantine = build_quarantine_list(master, listing, secondary)

    assert quarantine.iloc[0]["quarantine_status"] == "QUARANTINE"


def test_recent_listing_can_use_earliest_safe_replay_date():
    master = build_symbol_master(_prices(), ["GEV"], {"GEV": 1}, _universe(), pd.DataFrame(), _listing_sources(), "2024-01-01", "2024-07-01", "SPY")
    listing = build_listing_validation_matrix(master, _universe(), pd.DataFrame(), _listing_sources())
    secondary = pd.DataFrame({"ticker": ["GEV"], "validation_status": ["NO_SECOND_SOURCE"]})
    quarantine = build_quarantine_list(master, listing, secondary)

    assert quarantine.iloc[0]["suggested_action"] == "ALLOW_AFTER_DATE"
    assert quarantine.iloc[0]["earliest_safe_replay_date"]


def test_secondary_validation_never_matches_without_overlap():
    primary = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"]), "close": [10], "volume": [100]})
    secondary = pd.DataFrame({"date": pd.to_datetime(["2024-01-03"]), "close": [10], "volume": [100]})

    row = compare_ohlcv("AAPL", primary, secondary, "AVAILABLE")

    assert row["validation_status"] != "MATCH"
    assert row["overlap_trading_days"] == 0


def test_taxonomy_resolution_flags_every_low_confidence_row():
    master = pd.DataFrame({"ticker": ["AAPL", "UNKNOWNX"], "security_name": ["Apple Inc.", "Mystery Corp"]})
    taxonomy = build_taxonomy_resolution(master)

    assert set(taxonomy["confidence"]) <= {"HIGH", "MEDIUM", "LOW"}
    assert taxonomy.loc[taxonomy["ticker"].eq("UNKNOWNX"), "notes"].iloc[0]


def test_quarantined_symbols_do_not_appear_in_clean_watchlist():
    quarantine = pd.DataFrame(
        {
            "ticker": ["AAPL", "BITF", "SPY"],
            "quarantine_status": ["ALLOW_RESEARCH", "QUARANTINE", "ALLOW_RESEARCH"],
        }
    )

    text = build_clean_watchlist_candidate(quarantine)

    assert "AAPL" in text
    assert "BITF" not in text
    assert "SPY" not in text


def test_readiness_gate_status_rules_block_when_quarantine_high():
    master = pd.DataFrame(
        {
            "ticker": ["AAPL", "BITF", "SPY", "QQQ"],
            "symbol_master_status": ["ACTIVE_LISTED_EQUITY", "UNKNOWN", "ETF_OR_INDEX_PROXY", "ETF_OR_INDEX_PROXY"],
            "has_sufficient_factor_lookback": [True, False, True, True],
        }
    )
    listing = pd.DataFrame({"ticker": ["AAPL"], "validation_status": ["MATCH"]})
    secondary = pd.DataFrame({"ticker": ["AAPL", "BITF", "SPY", "QQQ"], "validation_status": ["NO_SECOND_SOURCE", "NO_SECOND_SOURCE", "NO_SECOND_SOURCE", "NO_SECOND_SOURCE"]})
    quarantine = pd.DataFrame({"ticker": ["AAPL", "BITF", "SPY", "QQQ"], "quarantine_status": ["ALLOW_RESEARCH", "QUARANTINE", "ALLOW_RESEARCH", "ALLOW_RESEARCH"], "suggested_action": ["KEEP_WITH_WARNING", "DROP_FROM_RESEARCH", "KEEP_WITH_WARNING", "KEEP_WITH_WARNING"]})
    taxonomy = pd.DataFrame({"ticker": ["AAPL", "BITF", "SPY", "QQQ"], "confidence": ["HIGH", "LOW", "HIGH", "HIGH"]})
    scorecard = build_data_readiness_scorecard(master, listing, secondary, quarantine, taxonomy)

    assert scorecard.iloc[0]["data_readiness_status"] == PHASE_1J_DATA_BLOCKED


def test_phase1j_reports_are_written(tmp_path: Path):
    paths = {
        "symbol_master": tmp_path / "symbol_master.csv",
        "listing": tmp_path / "listing.csv",
        "secondary": tmp_path / "secondary.csv",
        "scorecard": tmp_path / "scorecard.csv",
        "quarantine": tmp_path / "quarantine.csv",
        "taxonomy": tmp_path / "taxonomy.csv",
        "clean_watchlist": tmp_path / "clean.txt",
        "summary": tmp_path / "summary.md",
    }
    frame = pd.DataFrame({"ticker": ["AAPL"]})

    write_phase1j_reports(frame, frame, frame, frame, frame, frame, "# header\nAAPL\n", "PHOENIX NANO PHASE 1J — SYMBOL MASTER, SECONDARY VENDOR VALIDATION, AND DATA READINESS GATE\n", paths)

    assert paths["symbol_master"].exists()
    assert paths["clean_watchlist"].exists()
    assert paths["summary"].read_text(encoding="utf-8").startswith("PHOENIX NANO PHASE 1J")
