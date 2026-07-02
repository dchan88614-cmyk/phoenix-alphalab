# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1J — Symbol Master, Secondary Vendor Validation, and Research Data Readiness Gate

This task is historical research and data-hygiene work only.

Do not start Phase 2.
Do not start Phase 3.
Do not enable paper execution.
Do not enable real-money execution.
Do not change daily scan production behavior.
Do not loosen Candidate 34 thresholds.
Do not adopt Candidate 35, Phase 1H overlays, or any universe variant as active policy.
Do not create Candidate 36 entry rules.
Do not run another strategy threshold sweep.
Do not produce financial advice or an operational recommendation.

## Why This Task

Phase 1I completed the data quality, vendor validation, and universe design audit.

The result was:

- `PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH`
- Symbol audit rows: 119.
- PASS: 0.
- WARN: 98.
- FAIL: 21.
- Vendor validation rows: 119 of 119 were `NO_SECOND_SOURCE`.
- `BITF` still produced yfinance 404 / metadata incomplete behavior.
- Several symbols showed split/adjustment or abnormal-volume warnings.
- Current taxonomy still had 19 `UNMAPPED_LOW_CONFIDENCE` symbols.
- Candidate 34 failed every tested universe variant.
- Candidate 35 trend-quality remained stronger than Candidate 34, but still failed every holdout universe variant because drawdown, win rate, and top-theme loss concentration remained outside gates.
- Clean universe variants removed too many winners and did not solve drawdown.

Therefore the highest-priority next step is **not** another rule redesign, **not** another overlay, and **not** another threshold sweep.

The next optimized research task is to build a reproducible symbol master, validate listings and OHLCV with no-secret public sources where feasible, quarantine unsafe symbols, resolve taxonomy gaps, and create an explicit data-readiness gate before any more strategy research.

## Goal

Create Phase 1J research code that answers:

- Which watchlist symbols are active listed U.S. equities and safe for research replay?
- Which symbols are failing because of yfinance metadata quirks versus genuine listing/data problems?
- Can any no-secret secondary source validate OHLCV for enough symbols to resume research confidently?
- Which symbols must be quarantined before further strategy testing?
- Can the 19 `UNMAPPED_LOW_CONFIDENCE` taxonomy rows be resolved deterministically?
- Is Phoenix Nano data ready for another frozen strategy retest, or must data/vendor work continue first?

Do not use future returns, realized PnL, or holdout performance to decide symbol inclusion, taxonomy, or quarantine status.

## CLI

Add or update:

```bash
--phase1j-data-readiness-gate
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1j-data-readiness-gate
```

If network access to public symbol directories or secondary OHLCV sources is unavailable, the run must still complete with explicit `SOURCE_UNAVAILABLE` / `NO_SECOND_SOURCE` statuses. Do not fake validation.

## Required Outputs

Create or update:

- `data/reports/phase1j_symbol_master.csv`
- `data/reports/phase1j_listing_validation_matrix.csv`
- `data/reports/phase1j_secondary_ohlcv_validation.csv`
- `data/reports/phase1j_data_readiness_scorecard.csv`
- `data/reports/phase1j_quarantine_list.csv`
- `data/reports/phase1j_taxonomy_resolution.csv`
- `data/reports/phase1j_clean_watchlist_candidate.txt`
- `data/reports/phase1j_data_readiness_summary.md`
- `REPORT_TO_GPT.md`

Optional but preferred if useful:

- `data/cache/symbol_master/` for raw public symbol-directory snapshots.
- `data/cache/secondary_ohlcv/` for secondary-source OHLCV snapshots.

Keep earlier Phase 1 reports intact unless regeneration is required.

The summary must start with:

```text
PHOENIX NANO PHASE 1J — SYMBOL MASTER, SECONDARY VENDOR VALIDATION, AND DATA READINESS GATE
```

## Inputs

Reuse existing Phase 1 research outputs where useful:

- `data/reports/phase1i_symbol_data_quality_audit.csv`
- `data/reports/phase1i_vendor_validation_matrix.csv`
- `data/reports/phase1i_universe_composition_audit.csv`
- `data/reports/phase1i_data_gap_incident_log.csv`
- `data/reports/phase1i_rejected_symbol_audit.csv`
- `data/reports/phase1i_data_universe_summary.md`
- Phase 1F taxonomy/failure-attribution code if available.

Do not use Phase 1 holdout PnL to decide if a symbol is kept or removed.

## Part 1: Build a Symbol Master

Create `phase1j_symbol_master.csv`.

For every ticker in the watchlist plus SPY and QQQ, report:

- ticker
- normalized_ticker
- source_watchlist
- source_watchlist_line_number
- symbol_master_status: `ACTIVE_LISTED_EQUITY`, `ETF_OR_INDEX_PROXY`, `DELISTED_OR_INACTIVE`, `NON_EQUITY`, `UNKNOWN`, `SOURCE_UNAVAILABLE`
- primary_exchange
- listing_exchange
- asset_type
- security_name
- is_etf
- is_adr
- is_spac_or_former_spac_if_detectable
- is_recent_ipo_or_recent_listing
- first_trade_date_from_ohlcv
- last_trade_date_from_ohlcv
- has_sufficient_factor_lookback
- has_sufficient_forward_window
- normalized_symbol_notes
- validation_sources_used

Use no-secret public listing/reference sources where feasible. Acceptable sources include:

- NASDAQ Trader symbol directory files if accessible.
- SEC company ticker files if accessible.
- Stooq symbol availability if accessible.
- Existing local/cache files if present.
- yfinance metadata only as one input, not the sole authority when it conflicts with another public listing source.

Do not add paid APIs or secrets.

## Part 2: Listing Validation Matrix

Create `phase1j_listing_validation_matrix.csv`.

For each ticker and source, report:

- ticker
- source_name
- source_available
- source_lookup_symbol
- source_security_name
- source_exchange
- source_asset_type
- source_active_flag
- source_delisted_flag
- source_listing_date_if_available
- validation_status: `MATCH`, `WARN`, `FAIL`, `SOURCE_UNAVAILABLE`
- validation_reason

Special focus:

- Investigate symbols Phase 1I rejected as `exchange_excluded` even though they may be ordinary U.S. equities.
- Investigate `BITF` yfinance 404 / metadata incomplete.
- Investigate `SQ` metadata incomplete.
- Investigate recent-listing symbols such as GEV and RDDT separately from bad data.
- Distinguish true data failure from insufficient lookback caused by recent IPO/spinoff/listing.

## Part 3: Secondary OHLCV Validation

Create `phase1j_secondary_ohlcv_validation.csv`.

Attempt no-secret secondary OHLCV validation for every symbol where feasible.

For each symbol, report:

- ticker
- primary_vendor
- secondary_vendor
- primary_start_date
- primary_end_date
- secondary_start_date
- secondary_end_date
- overlap_trading_days
- close_price_median_abs_diff_pct
- close_price_p95_abs_diff_pct
- close_price_max_abs_diff_pct
- volume_median_abs_diff_pct
- volume_p95_abs_diff_pct
- volume_max_abs_diff_pct
- adjusted_close_available_primary
- adjusted_close_available_secondary
- adjusted_price_mismatch_flag
- split_or_corporate_action_mismatch_flag
- validation_status: `MATCH`, `WARN`, `FAIL`, `NO_SECOND_SOURCE`, `SOURCE_UNAVAILABLE`
- validation_reason

Potential no-secret secondary source:

- Stooq daily prices, if feasible and stable.

If no secondary OHLCV source is available, keep the matrix explicit and mark `NO_SECOND_SOURCE` or `SOURCE_UNAVAILABLE`. Do not infer validation from the same vendor twice.

## Part 4: Quarantine Rules

Create `phase1j_quarantine_list.csv`.

A ticker must be quarantined if any of these are true:

- no usable OHLCV for the requested replay window;
- symbol is delisted/inactive/non-equity and not an approved index/ETF proxy;
- severe metadata conflict cannot be resolved;
- yfinance 404 or repeat download failure persists;
- adjusted OHLCV appears structurally broken and cannot be validated;
- split/corporate-action anomaly cannot be validated by a secondary source;
- missing/zero-volume issues are severe enough to distort factors;
- insufficient factor lookback for the replay start date, unless explicitly classified as recent-listing and excluded from early replay dates only.

For each quarantined ticker, report:

- ticker
- quarantine_status: `QUARANTINE`, `RESEARCH_WARN`, `ALLOW_RESEARCH`
- quarantine_reason
- source_evidence
- suggested_action: `DROP_FROM_RESEARCH`, `ALLOW_AFTER_DATE`, `MANUAL_REVIEW`, `NEEDS_SECONDARY_VENDOR`, `KEEP_WITH_WARNING`
- earliest_safe_replay_date if applicable

Do not remove a symbol merely because it was a losing trade in prior research.

## Part 5: Resolve Taxonomy Gaps

Create `phase1j_taxonomy_resolution.csv`.

For every ticker with `UNMAPPED_LOW_CONFIDENCE` or missing taxonomy, assign a deterministic research taxonomy using only static information available from listing/security name, existing manually curated mappings, sector/industry metadata if available, and conservative fallback rules.

Columns:

- ticker
- prior_theme
- resolved_theme
- resolved_subtheme
- confidence: `HIGH`, `MEDIUM`, `LOW`
- evidence_source
- notes

If confidence remains LOW, keep the symbol in the taxonomy file but flag it for manual review.

## Part 6: Clean Watchlist Candidate

Create `phase1j_clean_watchlist_candidate.txt`.

This is a research-only candidate watchlist, not an active daily-scan production list.

Rules:

- Include only `ALLOW_RESEARCH` tickers and approved `RESEARCH_WARN` tickers.
- Exclude `QUARANTINE` tickers.
- Exclude symbols with no usable OHLCV.
- Exclude symbols with unresolved severe listing conflicts.
- Preserve SPY/QQQ only as regime/index proxies, not trade candidates.
- Keep one ticker per line.
- Add a header comment explaining that this file is research-only and not approved for paper/live execution.

## Part 7: Data Readiness Scorecard

Create `phase1j_data_readiness_scorecard.csv`.

Report:

- total_symbols
- active_listed_equity_count
- etf_or_index_proxy_count
- unknown_or_source_unavailable_count
- quarantined_count
- research_warn_count
- allow_research_count
- secondary_ohlcv_match_count
- secondary_ohlcv_warn_count
- secondary_ohlcv_fail_count
- no_second_source_count
- taxonomy_resolved_high_count
- taxonomy_resolved_medium_count
- taxonomy_resolved_low_count
- unresolved_taxonomy_count
- symbols_with_sufficient_lookback_count
- symbols_with_earliest_safe_replay_date_count
- data_readiness_status

Allowed statuses:

- `PHASE_1J_DATA_BLOCKED`
- `PHASE_1J_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING`
- `PHASE_1J_RESEARCH_DATA_READY_FOR_FROZEN_RETEST`

## Phase 1J Readiness Gates

Mark `PHASE_1J_RESEARCH_DATA_READY_FOR_FROZEN_RETEST` only if all are true:

1. Quarantined symbols are <= 5% of watchlist symbols.
2. No `BLOCKER` or unresolved HIGH severity data incident remains.
3. All active research candidates have usable OHLCV.
4. All active research candidates have deterministic taxonomy with confidence HIGH or MEDIUM.
5. SPY and QQQ, or their chosen regime proxies, are validated and usable.
6. Recent-listing symbols have explicit `earliest_safe_replay_date` handling.
7. At least 80% of active research candidates have secondary OHLCV `MATCH` or `WARN`, or the summary explicitly marks the project as research-only and not execution-grade due to missing secondary vendor.

If gates 1-6 pass but gate 7 fails because no no-secret secondary vendor is available, mark:

`PHASE_1J_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING`

If any of gates 1-6 fail, mark:

`PHASE_1J_DATA_BLOCKED`

Even if Phase 1J passes, do not start Phase 2, paper execution, or live execution. The only allowed next step after a pass is a frozen Candidate 34 vs Candidate 35 retest on the cleaned research watchlist, pending GPT review.

## Tests

Add tests for:

1. Symbol master output includes every watchlist ticker plus SPY and QQQ.
2. Listing validation distinguishes `SOURCE_UNAVAILABLE` from `FAIL`.
3. yfinance metadata rejection alone does not force failure if another public source validates an active listed equity.
4. `BITF`-style no-OHLCV / 404 behavior is quarantined.
5. Recent IPO/spinoff symbols can be classified with `earliest_safe_replay_date` instead of permanent data failure.
6. Secondary OHLCV validation never marks `MATCH` unless overlap_trading_days > 0 and differences are computed.
7. Taxonomy resolution eliminates or explicitly flags every low-confidence row.
8. Quarantined symbols do not appear in `phase1j_clean_watchlist_candidate.txt`.
9. Readiness gate statuses follow the rules above.
10. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1j-data-readiness-gate
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1J Symbol Master / Vendor Validation Summary
- Symbol master status counts
- Listing validation status counts
- Secondary OHLCV validation coverage
- Quarantine count and top quarantine reasons
- Taxonomy resolution status
- Clean watchlist candidate count
- Data readiness status
- Whether strategy research should remain paused
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2, paper execution, or live trading.
