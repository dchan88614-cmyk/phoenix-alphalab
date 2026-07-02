# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1K - Data Remediation, Ticker Lifecycle, and Secondary Vendor Smoke Tests.
- Added historical research-only Phase 1K data remediation code.
- Added CLI flag:
  - `--phase1k-data-remediation-gate`
- Added Stooq secondary vendor smoke test with explicit global-source-unavailable status.
- Added secondary OHLCV validation v2 with cache-aware labels.
- Added ticker lifecycle / alias map.
- Added SQ -> XYZ lifecycle handling with date-gated replay notes.
- Added Phase 1J quarantine remediation audit.
- Added deterministic taxonomy static overrides and taxonomy v2 output.
- Added research-only clean watchlist v2 candidate.
- Added Phase 1K data readiness scorecard.
- Created required outputs:
  - `data/reports/phase1k_secondary_vendor_smoke_test.csv`
  - `data/reports/phase1k_secondary_ohlcv_validation.csv`
  - `data/reports/phase1k_symbol_lifecycle_alias_map.csv`
  - `data/reports/phase1k_quarantine_remediation_audit.csv`
  - `data/reports/phase1k_taxonomy_static_overrides.csv`
  - `data/reports/phase1k_taxonomy_resolution_v2.csv`
  - `data/reports/phase1k_clean_watchlist_v2_candidate.txt`
  - `data/reports/phase1k_data_readiness_scorecard.csv`
  - `data/reports/phase1k_data_readiness_summary.md`
- Did not start Phase 2.
- Did not start Phase 3.
- Did not enable paper execution.
- Did not enable real-money execution.
- Did not change daily scan production behavior.
- Did not loosen Candidate 34 thresholds.
- Did not adopt Candidate 35, Phase 1H overlays, or any universe variant as active policy.
- Did not create Candidate 36.
- Did not run a Candidate 34 vs Candidate 35 retest.
- Did not run a strategy threshold sweep.
- Did not produce financial advice or an operational recommendation.

## Files Changed

- `src/main.py`
- `src/research/phase1k_data_remediation.py`
- `tests/test_phase1k_data_remediation.py`
- `data/reports/phase1k_secondary_vendor_smoke_test.csv`
- `data/reports/phase1k_secondary_ohlcv_validation.csv`
- `data/reports/phase1k_symbol_lifecycle_alias_map.csv`
- `data/reports/phase1k_quarantine_remediation_audit.csv`
- `data/reports/phase1k_taxonomy_static_overrides.csv`
- `data/reports/phase1k_taxonomy_resolution_v2.csv`
- `data/reports/phase1k_clean_watchlist_v2_candidate.txt`
- `data/reports/phase1k_data_readiness_scorecard.csv`
- `data/reports/phase1k_data_readiness_summary.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1k-data-remediation-gate
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_phase1k_data_remediation.py -q
# 10 passed in 0.20s
```

```bash
.venv/bin/python -m pytest -q
# 170 passed, 1 warning in 28.42s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1k-data-remediation-gate
```

## Phase 1K Data Remediation Summary

- Summary file starts with the required heading:
  - `PHOENIX NANO PHASE 1K — DATA REMEDIATION, TICKER LIFECYCLE, AND SECONDARY VENDOR SMOKE TESTS`
- Final status: `PHASE_1K_DATA_BLOCKED`
- Phase 1K did not approve any strategy, universe, data source, daily scan change, paper execution, or real-money execution.
- Strategy research should remain paused.

## Secondary Vendor Smoke Test Result

- `GLOBAL_SOURCE_UNAVAILABLE`: 4
- `PASS`: 0
- `CACHE_ONLY_PASS`: 0

Interpretation:

- AAPL, MSFT, SPY, and QQQ could not be validated against Stooq in this run.
- The system now distinguishes this as a global secondary-source availability problem instead of treating every ticker as an individual no-data case.

## Secondary OHLCV Validation Coverage

- `GLOBAL_SOURCE_UNAVAILABLE`: 119
- `MATCH`: 0
- `WARN`: 0
- `CACHE_ONLY_MATCH`: 0
- `CACHE_ONLY_WARN`: 0
- `FAIL`: 0
- `NO_DATA_FOR_SYMBOL`: 0

Interpretation:

- No active symbol has execution-grade secondary OHLCV validation.
- The secondary validation blocker remains unresolved.

## Ticker Lifecycle / Alias Findings

- `UNCHANGED`: 115
- `ETF_OR_INDEX_PROXY`: 2
- `RENAMED`: 1
- `UNKNOWN`: 1

## SQ / XYZ Handling Decision

- `SQ` is treated as a renamed ticker for Block.
- `canonical_current_ticker`: `XYZ`
- `historical_ticker`: `SQ`
- `effective_end_date`: `2025-01-20`
- `replay_handling`: `USE_HISTORICAL_THEN_CURRENT_ALIAS`
- Anti-leak rule: replay must not use `XYZ` eligibility before the 2025-01-21 ticker-change effective date.

## BITF Handling Decision

- `BITF` taxonomy is now resolved as crypto-adjacent / bitcoin mining.
- `BITF` still has yfinance 404 / metadata incomplete behavior.
- Phase 1K remediation class: `DATA_DOWNLOAD_RETRY_NEEDED`
- Phase 1K research action: `MANUAL_REVIEW`
- `BITF` is excluded from clean watchlist v2.

## SPY/QQQ Proxy Handling

- SPY taxonomy v2: ETF / index proxy; broad U.S. equity proxy.
- QQQ taxonomy v2: ETF / index proxy; Nasdaq-100 / growth equity proxy.
- Both are retained only as regime/index proxies.
- Both are excluded from trade candidates.

## Phase 1J Quarantine Remediation Results

- `PERMANENT_DROP`: 17
- `DYNAMIC_ALLOW_AFTER_DATE`: 2
- `ALIASED_OR_RENAMED`: 1
- `DATA_DOWNLOAD_RETRY_NEEDED`: 1

Recommended research actions:

- `DROP`: 17
- `ALLOW_DYNAMIC_DATE_GATED`: 3
- `MANUAL_REVIEW`: 1

## Taxonomy V2 Confidence Counts

- `HIGH`: 120
- `MEDIUM`: 0
- `LOW`: 0

Interpretation:

- The required targeted LOW and wrong MEDIUM taxonomy rows were resolved with static overrides.
- Any remaining blocker is now data availability / lifecycle readiness, not taxonomy confidence.

## Clean Watchlist V2 Candidate Count

- Research-only clean watchlist v2 candidate count: 99
- The file excludes SPY/QQQ as trade candidates.
- The file excludes permanent drops and manual-review symbols such as BITF.
- Dynamic-date-gated symbols include inline earliest-safe-replay-date comments.
- This file is not approved for daily scan, paper execution, or real-money execution.

## Phase 1K Data Readiness Status

- `total_symbols`: 119
- `phase1j_quarantined_count`: 19
- `phase1k_permanent_drop_count`: 17
- `phase1k_dynamic_allow_after_date_count`: 3
- `phase1k_allow_with_warning_count`: 0
- `unresolved_alias_count`: 0
- `unresolved_low_taxonomy_count`: 0
- `active_trade_candidate_count`: 99
- `proxy_count`: 2
- `secondary_smoke_pass_count`: 0
- `secondary_global_unavailable_count`: 4
- `secondary_ohlcv_match_count`: 0
- `secondary_ohlcv_warn_count`: 0
- `secondary_ohlcv_fail_count`: 0
- `secondary_no_data_for_symbol_count`: 0
- `secondary_global_source_unavailable_count`: 119
- Final status: `PHASE_1K_DATA_BLOCKED`

## Whether Strategy Research Should Remain Paused

Yes. Strategy research should remain paused.

Reasons:

- 17 symbols are still permanent drops from the Phase 1K remediation audit.
- 119 of 119 secondary OHLCV rows are `GLOBAL_SOURCE_UNAVAILABLE`.
- Secondary vendor smoke test did not pass for AAPL, MSFT, SPY, or QQQ.
- The data readiness gate did not pass.
- Phase 1K status is `PHASE_1K_DATA_BLOCKED`.

## Problems

- Stooq validation is globally unavailable in this run.
- No secondary OHLCV comparison produced MATCH, WARN, CACHE_ONLY_MATCH, or CACHE_ONLY_WARN.
- `BITF` remains unresolved at the data-download level and requires manual review or vendor retry.
- 17 Phase 1J quarantined symbols remain permanent drops because usable OHLCV was not present in the requested research dataset.
- The clean watchlist v2 candidate is research-only and should not be treated as an active universe policy.

## Questions For GPT

- Should Phoenix Nano integrate a different no-secret secondary OHLCV source before any retest?
- Should the 17 permanent-drop symbols be removed from the source watchlist, or preserved with explicit exclusion records?
- Should `SQ` be replaced by `XYZ` in the watchlist with lifecycle metadata retained for historical replay?
- Should `BITF` be retried through another vendor or removed from the research universe?
- Should GPT request a frozen Candidate 34 vs Candidate 35 retest only after secondary OHLCV validation is working?

## Next Suggested Tasks

- Do not start Phase 2.
- Do not start Phase 3.
- Do not enable paper execution.
- Do not enable real-money execution.
- Do not run Candidate 34 vs Candidate 35 retest yet.
- Keep Phoenix Nano historical research-only.
- Fix secondary OHLCV vendor availability or add an alternate no-secret source.
- Decide how to handle the 17 permanent-drop symbols.
- Decide whether to replace `SQ` with `XYZ` in the watchlist while preserving alias lifecycle rules.
