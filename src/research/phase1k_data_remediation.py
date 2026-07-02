from __future__ import annotations

import io
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from src.research.phase1j_data_readiness import pct, watchlist_symbols_with_lines


PHASE_1K_DATA_BLOCKED = "PHASE_1K_DATA_BLOCKED"
PHASE_1K_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING = "PHASE_1K_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING"
PHASE_1K_RESEARCH_DATA_READY_FOR_FROZEN_RETEST = "PHASE_1K_RESEARCH_DATA_READY_FOR_FROZEN_RETEST"

SMOKE_TICKERS = ["AAPL", "MSFT", "SPY", "QQQ"]
PROXY_TICKERS = {"SPY", "QQQ"}

TAXONOMY_OVERRIDES = {
    "ASTS": ("space / communications", "satellite broadband", "HIGH", "phase1k_static_override", "AST SpaceMobile satellite broadband business."),
    "BITF": ("crypto-adjacent / high beta", "bitcoin mining", "HIGH", "phase1k_static_override", "Bitfarms bitcoin mining."),
    "CELH": ("consumer growth", "beverages", "HIGH", "phase1k_static_override", "Celsius energy drink / beverages."),
    "CLSK": ("crypto-adjacent / high beta", "bitcoin mining", "HIGH", "phase1k_static_override", "CleanSpark bitcoin mining."),
    "CRSP": ("biotech", "gene editing", "HIGH", "phase1k_static_override", "CRISPR Therapeutics gene editing."),
    "IOVA": ("biotech", "oncology cell therapy", "HIGH", "phase1k_static_override", "Iovance oncology cell therapy."),
    "MARA": ("crypto-adjacent / high beta", "bitcoin mining", "HIGH", "phase1k_static_override", "MARA bitcoin mining."),
    "MDB": ("software", "database platform", "HIGH", "phase1k_static_override", "MongoDB database platform."),
    "MIRM": ("biotech", "rare disease therapeutics", "HIGH", "phase1k_static_override", "Mirum rare disease therapeutics."),
    "NNE": ("space / defense / nuclear", "advanced nuclear", "HIGH", "phase1k_static_override", "Nano Nuclear advanced nuclear."),
    "NTLA": ("biotech", "gene editing", "HIGH", "phase1k_static_override", "Intellia gene editing."),
    "QQQ": ("ETF / index proxy", "Nasdaq-100 / growth equity proxy", "HIGH", "phase1k_static_override", "Regime/index proxy only, not a trade candidate."),
    "RIOT": ("crypto-adjacent / high beta", "bitcoin mining", "HIGH", "phase1k_static_override", "Riot bitcoin mining."),
    "SOUN": ("AI / software", "voice AI", "HIGH", "phase1k_static_override", "SoundHound voice AI."),
    "SPY": ("ETF / index proxy", "broad U.S. equity proxy", "HIGH", "phase1k_static_override", "Regime/index proxy only, not a trade candidate."),
    "SQ": ("fintech", "payments / Cash App / merchant services", "HIGH", "phase1k_static_override", "Block historical ticker before XYZ ticker change."),
    "SYM": ("robotics / automation", "warehouse automation", "HIGH", "phase1k_static_override", "Symbotic warehouse automation."),
    "TGTX": ("biotech", "therapeutics", "HIGH", "phase1k_static_override", "TG Therapeutics."),
    "TTD": ("software / adtech", "demand-side platform", "HIGH", "phase1k_static_override", "The Trade Desk adtech demand-side platform."),
    "U": ("software", "game engine / real-time 3D platform", "HIGH", "phase1k_static_override", "Unity real-time 3D platform."),
    "VKTX": ("biotech", "metabolic disease therapeutics", "HIGH", "phase1k_static_override", "Viking metabolic disease therapeutics."),
    "XYZ": ("fintech", "payments / Cash App / merchant services", "HIGH", "phase1k_static_override", "Block current ticker after SQ changed to XYZ."),
}


def build_phase1k_data_remediation_gate(
    data: pd.DataFrame,
    watchlist_path: str | Path | None,
    watchlist_tickers: list[str],
    requested_start_date: str,
    requested_end_date: str,
    reports_dir: str | Path = "data/reports",
    cache_dir: str | Path = "data/cache",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, pd.DataFrame, str, dict]:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    reports = Path(reports_dir)
    cache = Path(cache_dir)
    phase1j_symbol_master = read_report(reports / "phase1j_symbol_master.csv")
    phase1j_quarantine = read_report(reports / "phase1j_quarantine_list.csv")
    phase1j_taxonomy = read_report(reports / "phase1j_taxonomy_resolution.csv")
    symbols_with_lines = watchlist_symbols_with_lines(watchlist_path, watchlist_tickers)
    symbols = sorted(set([item["ticker"] for item in symbols_with_lines] + list(PROXY_TICKERS)))
    smoke = build_secondary_vendor_smoke_test(requested_start_date, requested_end_date, cache / "secondary_ohlcv" / "stooq")
    source_global_status = secondary_source_global_status(smoke)
    secondary = build_secondary_ohlcv_validation_v2(frame, symbols, requested_start_date, requested_end_date, cache / "secondary_ohlcv" / "stooq", source_global_status)
    lifecycle = build_symbol_lifecycle_alias_map(symbols, phase1j_symbol_master)
    overrides = build_taxonomy_static_overrides()
    taxonomy = build_taxonomy_resolution_v2(phase1j_taxonomy, symbols, overrides)
    remediation = build_quarantine_remediation_audit(frame, phase1j_quarantine, phase1j_symbol_master, secondary, lifecycle, taxonomy, requested_start_date, requested_end_date)
    clean_watchlist = build_clean_watchlist_v2_candidate(phase1j_quarantine, remediation, taxonomy)
    scorecard = build_phase1k_data_readiness_scorecard(symbols, phase1j_quarantine, smoke, secondary, lifecycle, remediation, taxonomy, clean_watchlist)
    summary = {
        "phase_1k_status": str(scorecard.iloc[0]["data_readiness_status"]) if not scorecard.empty else PHASE_1K_DATA_BLOCKED,
        "smoke_counts": smoke["smoke_status"].value_counts().to_dict(),
        "secondary_counts": secondary["validation_status"].value_counts().to_dict(),
        "alias_counts": lifecycle["alias_status"].value_counts().to_dict(),
        "remediation_counts": remediation["remediation_class"].value_counts().to_dict(),
        "research_action_counts": remediation["phase1k_recommended_research_action"].value_counts().to_dict(),
        "taxonomy_counts": taxonomy["confidence"].value_counts().to_dict(),
        "clean_watchlist_count": count_clean_watchlist(clean_watchlist),
        "source_global_status": source_global_status,
    }
    summary_md = phase1k_summary_markdown(summary, scorecard, smoke, secondary, lifecycle, remediation, taxonomy)
    return smoke, secondary, lifecycle, remediation, overrides, taxonomy, clean_watchlist, scorecard, summary_md, summary


def read_report(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def stooq_url(ticker: str, start: str, end: str) -> str:
    return f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d&d1={start.replace('-', '')}&d2={end.replace('-', '')}"


def build_secondary_vendor_smoke_test(start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for ticker in SMOKE_TICKERS:
        rows.append(fetch_stooq_for_report(ticker, start, end, cache_dir, smoke=True)[1])
    frame = pd.DataFrame(rows)
    if not frame["smoke_status"].isin(["PASS", "CACHE_ONLY_PASS"]).any():
        frame["smoke_status"] = "GLOBAL_SOURCE_UNAVAILABLE"
        frame["smoke_reason"] = "No smoke-test ticker could be fetched or loaded from cache; treat source as globally unavailable for this run."
    return frame


def fetch_stooq_for_report(ticker: str, start: str, end: str, cache_dir: Path, smoke: bool = False) -> tuple[pd.DataFrame, dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    lookup_symbol = f"{ticker.lower()}.us"
    url = stooq_url(ticker, start, end)
    cache_path = cache_dir / f"{ticker}.csv"
    attempted = True
    used_cache = False
    http_status = ""
    exception_class = ""
    response_bytes = 0
    text = ""
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "PhoenixAlphaLab/1.0 research data validation"})
            with urllib.request.urlopen(request, timeout=8) as response:
                http_status = str(getattr(response, "status", ""))
                raw = response.read()
            response_bytes = len(raw)
            text = raw.decode("utf-8", errors="replace")
            break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            exception_class = exc.__class__.__name__
            if attempt == 0:
                time.sleep(0.4)
            continue
    if not text and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8")
        used_cache = True
        attempted = True
        response_bytes = len(text.encode("utf-8"))
    frame, parse_status, parse_reason = parse_stooq_csv(text)
    if parse_status == "PASS" and not used_cache:
        cache_path.write_text(text, encoding="utf-8")
    first_date = frame["date"].min().strftime("%Y-%m-%d") if not frame.empty else ""
    last_date = frame["date"].max().strftime("%Y-%m-%d") if not frame.empty else ""
    if not text and not used_cache:
        status = "GLOBAL_SOURCE_UNAVAILABLE" if smoke else "GLOBAL_SOURCE_UNAVAILABLE"
        reason = f"Network/source unavailable and no cache exists: {exception_class or 'unknown'}"
    elif parse_status == "PASS":
        status = "CACHE_ONLY_PASS" if used_cache and smoke else ("PASS" if smoke else ("CACHE_ONLY_AVAILABLE" if used_cache else "AVAILABLE"))
        reason = "Parsed Stooq OHLCV from cache." if used_cache else "Parsed Stooq OHLCV from network response."
    elif "No data" in text:
        status = "NO_DATA_FOR_SYMBOL"
        reason = "Source returned an explicit no-data response for this symbol."
    else:
        status = "PARSE_ERROR" if smoke else "NO_DATA_FOR_SYMBOL"
        reason = parse_reason
    report = {
        "source_name": "stooq",
        "ticker": ticker,
        "lookup_symbol": lookup_symbol,
        "url_or_cache_key": url if not used_cache else str(cache_path),
        "attempted_network_fetch": attempted,
        "used_cache_fallback": used_cache,
        "http_status_if_available": http_status,
        "exception_class_if_any": exception_class,
        "response_bytes": response_bytes,
        "parsed_rows": int(len(frame)),
        "first_date": first_date,
        "last_date": last_date,
        "required_start_date": start,
        "required_end_date": end,
        "smoke_status": status if smoke else "",
        "smoke_reason": reason,
        "_fetch_status": status,
    }
    return frame, report


def parse_stooq_csv(text: str) -> tuple[pd.DataFrame, str, str]:
    if not text.strip():
        return pd.DataFrame(), "EMPTY", "Empty response."
    try:
        frame = pd.read_csv(io.StringIO(text))
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        return pd.DataFrame(), "PARSE_ERROR", exc.__class__.__name__
    if frame.empty or "Date" not in frame.columns:
        return pd.DataFrame(), "PARSE_ERROR", "Response did not contain Stooq OHLCV columns."
    frame = frame.rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    frame["date"] = pd.to_datetime(frame["date"])
    return frame, "PASS", ""


def secondary_source_global_status(smoke: pd.DataFrame) -> str:
    if smoke.empty:
        return "GLOBAL_SOURCE_UNAVAILABLE"
    if smoke["smoke_status"].isin(["PASS", "CACHE_ONLY_PASS"]).any():
        return "AVAILABLE_OR_CACHED"
    return "GLOBAL_SOURCE_UNAVAILABLE"


def build_secondary_ohlcv_validation_v2(data: pd.DataFrame, symbols: list[str], start: str, end: str, cache_dir: Path, source_global_status: str) -> pd.DataFrame:
    rows = []
    for ticker in symbols:
        primary = data.loc[data["ticker"].eq(ticker)].copy()
        if source_global_status == "GLOBAL_SOURCE_UNAVAILABLE":
            rows.append(empty_secondary_row(ticker, primary, "GLOBAL_SOURCE_UNAVAILABLE", "Stooq smoke test failed globally; per-symbol validation skipped."))
            continue
        secondary, report = fetch_stooq_for_report(ticker, start, end, cache_dir, smoke=False)
        rows.append(compare_ohlcv_v2(ticker, primary, secondary, source_global_status, report))
    return pd.DataFrame(rows)


def empty_secondary_row(ticker: str, primary: pd.DataFrame, status: str, reason: str) -> dict:
    return {
        "ticker": ticker,
        "primary_vendor": "yfinance",
        "secondary_vendor": "stooq",
        "lookup_symbol": f"{ticker.lower()}.us",
        "source_global_status": status,
        "primary_start_date": primary["date"].min().strftime("%Y-%m-%d") if not primary.empty else "",
        "primary_end_date": primary["date"].max().strftime("%Y-%m-%d") if not primary.empty else "",
        "secondary_start_date": "",
        "secondary_end_date": "",
        "overlap_trading_days": 0,
        "close_price_median_abs_diff_pct": pd.NA,
        "close_price_p95_abs_diff_pct": pd.NA,
        "close_price_max_abs_diff_pct": pd.NA,
        "volume_median_abs_diff_pct": pd.NA,
        "volume_p95_abs_diff_pct": pd.NA,
        "volume_max_abs_diff_pct": pd.NA,
        "adjusted_close_available_primary": "adj_close" in primary.columns and primary["adj_close"].notna().any() if not primary.empty else False,
        "adjusted_close_available_secondary": False,
        "adjusted_price_mismatch_flag": pd.NA,
        "split_or_corporate_action_mismatch_flag": pd.NA,
        "validation_status": status,
        "validation_reason": reason,
    }


def compare_ohlcv_v2(ticker: str, primary: pd.DataFrame, secondary: pd.DataFrame, source_global_status: str, fetch_report: dict) -> dict:
    if fetch_report["_fetch_status"] in {"NO_DATA_FOR_SYMBOL", "PARSE_ERROR"}:
        return empty_secondary_row(ticker, primary, "NO_DATA_FOR_SYMBOL", fetch_report["smoke_reason"])
    if fetch_report["_fetch_status"] == "GLOBAL_SOURCE_UNAVAILABLE":
        return empty_secondary_row(ticker, primary, "GLOBAL_SOURCE_UNAVAILABLE", fetch_report["smoke_reason"])
    base = empty_secondary_row(ticker, primary, source_global_status, "")
    base["secondary_start_date"] = secondary["date"].min().strftime("%Y-%m-%d") if not secondary.empty else ""
    base["secondary_end_date"] = secondary["date"].max().strftime("%Y-%m-%d") if not secondary.empty else ""
    base["adjusted_close_available_secondary"] = "adj_close" in secondary.columns and secondary["adj_close"].notna().any() if not secondary.empty else False
    if primary.empty or secondary.empty:
        base["validation_status"] = "NO_DATA_FOR_SYMBOL"
        base["validation_reason"] = "Primary or secondary OHLCV missing."
        return base
    merged = primary[["date", "close", "volume"]].merge(secondary[["date", "close", "volume"]], on="date", suffixes=("_primary", "_secondary"))
    if merged.empty:
        base["validation_status"] = "NO_DATA_FOR_SYMBOL"
        base["validation_reason"] = "No overlapping trading days; never marking MATCH without overlap."
        return base
    close_diff = (pd.to_numeric(merged["close_primary"], errors="coerce") / pd.to_numeric(merged["close_secondary"], errors="coerce") - 1).abs().dropna()
    volume_diff = (pd.to_numeric(merged["volume_primary"], errors="coerce") / pd.to_numeric(merged["volume_secondary"], errors="coerce").replace(0, pd.NA) - 1).abs().dropna()
    if close_diff.empty:
        base["validation_status"] = "FAIL"
        base["validation_reason"] = "Overlap exists but close differences could not be computed."
        return base
    max_close = float(close_diff.max())
    fresh_status = "MATCH" if max_close <= 0.03 else "WARN"
    if bool(fetch_report["used_cache_fallback"]):
        fresh_status = "CACHE_ONLY_MATCH" if fresh_status == "MATCH" else "CACHE_ONLY_WARN"
    base.update(
        {
            "overlap_trading_days": int(len(merged)),
            "close_price_median_abs_diff_pct": pct(close_diff.median()),
            "close_price_p95_abs_diff_pct": pct(close_diff.quantile(0.95)),
            "close_price_max_abs_diff_pct": pct(max_close),
            "volume_median_abs_diff_pct": pct(volume_diff.median()) if not volume_diff.empty else pd.NA,
            "volume_p95_abs_diff_pct": pct(volume_diff.quantile(0.95)) if not volume_diff.empty else pd.NA,
            "volume_max_abs_diff_pct": pct(volume_diff.max()) if not volume_diff.empty else pd.NA,
            "adjusted_price_mismatch_flag": False,
            "split_or_corporate_action_mismatch_flag": bool(max_close > 0.10),
            "validation_status": fresh_status,
            "validation_reason": "Secondary OHLCV compared with positive overlap; cache use is explicit." if "CACHE_ONLY" in fresh_status else "Secondary OHLCV compared with positive overlap.",
        }
    )
    return base


def build_symbol_lifecycle_alias_map(symbols: list[str], symbol_master: pd.DataFrame) -> pd.DataFrame:
    master = symbol_master.set_index("ticker").to_dict("index") if not symbol_master.empty else {}
    rows = []
    for ticker in symbols:
        status = str(master.get(ticker, {}).get("symbol_master_status", "UNKNOWN"))
        if ticker == "SQ":
            rows.append(
                {
                    "original_watchlist_ticker": "SQ",
                    "canonical_current_ticker": "XYZ",
                    "historical_ticker": "SQ",
                    "effective_start_date": "2015-11-19",
                    "effective_end_date": "2025-01-20",
                    "alias_status": "RENAMED",
                    "replay_handling": "USE_HISTORICAL_THEN_CURRENT_ALIAS",
                    "evidence_source": "Block ticker-change announcement",
                    "evidence_notes": "Block Class A common stock began NYSE trading under XYZ on 2025-01-21; SQ must not leak XYZ eligibility before the effective date.",
                }
            )
        elif ticker in PROXY_TICKERS:
            rows.append(
                {
                    "original_watchlist_ticker": ticker,
                    "canonical_current_ticker": ticker,
                    "historical_ticker": ticker,
                    "effective_start_date": "",
                    "effective_end_date": "",
                    "alias_status": "ETF_OR_INDEX_PROXY",
                    "replay_handling": "USE_AS_IS",
                    "evidence_source": "phase1j_symbol_master",
                    "evidence_notes": "Regime/index proxy only; excluded from trade candidates.",
                }
            )
        elif status == "UNKNOWN":
            rows.append(alias_row(ticker, ticker, ticker, "UNKNOWN", "MANUAL_REVIEW", "phase1j_symbol_master", "Phase 1J could not resolve active listing/status."))
        elif status in {"DELISTED_OR_INACTIVE", "SOURCE_UNAVAILABLE"}:
            rows.append(alias_row(ticker, ticker, ticker, "DELISTED_OR_INACTIVE", "DROP_FROM_RESEARCH", "phase1j_symbol_master", f"Phase 1J status {status}."))
        else:
            rows.append(alias_row(ticker, ticker, ticker, "UNCHANGED", "USE_AS_IS", "phase1j_symbol_master", f"Phase 1J status {status}."))
    return pd.DataFrame(rows)


def alias_row(ticker: str, canonical: str, historical: str, status: str, handling: str, source: str, notes: str) -> dict:
    return {
        "original_watchlist_ticker": ticker,
        "canonical_current_ticker": canonical,
        "historical_ticker": historical,
        "effective_start_date": "",
        "effective_end_date": "",
        "alias_status": status,
        "replay_handling": handling,
        "evidence_source": source,
        "evidence_notes": notes,
    }


def build_taxonomy_static_overrides() -> pd.DataFrame:
    rows = []
    for ticker, (theme, subtheme, confidence, evidence, notes) in sorted(TAXONOMY_OVERRIDES.items()):
        rows.append({"ticker": ticker, "resolved_theme": theme, "resolved_subtheme": subtheme, "confidence": confidence, "evidence_source": evidence, "notes": notes})
    return pd.DataFrame(rows)


def build_taxonomy_resolution_v2(phase1j_taxonomy: pd.DataFrame, symbols: list[str], overrides: pd.DataFrame) -> pd.DataFrame:
    prior = phase1j_taxonomy.set_index("ticker").to_dict("index") if not phase1j_taxonomy.empty else {}
    override_map = overrides.set_index("ticker").to_dict("index") if not overrides.empty else {}
    rows = []
    for ticker in sorted(set(symbols) | set(override_map)):
        p = prior.get(ticker, {})
        if ticker in override_map:
            o = override_map[ticker]
            theme = o["resolved_theme"]
            subtheme = o["resolved_subtheme"]
            confidence = o["confidence"]
            evidence = o["evidence_source"]
            notes = o["notes"]
        else:
            theme = p.get("resolved_theme", "UNMAPPED_LOW_CONFIDENCE")
            subtheme = p.get("resolved_subtheme", "manual_review_required")
            confidence = p.get("confidence", "LOW")
            evidence = p.get("evidence_source", "phase1j_taxonomy")
            notes = p.get("notes", "")
        rows.append(
            {
                "ticker": ticker,
                "prior_theme": p.get("prior_theme", "UNMAPPED_LOW_CONFIDENCE"),
                "phase1j_resolved_theme": p.get("resolved_theme", ""),
                "phase1k_resolved_theme": theme,
                "phase1k_resolved_subtheme": subtheme,
                "confidence": confidence,
                "evidence_source": evidence,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def build_quarantine_remediation_audit(
    data: pd.DataFrame,
    phase1j_quarantine: pd.DataFrame,
    symbol_master: pd.DataFrame,
    secondary: pd.DataFrame,
    lifecycle: pd.DataFrame,
    taxonomy: pd.DataFrame,
    requested_start_date: str,
    requested_end_date: str,
) -> pd.DataFrame:
    rows = []
    q = phase1j_quarantine.loc[phase1j_quarantine["quarantine_status"].isin(["QUARANTINE", "RESEARCH_WARN"])].copy()
    master = symbol_master.set_index("ticker").to_dict("index") if not symbol_master.empty else {}
    sec = secondary.set_index("ticker").to_dict("index") if not secondary.empty else {}
    alias = lifecycle.set_index("original_watchlist_ticker").to_dict("index") if not lifecycle.empty else {}
    tax = taxonomy.set_index("ticker").to_dict("index") if not taxonomy.empty else {}
    requested_start = pd.Timestamp(requested_start_date)
    requested_end = pd.Timestamp(requested_end_date)
    for _, row in q.iterrows():
        ticker = row["ticker"]
        prices = data.loc[data["ticker"].eq(ticker)].sort_values("date")
        first_date = pd.Timestamp(prices["date"].min()) if not prices.empty else pd.NaT
        last_date = pd.Timestamp(prices["date"].max()) if not prices.empty else pd.NaT
        lookback_days = int((requested_start - first_date).days) if pd.notna(first_date) and first_date <= requested_start else 0
        forward_days = int((last_date - requested_end).days) if pd.notna(last_date) and last_date >= requested_end else 0
        phase1j_safe_date = clean_text(row.get("earliest_safe_replay_date", ""))
        dynamic_date = first_date.strftime("%Y-%m-%d") if pd.notna(first_date) and first_date > requested_start else phase1j_safe_date
        class_, action, rationale = classify_remediation(ticker, row, master.get(ticker, {}), sec.get(ticker, {}), alias.get(ticker, {}), tax.get(ticker, {}), bool(pd.notna(first_date)), dynamic_date)
        rows.append(
            {
                "ticker": ticker,
                "phase1j_quarantine_status": row["quarantine_status"],
                "phase1j_quarantine_reason": row["quarantine_reason"],
                "phase1j_suggested_action": row["suggested_action"],
                "phase1j_earliest_safe_replay_date": phase1j_safe_date,
                "phase1k_listing_status": master.get(ticker, {}).get("symbol_master_status", "UNKNOWN"),
                "phase1k_ohlcv_status": sec.get(ticker, {}).get("validation_status", "GLOBAL_SOURCE_UNAVAILABLE"),
                "phase1k_alias_status": alias.get(ticker, {}).get("alias_status", "UNKNOWN"),
                "phase1k_taxonomy_confidence": tax.get(ticker, {}).get("confidence", "LOW"),
                "factor_lookback_available_days_at_requested_start": lookback_days,
                "forward_window_available_days_at_requested_end": forward_days,
                "dynamic_earliest_safe_replay_date": dynamic_date,
                "remediation_class": class_,
                "phase1k_recommended_research_action": action,
                "rationale": rationale,
            }
        )
    return pd.DataFrame(rows)


def classify_remediation(ticker: str, phase1j_row: pd.Series, master: dict, secondary: dict, alias: dict, taxonomy: dict, has_prices: bool, dynamic_date: str) -> tuple[str, str, str]:
    if ticker in PROXY_TICKERS:
        return "KEEP_WITH_WARNING", "KEEP_PROXY_ONLY", "Proxy kept for regime/index context, not as a trade candidate."
    if alias.get("alias_status") == "RENAMED":
        return "ALIASED_OR_RENAMED", "ALLOW_DYNAMIC_DATE_GATED", "Ticker rename handled through lifecycle map without leaking future eligibility."
    if str(phase1j_row.get("suggested_action")) == "ALLOW_AFTER_DATE" and has_prices:
        return "DYNAMIC_ALLOW_AFTER_DATE", "ALLOW_DYNAMIC_DATE_GATED", "Recent listing has usable later OHLCV and should be date-gated instead of permanently dropped."
    if ticker == "BITF":
        return "DATA_DOWNLOAD_RETRY_NEEDED", "MANUAL_REVIEW", "BITF has metadata/price download failure and static taxonomy is resolved; data source retry is needed before inclusion."
    if alias.get("alias_status") in {"UNKNOWN", "POSSIBLE_RENAME"}:
        return "MANUAL_REVIEW_REQUIRED", "MANUAL_REVIEW", "Alias or listing status remains unresolved."
    if taxonomy.get("confidence") == "LOW":
        return "MANUAL_REVIEW_REQUIRED", "MANUAL_REVIEW", "Taxonomy remains LOW confidence."
    if not has_prices:
        return "PERMANENT_DROP", "DROP", "No usable OHLCV in the requested research dataset."
    if secondary.get("validation_status") in {"GLOBAL_SOURCE_UNAVAILABLE", "NO_DATA_FOR_SYMBOL"}:
        return "KEEP_WITH_WARNING", "ALLOW_WITH_WARNING", "Primary OHLCV exists but secondary validation remains unavailable; keep only as research warning."
    return "KEEP_WITH_WARNING", "ALLOW_WITH_WARNING", "No permanent data issue remains after Phase 1K remediation."


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def build_clean_watchlist_v2_candidate(phase1j_quarantine: pd.DataFrame, remediation: pd.DataFrame, taxonomy: pd.DataFrame) -> str:
    tax = taxonomy.set_index("ticker").to_dict("index") if not taxonomy.empty else {}
    remediation_map = remediation.set_index("ticker").to_dict("index") if not remediation.empty else {}
    lines = [
        "# Phase 1K research-only clean watchlist v2 candidate.",
        "# Not approved for daily scan, paper execution, or real-money execution.",
        "# Dynamic-date-gated symbols include their earliest safe replay date as an inline comment.",
    ]
    for _, phase1j_row in phase1j_quarantine.sort_values("ticker").iterrows():
        ticker = phase1j_row["ticker"]
        row = remediation_map.get(
            ticker,
            {
                "ticker": ticker,
                "phase1k_recommended_research_action": "ALLOW_WITH_WARNING" if phase1j_row["quarantine_status"] == "ALLOW_RESEARCH" else "MANUAL_REVIEW",
                "remediation_class": "KEEP_WITH_WARNING",
                "dynamic_earliest_safe_replay_date": "",
            },
        )
        ticker = row.get("ticker", ticker)
        if ticker in PROXY_TICKERS:
            continue
        if tax.get(ticker, {}).get("confidence") == "LOW":
            continue
        if row["remediation_class"] in {"PERMANENT_DROP", "MANUAL_REVIEW_REQUIRED"}:
            continue
        if row["phase1k_recommended_research_action"] not in {"ALLOW_WITH_WARNING", "ALLOW_DYNAMIC_DATE_GATED"}:
            continue
        if row["phase1k_recommended_research_action"] == "ALLOW_DYNAMIC_DATE_GATED":
            lines.append(f"{ticker} # earliest_safe_replay_date={row['dynamic_earliest_safe_replay_date']}")
        else:
            lines.append(ticker)
    return "\n".join(lines) + "\n"


def build_phase1k_data_readiness_scorecard(symbols: list[str], phase1j_quarantine: pd.DataFrame, smoke: pd.DataFrame, secondary: pd.DataFrame, lifecycle: pd.DataFrame, remediation: pd.DataFrame, taxonomy: pd.DataFrame, clean_watchlist: str) -> pd.DataFrame:
    trade_symbols = [ticker for ticker in symbols if ticker not in PROXY_TICKERS]
    active_actions = {"ALLOW_WITH_WARNING", "ALLOW_DYNAMIC_DATE_GATED"}
    active = remediation.loc[remediation["phase1k_recommended_research_action"].isin(active_actions)]
    clean_tickers = {line.split("#", 1)[0].strip() for line in clean_watchlist.splitlines() if line.strip() and not line.startswith("#")}
    active_tickers = set(active["ticker"]) | clean_tickers
    tax = taxonomy.set_index("ticker")
    unresolved_alias_count = int(lifecycle.loc[lifecycle["original_watchlist_ticker"].isin(active_tickers), "alias_status"].isin(["UNKNOWN", "POSSIBLE_RENAME"]).sum())
    unresolved_low_taxonomy_count = int(tax.loc[tax.index.intersection(active_tickers | PROXY_TICKERS), "confidence"].eq("LOW").sum()) if not tax.empty else len(active_tickers)
    permanent_drop_count = int(remediation["remediation_class"].isin(["PERMANENT_DROP", "MANUAL_REVIEW_REQUIRED"]).sum())
    good_secondary = int(secondary["validation_status"].isin(["MATCH", "WARN", "CACHE_ONLY_MATCH", "CACHE_ONLY_WARN"]).sum())
    active_secondary = secondary.loc[secondary["ticker"].isin(active_tickers)]
    active_good_secondary = int(active_secondary["validation_status"].isin(["MATCH", "WARN", "CACHE_ONLY_MATCH", "CACHE_ONLY_WARN"]).sum())
    gate_1_6 = (
        permanent_drop_count / max(1, len(trade_symbols)) <= 0.05
        and unresolved_alias_count == 0
        and unresolved_low_taxonomy_count == 0
        and set(PROXY_TICKERS).issubset(set(lifecycle.loc[lifecycle["alias_status"].eq("ETF_OR_INDEX_PROXY"), "original_watchlist_ticker"]))
        and bool(active_tickers)
    )
    gate_7_ratio = active_good_secondary / max(1, len(active_tickers))
    global_unavailable_only = int(smoke["smoke_status"].eq("GLOBAL_SOURCE_UNAVAILABLE").sum()) == len(smoke)
    if gate_1_6 and gate_7_ratio >= 0.80:
        status = PHASE_1K_RESEARCH_DATA_READY_FOR_FROZEN_RETEST
    elif gate_1_6 and global_unavailable_only:
        status = PHASE_1K_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING
    else:
        status = PHASE_1K_DATA_BLOCKED
    return pd.DataFrame(
        [
            {
                "total_symbols": int(len(symbols)),
                "phase1j_quarantined_count": int(phase1j_quarantine["quarantine_status"].eq("QUARANTINE").sum()) if not phase1j_quarantine.empty else 0,
                "phase1k_permanent_drop_count": permanent_drop_count,
                "phase1k_dynamic_allow_after_date_count": int(remediation["remediation_class"].eq("DYNAMIC_ALLOW_AFTER_DATE").sum() + remediation["remediation_class"].eq("ALIASED_OR_RENAMED").sum()),
                "phase1k_allow_with_warning_count": int(remediation["phase1k_recommended_research_action"].eq("ALLOW_WITH_WARNING").sum()),
                "unresolved_alias_count": unresolved_alias_count,
                "unresolved_low_taxonomy_count": unresolved_low_taxonomy_count,
                "active_trade_candidate_count": int(count_clean_watchlist(clean_watchlist)),
                "proxy_count": int(len(PROXY_TICKERS)),
                "secondary_smoke_pass_count": int(smoke["smoke_status"].isin(["PASS", "CACHE_ONLY_PASS"]).sum()),
                "secondary_global_unavailable_count": int(smoke["smoke_status"].eq("GLOBAL_SOURCE_UNAVAILABLE").sum()),
                "secondary_ohlcv_match_count": int(secondary["validation_status"].isin(["MATCH", "CACHE_ONLY_MATCH"]).sum()),
                "secondary_ohlcv_warn_count": int(secondary["validation_status"].isin(["WARN", "CACHE_ONLY_WARN"]).sum()),
                "secondary_ohlcv_fail_count": int(secondary["validation_status"].eq("FAIL").sum()),
                "secondary_no_data_for_symbol_count": int(secondary["validation_status"].eq("NO_DATA_FOR_SYMBOL").sum()),
                "secondary_global_source_unavailable_count": int(secondary["validation_status"].eq("GLOBAL_SOURCE_UNAVAILABLE").sum()),
                "data_readiness_status": status,
            }
        ]
    )


def count_clean_watchlist(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip() and not line.startswith("#")])


def phase1k_summary_markdown(summary: dict, scorecard: pd.DataFrame, smoke: pd.DataFrame, secondary: pd.DataFrame, lifecycle: pd.DataFrame, remediation: pd.DataFrame, taxonomy: pd.DataFrame) -> str:
    sq = lifecycle.loc[lifecycle["original_watchlist_ticker"].eq("SQ")]
    bitf = remediation.loc[remediation["ticker"].eq("BITF")]
    lines = [
        "PHOENIX NANO PHASE 1K — DATA REMEDIATION, TICKER LIFECYCLE, AND SECONDARY VENDOR SMOKE TESTS",
        "",
        "Historical research and data-readiness remediation only. No daily scan, paper execution, or real-money execution is approved.",
        "",
        "## Secondary Vendor Smoke Test Result",
        "",
        str(summary["smoke_counts"]),
        f"- source_global_status: {summary['source_global_status']}",
        "",
        "## Secondary OHLCV Validation Coverage",
        "",
        str(summary["secondary_counts"]),
        "",
        "## Ticker Lifecycle / Alias Findings",
        "",
        str(summary["alias_counts"]),
        "",
        "## SQ / XYZ Handling Decision",
        "",
        sq.to_markdown(index=False) if not sq.empty else "SQ was not present in the lifecycle map.",
        "",
        "## BITF Handling Decision",
        "",
        bitf.to_markdown(index=False) if not bitf.empty else "BITF was not present in the remediation audit.",
        "",
        "## SPY/QQQ Proxy Handling",
        "",
        "- SPY and QQQ are resolved as ETF/index proxies.",
        "- They are retained for regime/index context and excluded from trade candidates.",
        "",
        "## Phase 1J Quarantine Remediation Results",
        "",
        str(summary["remediation_counts"]),
        str(summary["research_action_counts"]),
        "",
        "## Taxonomy V2 Confidence Counts",
        "",
        str(summary["taxonomy_counts"]),
        "",
        "## Clean Watchlist V2 Candidate Count",
        "",
        f"- {summary['clean_watchlist_count']}",
        "",
        "## Phase 1K Data Readiness Status",
        "",
        scorecard.to_markdown(index=False) if not scorecard.empty else "No scorecard row.",
        "",
        f"## Final Phase 1K Status: {summary['phase_1k_status']}",
        "",
        "Strategy research should remain paused unless GPT explicitly accepts this data-readiness status and requests a frozen retest.",
        "",
        "Do not start Phase 2, Phase 3, paper execution, live execution, Candidate 36, or any strategy retest.",
        "",
    ]
    return "\n".join(lines)


def write_phase1k_reports(smoke, secondary, lifecycle, remediation, overrides, taxonomy, clean_watchlist, scorecard, summary_md, paths: dict[str, str | Path]) -> None:
    for path in paths.values():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    smoke.to_csv(paths["smoke"], index=False)
    secondary.to_csv(paths["secondary"], index=False)
    lifecycle.to_csv(paths["lifecycle"], index=False)
    remediation.to_csv(paths["remediation"], index=False)
    overrides.to_csv(paths["overrides"], index=False)
    taxonomy.to_csv(paths["taxonomy"], index=False)
    Path(paths["clean_watchlist"]).write_text(clean_watchlist, encoding="utf-8")
    scorecard.to_csv(paths["scorecard"], index=False)
    Path(paths["summary"]).write_text(summary_md, encoding="utf-8")
