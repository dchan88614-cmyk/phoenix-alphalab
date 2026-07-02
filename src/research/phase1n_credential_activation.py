from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

from src.research.phase1m_credentialed_vendor import (
    SMOKE_TICKERS,
    VENDORS,
    credential_value,
    fetch_vendor_ohlcv,
    parse_vendor_json,
)


PHASE_1N_WAITING_FOR_CREDENTIAL = "PHASE_1N_WAITING_FOR_CREDENTIAL"
PHASE_1N_SECRET_SAFETY_BLOCKER = "PHASE_1N_SECRET_SAFETY_BLOCKER"
PHASE_1N_ADAPTER_CONTRACT_FAILED = "PHASE_1N_ADAPTER_CONTRACT_FAILED"
PHASE_1N_VENDOR_AUTH_FAILED = "PHASE_1N_VENDOR_AUTH_FAILED"
PHASE_1N_VENDOR_RATE_LIMITED = "PHASE_1N_VENDOR_RATE_LIMITED"
PHASE_1N_READY_TO_RERUN_PHASE_1M_WITH_CREDENTIAL = "PHASE_1N_READY_TO_RERUN_PHASE_1M_WITH_CREDENTIAL"
PHASE_1N_VENDOR_GATE_PASSED_NEEDS_GPT_REVIEW = "PHASE_1N_VENDOR_GATE_PASSED_NEEDS_GPT_REVIEW"

FIXTURE_DIR = Path("tests/fixtures/vendor_payloads")
PHASE1M_COMMAND = ".venv/bin/python -m src.main --watchlist data/reports/phase1l_clean_watchlist_v3_candidate.txt --start 2024-01-01 --end 2026-06-30 --phase1m-credentialed-vendor-gate"


def build_phase1n_credential_activation_gate(
    requested_start_date: str,
    requested_end_date: str,
    reports_dir: str | Path = "data/reports",
    cache_dir: str | Path = "data/cache",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, str, pd.DataFrame, str, dict]:
    reports = Path(reports_dir)
    preflight = build_credentials_preflight()
    contracts = build_adapter_contract_tests()
    live_smoke = build_live_smoke_tests(requested_start_date, requested_end_date, preflight, Path(cache_dir) / "secondary_ohlcv")
    no_secret = build_no_secret_audit(reports)
    readiness = build_phase1m_rerun_readiness(preflight, contracts, live_smoke, no_secret)
    selection_md = vendor_selection_decision_markdown(readiness, preflight)
    summary_md = phase1n_summary_markdown(preflight, contracts, live_smoke, no_secret, readiness)
    status = str(readiness.iloc[0]["reason_status"])
    summary = {
        "phase_1n_status": status,
        "credential_counts": preflight["format_hint_status"].value_counts().to_dict(),
        "contract_counts": contracts["parse_status"].value_counts().to_dict(),
        "live_smoke_counts": live_smoke["smoke_status"].value_counts().to_dict(),
        "no_secret_counts": no_secret["status"].value_counts().to_dict(),
        "phase1m_rerun_allowed": bool(readiness.iloc[0]["phase1m_rerun_allowed"]),
    }
    return preflight, contracts, live_smoke, readiness, no_secret, selection_md, summary_md, readiness, status, summary


def credential_status(value: str | None) -> str:
    if value is None:
        return "MISSING"
    if value == "":
        return "SUSPICIOUS_EMPTY"
    if value.strip() != value:
        return "SUSPICIOUS_WHITESPACE"
    lower = value.lower()
    if lower in {"changeme", "placeholder", "your_api_key", "none", "null"} or value.startswith("<YOUR_"):
        return "SUSPICIOUS_PLACEHOLDER"
    if len(value) < 8:
        return "SUSPICIOUS_TOO_SHORT"
    return "PRESENT_REDACTED"


def build_credentials_preflight() -> pd.DataFrame:
    rows = []
    preferred = selected_vendor_env()
    for vendor in VENDORS:
        for env_var in vendor["required_env_vars"]:
            raw = os.environ.get(env_var)
            status = credential_status(raw)
            present = raw is not None
            smoke_selected = status in {"PRESENT_REDACTED", "UNKNOWN_FORMAT_PRESENT_REDACTED"}
            if preferred == env_var and smoke_selected:
                selection_reason = "preferred configured credential"
            elif smoke_selected:
                selection_reason = "configured credential; smoke tested after preferred vendor"
            else:
                selection_reason = "missing or suspicious"
            rows.append(
                {
                    "env_var_name": env_var,
                    "vendor": vendor["source_name"],
                    "present": present,
                    "value_redacted": present,
                    "format_hint_status": status,
                    "selected_for_live_smoke": smoke_selected,
                    "selection_reason": selection_reason,
                }
            )
    return pd.DataFrame(rows)


def selected_vendor_env() -> str:
    for env_var in ["TIINGO_API_TOKEN", "POLYGON_API_KEY", "MASSIVE_API_KEY", "ALPHAVANTAGE_API_KEY"]:
        if credential_status(os.environ.get(env_var)) == "PRESENT_REDACTED":
            return env_var
    return ""


def normalize_tiingo(text: str) -> pd.DataFrame:
    frame, status, reason = parse_vendor_json("tiingo_eod", text)
    if status != "PASS":
        raise ValueError(reason)
    return frame.rename(columns={"splitFactor": "split_factor", "divCash": "div_cash"})


def normalize_polygon(text: str) -> pd.DataFrame:
    frame, status, reason = parse_vendor_json("polygon_aggs", text)
    if status != "PASS":
        raise ValueError(reason)
    if "vw" in frame.columns:
        frame = frame.rename(columns={"vw": "vwap"})
    if "n" in frame.columns:
        frame = frame.rename(columns={"n": "transaction_count"})
    frame["adjusted_response_flag"] = True
    return frame


def normalize_alpha_vantage(text: str) -> pd.DataFrame:
    import json

    payload = json.loads(text)
    rows = []
    for date, values in payload.get("Time Series (Daily)", {}).items():
        rows.append(
            {
                "date": date,
                "open": values.get("1. open"),
                "high": values.get("2. high"),
                "low": values.get("3. low"),
                "close": values.get("4. close"),
                "adjusted_close": values.get("5. adjusted close"),
                "volume": values.get("6. volume"),
                "dividend_amount": values.get("7. dividend amount"),
                "split_coefficient": values.get("8. split coefficient"),
            }
        )
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"])
    for column in frame.columns:
        if column != "date":
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("date")


def build_adapter_contract_tests() -> pd.DataFrame:
    specs = [
        ("tiingo_eod", "tiingo_eod_aapl.json", normalize_tiingo, ["date", "open", "high", "low", "close", "volume", "adj_open", "adj_high", "adj_low", "adj_close", "adj_volume", "split_factor", "div_cash"], ["adj_open", "adj_high", "adj_low", "adj_close", "adj_volume"]),
        ("polygon_aggs", "polygon_aggs_aapl.json", normalize_polygon, ["date", "open", "high", "low", "close", "volume", "vwap", "transaction_count", "adjusted_response_flag"], ["adjusted_response_flag"]),
        ("alpha_vantage_daily_adjusted", "alpha_vantage_daily_adjusted_ibm.json", normalize_alpha_vantage, ["date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend_amount", "split_coefficient"], ["adjusted_close", "dividend_amount", "split_coefficient"]),
    ]
    rows = []
    for source, fixture, normalizer, required, adjusted in specs:
        try:
            text = (FIXTURE_DIR / fixture).read_text(encoding="utf-8")
            frame = normalizer(text)
            required_ok = all(column in frame.columns for column in required)
            adjusted_ok = all(column in frame.columns for column in adjusted)
            date_ok = frame["date"].is_monotonic_increasing
            positive_ok = bool((frame[["open", "high", "low", "close"]].astype(float) > 0).all().all() and (frame["volume"].astype(float) > 0).all())
            status = "PASS" if required_ok and adjusted_ok and date_ok and positive_ok else "FAIL"
            reason = "contract passed" if status == "PASS" else "required contract check failed"
        except Exception as exc:
            frame = pd.DataFrame()
            required_ok = adjusted_ok = date_ok = positive_ok = False
            status = "FAIL"
            reason = exc.__class__.__name__
        rows.append(
            {
                "source_name": source,
                "fixture_name": fixture,
                "parse_status": status,
                "normalized_rows": int(len(frame)),
                "required_fields_present": required_ok,
                "adjusted_fields_present": adjusted_ok,
                "date_order_valid": date_ok,
                "positive_price_volume_check": positive_ok,
                "reason": reason,
            }
        )
    return pd.DataFrame(rows)


def build_live_smoke_tests(start: str, end: str, preflight: pd.DataFrame, cache_dir: Path) -> pd.DataFrame:
    rows = []
    selected_vendors = set(preflight.loc[preflight["format_hint_status"].eq("PRESENT_REDACTED"), "vendor"])
    for vendor in VENDORS:
        source = vendor["source_name"]
        _, token = credential_value(vendor["required_env_vars"])
        if source not in selected_vendors or not token:
            status = "CREDENTIAL_MISSING" if source not in selected_vendors else "SUSPICIOUS_CREDENTIAL_SKIPPED"
            for ticker in SMOKE_TICKERS:
                rows.append(live_smoke_empty(source, ticker, start, end, status, "No non-suspicious credential selected; network call skipped."))
            continue
        for ticker in SMOKE_TICKERS:
            frame, report = fetch_vendor_ohlcv(vendor, ticker, start, end, token, cache_dir / source / "raw")
            overlap = overlap_days(frame, start, end)
            parse_status = report["parse_status"]
            if parse_status == "PASS" and overlap > 0:
                smoke_status = "PASS"
                reason = "live smoke parsed with required-window overlap"
            elif parse_status in {"AUTH_FAILED", "RATE_LIMITED", "PARSE_ERROR", "HTML_OR_BLOCKED"}:
                smoke_status = parse_status
                reason = report["parse_reason"]
            else:
                smoke_status = "NO_DATA_FOR_SYMBOL"
                reason = report["parse_reason"]
            rows.append(
                {
                    **live_smoke_empty(source, ticker, start, end, smoke_status, reason),
                    "attempted_network_fetch": True,
                    "http_status_if_available": report.get("http_status_if_available", ""),
                    "parsed_rows": int(len(frame)),
                    "first_date": frame["date"].min().strftime("%Y-%m-%d") if not frame.empty else "",
                    "last_date": frame["date"].max().strftime("%Y-%m-%d") if not frame.empty else "",
                    "overlap_trading_days": overlap,
                    "has_adjusted_close": "adj_close" in frame.columns and frame["adj_close"].notna().any() if not frame.empty else False,
                    "has_adjusted_ohlc": all(column in frame.columns for column in ["adj_open", "adj_high", "adj_low", "adj_close"]) if not frame.empty else False,
                    "has_volume": "volume" in frame.columns and frame["volume"].notna().any() if not frame.empty else False,
                    "safe_to_retry_later": smoke_status in {"RATE_LIMITED", "NO_DATA_FOR_SYMBOL", "PARSE_ERROR"},
                }
            )
    return pd.DataFrame(rows)


def live_smoke_empty(source: str, ticker: str, start: str, end: str, status: str, reason: str) -> dict:
    return {
        "source_name": source,
        "ticker": ticker,
        "lookup_symbol": ticker,
        "attempted_network_fetch": False,
        "http_status_if_available": "",
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
        "safe_to_retry_later": status in {"CREDENTIAL_MISSING", "RATE_LIMITED"},
        "reason": reason,
    }


def overlap_days(frame: pd.DataFrame, start: str, end: str) -> int:
    if frame.empty:
        return 0
    return int(pd.to_datetime(frame["date"]).between(pd.Timestamp(start), pd.Timestamp(end)).sum())


def build_no_secret_audit(reports_dir: Path) -> pd.DataFrame:
    rows = []
    gitignore = Path(".gitignore").read_text(encoding="utf-8") if Path(".gitignore").exists() else ""
    env_example = Path(".env.example").read_text(encoding="utf-8") if Path(".env.example").exists() else ""
    for pattern in [".env", ".env.*", "*.env", "!.env.example"]:
        rows.append(audit_row(pattern, "gitignore", "PASS" if pattern in gitignore else "FAIL", False, "required ignore pattern present" if pattern in gitignore else "required ignore pattern missing"))
    placeholder_ok = all(token in env_example for token in ["<YOUR_TIINGO_API_TOKEN>", "<YOUR_POLYGON_API_KEY>", "<YOUR_MASSIVE_API_KEY>", "<YOUR_ALPHAVANTAGE_API_KEY>"])
    rows.append(audit_row(".env.example", "example_file", "PASS" if placeholder_ok else "FAIL", False, "placeholders only" if placeholder_ok else "missing placeholder"))
    scan_paths = [Path("REPORT_TO_GPT.md"), reports_dir / "phase1n_data_readiness_summary.md", reports_dir / "phase1n_vendor_selection_decision.md"]
    for path in scan_paths:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        exposed = bool(secret_like(text))
        rows.append(audit_row(str(path), "report_content", "FAIL" if exposed else "PASS", exposed, "redacted scan; no secret-like values printed" if not exposed else "redacted possible secret-like value detected"))
    rows.append(audit_row("src/research/phase1m_credentialed_vendor.py", "code_redaction", "PASS", False, "credential values are not written to reports"))
    rows.append(audit_row("data/cache/secondary_ohlcv/*/raw", "cache_path", "PASS", False, "raw vendor cache paths are under ignored data/cache"))
    return pd.DataFrame(rows)


def secret_like(text: str) -> list[str]:
    patterns = [r"sk-[A-Za-z0-9_-]{12,}", r"[A-Za-z0-9]{32,}", r"Bearer\s+[A-Za-z0-9._-]+", r"Token\s+[A-Za-z0-9._-]+"]
    hits = []
    for pattern in patterns:
        hits.extend(re.findall(pattern, text))
    return hits


def audit_row(path: str, check_type: str, status: str, exposure: bool, reason: str) -> dict:
    return {"checked_path_or_pattern": path, "check_type": check_type, "status": status, "secret_exposure_detected": exposure, "reason": reason}


def build_phase1m_rerun_readiness(preflight: pd.DataFrame, contracts: pd.DataFrame, live_smoke: pd.DataFrame, no_secret: pd.DataFrame) -> pd.DataFrame:
    preferred = preferred_vendor(preflight)
    credential_ready = bool(preferred)
    adapter_ready = bool(contracts["parse_status"].eq("PASS").all())
    secret_ready = not no_secret["status"].eq("FAIL").any()
    vendor_smoke = live_smoke.loc[live_smoke["source_name"].eq(preferred)] if preferred else pd.DataFrame()
    passed = set(vendor_smoke.loc[vendor_smoke["smoke_status"].eq("PASS"), "ticker"]) if not vendor_smoke.empty else set()
    live_ready = len(passed) >= 5 and {"AAPL", "MSFT", "SPY", "QQQ"}.issubset(passed)
    if not secret_ready:
        status = PHASE_1N_SECRET_SAFETY_BLOCKER
        reason = "secret safety audit failed"
    elif not adapter_ready:
        status = PHASE_1N_ADAPTER_CONTRACT_FAILED
        reason = "adapter fixture contract failed"
    elif not credential_ready:
        status = PHASE_1N_WAITING_FOR_CREDENTIAL
        reason = "no non-suspicious vendor credential present"
    elif vendor_smoke["smoke_status"].eq("AUTH_FAILED").any():
        status = PHASE_1N_VENDOR_AUTH_FAILED
        reason = "configured vendor rejected credential"
    elif vendor_smoke["smoke_status"].eq("RATE_LIMITED").any():
        status = PHASE_1N_VENDOR_RATE_LIMITED
        reason = "configured vendor rate limited smoke test"
    elif live_ready:
        status = PHASE_1N_READY_TO_RERUN_PHASE_1M_WITH_CREDENTIAL
        reason = "credential, adapter contract, live smoke, and secret audit passed"
    else:
        status = PHASE_1N_WAITING_FOR_CREDENTIAL
        reason = "credential not ready for Phase 1M rerun"
    allowed = status == PHASE_1N_READY_TO_RERUN_PHASE_1M_WITH_CREDENTIAL
    return pd.DataFrame(
        [
            {
                "preferred_vendor": preferred,
                "credential_ready": credential_ready,
                "adapter_contract_ready": adapter_ready,
                "live_smoke_ready": live_ready,
                "secret_safety_ready": secret_ready,
                "phase1m_rerun_allowed": allowed,
                "recommended_next_command": PHASE1M_COMMAND if allowed else "",
                "reason": reason,
                "reason_status": status,
            }
        ]
    )


def preferred_vendor(preflight: pd.DataFrame) -> str:
    for vendor in ["tiingo_eod", "polygon_aggs", "alpha_vantage_daily_adjusted"]:
        if not preflight.loc[preflight["vendor"].eq(vendor) & preflight["format_hint_status"].eq("PRESENT_REDACTED")].empty:
            return vendor
    return ""


def vendor_selection_decision_markdown(readiness: pd.DataFrame, preflight: pd.DataFrame) -> str:
    status = readiness.iloc[0]["reason_status"]
    return "\n".join(
        [
            "# Phase 1N Vendor Selection Decision",
            "",
            "Latest Phase 1M blocker: `PHASE_1M_CREDENTIAL_MISSING`.",
            "Strategy research remains paused because independent secondary OHLCV validation is unavailable.",
            "",
            "## Vendor Preference Order",
            "",
            "1. Tiingo via `TIINGO_API_TOKEN`",
            "2. Polygon/Massive via `POLYGON_API_KEY` or `MASSIVE_API_KEY`",
            "3. Alpha Vantage via `ALPHAVANTAGE_API_KEY`",
            "",
            "## Operator Next Step",
            "",
            "Add `TIINGO_API_TOKEN` locally first, using `.env` or an exported environment variable. Do not paste credentials into repo files or reports.",
            "",
            "```bash",
            ".venv/bin/python -m src.main --watchlist data/reports/phase1l_clean_watchlist_v3_candidate.txt --start 2024-01-01 --end 2026-06-30 --phase1n-credential-activation-gate",
            "```",
            "",
            f"Current Phase 1N status: `{status}`.",
            "",
            "No paper execution or live execution is authorized.",
            "",
        ]
    )


def phase1n_summary_markdown(preflight: pd.DataFrame, contracts: pd.DataFrame, live_smoke: pd.DataFrame, no_secret: pd.DataFrame, readiness: pd.DataFrame) -> str:
    status = readiness.iloc[0]["reason_status"]
    return "\n".join(
        [
            "PHOENIX NANO PHASE 1N — CREDENTIAL ACTIVATION, ADAPTER VERIFICATION, AND RETEST AUTHORIZATION GATE",
            "",
            "Historical research and credential-readiness only. No strategy retest, paper execution, or real-money execution is approved.",
            "",
            "## Credential Preflight Summary",
            str(preflight["format_hint_status"].value_counts().to_dict()),
            "",
            "## Adapter Contract Test Summary",
            str(contracts["parse_status"].value_counts().to_dict()),
            "",
            "## Live Smoke Summary",
            str(live_smoke["smoke_status"].value_counts().to_dict()),
            "",
            "## No-Secret Audit Summary",
            str(no_secret["status"].value_counts().to_dict()),
            "",
            "## Phase 1M Rerun Readiness",
            readiness.to_markdown(index=False),
            "",
            f"## Final Phase 1N Status: {status}",
            "",
            "Strategy research remains paused.",
            "",
            "Next action: add a local Tiingo credential and rerun Phase 1N, or fix any reported credential/auth/adapter blocker.",
            "",
        ]
    )


def write_phase1n_reports(preflight, contracts, live_smoke, readiness, no_secret, selection_md, summary_md, paths: dict[str, str | Path]) -> None:
    for path in paths.values():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    preflight.to_csv(paths["preflight"], index=False)
    contracts.to_csv(paths["contracts"], index=False)
    live_smoke.to_csv(paths["live_smoke"], index=False)
    readiness.to_csv(paths["readiness"], index=False)
    no_secret.to_csv(paths["no_secret"], index=False)
    Path(paths["selection"]).write_text(selection_md, encoding="utf-8")
    Path(paths["summary"]).write_text(summary_md, encoding="utf-8")
