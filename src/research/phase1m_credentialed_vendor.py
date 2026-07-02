from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from src.research.phase1j_data_readiness import pct, watchlist_symbols_with_lines
from src.research.phase1l_secondary_adapter import PROXY_TICKERS, count_clean_watchlist


PHASE_1M_CREDENTIAL_MISSING = "PHASE_1M_CREDENTIAL_MISSING"
PHASE_1M_VENDOR_CONFIG_ERROR = "PHASE_1M_VENDOR_CONFIG_ERROR"
PHASE_1M_VENDOR_REACHABLE_COVERAGE_INSUFFICIENT = "PHASE_1M_VENDOR_REACHABLE_COVERAGE_INSUFFICIENT"
PHASE_1M_VENDOR_REACHABLE_VALIDATION_FAILED = "PHASE_1M_VENDOR_REACHABLE_VALIDATION_FAILED"
PHASE_1M_READY_FOR_FROZEN_RETEST_GPT_REVIEW = "PHASE_1M_READY_FOR_FROZEN_RETEST_GPT_REVIEW"

SMOKE_TICKERS = ["AAPL", "MSFT", "SPY", "QQQ", "SQ", "GEV", "RDDT"]
ADJUSTMENT_FOCUS = ["NVDA", "AVGO", "GEV", "RDDT", "SQ", "XYZ", "CORZ", "SMCI"]

VENDORS = [
    {
        "source_name": "tiingo_eod",
        "source_family": "tiingo",
        "adapter_name": "tiingo_eod_daily_prices",
        "required_env_vars": ["TIINGO_API_TOKEN"],
        "supports_adjusted_ohlcv": True,
        "supports_split_or_dividend_metadata": True,
        "expected_format": "JSON daily prices with adjOpen/adjHigh/adjLow/adjClose/adjVolume",
        "known_limitations": "Requires Tiingo token; symbol coverage and rate limits depend on account.",
    },
    {
        "source_name": "polygon_aggs",
        "source_family": "polygon",
        "adapter_name": "polygon_v2_aggs_adjusted",
        "required_env_vars": ["POLYGON_API_KEY", "MASSIVE_API_KEY"],
        "supports_adjusted_ohlcv": True,
        "supports_split_or_dividend_metadata": False,
        "expected_format": "JSON aggregate bars with adjusted=true",
        "known_limitations": "Requires Polygon/Massive key; available history depends on plan.",
    },
    {
        "source_name": "alpha_vantage_daily_adjusted",
        "source_family": "alpha_vantage",
        "adapter_name": "alpha_vantage_time_series_daily_adjusted",
        "required_env_vars": ["ALPHAVANTAGE_API_KEY"],
        "supports_adjusted_ohlcv": True,
        "supports_split_or_dividend_metadata": True,
        "expected_format": "JSON Time Series Daily adjusted",
        "known_limitations": "Requires key; rate limited and some adjusted endpoints may be premium.",
    },
]


def build_phase1m_credentialed_vendor_gate(
    data: pd.DataFrame,
    watchlist_path: str | Path | None,
    watchlist_tickers: list[str],
    requested_start_date: str,
    requested_end_date: str,
    reports_dir: str | Path = "data/reports",
    cache_dir: str | Path = "data/cache",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, pd.DataFrame, str, dict]:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    reports = Path(reports_dir)
    cache = Path(cache_dir)
    symbols = sorted(set([item["ticker"] for item in watchlist_symbols_with_lines(watchlist_path, watchlist_tickers)] + list(PROXY_TICKERS)))
    lifecycle = read_csv(reports / "phase1k_symbol_lifecycle_alias_map.csv")
    alias_audit = read_csv(reports / "phase1l_alias_clean_watchlist_audit.csv")
    clean_v3 = Path(watchlist_path).read_text(encoding="utf-8") if watchlist_path and Path(watchlist_path).exists() else read_text(reports / "phase1l_clean_watchlist_v3_candidate.txt")
    credentials = build_credentials_status()
    capability = build_vendor_capability_matrix(credentials)
    smoke, errors, vendor_status = build_vendor_smoke_tests(requested_start_date, requested_end_date, credentials, cache / "secondary_ohlcv")
    capability = update_capabilities_from_smoke(capability, vendor_status)
    secondary = build_secondary_validation(frame, symbols, lifecycle, vendor_status, requested_start_date, requested_end_date, credentials, cache / "secondary_ohlcv")
    coverage = build_coverage_by_symbol(symbols, lifecycle, secondary)
    adjustment = build_adjustment_consistency_audit(frame, secondary)
    errors = pd.concat([errors, build_error_audit_from_validation(secondary)], ignore_index=True)
    clean_v4 = build_clean_watchlist_v4(clean_v3, coverage, alias_audit)
    scorecard = build_phase1m_scorecard(symbols, credentials, capability, smoke, secondary, coverage, adjustment, errors, alias_audit, clean_v4)
    summary = {
        "phase_1m_status": str(scorecard.iloc[0]["data_readiness_status"]) if not scorecard.empty else PHASE_1M_CREDENTIAL_MISSING,
        "credential_counts": credentials["format_hint_status"].value_counts().to_dict(),
        "capability_counts": capability["capability_status"].value_counts().to_dict(),
        "smoke_counts": smoke["smoke_status"].value_counts().to_dict(),
        "validation_counts": secondary["validation_status"].value_counts().to_dict(),
        "coverage_count": int(coverage["covered_by_any_independent_vendor"].sum()) if not coverage.empty else 0,
        "adjustment_mismatch_count": int(adjustment["detected_mismatch"].sum()) if not adjustment.empty else 0,
        "clean_watchlist_v4_count": count_clean_watchlist(clean_v4),
    }
    summary_md = phase1m_summary_markdown(summary, scorecard)
    return capability, credentials, smoke, secondary, coverage, adjustment, errors, scorecard, clean_v4, summary_md, summary


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def credential_value(env_vars: list[str]) -> tuple[str, str]:
    for env_var in env_vars:
        value = os.environ.get(env_var, "")
        if value and value.strip() and value.strip().lower() not in {"changeme", "placeholder", "your_api_key", "none", "null"}:
            return env_var, value.strip()
    return "", ""


def build_credentials_status() -> pd.DataFrame:
    rows = []
    for vendor in VENDORS:
        chosen, _ = credential_value(vendor["required_env_vars"])
        for env_var in vendor["required_env_vars"]:
            raw = os.environ.get(env_var)
            present = bool(raw and raw.strip())
            if not present:
                status = "MISSING"
            elif raw.strip().lower() in {"changeme", "placeholder", "your_api_key", "none", "null"}:
                status = "SUSPICIOUS_PLACEHOLDER"
            elif not raw.strip():
                status = "SUSPICIOUS_EMPTY"
            else:
                status = "PRESENT_REDACTED"
            rows.append(
                {
                    "env_var_name": env_var,
                    "vendor": vendor["source_name"],
                    "present": present,
                    "value_redacted": bool(present),
                    "format_hint_status": status,
                    "used_in_network_call": env_var == chosen,
                }
            )
    return pd.DataFrame(rows)


def build_vendor_capability_matrix(credentials: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for vendor in VENDORS:
        present = credentials.loc[credentials["vendor"].eq(vendor["source_name"]) & credentials["format_hint_status"].eq("PRESENT_REDACTED")]
        credential_present = not present.empty
        rows.append(
            {
                "source_name": vendor["source_name"],
                "source_family": vendor["source_family"],
                "adapter_name": vendor["adapter_name"],
                "requires_secret": True,
                "required_env_vars": ",".join(vendor["required_env_vars"]),
                "credential_present": credential_present,
                "is_independent_of_primary_vendor": True,
                "allowed_for_execution_grade_secondary_validation": credential_present,
                "allowed_for_transport_fallback_only": False,
                "supports_adjusted_ohlcv": vendor["supports_adjusted_ohlcv"],
                "supports_split_or_dividend_metadata": vendor["supports_split_or_dividend_metadata"],
                "network_fetch_attempted": False,
                "cache_supported": True,
                "expected_format": vendor["expected_format"],
                "known_limitations": vendor["known_limitations"],
                "capability_status": "CANDIDATE" if credential_present else "CREDENTIAL_MISSING",
                "decision_reason": "Credential present; smoke test required." if credential_present else "Required credential is missing; authenticated calls skipped.",
            }
        )
    rows.extend(
        [
            {
                "source_name": "stooq_daily_csv",
                "source_family": "stooq",
                "adapter_name": "stooq_daily_csv_v2",
                "requires_secret": False,
                "required_env_vars": "",
                "credential_present": False,
                "is_independent_of_primary_vendor": True,
                "allowed_for_execution_grade_secondary_validation": False,
                "allowed_for_transport_fallback_only": False,
                "supports_adjusted_ohlcv": False,
                "supports_split_or_dividend_metadata": False,
                "network_fetch_attempted": False,
                "cache_supported": True,
                "expected_format": "CSV OHLCV",
                "known_limitations": "Phase 1L confirmed HTML/browser-verification block in this environment.",
                "capability_status": "GLOBAL_UNAVAILABLE",
                "decision_reason": "GLOBAL_UNAVAILABLE_PREVIOUSLY_CONFIRMED",
            },
            {
                "source_name": "yahoo_chart_api",
                "source_family": "yahoo",
                "adapter_name": "yahoo_chart_transport_audit",
                "requires_secret": False,
                "required_env_vars": "",
                "credential_present": False,
                "is_independent_of_primary_vendor": False,
                "allowed_for_execution_grade_secondary_validation": False,
                "allowed_for_transport_fallback_only": True,
                "supports_adjusted_ohlcv": True,
                "supports_split_or_dividend_metadata": False,
                "network_fetch_attempted": False,
                "cache_supported": True,
                "expected_format": "JSON chart OHLCV",
                "known_limitations": "Same vendor family as yfinance primary; transport fallback only.",
                "capability_status": "TRANSPORT_FALLBACK_ONLY",
                "decision_reason": "Not independent of primary vendor.",
            },
        ]
    )
    return pd.DataFrame(rows)


def build_vendor_smoke_tests(start: str, end: str, credentials: pd.DataFrame, cache_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    rows = []
    errors = []
    vendor_status = {}
    for vendor in VENDORS:
        source = vendor["source_name"]
        chosen, token = credential_value(vendor["required_env_vars"])
        vendor_rows = []
        if not token:
            for ticker in SMOKE_TICKERS:
                row = empty_smoke_row(source, ticker, start, end, "CREDENTIAL_MISSING", "Required credential missing; network call skipped.")
                rows.append(row)
                vendor_rows.append(row)
                errors.append(error_row(source, ticker, "CREDENTIAL_MISSING", "", "", False, True, "Required credential missing."))
            vendor_status[source] = "CREDENTIAL_MISSING"
            continue
        for ticker in SMOKE_TICKERS:
            frame, report = fetch_vendor_ohlcv(vendor, ticker, start, end, token, cache_dir / source / "raw")
            row = smoke_row_from_fetch(source, ticker, frame, report, start, end)
            rows.append(row)
            vendor_rows.append(row)
            if row["smoke_status"] != "PASS":
                errors.append(error_row(source, ticker, row["smoke_status"], report.get("http_status_if_available", ""), report.get("retry_after_if_available", ""), True, True, row["smoke_reason"]))
        vendor_status[source] = vendor_smoke_status(pd.DataFrame(vendor_rows))
    return pd.DataFrame(rows), pd.DataFrame(errors), vendor_status


def empty_smoke_row(source: str, ticker: str, start: str, end: str, status: str, reason: str) -> dict:
    return {
        "source_name": source,
        "ticker": ticker,
        "lookup_symbol": ticker,
        "attempted_network_fetch": False,
        "used_cache_fallback": False,
        "http_status_if_available": "",
        "response_bytes": 0,
        "parsed_rows": 0,
        "first_date": "",
        "last_date": "",
        "required_start_date": start,
        "required_end_date": end,
        "overlap_trading_days": 0,
        "has_adjusted_close": False,
        "has_adjusted_ohlc": False,
        "has_volume": False,
        "smoke_status": status,
        "smoke_reason": reason,
    }


def fetch_vendor_ohlcv(vendor: dict, ticker: str, start: str, end: str, token: str, raw_dir: Path) -> tuple[pd.DataFrame, dict]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    source = vendor["source_name"]
    if source == "tiingo_eod":
        url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices?startDate={start}&endDate={end}&format=json"
        headers = {"Authorization": f"Token {token}"}
    elif source == "polygon_aggs":
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={token}"
        headers = {}
    else:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&outputsize=full&apikey={token}"
        headers = {}
    raw = fetch_json_text(url, raw_dir / f"{ticker}.json", headers)
    frame, parse_status, parse_reason = parse_vendor_json(source, raw["text"])
    report = {**raw, "parse_status": parse_status, "parse_reason": parse_reason}
    return frame, report


def fetch_json_text(url: str, cache_path: Path, headers: dict) -> dict:
    safe_headers = {key: value for key, value in headers.items()}
    text = ""
    http_status = ""
    retry_after = ""
    used_cache = False
    exception_class = ""
    try:
        request = urllib.request.Request(url, headers=safe_headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            http_status = str(getattr(response, "status", ""))
            retry_after = response.headers.get("Retry-After", "")
            raw = response.read()
        text = raw.decode("utf-8", errors="replace")
        if text:
            cache_path.write_text(text, encoding="utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        exception_class = exc.__class__.__name__
        http_status = str(getattr(exc, "code", ""))
        retry_after = getattr(getattr(exc, "headers", {}), "get", lambda key, default="": default)("Retry-After", "")
        if cache_path.exists():
            text = cache_path.read_text(encoding="utf-8")
            used_cache = True
    return {
        "text": text,
        "http_status_if_available": http_status,
        "retry_after_if_available": retry_after,
        "used_cache_fallback": used_cache,
        "attempted_network_fetch": True,
        "response_bytes": len(text.encode("utf-8")),
        "exception_class_if_any": exception_class,
    }


def parse_vendor_json(source: str, text: str) -> tuple[pd.DataFrame, str, str]:
    if not text:
        return pd.DataFrame(), "NO_DATA_FOR_SYMBOL", "Empty response."
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        if "<html" in text.lower():
            return pd.DataFrame(), "HTML_OR_BLOCKED", "HTML response."
        return pd.DataFrame(), "PARSE_ERROR", "JSON parse error."
    if source == "tiingo_eod":
        if isinstance(payload, dict) and payload.get("detail"):
            return pd.DataFrame(), auth_or_rate_status(str(payload.get("detail"))), str(payload.get("detail"))
        rows = payload if isinstance(payload, list) else []
        frame = pd.DataFrame(rows)
        if frame.empty:
            return pd.DataFrame(), "NO_DATA_FOR_SYMBOL", "No Tiingo rows."
        rename = {"adjClose": "adj_close", "adjOpen": "adj_open", "adjHigh": "adj_high", "adjLow": "adj_low", "adjVolume": "adj_volume"}
        frame = frame.rename(columns=rename)
    elif source == "polygon_aggs":
        status = str(payload.get("status", ""))
        if status.upper() in {"ERROR", "AUTH_ERROR"}:
            return pd.DataFrame(), auth_or_rate_status(str(payload)), str(payload)[:160]
        frame = pd.DataFrame(payload.get("results", []))
        if frame.empty:
            return pd.DataFrame(), "NO_DATA_FOR_SYMBOL", "No Polygon results."
        frame = frame.rename(columns={"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        frame["date"] = pd.to_datetime(frame["timestamp"], unit="ms").dt.normalize()
        frame["adj_close"] = frame["close"]
    else:
        note = " ".join(str(payload.get(key, "")) for key in ["Note", "Information", "Error Message"])
        if note:
            return pd.DataFrame(), auth_or_rate_status(note), note[:160]
        series = payload.get("Time Series (Daily)", {})
        rows = []
        for date, values in series.items():
            rows.append(
                {
                    "date": date,
                    "open": values.get("1. open"),
                    "high": values.get("2. high"),
                    "low": values.get("3. low"),
                    "close": values.get("4. close"),
                    "adj_close": values.get("5. adjusted close"),
                    "volume": values.get("6. volume"),
                }
            )
        frame = pd.DataFrame(rows)
        if frame.empty:
            return pd.DataFrame(), "NO_DATA_FOR_SYMBOL", "No Alpha Vantage rows."
    if "date" not in frame.columns:
        return pd.DataFrame(), "PARSE_ERROR", "Missing date column."
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    for column in ["open", "high", "low", "close", "adj_close", "adj_open", "adj_high", "adj_low", "volume"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["date"]).sort_values("date")
    return frame, "PASS", ""


def auth_or_rate_status(message: str) -> str:
    lower = message.lower()
    if "rate" in lower or "limit" in lower or "premium" in lower or "thank you for using alpha vantage" in lower:
        return "RATE_LIMITED"
    if "auth" in lower or "token" in lower or "api key" in lower or "forbidden" in lower:
        return "AUTH_FAILED"
    return "FAIL"


def smoke_row_from_fetch(source: str, ticker: str, frame: pd.DataFrame, report: dict, start: str, end: str) -> dict:
    overlap = overlap_days(frame, start, end)
    parse_status = report["parse_status"]
    if parse_status == "PASS" and overlap > 0:
        status = "CACHE_ONLY_PASS" if report["used_cache_fallback"] else "PASS"
        reason = "Parsed adjusted daily OHLCV with required-window overlap."
    elif parse_status in {"RATE_LIMITED", "AUTH_FAILED", "HTML_OR_BLOCKED", "PARSE_ERROR"}:
        status = parse_status
        reason = report["parse_reason"]
    else:
        status = "NO_DATA_FOR_SYMBOL"
        reason = report["parse_reason"]
    return {
        "source_name": source,
        "ticker": ticker,
        "lookup_symbol": ticker,
        "attempted_network_fetch": report["attempted_network_fetch"],
        "used_cache_fallback": report["used_cache_fallback"],
        "http_status_if_available": report["http_status_if_available"],
        "response_bytes": report["response_bytes"],
        "parsed_rows": int(len(frame)),
        "first_date": frame["date"].min().strftime("%Y-%m-%d") if not frame.empty else "",
        "last_date": frame["date"].max().strftime("%Y-%m-%d") if not frame.empty else "",
        "required_start_date": start,
        "required_end_date": end,
        "overlap_trading_days": overlap,
        "has_adjusted_close": "adj_close" in frame.columns and frame["adj_close"].notna().any() if not frame.empty else False,
        "has_adjusted_ohlc": all(column in frame.columns for column in ["adj_open", "adj_high", "adj_low", "adj_close"]) if not frame.empty else False,
        "has_volume": "volume" in frame.columns and frame["volume"].notna().any() if not frame.empty else False,
        "smoke_status": status,
        "smoke_reason": reason,
    }


def vendor_smoke_status(rows: pd.DataFrame) -> str:
    if rows.empty:
        return "CREDENTIAL_MISSING"
    if rows["smoke_status"].eq("CREDENTIAL_MISSING").all():
        return "CREDENTIAL_MISSING"
    if rows["smoke_status"].eq("AUTH_FAILED").any():
        return "AUTH_FAILED"
    if rows["smoke_status"].eq("RATE_LIMITED").any():
        return "RATE_LIMITED"
    required = {"AAPL", "MSFT", "SPY", "QQQ"}
    passed = set(rows.loc[rows["smoke_status"].isin(["PASS", "CACHE_ONLY_PASS"]), "ticker"])
    return "SMOKE_PASS" if len(passed) >= 5 and required.issubset(passed) else "SMOKE_FAIL"


def update_capabilities_from_smoke(capability: pd.DataFrame, vendor_status: dict[str, str]) -> pd.DataFrame:
    frame = capability.copy()
    for source, status in vendor_status.items():
        frame.loc[frame["source_name"].eq(source), "capability_status"] = status
        frame.loc[frame["source_name"].eq(source), "network_fetch_attempted"] = status != "CREDENTIAL_MISSING"
        frame.loc[frame["source_name"].eq(source), "allowed_for_execution_grade_secondary_validation"] = status == "SMOKE_PASS"
        frame.loc[frame["source_name"].eq(source), "decision_reason"] = f"Vendor smoke status: {status}."
    return frame


def overlap_days(frame: pd.DataFrame, start: str, end: str) -> int:
    if frame.empty:
        return 0
    return int(pd.to_datetime(frame["date"]).between(pd.Timestamp(start), pd.Timestamp(end)).sum())


def lifecycle_lookup(lifecycle: pd.DataFrame) -> dict:
    return lifecycle.set_index("original_watchlist_ticker").to_dict("index") if not lifecycle.empty else {}


def build_secondary_validation(data: pd.DataFrame, symbols: list[str], lifecycle: pd.DataFrame, vendor_status: dict[str, str], start: str, end: str, credentials: pd.DataFrame, cache_dir: Path) -> pd.DataFrame:
    rows = []
    life = lifecycle_lookup(lifecycle)
    runnable = [vendor for vendor in VENDORS if vendor_status.get(vendor["source_name"]) == "SMOKE_PASS"]
    if not runnable:
        status = "CREDENTIAL_MISSING" if all(vendor_status.get(v["source_name"]) == "CREDENTIAL_MISSING" for v in VENDORS) else "NOT_RUN_SMOKE_FAILED"
        for ticker in symbols:
            rows.append(empty_validation_row(ticker, life.get(ticker, {}), data, status, "No credentialed independent vendor passed smoke."))
        return pd.DataFrame(rows)
    for vendor in runnable:
        _, token = credential_value(vendor["required_env_vars"])
        for ticker in symbols:
            frame, report = fetch_vendor_ohlcv(vendor, ticker, start, end, token, cache_dir / vendor["source_name"] / "raw")
            rows.append(compare_secondary(ticker, vendor, life.get(ticker, {}), data, frame, report))
    return pd.DataFrame(rows)


def empty_validation_row(ticker: str, life: dict, data: pd.DataFrame, status: str, reason: str) -> dict:
    primary = data.loc[data["ticker"].eq(ticker)].copy()
    return {
        "ticker": ticker,
        "canonical_current_ticker": life.get("canonical_current_ticker", ticker),
        "historical_ticker": life.get("historical_ticker", ticker),
        "is_proxy_only": ticker in PROXY_TICKERS,
        "primary_vendor": "yfinance",
        "secondary_vendor": "",
        "secondary_source_family": "",
        "is_independent_secondary": True,
        "lookup_symbol": ticker,
        "primary_start_date": primary["date"].min().strftime("%Y-%m-%d") if not primary.empty else "",
        "primary_end_date": primary["date"].max().strftime("%Y-%m-%d") if not primary.empty else "",
        "secondary_start_date": "",
        "secondary_end_date": "",
        "overlap_trading_days": 0,
        "overlap_pct_of_required_window": 0.0,
        "close_price_median_abs_diff_pct": pd.NA,
        "close_price_p95_abs_diff_pct": pd.NA,
        "close_price_max_abs_diff_pct": pd.NA,
        "volume_median_abs_diff_pct": pd.NA,
        "volume_p95_abs_diff_pct": pd.NA,
        "volume_max_abs_diff_pct": pd.NA,
        "adjusted_close_available_primary": "adj_close" in primary.columns and primary["adj_close"].notna().any() if not primary.empty else False,
        "adjusted_close_available_secondary": False,
        "adjusted_ohlc_available_secondary": False,
        "adjusted_price_mismatch_flag": pd.NA,
        "split_or_corporate_action_mismatch_flag": pd.NA,
        "validation_status": status,
        "validation_reason": reason,
    }


def compare_secondary(ticker: str, vendor: dict, life: dict, data: pd.DataFrame, secondary: pd.DataFrame, report: dict) -> dict:
    primary = data.loc[data["ticker"].eq(ticker)].copy()
    if report["parse_status"] != "PASS":
        return empty_validation_row(ticker, life, data, report["parse_status"], report["parse_reason"])
    base = empty_validation_row(ticker, life, data, "NO_SECONDARY_DATA", "")
    base.update({"secondary_vendor": vendor["source_name"], "secondary_source_family": vendor["source_family"]})
    if primary.empty or secondary.empty:
        base["validation_reason"] = "Primary or secondary data missing."
        return base
    secondary_price_col = "adj_close" if "adj_close" in secondary.columns and secondary["adj_close"].notna().any() else "close"
    merged = primary[["date", "adj_close", "close", "volume"]].merge(secondary[["date", secondary_price_col, "volume"]], on="date", suffixes=("_primary", "_secondary"))
    if merged.empty:
        base["validation_status"] = "FAIL"
        base["validation_reason"] = "No overlapping trading days."
        return base
    primary_adj_col = "adj_close_primary" if "adj_close_primary" in merged.columns else "adj_close"
    primary_close_col = "close_primary" if "close_primary" in merged.columns else "close"
    secondary_col = f"{secondary_price_col}_secondary" if f"{secondary_price_col}_secondary" in merged.columns else secondary_price_col
    primary_price = pd.to_numeric(merged[primary_adj_col], errors="coerce").fillna(pd.to_numeric(merged[primary_close_col], errors="coerce"))
    secondary_price = pd.to_numeric(merged[secondary_col], errors="coerce")
    close_diff = (primary_price / secondary_price - 1).abs().dropna()
    volume_diff = (pd.to_numeric(merged["volume_primary"], errors="coerce") / pd.to_numeric(merged["volume_secondary"], errors="coerce").replace(0, pd.NA) - 1).abs().dropna()
    if close_diff.empty:
        status = "FAIL"
        reason = "Could not compute adjusted price differences."
    else:
        median = float(close_diff.median())
        p95 = float(close_diff.quantile(0.95))
        if median <= 0.005 and p95 <= 0.02:
            status = "MATCH"
            reason = "Adjusted close differences within MATCH thresholds."
        elif median <= 0.01 and p95 <= 0.05:
            status = "WARN"
            reason = "Adjusted close differences within WARN thresholds."
        else:
            status = "FAIL"
            reason = "Adjusted close differences exceed WARN thresholds."
    base.update(
        {
            "secondary_start_date": secondary["date"].min().strftime("%Y-%m-%d"),
            "secondary_end_date": secondary["date"].max().strftime("%Y-%m-%d"),
            "overlap_trading_days": int(len(merged)),
            "overlap_pct_of_required_window": len(merged) / max(1, primary["date"].nunique()) * 100.0,
            "close_price_median_abs_diff_pct": pct(close_diff.median()) if not close_diff.empty else pd.NA,
            "close_price_p95_abs_diff_pct": pct(close_diff.quantile(0.95)) if not close_diff.empty else pd.NA,
            "close_price_max_abs_diff_pct": pct(close_diff.max()) if not close_diff.empty else pd.NA,
            "volume_median_abs_diff_pct": pct(volume_diff.median()) if not volume_diff.empty else pd.NA,
            "volume_p95_abs_diff_pct": pct(volume_diff.quantile(0.95)) if not volume_diff.empty else pd.NA,
            "volume_max_abs_diff_pct": pct(volume_diff.max()) if not volume_diff.empty else pd.NA,
            "adjusted_close_available_secondary": secondary_price_col == "adj_close",
            "adjusted_ohlc_available_secondary": all(column in secondary.columns for column in ["adj_open", "adj_high", "adj_low", "adj_close"]),
            "adjusted_price_mismatch_flag": status == "FAIL",
            "split_or_corporate_action_mismatch_flag": bool(not close_diff.empty and float(close_diff.max()) > 0.10),
            "validation_status": status,
            "validation_reason": reason,
        }
    )
    return base


def build_coverage_by_symbol(symbols: list[str], lifecycle: pd.DataFrame, secondary: pd.DataFrame) -> pd.DataFrame:
    life = lifecycle_lookup(lifecycle)
    rows = []
    for ticker in symbols:
        rows_for_ticker = secondary.loc[secondary["ticker"].eq(ticker)]
        good = rows_for_ticker.loc[rows_for_ticker["validation_status"].isin(["MATCH", "WARN"])]
        best = good.iloc[0].to_dict() if not good.empty else (rows_for_ticker.iloc[0].to_dict() if not rows_for_ticker.empty else {})
        rows.append(
            {
                "ticker": ticker,
                "canonical_current_ticker": life.get(ticker, {}).get("canonical_current_ticker", ticker),
                "is_trade_candidate": ticker not in PROXY_TICKERS,
                "is_proxy_only": ticker in PROXY_TICKERS,
                "covered_by_any_independent_vendor": not good.empty,
                "best_independent_vendor": best.get("secondary_vendor", ""),
                "best_validation_status": best.get("validation_status", ""),
                "has_required_window_coverage": bool(best.get("overlap_pct_of_required_window", 0) >= 90),
                "coverage_start_date": best.get("secondary_start_date", ""),
                "coverage_end_date": best.get("secondary_end_date", ""),
                "coverage_reason": "Validated by independent vendor." if not good.empty else best.get("validation_reason", "No validation row."),
            }
        )
    return pd.DataFrame(rows)


def build_adjustment_consistency_audit(data: pd.DataFrame, secondary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    mismatch_tickers = secondary.loc[secondary["split_or_corporate_action_mismatch_flag"].eq(True), "ticker"].tolist() if "split_or_corporate_action_mismatch_flag" in secondary.columns else []
    for ticker in sorted(set(ADJUSTMENT_FOCUS + mismatch_tickers)):
        row = secondary.loc[secondary["ticker"].eq(ticker)].head(1)
        mismatch = bool(not row.empty and row.iloc[0].get("split_or_corporate_action_mismatch_flag") is True)
        primary_adj_available = bool("adj_close" in data.columns and data.loc[data["ticker"].eq(ticker), "adj_close"].notna().any())
        rows.append(
            {
                "ticker": ticker,
                "event_or_reason_checked": "split_or_corporate_action_or_date_gated_focus",
                "primary_adjusted_close_behavior": "adj_close_available" if primary_adj_available else "not_available",
                "secondary_adjusted_close_behavior": "available" if not row.empty and bool(row.iloc[0].get("adjusted_close_available_secondary", False)) else "not_validated",
                "detected_mismatch": mismatch,
                "recommended_replay_handling": "MANUAL_REVIEW" if mismatch else ("DATE_GATE" if ticker in {"GEV", "RDDT", "SQ", "XYZ"} else "OK"),
                "reason": "No independent validation row; retain conservative handling." if row.empty or row.iloc[0].get("validation_status") not in {"MATCH", "WARN"} else "Independent adjusted price validation available.",
            }
        )
    return pd.DataFrame(rows)


def build_error_audit_from_validation(secondary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in secondary.loc[~secondary["validation_status"].isin(["MATCH", "WARN"])].iterrows():
        status = row["validation_status"]
        rows.append(error_row(row.get("secondary_vendor", ""), row["ticker"], status, "", "", status not in {"CREDENTIAL_MISSING"}, status != "NO_SECONDARY_DATA", row["validation_reason"]))
    return pd.DataFrame(rows)


def error_row(source: str, ticker: str, error_type: str, http_status: str, retry_after: str, safe_retry: bool, counts: bool, reason: str) -> dict:
    mapping = {
        "CREDENTIAL_MISSING": "CREDENTIAL_MISSING",
        "AUTH_FAILED": "AUTH_FAILED",
        "RATE_LIMITED": "RATE_LIMITED",
        "PARSE_ERROR": "PARSE_ERROR",
        "NO_DATA_FOR_SYMBOL": "NO_DATA",
        "NO_SECONDARY_DATA": "NO_DATA",
        "HTML_OR_BLOCKED": "HTTP_ERROR",
    }
    return {
        "source_name": source,
        "ticker": ticker,
        "error_type": mapping.get(error_type, error_type if error_type in {"HTTP_ERROR", "NETWORK_ERROR", "CACHE_ONLY", "UNKNOWN"} else "UNKNOWN"),
        "http_status_if_available": http_status,
        "retry_after_if_available": retry_after,
        "safe_to_retry_later": safe_retry,
        "counts_against_vendor_readiness": counts,
        "reason": reason,
    }


def build_clean_watchlist_v4(clean_v3: str, coverage: pd.DataFrame, alias_audit: pd.DataFrame) -> str:
    coverage_map = coverage.set_index("ticker").to_dict("index") if not coverage.empty else {}
    alias_map = alias_audit.set_index("ticker").to_dict("index") if not alias_audit.empty else {}
    lines = [
        "# Phase 1M research-only clean watchlist v4 candidate.",
        "# Not approved for daily scan, paper execution, or real-money execution.",
        "# Requires GPT review; generated from symbols with independent vendor MATCH/WARN coverage only.",
    ]
    for raw in clean_v3.splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        ticker = raw.split("#", 1)[0].strip()
        cov = coverage_map.get(ticker, {})
        audit = alias_map.get(ticker, {})
        if cov.get("covered_by_any_independent_vendor") and audit.get("audit_status", "PASS") == "PASS":
            lines.append(raw)
    return "\n".join(lines) + "\n"


def build_phase1m_scorecard(symbols: list[str], credentials: pd.DataFrame, capability: pd.DataFrame, smoke: pd.DataFrame, secondary: pd.DataFrame, coverage: pd.DataFrame, adjustment: pd.DataFrame, errors: pd.DataFrame, alias_audit: pd.DataFrame, clean_v4: str) -> pd.DataFrame:
    active = coverage.loc[coverage["is_trade_candidate"]] if not coverage.empty else pd.DataFrame()
    proxies = coverage.loc[coverage["is_proxy_only"]] if not coverage.empty else pd.DataFrame()
    active_covered = int(active["covered_by_any_independent_vendor"].sum()) if not active.empty else 0
    proxy_covered = int(proxies["covered_by_any_independent_vendor"].sum()) if not proxies.empty else 0
    smoke_pass_vendors = set(capability.loc[capability["capability_status"].eq("SMOKE_PASS"), "source_name"])
    required_smoke = {"AAPL", "MSFT", "SPY", "QQQ"}
    required_smoke_pass = required_smoke.issubset(set(smoke.loc[smoke["smoke_status"].isin(["PASS", "CACHE_ONLY_PASS"]), "ticker"]))
    match_count = int(secondary["validation_status"].eq("MATCH").sum())
    warn_count = int(secondary["validation_status"].eq("WARN").sum())
    fail_count = int(secondary["validation_status"].eq("FAIL").sum())
    active_coverage_pct = active_covered / max(1, len(active)) * 100.0
    proxy_coverage_pct = proxy_covered / max(1, len(proxies)) * 100.0
    mismatch_count = int(adjustment["detected_mismatch"].sum()) if not adjustment.empty else 0
    rate_limited = int(errors["error_type"].eq("RATE_LIMITED").sum()) if not errors.empty else 0
    alias_fail = int(alias_audit["audit_status"].eq("FAIL").sum()) if not alias_audit.empty else 0
    blank_dates = int(((alias_audit["raw_line"].astype(str).str.contains("earliest_safe_replay_date=", regex=False)) & alias_audit["dynamic_earliest_safe_replay_date"].fillna("").eq("")).sum()) if not alias_audit.empty else 0
    unresolved_alias = int(alias_audit.loc[alias_audit["is_trade_candidate"], "alias_status"].isin(["UNKNOWN", "POSSIBLE_RENAME"]).sum()) if not alias_audit.empty else 0
    if capability.loc[capability["source_name"].isin([vendor["source_name"] for vendor in VENDORS]), "capability_status"].eq("CREDENTIAL_MISSING").all():
        status = PHASE_1M_CREDENTIAL_MISSING
    elif int(capability["capability_status"].eq("AUTH_FAILED").sum()) > 0:
        status = PHASE_1M_VENDOR_CONFIG_ERROR
    elif smoke_pass_vendors and required_smoke_pass and active_coverage_pct >= 90 and proxy_coverage_pct == 100 and fail_count / max(1, match_count + warn_count + fail_count) <= 0.05 and mismatch_count == 0 and alias_fail == 0 and blank_dates == 0 and unresolved_alias == 0 and rate_limited == 0:
        status = PHASE_1M_READY_FOR_FROZEN_RETEST_GPT_REVIEW
    elif smoke_pass_vendors:
        status = PHASE_1M_VENDOR_REACHABLE_COVERAGE_INSUFFICIENT
    else:
        status = PHASE_1M_VENDOR_REACHABLE_VALIDATION_FAILED if fail_count else PHASE_1M_VENDOR_REACHABLE_COVERAGE_INSUFFICIENT
    return pd.DataFrame(
        [
            {
                "total_symbols": int(len(symbols)),
                "active_trade_candidate_count": int(len(active)),
                "proxy_count": int(len(proxies)),
                "configured_independent_vendor_count": int(capability.loc[capability["credential_present"] & capability["is_independent_of_primary_vendor"]].shape[0]),
                "credential_missing_vendor_count": int(capability["capability_status"].eq("CREDENTIAL_MISSING").sum()),
                "auth_failed_vendor_count": int(capability["capability_status"].eq("AUTH_FAILED").sum()),
                "smoke_pass_vendor_count": int(len(smoke_pass_vendors)),
                "independent_secondary_match_count": match_count,
                "independent_secondary_warn_count": warn_count,
                "independent_secondary_fail_count": fail_count,
                "independent_secondary_coverage_pct": (match_count + warn_count) / max(1, len(secondary)) * 100.0,
                "active_trade_candidate_coverage_pct": active_coverage_pct,
                "proxy_coverage_pct": proxy_coverage_pct,
                "adjustment_mismatch_count": mismatch_count,
                "rate_limited_request_count": rate_limited,
                "alias_audit_fail_count": alias_fail,
                "blank_date_gate_comment_count": blank_dates,
                "unresolved_alias_count": unresolved_alias,
                "clean_watchlist_v4_candidate_count": count_clean_watchlist(clean_v4),
                "data_readiness_status": status,
            }
        ]
    )


def phase1m_summary_markdown(summary: dict, scorecard: pd.DataFrame) -> str:
    return "\n".join(
        [
            "PHOENIX NANO PHASE 1M — CREDENTIALED INDEPENDENT VENDOR INTEGRATION AND DATA READINESS GATE",
            "",
            "Historical research and data-readiness remediation only. No strategy retest, paper execution, or real-money execution is approved.",
            "",
            "## Credential Status",
            str(summary["credential_counts"]),
            "",
            "## Vendor Capability Summary",
            str(summary["capability_counts"]),
            "",
            "## Smoke Test Summary",
            str(summary["smoke_counts"]),
            "",
            "## Independent Secondary Validation Summary",
            str(summary["validation_counts"]),
            f"- covered symbols: {summary['coverage_count']}",
            "",
            "## Adjustment Consistency Summary",
            f"- adjustment_mismatch_count: {summary['adjustment_mismatch_count']}",
            "",
            "## Clean Watchlist V4 Candidate Count",
            f"- {summary['clean_watchlist_v4_count']}",
            "",
            "## Data Readiness Scorecard",
            scorecard.to_markdown(index=False) if not scorecard.empty else "No scorecard row.",
            "",
            f"## Final Phase 1M Status: {summary['phase_1m_status']}",
            "",
            "Do not start Phase 2, Phase 3, paper execution, live execution, Candidate 36, or any strategy retest.",
            "",
        ]
    )


def write_phase1m_reports(capability, credentials, smoke, secondary, coverage, adjustment, errors, clean_v4, scorecard, summary_md, paths: dict[str, str | Path]) -> None:
    for path in paths.values():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    capability.to_csv(paths["capability"], index=False)
    credentials.to_csv(paths["credentials"], index=False)
    smoke.to_csv(paths["smoke"], index=False)
    secondary.to_csv(paths["secondary"], index=False)
    coverage.to_csv(paths["coverage"], index=False)
    adjustment.to_csv(paths["adjustment"], index=False)
    errors.to_csv(paths["errors"], index=False)
    Path(paths["clean_watchlist"]).write_text(clean_v4, encoding="utf-8")
    scorecard.to_csv(paths["scorecard"], index=False)
    Path(paths["summary"]).write_text(summary_md, encoding="utf-8")
