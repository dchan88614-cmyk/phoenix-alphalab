from __future__ import annotations

import csv
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from src.research.phase1j_data_readiness import pct, watchlist_symbols_with_lines
from src.research.phase1k_data_remediation import PROXY_TICKERS, SMOKE_TICKERS, read_report


PHASE_1L_SECONDARY_VENDOR_BLOCKED = "PHASE_1L_SECONDARY_VENDOR_BLOCKED"
PHASE_1L_DATA_ADAPTER_READY_VENDOR_MISSING = "PHASE_1L_DATA_ADAPTER_READY_VENDOR_MISSING"
PHASE_1L_READY_FOR_FROZEN_RETEST_GPT_REVIEW = "PHASE_1L_READY_FOR_FROZEN_RETEST_GPT_REVIEW"


def build_phase1l_secondary_data_adapter_gate(
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
    symbols = sorted(set([item["ticker"] for item in watchlist_symbols_with_lines(watchlist_path, watchlist_tickers)] + list(PROXY_TICKERS)))
    clean_v2 = (reports / "phase1k_clean_watchlist_v2_candidate.txt").read_text(encoding="utf-8") if (reports / "phase1k_clean_watchlist_v2_candidate.txt").exists() else ""
    lifecycle = read_report(reports / "phase1k_symbol_lifecycle_alias_map.csv")
    taxonomy = read_report(reports / "phase1k_taxonomy_resolution_v2.csv")

    raw_diagnostics, stooq_smoke = build_stooq_smoke_v2(requested_start_date, requested_end_date, cache / "secondary_ohlcv" / "stooq")
    capability = build_secondary_source_capability_matrix(stooq_smoke)
    yahoo_audit = build_yahoo_chart_transport_fallback_audit(frame, clean_v2, requested_start_date, requested_end_date, cache / "secondary_ohlcv" / "yahoo_chart")
    alias_audit, clean_v3 = build_alias_clean_watchlist_audit(clean_v2, lifecycle)
    secondary_v3 = build_secondary_ohlcv_validation_v3(frame, symbols, stooq_smoke, requested_start_date, requested_end_date, cache / "secondary_ohlcv" / "stooq")
    scorecard = build_phase1l_data_readiness_scorecard(symbols, stooq_smoke, raw_diagnostics, secondary_v3, yahoo_audit, alias_audit, taxonomy, clean_v3)
    summary = {
        "phase_1l_status": str(scorecard.iloc[0]["data_readiness_status"]) if not scorecard.empty else PHASE_1L_SECONDARY_VENDOR_BLOCKED,
        "capability_counts": capability["capability_status"].value_counts().to_dict(),
        "payload_counts": raw_diagnostics["detected_payload_type"].value_counts().to_dict(),
        "stooq_smoke_counts": stooq_smoke["smoke_status"].value_counts().to_dict(),
        "secondary_counts": secondary_v3["validation_status"].value_counts().to_dict(),
        "yahoo_transport_counts": yahoo_audit["transport_status"].value_counts().to_dict(),
        "alias_audit_counts": alias_audit["audit_status"].value_counts().to_dict(),
        "clean_watchlist_v3_count": count_clean_watchlist(clean_v3),
    }
    summary_md = phase1l_summary_markdown(summary, scorecard, raw_diagnostics, capability, stooq_smoke, secondary_v3, yahoo_audit, alias_audit)
    return capability, raw_diagnostics, stooq_smoke, secondary_v3, yahoo_audit, alias_audit, clean_v3, scorecard, summary_md, summary


def stooq_lookup_symbols(ticker: str) -> list[str]:
    return [f"{ticker.lower()}.us", f"{ticker.upper()}.US", ticker.lower()]


def stooq_url(lookup_symbol: str, start: str, end: str) -> str:
    return f"https://stooq.com/q/d/l/?s={lookup_symbol}&i=d&d1={start.replace('-', '')}&d2={end.replace('-', '')}"


def build_stooq_smoke_v2(start: str, end: str, cache_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = cache_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    diagnostics = []
    smoke_rows = []
    for ticker in SMOKE_TICKERS:
        attempts = []
        for lookup in stooq_lookup_symbols(ticker):
            raw = fetch_text(stooq_url(lookup, start, end), raw_dir / f"{ticker}_{lookup.replace('.', '_')}.txt")
            diag = diagnose_raw_response("stooq_daily_csv", ticker, lookup, raw, start, end)
            diagnostics.append(diag)
            frame, parser_status, parser_reason = parse_ohlcv_text(raw["text"])
            overlap = overlap_days(frame, start, end)
            status = stooq_attempt_status(parser_status, overlap, diag["detected_payload_type"], bool(raw["used_cache_fallback"]))
            attempts.append((status, frame, diag, raw, overlap, parser_reason))
        selected = select_stooq_attempt(attempts)
        status, frame, diag, raw, overlap, reason = selected
        smoke_rows.append(
            {
                "source_name": "stooq_daily_csv",
                "ticker": ticker,
                "lookup_symbol": diag["lookup_symbol"],
                "url_or_cache_key": diag["url_or_cache_key"],
                "attempted_network_fetch": raw["attempted_network_fetch"],
                "used_cache_fallback": raw["used_cache_fallback"],
                "http_status_if_available": raw["http_status_if_available"],
                "response_bytes": diag["response_bytes"],
                "parsed_rows": int(len(frame)),
                "first_date": frame["date"].min().strftime("%Y-%m-%d") if not frame.empty else "",
                "last_date": frame["date"].max().strftime("%Y-%m-%d") if not frame.empty else "",
                "required_start_date": start,
                "required_end_date": end,
                "overlap_days_with_required_window": overlap,
                "smoke_status": status,
                "smoke_reason": reason or diag["parser_reason"],
                "payload_type": diag["detected_payload_type"],
                "selected_attempt_for_ticker": True,
            }
        )
    smoke = pd.DataFrame(smoke_rows)
    pass_count = int(smoke["smoke_status"].eq("PASS").sum())
    cache_pass_count = int(smoke["smoke_status"].eq("CACHE_ONLY_PASS").sum())
    if pass_count >= 3:
        source_status = "SMOKE_PASS"
    elif cache_pass_count >= 3:
        source_status = "CACHE_ONLY_PASS"
    elif smoke["payload_type"].isin(["HTML_BLOCK", "HTML_ERROR"]).any():
        source_status = "GLOBAL_SOURCE_UNAVAILABLE"
    elif smoke["smoke_status"].eq("PARSE_ERROR").any():
        source_status = "PARSER_BUG_SUSPECTED"
    else:
        source_status = "SMOKE_FAIL"
    smoke["source_level_status"] = source_status
    return pd.DataFrame(diagnostics), smoke


def fetch_text(url: str, cache_path: Path) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "PhoenixAlphaLab/1.0 research data validation"})
    text = ""
    http_status = ""
    final_url = url
    content_type = ""
    exception_class = ""
    used_cache = False
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                http_status = str(getattr(response, "status", ""))
                final_url = response.geturl()
                content_type = response.headers.get("Content-Type", "")
                raw = response.read()
            text = raw.decode("utf-8-sig", errors="replace")
            break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            exception_class = exc.__class__.__name__
            if attempt == 0:
                time.sleep(0.25)
    if not text and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8")
        used_cache = True
    return {
        "text": text,
        "url": url,
        "cache_path": str(cache_path),
        "attempted_network_fetch": True,
        "used_cache_fallback": used_cache,
        "http_status_if_available": http_status,
        "final_url_if_available": final_url,
        "content_type_if_available": content_type,
        "exception_class_if_any": exception_class,
    }


def diagnose_raw_response(source_name: str, ticker: str, lookup_symbol: str, raw: dict, start: str, end: str) -> dict:
    text = raw["text"]
    frame, parser_status, parser_reason = parse_ohlcv_text(text)
    payload_type = detect_payload_type(text, frame)
    if parser_status == "PASS" and not raw["used_cache_fallback"]:
        Path(raw["cache_path"]).write_text(text, encoding="utf-8")
    return {
        "source_name": source_name,
        "ticker": ticker,
        "lookup_symbol": lookup_symbol,
        "url_or_cache_key": raw["cache_path"] if raw["used_cache_fallback"] else raw["url"],
        "http_status_if_available": raw["http_status_if_available"],
        "final_url_if_available": raw["final_url_if_available"],
        "content_type_if_available": raw["content_type_if_available"],
        "response_bytes": len(text.encode("utf-8")),
        "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
        "first_200_chars_sanitized": sanitize(text[:200]),
        "detected_payload_type": payload_type,
        "detected_columns": ",".join(frame.columns.tolist()) if not frame.empty else "",
        "parser_status": parser_status,
        "parser_reason": parser_reason,
        "required_start_date": start,
        "required_end_date": end,
    }


def sanitize(value: str) -> str:
    return " ".join(value.replace("\n", " ").replace("\r", " ").split())


def detect_payload_type(text: str, frame: pd.DataFrame) -> str:
    stripped = text.lstrip("\ufeff").strip()
    lower = stripped.lower()
    if not stripped:
        return "EMPTY"
    if lower.startswith("<!doctype html") or lower.startswith("<html") or "<script" in lower or "<noscript" in lower:
        return "HTML_BLOCK" if "__verify" in lower or "requires javascript" in lower else "HTML_ERROR"
    if "no data" in lower:
        return "CSV_NO_DATA"
    if not frame.empty:
        return "CSV_OHLCV"
    if "error" in lower:
        return "TEXT_ERROR"
    return "UNKNOWN"


def parse_ohlcv_text(text: str) -> tuple[pd.DataFrame, str, str]:
    stripped = text.lstrip("\ufeff").strip()
    if not stripped:
        return pd.DataFrame(), "EMPTY", "Empty response."
    if stripped.lower().startswith("<!doctype html") or stripped.lower().startswith("<html") or "<script" in stripped.lower():
        return pd.DataFrame(), "HTML_OR_BLOCKED", "HTML or browser-verification payload detected."
    if "no data" in stripped.lower():
        return pd.DataFrame(), "NO_DATA_FOR_SYMBOL", "Explicit no-data response."
    sample = stripped[:1000]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    try:
        frame = pd.read_csv(io.StringIO(stripped), sep=delimiter)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        return pd.DataFrame(), "PARSE_ERROR", exc.__class__.__name__
    columns = {str(col).strip().lower(): col for col in frame.columns}
    required = ["date", "open", "high", "low", "close", "volume"]
    if frame.empty or not all(col in columns for col in required):
        return pd.DataFrame(), "PARSE_ERROR", "Missing OHLCV columns."
    out = frame.rename(columns={columns[col]: col for col in required})[required].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"])
    if out.empty:
        return pd.DataFrame(), "PARSE_ERROR", "No parseable dates."
    return out, "PASS", ""


def stooq_attempt_status(parser_status: str, overlap: int, payload_type: str, used_cache: bool) -> str:
    if parser_status == "PASS" and overlap > 0:
        return "CACHE_ONLY_PASS" if used_cache else "PASS"
    if parser_status == "NO_DATA_FOR_SYMBOL":
        return "NO_DATA_FOR_SYMBOL"
    if parser_status == "HTML_OR_BLOCKED" or payload_type in {"HTML_BLOCK", "HTML_ERROR"}:
        return "HTML_OR_BLOCKED"
    if parser_status == "EMPTY":
        return "GLOBAL_SOURCE_UNAVAILABLE"
    return "PARSE_ERROR"


def select_stooq_attempt(attempts: list[tuple]) -> tuple:
    priority = {"PASS": 0, "CACHE_ONLY_PASS": 1, "NO_DATA_FOR_SYMBOL": 2, "HTML_OR_BLOCKED": 3, "PARSE_ERROR": 4, "GLOBAL_SOURCE_UNAVAILABLE": 5}
    return sorted(attempts, key=lambda item: priority.get(item[0], 9))[0]


def overlap_days(frame: pd.DataFrame, start: str, end: str) -> int:
    if frame.empty:
        return 0
    dates = pd.to_datetime(frame["date"])
    return int(dates.between(pd.Timestamp(start), pd.Timestamp(end)).sum())


def build_secondary_source_capability_matrix(stooq_smoke: pd.DataFrame) -> pd.DataFrame:
    stooq_status = str(stooq_smoke["source_level_status"].iloc[0]) if not stooq_smoke.empty else "GLOBAL_UNAVAILABLE"
    stooq_capability = "SMOKE_PASS" if stooq_status == "SMOKE_PASS" else ("SMOKE_FAIL" if stooq_status in {"SMOKE_FAIL", "PARSER_BUG_SUSPECTED"} else "GLOBAL_UNAVAILABLE")
    return pd.DataFrame(
        [
            {
                "source_name": "stooq_daily_csv",
                "source_family": "stooq",
                "adapter_name": "stooq_daily_csv_v2",
                "requires_secret": False,
                "is_independent_of_primary_vendor": True,
                "allowed_for_execution_grade_secondary_validation": stooq_capability == "SMOKE_PASS",
                "allowed_for_transport_fallback_only": False,
                "network_fetch_attempted": True,
                "cache_supported": True,
                "expected_format": "CSV OHLCV",
                "known_limitations": "May return HTML/browser-verification payloads.",
                "capability_status": stooq_capability,
                "decision_reason": f"Stooq source-level smoke status: {stooq_status}.",
            },
            {
                "source_name": "yahoo_chart_api",
                "source_family": "yahoo",
                "adapter_name": "yahoo_chart_transport_audit",
                "requires_secret": False,
                "is_independent_of_primary_vendor": False,
                "allowed_for_execution_grade_secondary_validation": False,
                "allowed_for_transport_fallback_only": True,
                "network_fetch_attempted": True,
                "cache_supported": True,
                "expected_format": "JSON chart OHLCV",
                "known_limitations": "Same vendor family as yfinance primary data; transport fallback only.",
                "capability_status": "TRANSPORT_FALLBACK_ONLY",
                "decision_reason": "Same-vendor transport sanity check; cannot count as independent secondary validation.",
            },
        ]
    )


def build_yahoo_chart_transport_fallback_audit(data: pd.DataFrame, clean_watchlist: str, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    sample = [line.split("#", 1)[0].strip() for line in clean_watchlist.splitlines() if line.strip() and not line.startswith("#")]
    tickers = sorted(set(SMOKE_TICKERS + sample[:20]))
    rows = []
    for ticker in tickers:
        primary = data.loc[data["ticker"].eq(ticker)].copy()
        secondary, report = fetch_yahoo_chart(ticker, start, end, cache_dir)
        rows.append(compare_transport_fallback(ticker, primary, secondary, report))
    return pd.DataFrame(rows)


def fetch_yahoo_chart(ticker: str, start: str, end: str, cache_dir: Path) -> tuple[pd.DataFrame, dict]:
    period1 = int(pd.Timestamp(start, tz="UTC").timestamp())
    period2 = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={period1}&period2={period2}&interval=1d&events=history"
    cache_path = cache_dir / "raw" / f"{ticker}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    raw = fetch_text(url, cache_path)
    text = raw["text"]
    frame = pd.DataFrame()
    if text:
        try:
            payload = json.loads(text)
            result = payload.get("chart", {}).get("result", []) or []
            if result:
                item = result[0]
                timestamps = item.get("timestamp", []) or []
                quote = (item.get("indicators", {}).get("quote", []) or [{}])[0]
                adj = (item.get("indicators", {}).get("adjclose", []) or [{}])[0]
                frame = pd.DataFrame(
                    {
                        "date": pd.to_datetime(timestamps, unit="s").normalize(),
                        "open": quote.get("open", []),
                        "high": quote.get("high", []),
                        "low": quote.get("low", []),
                        "close": quote.get("close", []),
                        "volume": quote.get("volume", []),
                        "adj_close": adj.get("adjclose", quote.get("close", [])),
                    }
                ).dropna(subset=["date", "close"])
                if not raw["used_cache_fallback"]:
                    cache_path.write_text(text, encoding="utf-8")
        except (json.JSONDecodeError, ValueError, TypeError):
            frame = pd.DataFrame()
    return frame, raw


def compare_transport_fallback(ticker: str, primary: pd.DataFrame, secondary: pd.DataFrame, report: dict) -> dict:
    merged = pd.DataFrame()
    if not primary.empty and not secondary.empty:
        merged = primary[["date", "close", "volume"]].merge(secondary[["date", "close", "volume"]], on="date", suffixes=("_primary", "_secondary"))
    if merged.empty:
        status = "NO_DATA_FOR_SYMBOL" if report["text"] else "GLOBAL_SOURCE_UNAVAILABLE"
        close_med = pd.NA
        vol_med = pd.NA
    else:
        close_diff = (pd.to_numeric(merged["close_primary"], errors="coerce") / pd.to_numeric(merged["close_secondary"], errors="coerce") - 1).abs().dropna()
        vol_diff = (pd.to_numeric(merged["volume_primary"], errors="coerce") / pd.to_numeric(merged["volume_secondary"], errors="coerce").replace(0, pd.NA) - 1).abs().dropna()
        close_med = pct(close_diff.median()) if not close_diff.empty else pd.NA
        vol_med = pct(vol_diff.median()) if not vol_diff.empty else pd.NA
        status = "TRANSPORT_MATCH" if not close_diff.empty and float(close_diff.max()) <= 0.03 else "TRANSPORT_WARN"
    return {
        "ticker": ticker,
        "source_name": "yahoo_chart_api",
        "source_family": "yahoo",
        "is_independent_of_primary_vendor": False,
        "network_fetch_attempted": True,
        "used_cache_fallback": report["used_cache_fallback"],
        "parsed_rows": int(len(secondary)),
        "first_date": secondary["date"].min().strftime("%Y-%m-%d") if not secondary.empty else "",
        "last_date": secondary["date"].max().strftime("%Y-%m-%d") if not secondary.empty else "",
        "overlap_days_with_primary": int(len(merged)),
        "close_price_median_abs_diff_pct_vs_primary": close_med,
        "volume_median_abs_diff_pct_vs_primary": vol_med,
        "transport_status": status,
        "reason": "Same-vendor transport fallback only; not independent validation.",
    }


def build_secondary_ohlcv_validation_v3(data: pd.DataFrame, symbols: list[str], stooq_smoke: pd.DataFrame, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    source_status = str(stooq_smoke["source_level_status"].iloc[0]) if not stooq_smoke.empty else "GLOBAL_SOURCE_UNAVAILABLE"
    rows = []
    for ticker in symbols:
        primary = data.loc[data["ticker"].eq(ticker)].copy()
        if source_status not in {"SMOKE_PASS", "CACHE_ONLY_PASS"}:
            rows.append(empty_validation_v3(ticker, primary, source_status, "Independent Stooq smoke did not pass; full independent validation skipped."))
            continue
        secondary = pd.DataFrame()
        fetch_status = source_status
        lookup_symbol = ""
        used_cache = source_status == "CACHE_ONLY_PASS"
        for lookup in stooq_lookup_symbols(ticker):
            raw = fetch_text(stooq_url(lookup, start, end), cache_dir / "raw" / f"{ticker}_{lookup.replace('.', '_')}.txt")
            frame, parser_status, _ = parse_ohlcv_text(raw["text"])
            if parser_status == "PASS":
                secondary = frame
                lookup_symbol = lookup
                used_cache = raw["used_cache_fallback"]
                break
        rows.append(compare_validation_v3(ticker, primary, secondary, lookup_symbol or f"{ticker.lower()}.us", source_status, used_cache))
    return pd.DataFrame(rows)


def empty_validation_v3(ticker: str, primary: pd.DataFrame, source_status: str, reason: str) -> dict:
    return {
        "ticker": ticker,
        "primary_vendor": "yfinance",
        "secondary_vendor": "stooq_daily_csv",
        "secondary_source_family": "stooq",
        "is_independent_secondary": True,
        "lookup_symbol": f"{ticker.lower()}.us",
        "source_global_status": source_status,
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
        "validation_status": "GLOBAL_SOURCE_UNAVAILABLE",
        "validation_reason": reason,
    }


def compare_validation_v3(ticker: str, primary: pd.DataFrame, secondary: pd.DataFrame, lookup_symbol: str, source_status: str, used_cache: bool) -> dict:
    base = empty_validation_v3(ticker, primary, source_status, "")
    base["lookup_symbol"] = lookup_symbol
    if secondary.empty or primary.empty:
        base["validation_status"] = "NO_DATA_FOR_SYMBOL"
        base["validation_reason"] = "Primary or secondary data missing."
        return base
    base["secondary_start_date"] = secondary["date"].min().strftime("%Y-%m-%d")
    base["secondary_end_date"] = secondary["date"].max().strftime("%Y-%m-%d")
    merged = primary[["date", "close", "volume"]].merge(secondary[["date", "close", "volume"]], on="date", suffixes=("_primary", "_secondary"))
    if merged.empty:
        base["validation_status"] = "NO_DATA_FOR_SYMBOL"
        base["validation_reason"] = "No overlap; never emit MATCH without overlap."
        return base
    close_diff = (pd.to_numeric(merged["close_primary"], errors="coerce") / pd.to_numeric(merged["close_secondary"], errors="coerce") - 1).abs().dropna()
    volume_diff = (pd.to_numeric(merged["volume_primary"], errors="coerce") / pd.to_numeric(merged["volume_secondary"], errors="coerce").replace(0, pd.NA) - 1).abs().dropna()
    if close_diff.empty:
        base["validation_status"] = "FAIL"
        base["validation_reason"] = "Overlap exists but close differences could not be computed."
        return base
    max_close = float(close_diff.max())
    status = "MATCH" if max_close <= 0.03 else "WARN"
    if used_cache:
        status = "CACHE_ONLY_MATCH" if status == "MATCH" else "CACHE_ONLY_WARN"
    base.update(
        {
            "overlap_trading_days": int(len(merged)),
            "close_price_median_abs_diff_pct": pct(close_diff.median()),
            "close_price_p95_abs_diff_pct": pct(close_diff.quantile(0.95)),
            "close_price_max_abs_diff_pct": pct(max_close),
            "volume_median_abs_diff_pct": pct(volume_diff.median()) if not volume_diff.empty else pd.NA,
            "volume_p95_abs_diff_pct": pct(volume_diff.quantile(0.95)) if not volume_diff.empty else pd.NA,
            "volume_max_abs_diff_pct": pct(volume_diff.max()) if not volume_diff.empty else pd.NA,
            "adjusted_close_available_secondary": "adj_close" in secondary.columns,
            "adjusted_price_mismatch_flag": False,
            "split_or_corporate_action_mismatch_flag": bool(max_close > 0.10),
            "validation_status": status,
            "validation_reason": "Independent secondary validation with positive overlap.",
        }
    )
    return base


def build_alias_clean_watchlist_audit(clean_watchlist: str, lifecycle: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    lifecycle_map = lifecycle.set_index("original_watchlist_ticker").to_dict("index") if not lifecycle.empty else {}
    rows = []
    output = [
        "# Phase 1L research-only clean watchlist v3 candidate.",
        "# Not approved for daily scan, paper execution, or real-money execution.",
        "# Alias/date-gated symbols are research-only and must be handled by replay eligibility logic.",
    ]
    for line_number, raw_line in enumerate(clean_watchlist.splitlines(), start=1):
        if not raw_line.strip() or raw_line.startswith("#"):
            continue
        ticker = raw_line.split("#", 1)[0].strip().upper()
        comment = raw_line.split("#", 1)[1].strip() if "#" in raw_line else ""
        lifecycle_row = lifecycle_map.get(ticker, {})
        canonical = lifecycle_row.get("canonical_current_ticker", ticker)
        historical = lifecycle_row.get("historical_ticker", ticker)
        alias_status = lifecycle_row.get("alias_status", "UNKNOWN")
        is_proxy = ticker in PROXY_TICKERS or alias_status == "ETF_OR_INDEX_PROXY"
        date_gate = parse_date_gate(comment)
        comment_status = "PASS"
        audit_status = "PASS"
        reason = "clean"
        if ticker == "SQ":
            date_gate = "2025-01-21"
            canonical = "XYZ"
            historical = "SQ"
            alias_status = "RENAMED"
            reason = "SQ date gate normalized to XYZ effective date."
        if "earliest_safe_replay_date=" in comment and not date_gate:
            comment_status = "FAIL"
            audit_status = "FAIL"
            reason = "blank earliest_safe_replay_date comment"
        if is_proxy:
            audit_status = "FAIL"
            reason = "proxy appeared in trade-candidate watchlist"
        if audit_status != "FAIL":
            if date_gate:
                output.append(f"{ticker} # canonical_current_ticker={canonical};historical_ticker={historical};earliest_safe_replay_date={date_gate}")
            else:
                output.append(ticker)
        rows.append(
            {
                "line_number": line_number,
                "raw_line": raw_line,
                "ticker": ticker,
                "canonical_current_ticker": canonical,
                "historical_ticker": historical,
                "is_trade_candidate": not is_proxy and audit_status != "FAIL",
                "is_proxy_only": is_proxy,
                "dynamic_earliest_safe_replay_date": date_gate,
                "alias_status": alias_status,
                "comment_parse_status": comment_status,
                "audit_status": audit_status,
                "audit_reason": reason,
            }
        )
    return pd.DataFrame(rows), "\n".join(output) + "\n"


def parse_date_gate(comment: str) -> str:
    for part in comment.replace(";", " ").split():
        if part.startswith("earliest_safe_replay_date="):
            return part.split("=", 1)[1].strip()
    return ""


def build_phase1l_data_readiness_scorecard(symbols: list[str], stooq_smoke: pd.DataFrame, diagnostics: pd.DataFrame, secondary: pd.DataFrame, yahoo: pd.DataFrame, alias_audit: pd.DataFrame, taxonomy: pd.DataFrame, clean_v3: str) -> pd.DataFrame:
    active_count = count_clean_watchlist(clean_v3)
    independent_good = int(secondary["validation_status"].isin(["MATCH", "WARN", "CACHE_ONLY_MATCH", "CACHE_ONLY_WARN"]).sum())
    independent_fail = int(secondary["validation_status"].eq("FAIL").sum())
    coverage = independent_good / max(1, active_count)
    fail_rate = independent_fail / max(1, active_count)
    alias_fail = int(alias_audit["audit_status"].eq("FAIL").sum()) if not alias_audit.empty else 0
    blank_dates = int(((alias_audit["raw_line"].astype(str).str.contains("earliest_safe_replay_date=", regex=False)) & alias_audit["dynamic_earliest_safe_replay_date"].eq("")).sum()) if not alias_audit.empty else 0
    unresolved_alias = int(alias_audit.loc[alias_audit["is_trade_candidate"], "alias_status"].isin(["UNKNOWN", "POSSIBLE_RENAME"]).sum()) if not alias_audit.empty else 0
    tax = taxonomy.set_index("ticker") if not taxonomy.empty else pd.DataFrame()
    clean_tickers = [line.split("#", 1)[0].strip() for line in clean_v3.splitlines() if line.strip() and not line.startswith("#")]
    unresolved_low_taxonomy = int(tax.loc[tax.index.intersection(set(clean_tickers) | PROXY_TICKERS), "confidence"].eq("LOW").sum()) if not tax.empty else 0
    transport_ok = int(yahoo["transport_status"].isin(["TRANSPORT_MATCH", "TRANSPORT_WARN"]).sum()) > 0 if not yahoo.empty else False
    diagnostics_clear = int(diagnostics["detected_payload_type"].isin(["UNKNOWN"]).sum()) == 0 if not diagnostics.empty else False
    stooq_pass = int(stooq_smoke["smoke_status"].eq("PASS").sum())
    if stooq_pass >= 3 and coverage >= 0.90 and fail_rate <= 0.05 and alias_fail == 0 and blank_dates == 0 and unresolved_alias == 0 and unresolved_low_taxonomy == 0:
        status = PHASE_1L_READY_FOR_FROZEN_RETEST_GPT_REVIEW
    elif diagnostics_clear and alias_fail == 0 and blank_dates == 0 and unresolved_alias == 0 and unresolved_low_taxonomy == 0 and transport_ok and stooq_pass == 0:
        status = PHASE_1L_DATA_ADAPTER_READY_VENDOR_MISSING
    else:
        status = PHASE_1L_SECONDARY_VENDOR_BLOCKED
    return pd.DataFrame(
        [
            {
                "total_symbols": int(len(symbols)),
                "active_trade_candidate_count": active_count,
                "proxy_count": int(len(PROXY_TICKERS)),
                "stooq_smoke_pass_count": stooq_pass,
                "stooq_smoke_cache_only_pass_count": int(stooq_smoke["smoke_status"].eq("CACHE_ONLY_PASS").sum()),
                "stooq_payload_parse_error_count": int(diagnostics["parser_status"].eq("PARSE_ERROR").sum()),
                "stooq_html_or_blocked_count": int(diagnostics["parser_status"].eq("HTML_OR_BLOCKED").sum()),
                "independent_secondary_match_count": int(secondary["validation_status"].isin(["MATCH", "CACHE_ONLY_MATCH"]).sum()),
                "independent_secondary_warn_count": int(secondary["validation_status"].isin(["WARN", "CACHE_ONLY_WARN"]).sum()),
                "independent_secondary_fail_count": independent_fail,
                "independent_secondary_coverage_pct": coverage * 100.0,
                "transport_fallback_match_count": int(yahoo["transport_status"].eq("TRANSPORT_MATCH").sum()) if not yahoo.empty else 0,
                "transport_fallback_warn_count": int(yahoo["transport_status"].eq("TRANSPORT_WARN").sum()) if not yahoo.empty else 0,
                "alias_audit_fail_count": alias_fail,
                "blank_date_gate_comment_count": blank_dates,
                "unresolved_alias_count": unresolved_alias,
                "unresolved_low_taxonomy_count": unresolved_low_taxonomy,
                "clean_watchlist_v3_candidate_count": active_count,
                "data_readiness_status": status,
            }
        ]
    )


def count_clean_watchlist(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip() and not line.startswith("#")])


def phase1l_summary_markdown(summary: dict, scorecard: pd.DataFrame, diagnostics: pd.DataFrame, capability: pd.DataFrame, smoke: pd.DataFrame, secondary: pd.DataFrame, yahoo: pd.DataFrame, alias_audit: pd.DataFrame) -> str:
    lines = [
        "PHOENIX NANO PHASE 1L — SECONDARY DATA ADAPTER HARDENING AND VENDOR DECISION GATE",
        "",
        "Historical research and data-readiness remediation only. No strategy retest, paper execution, or real-money execution is approved.",
        "",
        "## Stooq Raw Response Diagnostics",
        str(summary["payload_counts"]),
        "",
        "## Secondary Source Capability Matrix Summary",
        str(summary["capability_counts"]),
        "",
        "## Secondary Vendor Smoke Test V2 Result",
        str(summary["stooq_smoke_counts"]),
        "",
        "## Independent Secondary OHLCV Validation Coverage",
        str(summary["secondary_counts"]),
        "",
        "## Yahoo Chart Transport Fallback Audit Summary",
        str(summary["yahoo_transport_counts"]),
        "",
        "## Alias / Clean Watchlist V3 Audit Result",
        str(summary["alias_audit_counts"]),
        f"- clean_watchlist_v3_candidate_count: {summary['clean_watchlist_v3_count']}",
        "",
        "## Data Readiness Scorecard",
        scorecard.to_markdown(index=False) if not scorecard.empty else "No scorecard row.",
        "",
        f"## Final Phase 1L Status: {summary['phase_1l_status']}",
        "",
        "Strategy research should remain paused unless GPT explicitly reviews and authorizes a future frozen retest.",
        "",
    ]
    return "\n".join(lines)


def write_phase1l_reports(capability, diagnostics, smoke, secondary, yahoo, alias_audit, clean_v3, scorecard, summary_md, paths: dict[str, str | Path]) -> None:
    for path in paths.values():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    capability.to_csv(paths["capability"], index=False)
    diagnostics.to_csv(paths["diagnostics"], index=False, quoting=csv.QUOTE_MINIMAL)
    smoke.to_csv(paths["smoke"], index=False)
    secondary.to_csv(paths["secondary"], index=False)
    yahoo.to_csv(paths["yahoo"], index=False)
    alias_audit.to_csv(paths["alias_audit"], index=False)
    Path(paths["clean_watchlist"]).write_text(clean_v3, encoding="utf-8")
    scorecard.to_csv(paths["scorecard"], index=False)
    Path(paths["summary"]).write_text(summary_md, encoding="utf-8")
