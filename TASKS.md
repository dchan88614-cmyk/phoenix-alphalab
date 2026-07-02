# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1L — Secondary Data Adapter Hardening and Vendor Decision Gate

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

Phase 1K completed implementation but ended as:

`PHASE_1K_DATA_BLOCKED`

Latest Phase 1K evidence:

- tests passed: `170 passed, 1 warning`
- secondary vendor smoke test: `GLOBAL_SOURCE_UNAVAILABLE`: 4, `PASS`: 0
- secondary OHLCV validation: `GLOBAL_SOURCE_UNAVAILABLE`: 119, `MATCH`: 0
- active trade candidate count: 99
- unresolved alias count: 0
- unresolved low taxonomy count: 0
- Stooq smoke-test rows returned HTTP 200 and 796 bytes for AAPL/MSFT/SPY/QQQ but parsed 0 rows with `_fetch_status=PARSE_ERROR`
- clean watchlist v2 is research-only and contains dynamic-date comments, but `SQ # earliest_safe_replay_date=` is blank and needs alias/watchlist normalization
- final status: `PHASE_1K_DATA_BLOCKED`

This means the next optimized step is **not strategy testing**. The highest-priority issue is to harden the data adapter layer enough to answer:

1. Is Stooq truly globally unavailable, or is the adapter/parser mishandling a nonstandard response?
2. Can any no-secret independent OHLCV source provide usable secondary validation?
3. If no independent source works, can the project at least separate:
   - execution-grade independent vendor validation,
   - same-vendor transport fallback,
   - cache-only research evidence,
   - and no-source blockers?
4. Can the clean watchlist candidate be made alias-safe and date-gated without blank or misleading comments?

Do not use realized future returns, realized PnL, holdout performance, prior winning/losing status, or strategy outcomes to make data-source, alias, or watchlist inclusion decisions.

## Goal

Build Phase 1L data adapter diagnostics and a formal vendor decision gate.

The goal is to produce a clear answer:

- `PHASE_1L_SECONDARY_VENDOR_BLOCKED`
- `PHASE_1L_DATA_ADAPTER_READY_VENDOR_MISSING`
- or `PHASE_1L_READY_FOR_FROZEN_RETEST_GPT_REVIEW`

Even if Phase 1L passes, do **not** run the frozen Candidate 34 vs Candidate 35 retest in this task. Passing Phase 1L may only recommend that GPT review and separately authorize a frozen retest.

## CLI

Add or update:

```bash
--phase1l-secondary-data-adapter-gate
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1l-secondary-data-adapter-gate
```

The command must complete even if all public network sources fail. Do not fake validation. Report explicit statuses.

## Required Outputs

Create or update:

- `data/reports/phase1l_secondary_source_capability_matrix.csv`
- `data/reports/phase1l_raw_response_diagnostics.csv`
- `data/reports/phase1l_secondary_vendor_smoke_test_v2.csv`
- `data/reports/phase1l_secondary_ohlcv_validation_v3.csv`
- `data/reports/phase1l_yahoo_chart_transport_fallback_audit.csv`
- `data/reports/phase1l_alias_clean_watchlist_audit.csv`
- `data/reports/phase1l_clean_watchlist_v3_candidate.txt`
- `data/reports/phase1l_data_readiness_scorecard.csv`
- `data/reports/phase1l_data_readiness_summary.md`
- `REPORT_TO_GPT.md`

Optional but preferred if useful:

- `data/cache/secondary_ohlcv/stooq/raw/`
- `data/cache/secondary_ohlcv/yahoo_chart/raw/`
- `data/cache/secondary_ohlcv/diagnostics/`

Keep earlier Phase 1 reports intact unless regeneration is required.

The summary must start with:

```text
PHOENIX NANO PHASE 1L — SECONDARY DATA ADAPTER HARDENING AND VENDOR DECISION GATE
```

## Inputs

Reuse these Phase 1K outputs:

- `data/reports/phase1k_secondary_vendor_smoke_test.csv`
- `data/reports/phase1k_secondary_ohlcv_validation.csv`
- `data/reports/phase1k_symbol_lifecycle_alias_map.csv`
- `data/reports/phase1k_quarantine_remediation_audit.csv`
- `data/reports/phase1k_taxonomy_resolution_v2.csv`
- `data/reports/phase1k_clean_watchlist_v2_candidate.txt`
- `data/reports/phase1k_data_readiness_scorecard.csv`
- `data/reports/phase1k_data_readiness_summary.md`

Also reuse Phase 1J / Phase 1I incident reports where helpful:

- `data/reports/phase1j_symbol_master.csv`
- `data/reports/phase1j_quarantine_list.csv`
- `data/reports/phase1i_data_gap_incident_log.csv`
- `data/reports/phase1i_symbol_data_quality_audit.csv`

## Part 1: Secondary Source Capability Matrix

Create `phase1l_secondary_source_capability_matrix.csv`.

For each candidate source/adapter, report:

- `source_name`
- `source_family`
- `adapter_name`
- `requires_secret`
- `is_independent_of_primary_vendor`
- `allowed_for_execution_grade_secondary_validation`
- `allowed_for_transport_fallback_only`
- `network_fetch_attempted`
- `cache_supported`
- `expected_format`
- `known_limitations`
- `capability_status`: `CANDIDATE`, `SMOKE_PASS`, `SMOKE_FAIL`, `GLOBAL_UNAVAILABLE`, `NOT_ALLOWED_REQUIRES_SECRET`, `TRANSPORT_FALLBACK_ONLY`
- `decision_reason`

At minimum include:

1. `stooq_daily_csv`
   - no secret
   - independent of yfinance
   - can count as secondary vendor only if smoke test and overlap validation pass
2. `yahoo_chart_api`
   - no secret
   - same vendor family as yfinance / Yahoo-derived primary data
   - may be used only as a transport fallback / extraction sanity check
   - must **not** count as independent secondary vendor validation
3. Any other no-secret source only if it can be implemented without credentials and without scraping terms-unsafe pages.

Do not add key-required vendors unless they are clearly marked `NOT_ALLOWED_REQUIRES_SECRET` and not used.

## Part 2: Raw Response Diagnostics

Create `phase1l_raw_response_diagnostics.csv`.

The Phase 1K Stooq result is suspicious because AAPL/MSFT/SPY/QQQ returned HTTP 200 and 796 bytes but parsed 0 rows. Diagnose this before declaring the source globally unavailable.

For each smoke-test fetch attempt, report:

- `source_name`
- `ticker`
- `lookup_symbol`
- `url_or_cache_key`
- `http_status_if_available`
- `final_url_if_available`
- `content_type_if_available`
- `response_bytes`
- `response_sha256`
- `first_200_chars_sanitized`
- `detected_payload_type`: `CSV_OHLCV`, `CSV_NO_DATA`, `HTML_BLOCK`, `HTML_ERROR`, `TEXT_ERROR`, `EMPTY`, `UNKNOWN`
- `detected_columns`
- `parser_status`: `PASS`, `NO_DATA_FOR_SYMBOL`, `PARSE_ERROR`, `HTML_OR_BLOCKED`, `EMPTY`
- `parser_reason`

Parser hardening requirements:

- Support BOM-prefixed CSV.
- Support comma or semicolon delimiter if detected.
- Support case-insensitive column names for date/open/high/low/close/volume.
- Detect HTML responses explicitly instead of treating them as generic CSV parse errors.
- Detect explicit no-data responses.
- Store successful raw CSV snapshots in cache.
- Do not store credentials or secrets.

## Part 3: Stooq Smoke Test v2

Create `phase1l_secondary_vendor_smoke_test_v2.csv`.

Smoke-test these tickers:

- `AAPL`
- `MSFT`
- `SPY`
- `QQQ`

For Stooq, try a small deterministic lookup-symbol matrix before declaring failure:

- `{ticker_lower}.us`
- `{ticker_upper}.US`
- `{ticker_lower}`

For each attempt, report:

- `source_name`
- `ticker`
- `lookup_symbol`
- `url_or_cache_key`
- `attempted_network_fetch`
- `used_cache_fallback`
- `http_status_if_available`
- `response_bytes`
- `parsed_rows`
- `first_date`
- `last_date`
- `required_start_date`
- `required_end_date`
- `overlap_days_with_required_window`
- `smoke_status`: `PASS`, `CACHE_ONLY_PASS`, `NO_DATA_FOR_SYMBOL`, `GLOBAL_SOURCE_UNAVAILABLE`, `PARSE_ERROR`, `HTML_OR_BLOCKED`, `FAIL`
- `smoke_reason`
- `payload_type`
- `selected_attempt_for_ticker`

Source-level Stooq decision rules:

- `SMOKE_PASS` if at least 3 of 4 smoke tickers parse with positive rows and positive overlap.
- `CACHE_ONLY_PASS` if at least 3 of 4 smoke tickers only pass through cache.
- `GLOBAL_SOURCE_UNAVAILABLE` only if network/cache cannot produce usable data and diagnostics show network/source/blocking problems.
- `PARSER_BUG_SUSPECTED` if HTTP 200 responses exist but parser cannot classify payloads clearly.
- `SMOKE_FAIL` if payloads are valid but the source does not provide required symbols/data.

## Part 4: Yahoo Chart Transport Fallback Audit

Create `phase1l_yahoo_chart_transport_fallback_audit.csv`.

Implement a no-secret Yahoo Chart adapter only as a **same-vendor transport fallback audit**, not as independent secondary validation.

For AAPL/MSFT/SPY/QQQ and a sample of at least 20 active clean-watchlist symbols, report:

- `ticker`
- `source_name`: `yahoo_chart_api`
- `source_family`: `yahoo`
- `is_independent_of_primary_vendor`: `False`
- `network_fetch_attempted`
- `used_cache_fallback`
- `parsed_rows`
- `first_date`
- `last_date`
- `overlap_days_with_primary`
- `close_price_median_abs_diff_pct_vs_primary`
- `volume_median_abs_diff_pct_vs_primary`
- `transport_status`: `TRANSPORT_MATCH`, `TRANSPORT_WARN`, `TRANSPORT_FAIL`, `GLOBAL_SOURCE_UNAVAILABLE`, `NO_DATA_FOR_SYMBOL`
- `reason`

This can help diagnose yfinance extraction/cache problems, but it must never satisfy the independent secondary vendor gate.

## Part 5: Secondary OHLCV Validation v3

Create `phase1l_secondary_ohlcv_validation_v3.csv`.

Run full per-symbol comparison only for sources whose smoke test passes or cache-only passes.

For every watchlist symbol plus SPY/QQQ, report:

- `ticker`
- `primary_vendor`
- `secondary_vendor`
- `secondary_source_family`
- `is_independent_secondary`
- `lookup_symbol`
- `source_global_status`
- `primary_start_date`
- `primary_end_date`
- `secondary_start_date`
- `secondary_end_date`
- `overlap_trading_days`
- `close_price_median_abs_diff_pct`
- `close_price_p95_abs_diff_pct`
- `close_price_max_abs_diff_pct`
- `volume_median_abs_diff_pct`
- `volume_p95_abs_diff_pct`
- `volume_max_abs_diff_pct`
- `adjusted_close_available_primary`
- `adjusted_close_available_secondary`
- `adjusted_price_mismatch_flag`
- `split_or_corporate_action_mismatch_flag`
- `validation_status`: `MATCH`, `WARN`, `FAIL`, `NO_DATA_FOR_SYMBOL`, `GLOBAL_SOURCE_UNAVAILABLE`, `CACHE_ONLY_MATCH`, `CACHE_ONLY_WARN`, `TRANSPORT_ONLY_MATCH`, `TRANSPORT_ONLY_WARN`
- `validation_reason`

Rules:

- Never mark `MATCH` without positive overlap days and computed differences.
- Same-vendor Yahoo Chart checks must be labeled `TRANSPORT_ONLY_*` and must not count as independent validation.
- If Stooq or another independent source is unavailable, mark independent validation blocker clearly.
- Cache-only results must be labeled cache-only and cannot be execution-grade unless GPT later explicitly accepts cache-only research evidence.

## Part 6: Alias and Clean Watchlist v3 Audit

Create:

- `phase1l_alias_clean_watchlist_audit.csv`
- `phase1l_clean_watchlist_v3_candidate.txt`

Audit `phase1k_clean_watchlist_v2_candidate.txt` for alias/date bugs.

At minimum, verify and fix these issues:

1. `SQ # earliest_safe_replay_date=` must not remain blank.
2. SQ/XYZ lifecycle must preserve:
   - historical ticker `SQ` through `2025-01-20`
   - current canonical ticker `XYZ` effective `2025-01-21`
   - no replay eligibility leakage before the ticker-change date
3. SPY/QQQ must remain proxy-only and excluded from trade candidates.
4. Dynamic-date-gated recent listings such as RDDT and GEV must retain explicit dates.
5. Comments must be machine-parseable.

For each watchlist line, report:

- `line_number`
- `raw_line`
- `ticker`
- `canonical_current_ticker`
- `historical_ticker`
- `is_trade_candidate`
- `is_proxy_only`
- `dynamic_earliest_safe_replay_date`
- `alias_status`
- `comment_parse_status`: `PASS`, `WARN`, `FAIL`
- `audit_status`: `PASS`, `WARN`, `FAIL`
- `audit_reason`

The v3 watchlist file remains research-only and must start with comments saying:

```text
# Phase 1L research-only clean watchlist v3 candidate.
# Not approved for daily scan, paper execution, or real-money execution.
# Alias/date-gated symbols are research-only and must be handled by replay eligibility logic.
```

## Part 7: Data Readiness Scorecard

Create `phase1l_data_readiness_scorecard.csv` and `phase1l_data_readiness_summary.md`.

Scorecard columns:

- `total_symbols`
- `active_trade_candidate_count`
- `proxy_count`
- `stooq_smoke_pass_count`
- `stooq_smoke_cache_only_pass_count`
- `stooq_payload_parse_error_count`
- `stooq_html_or_blocked_count`
- `independent_secondary_match_count`
- `independent_secondary_warn_count`
- `independent_secondary_fail_count`
- `independent_secondary_coverage_pct`
- `transport_fallback_match_count`
- `transport_fallback_warn_count`
- `alias_audit_fail_count`
- `blank_date_gate_comment_count`
- `unresolved_alias_count`
- `unresolved_low_taxonomy_count`
- `clean_watchlist_v3_candidate_count`
- `data_readiness_status`

Status rules:

### `PHASE_1L_SECONDARY_VENDOR_BLOCKED`

Use this if:

- no independent secondary source smoke test passes, or
- independent secondary coverage is below 80%, or
- Stooq/source diagnostics are still ambiguous, or
- alias/watchlist audit has FAIL rows.

### `PHASE_1L_DATA_ADAPTER_READY_VENDOR_MISSING`

Use this if:

- adapter diagnostics are clear,
- alias/watchlist audit passes,
- Yahoo Chart transport fallback works as a same-vendor sanity check,
- but no independent secondary source is available.

This means the project is cleaner but still not ready for execution-grade validation.

### `PHASE_1L_READY_FOR_FROZEN_RETEST_GPT_REVIEW`

Use this only if all are true:

- independent secondary source smoke passes for at least 3 of 4 smoke symbols;
- independent secondary validation has `MATCH` or `WARN` coverage for at least 90% of active trade candidates;
- independent secondary `FAIL` rate is <= 5%;
- alias audit has 0 FAIL rows;
- blank date-gate comments = 0;
- unresolved alias count = 0;
- unresolved LOW taxonomy count = 0.

Even with this status, do not run any strategy retest until GPT reviews the report and explicitly requests it in a future task.

## Tests

Add tests for:

1. Stooq parser successfully parses a normal OHLCV CSV.
2. Stooq parser detects HTML/block/error payloads instead of generic parse failure.
3. Stooq parser supports case-insensitive columns and BOM-prefixed CSV.
4. Smoke-test v2 does not mark global unavailable without diagnostics.
5. Yahoo Chart adapter is always labeled same-vendor / transport-only and never counts as independent secondary validation.
6. Secondary validation v3 cannot emit `MATCH` without positive overlap days.
7. Readiness gate fails when independent secondary coverage is 0%.
8. Readiness gate can produce `PHASE_1L_DATA_ADAPTER_READY_VENDOR_MISSING` when diagnostics and alias audit pass but independent vendor is absent.
9. Alias clean watchlist audit fails on a blank `earliest_safe_replay_date=` comment.
10. SQ/XYZ lifecycle handling preserves the 2025-01-21 effective current-ticker date and prevents pre-change leakage.
11. SPY/QQQ remain proxy-only and excluded from trade candidates.
12. All required Phase 1L reports are written.
13. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1l-secondary-data-adapter-gate
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1L Summary
- Stooq raw response diagnostics
- Secondary source capability matrix summary
- Secondary vendor smoke test v2 result
- Independent secondary OHLCV validation coverage
- Yahoo Chart transport fallback audit summary
- Alias / clean watchlist v3 audit result
- Data readiness scorecard
- Final Phase 1L status
- Whether strategy research should remain paused
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2 or Phase 3. Do not run a frozen Candidate 34 vs Candidate 35 retest. Do not enable paper execution or live trading.
