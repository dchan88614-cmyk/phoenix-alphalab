# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1M — Credentialed Independent Vendor Integration and Data Readiness Gate

This task is **historical research and data-readiness remediation only**.

Do not start Phase 2.
Do not start Phase 3.
Do not enable paper execution.
Do not enable real-money execution.
Do not change daily scan production behavior.
Do not loosen Candidate 34 thresholds.
Do not adopt Candidate 35, Phase 1H overlays, or any universe variant as active policy.
Do not create Candidate 36 entry rules.
Do not run a strategy threshold sweep.
Do not run a Candidate 34 vs Candidate 35 retest in this task.
Do not produce financial advice or an operational recommendation.

## Why This Task

Phase 1L completed implementation but ended as:

`PHASE_1L_DATA_ADAPTER_READY_VENDOR_MISSING`

Latest Phase 1L evidence:

- tests passed: `182 passed, 1 warning`
- Stooq raw diagnostics: `HTML_BLOCK`: 12, `PARSE_ERROR`: 0
- Stooq smoke test v2: AAPL, MSFT, SPY, and QQQ all failed with `HTML_OR_BLOCKED`
- secondary source capability matrix: `stooq_daily_csv` = `GLOBAL_UNAVAILABLE`; `yahoo_chart_api` = `TRANSPORT_FALLBACK_ONLY`
- independent secondary OHLCV validation coverage: `0.0%`
- Yahoo Chart transport fallback matched 23 sampled rows, but it is Yahoo-family and cannot count as independent validation
- alias / clean watchlist v3 audit passed: 99 active trade candidates, 2 proxy symbols, 0 blank date-gate comments, 0 unresolved aliases, 0 unresolved low taxonomy rows
- clean watchlist v3 is still research-only and not approved for daily scan, paper execution, or live execution

This means the next optimized step is **not strategy testing**. The highest-priority issue is to add a real independent secondary OHLCV vendor path that can work with credentials supplied through environment variables, while still completing cleanly when credentials are absent.

The research system must answer:

1. Is at least one credentialed independent vendor configured and reachable?
2. Does the configured vendor return adjusted daily OHLCV with enough overlap for the Phase 1 research window?
3. Does the vendor validate yfinance primary data closely enough on price and volume?
4. Does the vendor cover enough of the Phase 1L clean watchlist v3 to support a future frozen Candidate 34 vs Candidate 35 retest?
5. If no credentials are present, can the repo clearly report `CREDENTIAL_MISSING` without failing tests or pretending validation passed?

Do not use realized future returns, realized PnL, holdout performance, prior winning/losing status, or strategy outcomes to make vendor, alias, or watchlist inclusion decisions.

## Goal

Build Phase 1M credentialed vendor integration scaffolding and a formal independent vendor readiness gate.

The goal is to produce one of these statuses:

- `PHASE_1M_CREDENTIAL_MISSING`
- `PHASE_1M_VENDOR_CONFIG_ERROR`
- `PHASE_1M_VENDOR_REACHABLE_COVERAGE_INSUFFICIENT`
- `PHASE_1M_VENDOR_REACHABLE_VALIDATION_FAILED`
- `PHASE_1M_READY_FOR_FROZEN_RETEST_GPT_REVIEW`

Even if Phase 1M passes, do **not** run the frozen Candidate 34 vs Candidate 35 retest in this task. Passing Phase 1M may only recommend that GPT review and separately authorize a frozen retest.

## Candidate Vendors

Implement a pluggable vendor layer. Do not hardcode credentials. Do not commit secrets. Redact secrets in logs and reports.

At minimum support these providers as capability entries:

1. `tiingo_eod`
   - independent of Yahoo/yfinance
   - requires `TIINGO_API_TOKEN`
   - supports daily EOD prices and adjusted fields
   - preferred first credentialed vendor because it exposes explicit adjusted OHLCV fields and ticker metadata
2. `polygon_aggs`
   - independent of Yahoo/yfinance
   - requires `POLYGON_API_KEY` or `MASSIVE_API_KEY`
   - supports stock aggregate OHLCV bars with an adjusted parameter
   - note that available history may depend on account plan
3. `alpha_vantage_daily_adjusted`
   - independent of Yahoo/yfinance
   - requires `ALPHAVANTAGE_API_KEY`
   - supports adjusted daily time series, but may be premium / rate limited
   - use only if configured and reachable; never let rate limits masquerade as data failure
4. `stooq_daily_csv`
   - no secret, independent, but currently blocked in this environment
   - carry forward Phase 1L status as `GLOBAL_UNAVAILABLE_PREVIOUSLY_CONFIRMED`
5. `yahoo_chart_api`
   - same vendor family as yfinance / Yahoo-derived primary data
   - transport fallback only
   - must **not** count as independent secondary vendor validation

If additional vendors are added, they must be explicit in the capability matrix with `requires_secret`, `is_independent_of_primary_vendor`, licensing / rate-limit notes, and whether they are allowed for execution-grade validation.

## CLI

Add or update:

```bash
--phase1m-credentialed-vendor-gate
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist data/reports/phase1l_clean_watchlist_v3_candidate.txt --start 2024-01-01 --end 2026-06-30 --phase1m-credentialed-vendor-gate
```

The command must complete when credentials are missing. Missing credentials should produce explicit `CREDENTIAL_MISSING` rows and a non-ready final status, not a crash.

## Required Outputs

Create or update:

- `data/reports/phase1m_vendor_capability_matrix.csv`
- `data/reports/phase1m_credentials_status.csv`
- `data/reports/phase1m_vendor_smoke_tests.csv`
- `data/reports/phase1m_secondary_ohlcv_validation.csv`
- `data/reports/phase1m_coverage_by_symbol.csv`
- `data/reports/phase1m_adjustment_consistency_audit.csv`
- `data/reports/phase1m_rate_limit_and_error_audit.csv`
- `data/reports/phase1m_clean_watchlist_v4_candidate.txt`
- `data/reports/phase1m_data_readiness_scorecard.csv`
- `data/reports/phase1m_data_readiness_summary.md`
- `REPORT_TO_GPT.md`

Optional but preferred if useful:

- `data/cache/secondary_ohlcv/tiingo_eod/raw/`
- `data/cache/secondary_ohlcv/polygon_aggs/raw/`
- `data/cache/secondary_ohlcv/alpha_vantage/raw/`
- `data/cache/secondary_ohlcv/vendor_gate/`

Keep earlier Phase 1 reports intact unless regeneration is required.

The summary must start with:

```text
PHOENIX NANO PHASE 1M — CREDENTIALED INDEPENDENT VENDOR INTEGRATION AND DATA READINESS GATE
```

## Inputs

Reuse Phase 1L outputs:

- `data/reports/phase1l_secondary_source_capability_matrix.csv`
- `data/reports/phase1l_raw_response_diagnostics.csv`
- `data/reports/phase1l_secondary_vendor_smoke_test_v2.csv`
- `data/reports/phase1l_secondary_ohlcv_validation_v3.csv`
- `data/reports/phase1l_yahoo_chart_transport_fallback_audit.csv`
- `data/reports/phase1l_alias_clean_watchlist_audit.csv`
- `data/reports/phase1l_clean_watchlist_v3_candidate.txt`
- `data/reports/phase1l_data_readiness_scorecard.csv`
- `data/reports/phase1l_data_readiness_summary.md`

Also reuse Phase 1J / Phase 1K outputs where helpful:

- `data/reports/phase1j_symbol_master.csv`
- `data/reports/phase1j_quarantine_list.csv`
- `data/reports/phase1k_symbol_lifecycle_alias_map.csv`
- `data/reports/phase1k_taxonomy_resolution_v2.csv`
- `data/reports/phase1k_quarantine_remediation_audit.csv`

## Part 1: Vendor Capability Matrix

Create `phase1m_vendor_capability_matrix.csv`.

For each candidate vendor/adapter, report:

- `source_name`
- `source_family`
- `adapter_name`
- `requires_secret`
- `required_env_vars`
- `credential_present`
- `is_independent_of_primary_vendor`
- `allowed_for_execution_grade_secondary_validation`
- `allowed_for_transport_fallback_only`
- `supports_adjusted_ohlcv`
- `supports_split_or_dividend_metadata`
- `network_fetch_attempted`
- `cache_supported`
- `expected_format`
- `known_limitations`
- `capability_status`: `CREDENTIAL_MISSING`, `CANDIDATE`, `SMOKE_PASS`, `SMOKE_FAIL`, `GLOBAL_UNAVAILABLE`, `RATE_LIMITED`, `TRANSPORT_FALLBACK_ONLY`, `NOT_ALLOWED_REQUIRES_SECRET`, `CONFIG_ERROR`
- `decision_reason`

Rules:

- If credentials are missing, do not attempt authenticated network calls for that vendor.
- If credentials are present, smoke-test the vendor.
- Do not print or store the actual credential value.
- Do not count Yahoo Chart as independent validation.
- Keep Stooq as blocked unless the implementation explicitly rechecks it and obtains real CSV rows.

## Part 2: Credentials Status

Create `phase1m_credentials_status.csv`.

For each env var, report:

- `env_var_name`
- `vendor`
- `present`: True / False
- `value_redacted`: always True if present
- `format_hint_status`: `PRESENT_REDACTED`, `MISSING`, `SUSPICIOUS_EMPTY`, `SUSPICIOUS_PLACEHOLDER`
- `used_in_network_call`: True / False

Do not store credential lengths if that might leak useful information. Do not store prefixes or suffixes.

## Part 3: Vendor Smoke Tests

Create `phase1m_vendor_smoke_tests.csv`.

Smoke-test these symbols for every configured independent vendor:

- `AAPL`
- `MSFT`
- `SPY`
- `QQQ`
- `SQ`
- `GEV`
- `RDDT`

For each row, report:

- `source_name`
- `ticker`
- `lookup_symbol`
- `attempted_network_fetch`
- `used_cache_fallback`
- `http_status_if_available`
- `response_bytes`
- `parsed_rows`
- `first_date`
- `last_date`
- `required_start_date`
- `required_end_date`
- `overlap_trading_days`
- `has_adjusted_close`
- `has_adjusted_ohlc`
- `has_volume`
- `smoke_status`: `PASS`, `CACHE_ONLY_PASS`, `CREDENTIAL_MISSING`, `NO_DATA_FOR_SYMBOL`, `RATE_LIMITED`, `AUTH_FAILED`, `PARSE_ERROR`, `HTML_OR_BLOCKED`, `FAIL`
- `smoke_reason`

Vendor-level smoke pass:

- `SMOKE_PASS` if at least 5 of 7 smoke tickers parse with positive rows and positive overlap, including at least AAPL, MSFT, SPY, and QQQ.
- `RATE_LIMITED` if the vendor is reachable but rejects due to quota/rate constraints.
- `AUTH_FAILED` if credentials are present but rejected.
- `CREDENTIAL_MISSING` if no credential is present.

## Part 4: Full Secondary OHLCV Validation

Create `phase1m_secondary_ohlcv_validation.csv`.

Only run this for vendors whose smoke status is `SMOKE_PASS`.

Validate all Phase 1L clean watchlist v3 active trade candidates plus SPY/QQQ proxies where the vendor has data.

For each ticker/vendor, report:

- `ticker`
- `canonical_current_ticker`
- `historical_ticker`
- `is_proxy_only`
- `primary_vendor`
- `secondary_vendor`
- `secondary_source_family`
- `is_independent_secondary`
- `lookup_symbol`
- `primary_start_date`
- `primary_end_date`
- `secondary_start_date`
- `secondary_end_date`
- `overlap_trading_days`
- `overlap_pct_of_required_window`
- `close_price_median_abs_diff_pct`
- `close_price_p95_abs_diff_pct`
- `close_price_max_abs_diff_pct`
- `volume_median_abs_diff_pct`
- `volume_p95_abs_diff_pct`
- `volume_max_abs_diff_pct`
- `adjusted_close_available_primary`
- `adjusted_close_available_secondary`
- `adjusted_ohlc_available_secondary`
- `adjusted_price_mismatch_flag`
- `split_or_corporate_action_mismatch_flag`
- `validation_status`: `MATCH`, `WARN`, `FAIL`, `NO_SECONDARY_DATA`, `RATE_LIMITED`, `AUTH_FAILED`, `CREDENTIAL_MISSING`, `NOT_RUN_SMOKE_FAILED`
- `validation_reason`

Validation thresholds:

- `MATCH` if overlap is sufficient and adjusted close median absolute difference is <= 0.50% and p95 absolute difference is <= 2.00%, unless a split/corporate-action mismatch is detected.
- `WARN` if median difference is <= 1.00% and p95 difference is <= 5.00%, or if volume differs materially but price validates.
- `FAIL` if price differences exceed warning thresholds, overlap is too small, or corporate-action mismatch is suspected.

Do not force exact volume matches across vendors; volume methodology may differ. Treat volume as diagnostic, not the primary pass/fail criterion.

## Part 5: Coverage by Symbol

Create `phase1m_coverage_by_symbol.csv`.

For every Phase 1L clean watchlist v3 symbol and proxy, report:

- `ticker`
- `canonical_current_ticker`
- `is_trade_candidate`
- `is_proxy_only`
- `covered_by_any_independent_vendor`
- `best_independent_vendor`
- `best_validation_status`
- `has_required_window_coverage`
- `coverage_start_date`
- `coverage_end_date`
- `coverage_reason`

Generate `phase1m_clean_watchlist_v4_candidate.txt` only from symbols that are alias-safe and data-validated or explicitly data-warn but acceptable for future GPT review. This is still research-only and must not replace production watchlists.

## Part 6: Adjustment Consistency Audit

Create `phase1m_adjustment_consistency_audit.csv`.

Focus on split / corporate-action prone tickers and recent IPO/spinoff/date-gated names:

- `NVDA`
- `AVGO`
- `GEV`
- `RDDT`
- `SQ`
- `XYZ` if the vendor requires current ticker alias testing
- `CORZ`
- `SMCI`
- any ticker flagged by validation as adjustment mismatch

Report:

- `ticker`
- `event_or_reason_checked`
- `primary_adjusted_close_behavior`
- `secondary_adjusted_close_behavior`
- `detected_mismatch`
- `recommended_replay_handling`: `OK`, `DATE_GATE`, `EXCLUDE`, `MANUAL_REVIEW`
- `reason`

## Part 7: Rate Limit and Error Audit

Create `phase1m_rate_limit_and_error_audit.csv`.

For every failed or skipped vendor request, report:

- `source_name`
- `ticker`
- `error_type`: `CREDENTIAL_MISSING`, `AUTH_FAILED`, `RATE_LIMITED`, `HTTP_ERROR`, `NETWORK_ERROR`, `PARSE_ERROR`, `NO_DATA`, `CACHE_ONLY`, `UNKNOWN`
- `http_status_if_available`
- `retry_after_if_available`
- `safe_to_retry_later`
- `counts_against_vendor_readiness`
- `reason`

## Part 8: Data Readiness Scorecard

Create `phase1m_data_readiness_scorecard.csv` with at least:

- `total_symbols`
- `active_trade_candidate_count`
- `proxy_count`
- `configured_independent_vendor_count`
- `credential_missing_vendor_count`
- `auth_failed_vendor_count`
- `smoke_pass_vendor_count`
- `independent_secondary_match_count`
- `independent_secondary_warn_count`
- `independent_secondary_fail_count`
- `independent_secondary_coverage_pct`
- `active_trade_candidate_coverage_pct`
- `proxy_coverage_pct`
- `adjustment_mismatch_count`
- `rate_limited_request_count`
- `alias_audit_fail_count`
- `blank_date_gate_comment_count`
- `unresolved_alias_count`
- `clean_watchlist_v4_candidate_count`
- `data_readiness_status`

Readiness gates:

- At least one independent credentialed vendor must have `SMOKE_PASS`.
- AAPL, MSFT, SPY, and QQQ must all pass smoke.
- Independent secondary coverage must be >= 90% of active trade candidates.
- SPY and QQQ proxy coverage must be 100%.
- Independent secondary `FAIL` rows must be <= 5% of validated active trade candidates.
- `adjustment_mismatch_count` must be 0 for symbols included in clean watchlist v4.
- `alias_audit_fail_count` must be 0.
- `blank_date_gate_comment_count` must be 0.
- `unresolved_alias_count` must be 0.
- Rate limiting must not prevent coverage scoring.

If all gates pass, final status may be:

`PHASE_1M_READY_FOR_FROZEN_RETEST_GPT_REVIEW`

Otherwise choose the most specific non-ready status.

## REPORT_TO_GPT.md Requirements

Update `REPORT_TO_GPT.md` with:

- files changed
- commands run
- test results
- whether credentials were present, without exposing secrets
- vendor capability summary
- smoke-test summary
- independent secondary coverage summary
- adjustment consistency summary
- clean watchlist v4 candidate count
- final Phase 1M status
- explicit statement that no Phase 2, paper execution, or live execution was started
- clear recommendation for GPT:
  - add credentials and rerun Phase 1M,
  - fix vendor adapter bugs,
  - or authorize a separate frozen Candidate 34 vs Candidate 35 retest only if gates pass

## Acceptance Criteria

- All tests pass.
- The Phase 1M CLI completes with and without credentials.
- Missing credentials are reported cleanly.
- No secrets are printed, cached, committed, or exposed in reports.
- Yahoo Chart remains transport fallback only.
- Stooq remains blocked unless real CSV rows are obtained.
- No strategy retest is run.
- No production daily scan behavior changes are made.
- No paper or live trading path is enabled.
- `REPORT_TO_GPT.md` gives GPT a concrete next decision.

## Stop Conditions

Stop and report blockers if:

- credential handling would risk leaking secrets,
- a vendor's license/rate-limit behavior cannot be represented safely,
- no vendor credentials are present,
- all configured vendors fail auth or smoke tests,
- rate limits prevent meaningful coverage scoring,
- adjusted price semantics cannot be normalized.

These stop conditions should not fail the test suite; they should produce explicit non-ready statuses.
