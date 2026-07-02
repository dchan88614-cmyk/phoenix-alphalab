from __future__ import annotations

import io
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from src.research.phase1f_failure_audit import STATIC_TAXONOMY, ticker_theme_subtheme


PHASE_1J_DATA_BLOCKED = "PHASE_1J_DATA_BLOCKED"
PHASE_1J_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING = "PHASE_1J_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING"
PHASE_1J_RESEARCH_DATA_READY_FOR_FROZEN_RETEST = "PHASE_1J_RESEARCH_DATA_READY_FOR_FROZEN_RETEST"

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


def build_phase1j_data_readiness_gate(
    data: pd.DataFrame,
    watchlist_path: str | Path | None,
    watchlist_tickers: list[str],
    universe: pd.DataFrame,
    rejected_metadata: pd.DataFrame,
    requested_start_date: str,
    requested_end_date: str,
    benchmark_ticker: str = "SPY",
    cache_dir: str | Path = "data/cache",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, str, dict]:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    symbols_with_lines = watchlist_symbols_with_lines(watchlist_path, watchlist_tickers)
    symbols = sorted(set([item["ticker"] for item in symbols_with_lines] + [benchmark_ticker, "QQQ"]))
    line_lookup = {item["ticker"]: item["line_number"] for item in symbols_with_lines}
    listing_sources = load_listing_sources(Path(cache_dir) / "symbol_master")
    symbol_master = build_symbol_master(frame, symbols, line_lookup, universe, rejected_metadata, listing_sources, requested_start_date, requested_end_date, benchmark_ticker)
    listing = build_listing_validation_matrix(symbol_master, universe, rejected_metadata, listing_sources)
    secondary = build_secondary_ohlcv_validation(frame, symbols, requested_start_date, requested_end_date, Path(cache_dir) / "secondary_ohlcv")
    quarantine = build_quarantine_list(symbol_master, listing, secondary)
    taxonomy = build_taxonomy_resolution(symbol_master)
    clean_watchlist_text = build_clean_watchlist_candidate(quarantine)
    scorecard = build_data_readiness_scorecard(symbol_master, listing, secondary, quarantine, taxonomy)
    status = str(scorecard.iloc[0]["data_readiness_status"]) if not scorecard.empty else PHASE_1J_DATA_BLOCKED
    summary = {
        "phase_1j_status": status,
        "symbol_master_counts": symbol_master["symbol_master_status"].value_counts().to_dict(),
        "listing_counts": listing["validation_status"].value_counts().to_dict(),
        "secondary_counts": secondary["validation_status"].value_counts().to_dict(),
        "quarantine_counts": quarantine["quarantine_status"].value_counts().to_dict(),
        "taxonomy_counts": taxonomy["confidence"].value_counts().to_dict(),
        "clean_watchlist_count": len([line for line in clean_watchlist_text.splitlines() if line and not line.startswith("#")]),
    }
    summary_md = phase1j_summary_markdown(summary, scorecard, symbol_master, listing, secondary, quarantine, taxonomy)
    return symbol_master, listing, secondary, scorecard, quarantine, taxonomy, clean_watchlist_text, summary_md, summary


def watchlist_symbols_with_lines(watchlist_path: str | Path | None, tickers: list[str]) -> list[dict]:
    if watchlist_path:
        rows = []
        for line_number, line in enumerate(Path(watchlist_path).read_text(encoding="utf-8").splitlines(), start=1):
            value = line.split("#", 1)[0].strip().upper()
            if value:
                rows.append({"ticker": value, "line_number": line_number})
        return rows
    return [{"ticker": ticker, "line_number": index} for index, ticker in enumerate(tickers, start=1)]


def load_listing_sources(cache_dir: Path) -> dict[str, pd.DataFrame | None]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return {
        "nasdaq_trader_nasdaq": fetch_symbol_directory(NASDAQ_LISTED_URL, cache_dir / "nasdaqlisted.txt", "|"),
        "nasdaq_trader_other": fetch_symbol_directory(OTHER_LISTED_URL, cache_dir / "otherlisted.txt", "|"),
    }


def fetch_symbol_directory(url: str, cache_path: Path, sep: str) -> pd.DataFrame | None:
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            text = response.read().decode("utf-8", errors="replace")
        cache_path.write_text(text, encoding="utf-8")
    except (urllib.error.URLError, TimeoutError, OSError):
        if cache_path.exists():
            text = cache_path.read_text(encoding="utf-8")
        else:
            return None
    lines = [line for line in text.splitlines() if line and not line.startswith("File Creation Time")]
    if not lines:
        return None
    return pd.read_csv(io.StringIO("\n".join(lines)), sep=sep)


def build_symbol_master(data: pd.DataFrame, symbols: list[str], line_lookup: dict[str, int], universe: pd.DataFrame, rejected_metadata: pd.DataFrame, listing_sources: dict, requested_start_date: str, requested_end_date: str, benchmark_ticker: str) -> pd.DataFrame:
    meta = universe.set_index("ticker").to_dict("index") if universe is not None and not universe.empty else {}
    rejected = dict(zip(rejected_metadata["ticker"], rejected_metadata["reason"])) if rejected_metadata is not None and not rejected_metadata.empty else {}
    requested_start = pd.Timestamp(requested_start_date)
    requested_end = pd.Timestamp(requested_end_date)
    rows = []
    for ticker in symbols:
        group = data.loc[data["ticker"].eq(ticker)].sort_values("date").copy()
        listing = listing_lookup(ticker, listing_sources)
        metadata = meta.get(ticker, {})
        status = symbol_master_status(ticker, listing, metadata, group, benchmark_ticker)
        first_date = pd.Timestamp(group["date"].min()) if not group.empty else pd.NaT
        last_date = pd.Timestamp(group["date"].max()) if not group.empty else pd.NaT
        recent_listing = bool(pd.notna(first_date) and first_date > requested_start + pd.Timedelta(days=90))
        rows.append(
            {
                "ticker": ticker,
                "normalized_ticker": ticker.replace(".", "-").upper(),
                "source_watchlist": bool(ticker in line_lookup),
                "source_watchlist_line_number": line_lookup.get(ticker, ""),
                "symbol_master_status": status,
                "primary_exchange": metadata.get("exchange", ""),
                "listing_exchange": listing.get("exchange", ""),
                "asset_type": metadata.get("quote_type", listing.get("asset_type", "")),
                "security_name": metadata.get("short_name") or listing.get("security_name", ""),
                "is_etf": bool(ticker in {benchmark_ticker, "QQQ"} or listing.get("is_etf", False) or metadata.get("quote_type") == "ETF"),
                "is_adr": bool("ADR" in str(metadata.get("short_name", "")).upper() or "ADS" in str(metadata.get("short_name", "")).upper()),
                "is_spac_or_former_spac_if_detectable": bool("SPAC" in str(metadata.get("short_name", "")).upper() or "SPAC" in str(metadata.get("long_name", "")).upper()),
                "is_recent_ipo_or_recent_listing": recent_listing,
                "first_trade_date_from_ohlcv": first_date.strftime("%Y-%m-%d") if pd.notna(first_date) else "",
                "last_trade_date_from_ohlcv": last_date.strftime("%Y-%m-%d") if pd.notna(last_date) else "",
                "has_sufficient_factor_lookback": bool(pd.notna(first_date) and first_date <= requested_start + pd.Timedelta(days=90)),
                "has_sufficient_forward_window": bool(pd.notna(last_date) and last_date >= requested_end - pd.Timedelta(days=35)),
                "normalized_symbol_notes": normalized_symbol_notes(ticker, listing, rejected),
                "validation_sources_used": ",".join(listing.get("sources", [])) or "yfinance_metadata_only",
            }
        )
    return pd.DataFrame(rows)


def listing_lookup(ticker: str, listing_sources: dict) -> dict:
    hits = []
    nasdaq = listing_sources.get("nasdaq_trader_nasdaq")
    if nasdaq is not None and "Symbol" in nasdaq.columns:
        rows = nasdaq.loc[nasdaq["Symbol"].astype(str).str.upper().eq(ticker)]
        if not rows.empty:
            row = rows.iloc[0]
            hits.append({"source": "nasdaq_trader_nasdaq", "exchange": "NASDAQ", "security_name": row.get("Security Name", ""), "asset_type": "EQUITY", "active": str(row.get("Test Issue", "N")) != "Y", "is_etf": str(row.get("ETF", "N")) == "Y"})
    other = listing_sources.get("nasdaq_trader_other")
    if other is not None and "ACT Symbol" in other.columns:
        rows = other.loc[other["ACT Symbol"].astype(str).str.upper().eq(ticker)]
        if not rows.empty:
            row = rows.iloc[0]
            hits.append({"source": "nasdaq_trader_other", "exchange": row.get("Exchange", ""), "security_name": row.get("Security Name", ""), "asset_type": "EQUITY", "active": str(row.get("Test Issue", "N")) != "Y", "is_etf": str(row.get("ETF", "N")) == "Y"})
    if not hits:
        if all(value is None for value in listing_sources.values()):
            return {"sources": [], "source_unavailable": True}
        return {"sources": [], "source_unavailable": False}
    first = hits[0]
    first["sources"] = [hit["source"] for hit in hits]
    first["source_unavailable"] = False
    return first


def symbol_master_status(ticker: str, listing: dict, metadata: dict, prices: pd.DataFrame, benchmark_ticker: str) -> str:
    if ticker in {benchmark_ticker, "QQQ"}:
        return "ETF_OR_INDEX_PROXY"
    if listing.get("source_unavailable") and not metadata:
        return "SOURCE_UNAVAILABLE"
    if listing.get("active") and not listing.get("is_etf"):
        return "ACTIVE_LISTED_EQUITY"
    quote_type = metadata.get("quote_type") or metadata.get("quoteType")
    if quote_type == "EQUITY":
        return "ACTIVE_LISTED_EQUITY" if not prices.empty else "UNKNOWN"
    if quote_type in {"ETF", "INDEX", "MUTUALFUND"}:
        return "NON_EQUITY"
    if listing.get("is_etf"):
        return "NON_EQUITY"
    return "UNKNOWN"


def normalized_symbol_notes(ticker: str, listing: dict, rejected: dict) -> str:
    notes = []
    if ticker in rejected:
        notes.append(f"yfinance_metadata_rejected:{rejected[ticker]}")
    if not listing.get("sources"):
        notes.append("not_found_in_public_listing_directory" if not listing.get("source_unavailable") else "listing_source_unavailable")
    return ";".join(notes)


def build_listing_validation_matrix(symbol_master: pd.DataFrame, universe: pd.DataFrame, rejected_metadata: pd.DataFrame, listing_sources: dict) -> pd.DataFrame:
    rows = []
    rejected = dict(zip(rejected_metadata["ticker"], rejected_metadata["reason"])) if rejected_metadata is not None and not rejected_metadata.empty else {}
    for _, row in symbol_master.iterrows():
        ticker = row["ticker"]
        source_available = "nasdaq_trader" in str(row["validation_sources_used"])
        status = "SOURCE_UNAVAILABLE" if row["symbol_master_status"] == "SOURCE_UNAVAILABLE" else ("MATCH" if source_available and row["symbol_master_status"] in {"ACTIVE_LISTED_EQUITY", "ETF_OR_INDEX_PROXY"} else "WARN")
        reason = "Public listing source confirms active symbol." if status == "MATCH" else "Public listing source unavailable or did not confirm symbol."
        if ticker in rejected and status == "MATCH":
            status = "WARN"
            reason = f"Public listing validates symbol but yfinance metadata rejected it: {rejected[ticker]}"
        rows.append(
            {
                "ticker": ticker,
                "source_name": "nasdaq_trader_symbol_directory",
                "source_available": source_available,
                "source_lookup_symbol": ticker,
                "source_security_name": row["security_name"],
                "source_exchange": row["listing_exchange"],
                "source_asset_type": row["asset_type"],
                "source_active_flag": row["symbol_master_status"] in {"ACTIVE_LISTED_EQUITY", "ETF_OR_INDEX_PROXY"},
                "source_delisted_flag": row["symbol_master_status"] == "DELISTED_OR_INACTIVE",
                "source_listing_date_if_available": "",
                "validation_status": status,
                "validation_reason": reason,
            }
        )
    return pd.DataFrame(rows)


def build_secondary_ohlcv_validation(data: pd.DataFrame, symbols: list[str], requested_start_date: str, requested_end_date: str, cache_dir: Path) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for ticker in symbols:
        primary = data.loc[data["ticker"].eq(ticker)].copy()
        secondary, source_status = fetch_stooq_ohlcv(ticker, requested_start_date, requested_end_date, cache_dir)
        rows.append(compare_ohlcv(ticker, primary, secondary, source_status))
    return pd.DataFrame(rows)


def fetch_stooq_ohlcv(ticker: str, start: str, end: str, cache_dir: Path) -> tuple[pd.DataFrame, str]:
    cache_path = cache_dir / f"{ticker}.csv"
    url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d&d1={start.replace('-', '')}&d2={end.replace('-', '')}"
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            text = response.read().decode("utf-8", errors="replace")
        if "No data" in text or not text.strip():
            return pd.DataFrame(), "NO_SECOND_SOURCE"
        cache_path.write_text(text, encoding="utf-8")
    except (urllib.error.URLError, TimeoutError, OSError):
        if cache_path.exists():
            text = cache_path.read_text(encoding="utf-8")
        else:
            return pd.DataFrame(), "SOURCE_UNAVAILABLE"
    try:
        frame = pd.read_csv(io.StringIO(text))
    except pd.errors.EmptyDataError:
        return pd.DataFrame(), "NO_SECOND_SOURCE"
    if frame.empty or "Date" not in frame.columns:
        return pd.DataFrame(), "NO_SECOND_SOURCE"
    frame = frame.rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    frame["date"] = pd.to_datetime(frame["date"])
    return frame, "AVAILABLE"


def compare_ohlcv(ticker: str, primary: pd.DataFrame, secondary: pd.DataFrame, source_status: str) -> dict:
    base = {
        "ticker": ticker,
        "primary_vendor": "yfinance",
        "secondary_vendor": "stooq" if source_status == "AVAILABLE" else "",
        "primary_start_date": primary["date"].min().strftime("%Y-%m-%d") if not primary.empty else "",
        "primary_end_date": primary["date"].max().strftime("%Y-%m-%d") if not primary.empty else "",
        "secondary_start_date": secondary["date"].min().strftime("%Y-%m-%d") if not secondary.empty else "",
        "secondary_end_date": secondary["date"].max().strftime("%Y-%m-%d") if not secondary.empty else "",
        "adjusted_close_available_primary": "adj_close" in primary.columns and primary["adj_close"].notna().any() if not primary.empty else False,
        "adjusted_close_available_secondary": False,
    }
    if source_status != "AVAILABLE" or primary.empty or secondary.empty:
        base.update(empty_ohlcv_metrics(source_status))
        return base
    merged = primary[["date", "close", "volume"]].merge(secondary[["date", "close", "volume"]], on="date", suffixes=("_primary", "_secondary"))
    if merged.empty:
        base.update(empty_ohlcv_metrics("NO_SECOND_SOURCE"))
        return base
    close_diff = (pd.to_numeric(merged["close_primary"], errors="coerce") / pd.to_numeric(merged["close_secondary"], errors="coerce") - 1).abs().dropna()
    volume_diff = (pd.to_numeric(merged["volume_primary"], errors="coerce") / pd.to_numeric(merged["volume_secondary"], errors="coerce").replace(0, pd.NA) - 1).abs().dropna()
    max_close = float(close_diff.max()) if not close_diff.empty else pd.NA
    status = "MATCH" if pd.notna(max_close) and max_close <= 0.03 and len(merged) > 0 else "WARN"
    base.update(
        {
            "overlap_trading_days": int(len(merged)),
            "close_price_median_abs_diff_pct": pct(close_diff.median()),
            "close_price_p95_abs_diff_pct": pct(close_diff.quantile(0.95)) if not close_diff.empty else pd.NA,
            "close_price_max_abs_diff_pct": pct(max_close),
            "volume_median_abs_diff_pct": pct(volume_diff.median()) if not volume_diff.empty else pd.NA,
            "volume_p95_abs_diff_pct": pct(volume_diff.quantile(0.95)) if not volume_diff.empty else pd.NA,
            "volume_max_abs_diff_pct": pct(volume_diff.max()) if not volume_diff.empty else pd.NA,
            "adjusted_price_mismatch_flag": False,
            "split_or_corporate_action_mismatch_flag": bool(pd.notna(max_close) and max_close > 0.10),
            "validation_status": status,
            "validation_reason": "Secondary OHLCV compared against yfinance close/volume." if status == "MATCH" else "Secondary OHLCV available but differences require review.",
        }
    )
    return base


def empty_ohlcv_metrics(status: str) -> dict:
    validation = "SOURCE_UNAVAILABLE" if status == "SOURCE_UNAVAILABLE" else "NO_SECOND_SOURCE"
    return {
        "overlap_trading_days": 0,
        "close_price_median_abs_diff_pct": pd.NA,
        "close_price_p95_abs_diff_pct": pd.NA,
        "close_price_max_abs_diff_pct": pd.NA,
        "volume_median_abs_diff_pct": pd.NA,
        "volume_p95_abs_diff_pct": pd.NA,
        "volume_max_abs_diff_pct": pd.NA,
        "adjusted_price_mismatch_flag": pd.NA,
        "split_or_corporate_action_mismatch_flag": pd.NA,
        "validation_status": validation,
        "validation_reason": "Secondary source unavailable or has no data.",
    }


def build_quarantine_list(symbol_master: pd.DataFrame, listing: pd.DataFrame, secondary: pd.DataFrame) -> pd.DataFrame:
    listing_status = listing.set_index("ticker")["validation_status"].to_dict() if not listing.empty else {}
    secondary_status = secondary.set_index("ticker")["validation_status"].to_dict() if not secondary.empty else {}
    rows = []
    for _, row in symbol_master.iterrows():
        reasons = []
        action = "KEEP_WITH_WARNING"
        if row["symbol_master_status"] in {"DELISTED_OR_INACTIVE", "NON_EQUITY", "UNKNOWN", "SOURCE_UNAVAILABLE"} and row["symbol_master_status"] != "ETF_OR_INDEX_PROXY":
            reasons.append(f"symbol_master_status:{row['symbol_master_status']}")
        if not bool(row["has_sufficient_factor_lookback"]):
            if bool(row["is_recent_ipo_or_recent_listing"]):
                reasons.append("recent_listing_requires_earliest_safe_replay_date")
                action = "ALLOW_AFTER_DATE"
            else:
                reasons.append("insufficient_factor_lookback")
        if not bool(row["has_sufficient_forward_window"]):
            reasons.append("insufficient_forward_window")
        if "yfinance_metadata_rejected" in str(row["normalized_symbol_notes"]) and listing_status.get(row["ticker"]) not in {"MATCH", "WARN"}:
            reasons.append("unresolved_metadata_conflict")
        if secondary_status.get(row["ticker"]) in {"FAIL"}:
            reasons.append("secondary_ohlcv_fail")
        if reasons and action != "ALLOW_AFTER_DATE":
            status = "QUARANTINE"
            action = "DROP_FROM_RESEARCH" if "symbol_master_status" in ";".join(reasons) else "MANUAL_REVIEW"
        elif reasons:
            status = "RESEARCH_WARN"
        else:
            status = "ALLOW_RESEARCH"
        rows.append(
            {
                "ticker": row["ticker"],
                "quarantine_status": status,
                "quarantine_reason": ";".join(reasons) if reasons else "clean_research_symbol",
                "source_evidence": f"symbol_master={row['symbol_master_status']};listing={listing_status.get(row['ticker'], '')};secondary={secondary_status.get(row['ticker'], '')}",
                "suggested_action": action,
                "earliest_safe_replay_date": row["first_trade_date_from_ohlcv"] if action == "ALLOW_AFTER_DATE" else "",
            }
        )
    return pd.DataFrame(rows)


def build_taxonomy_resolution(symbol_master: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in symbol_master.iterrows():
        ticker = row["ticker"]
        prior_theme, prior_subtheme = ticker_theme_subtheme(ticker)
        theme, subtheme, confidence, evidence, notes = resolve_taxonomy(ticker, str(row.get("security_name", "")), prior_theme, prior_subtheme)
        rows.append(
            {
                "ticker": ticker,
                "prior_theme": prior_theme,
                "resolved_theme": theme,
                "resolved_subtheme": subtheme,
                "confidence": confidence,
                "evidence_source": evidence,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def resolve_taxonomy(ticker: str, security_name: str, prior_theme: str, prior_subtheme: str) -> tuple[str, str, str, str, str]:
    if ticker in STATIC_TAXONOMY:
        theme, subtheme = STATIC_TAXONOMY[ticker]
        return theme, subtheme, "HIGH", "static_taxonomy", ""
    name = security_name.lower()
    rules = [
        ("software", ["software", "cloud", "data", "cyber", "elastic"], "software", "name_keyword"),
        ("semiconductor / hardware", ["semiconductor", "chip", "micro", "electronics"], "hardware", "name_keyword"),
        ("biotech", ["therapeutics", "biotech", "pharma", "medicine"], "life sciences", "name_keyword"),
        ("consumer internet", ["inc.", "platform", "media"], "consumer platform", "name_keyword"),
        ("fintech", ["financial", "payments", "capital"], "financial technology", "name_keyword"),
    ]
    for theme, keywords, subtheme, source in rules:
        if any(keyword in name for keyword in keywords):
            return theme, subtheme, "MEDIUM", source, "resolved from listing/security name"
    if prior_theme != "UNMAPPED_LOW_CONFIDENCE":
        return prior_theme, prior_subtheme, "MEDIUM", "existing_phase1_taxonomy", ""
    return "UNMAPPED_LOW_CONFIDENCE", "manual_review_required", "LOW", "conservative_fallback", "manual review required"


def build_clean_watchlist_candidate(quarantine: pd.DataFrame) -> str:
    allowed = quarantine.loc[quarantine["quarantine_status"].isin(["ALLOW_RESEARCH", "RESEARCH_WARN"])].copy()
    allowed = allowed.loc[~allowed["ticker"].isin(["SPY", "QQQ"])]
    lines = [
        "# Phase 1J research-only clean watchlist candidate.",
        "# Not approved for daily scan, paper execution, or real-money execution.",
    ]
    lines.extend(sorted(allowed["ticker"].astype(str).unique()))
    return "\n".join(lines) + "\n"


def build_data_readiness_scorecard(symbol_master: pd.DataFrame, listing: pd.DataFrame, secondary: pd.DataFrame, quarantine: pd.DataFrame, taxonomy: pd.DataFrame) -> pd.DataFrame:
    total = int(len(symbol_master))
    quarantined = int(quarantine["quarantine_status"].eq("QUARANTINE").sum())
    active_candidates = quarantine.loc[~quarantine["ticker"].isin(["SPY", "QQQ"]) & quarantine["quarantine_status"].isin(["ALLOW_RESEARCH", "RESEARCH_WARN"])]
    active_taxonomy = taxonomy.loc[taxonomy["ticker"].isin(active_candidates["ticker"])]
    proxy_ok = set(["SPY", "QQQ"]).issubset(set(symbol_master.loc[symbol_master["symbol_master_status"].eq("ETF_OR_INDEX_PROXY"), "ticker"]))
    gates_1_6 = (
        quarantined / max(1, total) <= 0.05
        and active_taxonomy["confidence"].isin(["HIGH", "MEDIUM"]).all()
        and proxy_ok
        and int(symbol_master.loc[symbol_master["ticker"].isin(active_candidates["ticker"]), "has_sufficient_factor_lookback"].sum()) == len(active_candidates)
    )
    secondary_good = int(secondary["validation_status"].isin(["MATCH", "WARN"]).sum())
    secondary_ratio = secondary_good / max(1, len(secondary))
    if gates_1_6 and secondary_ratio >= 0.80:
        status = PHASE_1J_RESEARCH_DATA_READY_FOR_FROZEN_RETEST
    elif gates_1_6:
        status = PHASE_1J_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING
    else:
        status = PHASE_1J_DATA_BLOCKED
    return pd.DataFrame(
        [
            {
                "total_symbols": total,
                "active_listed_equity_count": int(symbol_master["symbol_master_status"].eq("ACTIVE_LISTED_EQUITY").sum()),
                "etf_or_index_proxy_count": int(symbol_master["symbol_master_status"].eq("ETF_OR_INDEX_PROXY").sum()),
                "unknown_or_source_unavailable_count": int(symbol_master["symbol_master_status"].isin(["UNKNOWN", "SOURCE_UNAVAILABLE"]).sum()),
                "quarantined_count": quarantined,
                "research_warn_count": int(quarantine["quarantine_status"].eq("RESEARCH_WARN").sum()),
                "allow_research_count": int(quarantine["quarantine_status"].eq("ALLOW_RESEARCH").sum()),
                "secondary_ohlcv_match_count": int(secondary["validation_status"].eq("MATCH").sum()),
                "secondary_ohlcv_warn_count": int(secondary["validation_status"].eq("WARN").sum()),
                "secondary_ohlcv_fail_count": int(secondary["validation_status"].eq("FAIL").sum()),
                "no_second_source_count": int(secondary["validation_status"].isin(["NO_SECOND_SOURCE", "SOURCE_UNAVAILABLE"]).sum()),
                "taxonomy_resolved_high_count": int(taxonomy["confidence"].eq("HIGH").sum()),
                "taxonomy_resolved_medium_count": int(taxonomy["confidence"].eq("MEDIUM").sum()),
                "taxonomy_resolved_low_count": int(taxonomy["confidence"].eq("LOW").sum()),
                "unresolved_taxonomy_count": int(taxonomy["confidence"].eq("LOW").sum()),
                "symbols_with_sufficient_lookback_count": int(symbol_master["has_sufficient_factor_lookback"].sum()),
                "symbols_with_earliest_safe_replay_date_count": int(quarantine["suggested_action"].eq("ALLOW_AFTER_DATE").sum()),
                "data_readiness_status": status,
            }
        ]
    )


def phase1j_summary_markdown(summary: dict, scorecard: pd.DataFrame, symbol_master: pd.DataFrame, listing: pd.DataFrame, secondary: pd.DataFrame, quarantine: pd.DataFrame, taxonomy: pd.DataFrame) -> str:
    lines = [
        "PHOENIX NANO PHASE 1J — SYMBOL MASTER, SECONDARY VENDOR VALIDATION, AND DATA READINESS GATE",
        "",
        "Research-only. No symbol, vendor, watchlist, or strategy is approved for daily scan, paper execution, or real-money execution.",
        "",
        "## Phase 1I Recap",
        "",
        "- Phase 1I ended as PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH.",
        "- Phase 1J builds a symbol master and readiness gate before more strategy research.",
        "",
        "## Symbol Master Status Counts",
        "",
        str(summary["symbol_master_counts"]),
        "",
        "## Listing Validation Status Counts",
        "",
        str(summary["listing_counts"]),
        "",
        "## Secondary OHLCV Validation Coverage",
        "",
        str(summary["secondary_counts"]),
        "",
        "## Quarantine Count And Top Reasons",
        "",
        str(summary["quarantine_counts"]),
        top_reason_summary(quarantine, "quarantine_reason"),
        "",
        "## Taxonomy Resolution Status",
        "",
        str(summary["taxonomy_counts"]),
        "",
        "## Clean Watchlist Candidate Count",
        "",
        f"- {summary['clean_watchlist_count']}",
        "",
        "## Data Readiness Scorecard",
        "",
        scorecard.to_markdown(index=False) if not scorecard.empty else "No scorecard row.",
        "",
        f"## Final Phase 1J Status: {summary['phase_1j_status']}",
        "",
        "Do not start paper execution or real-money execution.",
        "",
        "## Next Research Task Recommendation",
        "",
        "Ask GPT whether to continue data/vendor remediation or run a frozen retest only if GPT accepts the data-readiness status.",
        "",
    ]
    return "\n".join(lines)


def write_phase1j_reports(symbol_master, listing, secondary, scorecard, quarantine, taxonomy, clean_watchlist_text, summary_md, paths: dict[str, str | Path]) -> None:
    for path in paths.values():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    symbol_master.to_csv(paths["symbol_master"], index=False)
    listing.to_csv(paths["listing"], index=False)
    secondary.to_csv(paths["secondary"], index=False)
    scorecard.to_csv(paths["scorecard"], index=False)
    quarantine.to_csv(paths["quarantine"], index=False)
    taxonomy.to_csv(paths["taxonomy"], index=False)
    Path(paths["clean_watchlist"]).write_text(clean_watchlist_text, encoding="utf-8")
    Path(paths["summary"]).write_text(summary_md, encoding="utf-8")


def pct(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    return float(value) * 100.0


def top_reason_summary(frame: pd.DataFrame, column: str) -> str:
    if frame.empty or column not in frame.columns:
        return "- none"
    return "\n".join(f"- {reason}: {count}" for reason, count in frame[column].value_counts().head(8).items())
