# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1K — Data Remediation, Ticker Lifecycle, and Secondary Vendor Smoke Tests

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
Do not run a Candidate 34 vs Candidate 35 retest yet.
Do not produce financial advice or an operational recommendation.

## Why This Task

Phase 1J completed the symbol master / secondary validation / data readiness gate, but it ended as:

`PHASE_1J_DATA_BLOCKED`

Latest Phase 1J evidence:

- total symbols: 119
- active listed equities: 115
- ETF/index proxies: 2
- unknown symbols: 2
- quarantined symbols: 19
- research warnings: 2
- clean research candidates: 98
- secondary OHLCV matches: 0
- secondary OHLCV warnings: 0
- secondary OHLCV failures: 0
- no usable secondary OHLCV source: 119 of 119
- taxonomy HIGH confidence: 98
- taxonomy MEDIUM confidence: 17
- taxonomy LOW confidence: 4
- final status: `PHASE_1J_DATA_BLOCKED`

The most important blockers are now data-readiness blockers, not strategy-rule blockers:

1. Secondary OHLCV validation was globally unavailable, so every symbol is still effectively yfinance-only.
2. 19 symbols are quarantined, mostly from lookback / forward-window / unknown symbol status issues.
3. Some taxonomy rows are still LOW confidence, including SPY/QQQ proxies and renamed or problematic tickers.
4. Some medium-confidence taxonomy rows were mechanically inferred from company names and are likely wrong, especially crypto miners, biotech names, AI/software names, and recent listings.
5. The repo needs time-varying ticker lifecycle / alias handling before another historical replay. Example: Block changed from `SQ` to `XYZ` in 2025, so replay code must not treat a renamed ticker as a simple permanent data failure or leak future ticker knowledge into old replay dates.

Therefore the next optimized task is **not** another trading-rule redesign. The next task is to repair the data layer enough to know whether a frozen Candidate 34 vs Candidate 35 retest is even legitimate.

## Goal

Create Phase 1K research code that answers:

- Is secondary OHLCV unavailable because Stooq/network access is globally blocked, or because individual symbols are missing?
- Can Stooq or another no-secret source validate at least known liquid test symbols such as AAPL, MSFT, SPY, and QQQ?
- Which quarantined symbols are true permanent drops, which are recent listings that need dynamic `earliest_safe_replay_date`, and which are ticker alias / rename problems?
- Can low-confidence and obviously wrong medium-confidence taxonomy rows be fixed with deterministic static overrides?
- Can the clean watchlist candidate be upgraded to a **research-only v2** list with explicit dynamic replay eligibility?
- Is the project ready for a frozen Candidate 34 vs Candidate 35 retest, or must data work continue?

Do not use realized future returns, realized PnL, holdout performance, or prior winning/losing status to decide symbol inclusion, taxonomy, aliases, or quarantine status.

## CLI

Add or update:

```bash
--phase1k-data-remediation-gate
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1k-data-remediation-gate
```

If network access to public OHLCV sources is unavailable, the run must still complete with explicit global and per-symbol statuses. Do not fake validation.

## Required Outputs

Create or update:

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

Optional but preferred if useful:

- `data/cache/secondary_ohlcv/stooq/`
- `data/cache/symbol_lifecycle/`

Keep earlier Phase 1 reports intact unless regeneration is required.

The summary must start with:

```text
PHOENIX NANO PHASE 1K — DATA REMEDIATION, TICKER LIFECYCLE, AND SECONDARY VENDOR SMOKE TESTS
```

## Inputs

Reuse these Phase 1J outputs:

- `data/reports/phase1j_symbol_master.csv`
- `data/reports/phase1j_listing_validation_matrix.csv`
- `data/reports/phase1j_secondary_ohlcv_validation.csv`
- `data/reports/phase1j_data_readiness_scorecard.csv`
- `data/reports/phase1j_quarantine_list.csv`
- `data/reports/phase1j_taxonomy_resolution.csv`
- `data/reports/phase1j_clean_watchlist_candidate.txt`
- `data/reports/phase1j_data_readiness_summary.md`

Also reuse Phase 1I incident reports where helpful:

- `data/reports/phase1i_data_gap_incident_log.csv`
- `data/reports/phase1i_symbol_data_quality_audit.csv`
- `data/reports/phase1i_rejected_symbol_audit.csv`

## Part 1: Secondary Vendor Smoke Test

Create `phase1k_secondary_vendor_smoke_test.csv`.

Before validating all symbols, run a small explicit smoke test on known high-liquidity symbols:

- `AAPL`
- `MSFT`
- `SPY`
- `QQQ`

For each candidate secondary source / symbol pair, report:

- source_name
- ticker
- lookup_symbol
- url_or_cache_key
- attempted_network_fetch
- used_cache_fallback
- http_status_if_available
- exception_class_if_any
- response_bytes
- parsed_rows
- first_date
- last_date
- required_start_date
- required_end_date
- smoke_status: `PASS`, `NO_DATA_FOR_SYMBOL`, `GLOBAL_SOURCE_UNAVAILABLE`, `PARSE_ERROR`, `CACHE_ONLY_PASS`, `FAIL`
- smoke_reason

For Stooq specifically:

- try the `.us` format currently used by Phase 1J;
- include a reasonable User-Agent header;
- use short retry/backoff;
- preserve raw snapshots in cache when successful;
- distinguish a global network/source failure from a legitimate symbol-level no-data response.

If AAPL/MSFT/SPY/QQQ cannot be fetched from the source and no cache exists, mark the source as `GLOBAL_SOURCE_UNAVAILABLE` for this run. Do not mark every ticker as if the individual ticker has no second source.

## Part 2: Secondary OHLCV Validation v2

Create `phase1k_secondary_ohlcv_validation.csv`.

Only run full per-symbol secondary comparison if the smoke test shows at least one source is available or cached.

For each symbol, report:

- ticker
- primary_vendor
- secondary_vendor
- lookup_symbol
- source_global_status
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
- validation_status: `MATCH`, `WARN`, `FAIL`, `NO_DATA_FOR_SYMBOL`, `GLOBAL_SOURCE_UNAVAILABLE`, `CACHE_ONLY_MATCH`, `CACHE_ONLY_WARN`
- validation_reason

Rules:

- Never mark `MATCH` without positive overlap days and computed differences.
- If the source is globally unavailable, report `GLOBAL_SOURCE_UNAVAILABLE` consistently.
- If cache is used, label it explicitly as cache-based.
- A missing secondary source is a research-readiness warning/blocker, never an execution-grade validation.

## Part 3: Ticker Lifecycle and Alias Map

Create `phase1k_symbol_lifecycle_alias_map.csv`.

For every watchlist ticker plus SPY/QQQ, report:

- original_watchlist_ticker
- canonical_current_ticker
- historical_ticker
- effective_start_date
- effective_end_date
- alias_status: `UNCHANGED`, `RENAMED`, `POSSIBLE_RENAME`, `DELISTED_OR_INACTIVE`, `UNKNOWN`, `ETF_OR_INDEX_PROXY`
- replay_handling: `USE_AS_IS`, `USE_HISTORICAL_THEN_CURRENT_ALIAS`, `ALLOW_AFTER_DATE`, `DROP_FROM_RESEARCH`, `MANUAL_REVIEW`
- evidence_source
- evidence_notes

Special investigations:

- `SQ` / `XYZ` ticker lifecycle for Block.
- `BITF` yfinance 404 / metadata incomplete behavior.
- Any symbol with `symbol_master_status:UNKNOWN` from Phase 1J.
- SPY and QQQ as regime/index proxies, not trade candidates.

Important anti-leak rule:

Historical replay must not use future ticker knowledge to create an investable candidate before the relevant ticker/listing actually existed. Alias mapping is for data continuity and replay eligibility, not for leaking future symbols into old replay dates.

## Part 4: Quarantine Remediation Audit

Create `phase1k_quarantine_remediation_audit.csv`.

Start with all 19 Phase 1J quarantined symbols and the 2 research-warn symbols.

For each, report:

- ticker
- phase1j_quarantine_status
- phase1j_quarantine_reason
- phase1j_suggested_action
- phase1j_earliest_safe_replay_date
- phase1k_listing_status
- phase1k_ohlcv_status
- phase1k_alias_status
- phase1k_taxonomy_confidence
- factor_lookback_available_days_at_requested_start
- forward_window_available_days_at_requested_end
- dynamic_earliest_safe_replay_date
- remediation_class: `PERMANENT_DROP`, `DYNAMIC_ALLOW_AFTER_DATE`, `ALIASED_OR_RENAMED`, `DATA_DOWNLOAD_RETRY_NEEDED`, `KEEP_WITH_WARNING`, `MANUAL_REVIEW_REQUIRED`
- phase1k_recommended_research_action: `DROP`, `ALLOW_DYNAMIC_DATE_GATED`, `ALLOW_WITH_WARNING`, `KEEP_PROXY_ONLY`, `MANUAL_REVIEW`
- rationale

Rules:

- Do not permanently drop a symbol merely because it lacks enough lookback at 2024-01-01 if it has usable later data. Prefer dynamic replay-date gating where appropriate.
- Do not keep a symbol merely because it was profitable in prior research.
- Do not drop a symbol merely because it was unprofitable in prior research.
- If a symbol has a ticker rename, handle via alias map instead of treating it as a normal missing-data ticker.

## Part 5: Taxonomy Static Overrides and v2 Taxonomy

Create `phase1k_taxonomy_static_overrides.csv` and `phase1k_taxonomy_resolution_v2.csv`.

Fix LOW-confidence taxonomy rows and obviously wrong MEDIUM name-keyword rows with deterministic static overrides.

At minimum, review and override these symbols if supported by static business/listing evidence:

- `BITF`: crypto-adjacent / high beta; bitcoin mining
- `SPY`: ETF / index proxy; broad U.S. equity proxy
- `QQQ`: ETF / index proxy; Nasdaq-100 / growth equity proxy
- `SQ` and/or `XYZ`: fintech; payments / Cash App / merchant services
- `ASTS`: space / communications; satellite broadband
- `CELH`: consumer growth; beverages
- `CLSK`: crypto-adjacent / high beta; bitcoin mining
- `CRSP`: biotech; gene editing
- `IOVA`: biotech; oncology cell therapy
- `MARA`: crypto-adjacent / high beta; bitcoin mining
- `MDB`: software; database platform
- `MIRM`: biotech; rare disease therapeutics
- `NNE`: space / defense / nuclear; advanced nuclear
- `NTLA`: biotech; gene editing
- `RIOT`: crypto-adjacent / high beta; bitcoin mining
- `SOUN`: AI / software; voice AI
- `SYM`: robotics / automation; warehouse automation
- `TGTX`: biotech; therapeutics
- `TTD`: software / adtech; demand-side platform
- `U`: software; game engine / real-time 3D platform
- `VKTX`: biotech; metabolic disease therapeutics

Columns for override file:

- ticker
- resolved_theme
- resolved_subtheme
- confidence
- evidence_source
- notes

Columns for v2 taxonomy:

- ticker
- prior_theme
- phase1j_resolved_theme
- phase1k_resolved_theme
- phase1k_resolved_subtheme
- confidence
- evidence_source
- notes

Goal:

- 0 LOW-confidence rows for active research candidates and SPY/QQQ proxies.
- Any remaining LOW-confidence row must be `DROP` or `MANUAL_REVIEW_REQUIRED` and excluded from clean research retesting.

## Part 6: Research-Only Clean Watchlist v2 Candidate

Create `phase1k_clean_watchlist_v2_candidate.txt`.

This is not approved for daily scan, paper execution, or real-money execution.

Rules:

- Include only symbols with `ALLOW_WITH_WARNING` or `ALLOW_DYNAMIC_DATE_GATED` research action.
- Exclude permanent drops.
- Exclude unresolved aliases.
- Exclude unresolved LOW-confidence active taxonomy rows.
- Exclude SPY and QQQ as trade candidates; keep them only as regime/index proxies in metadata/reports.
- If a symbol is dynamic-date-gated, include a comment or sidecar record documenting earliest safe replay date.
- Keep one trade-candidate ticker per line.
- Add a header comment explaining that this file is research-only and not approved for paper/live execution.

## Part 7: Phase 1K Data Readiness Scorecard

Create `phase1k_data_readiness_scorecard.csv`.

Report:

- total_symbols
- phase1j_quarantined_count
- phase1k_permanent_drop_count
- phase1k_dynamic_allow_after_date_count
- phase1k_allow_with_warning_count
- unresolved_alias_count
- unresolved_low_taxonomy_count
- active_trade_candidate_count
- proxy_count
- secondary_smoke_pass_count
- secondary_global_unavailable_count
- secondary_ohlcv_match_count
- secondary_ohlcv_warn_count
- secondary_ohlcv_fail_count
- secondary_no_data_for_symbol_count
- secondary_global_source_unavailable_count
- data_readiness_status

Allowed statuses:

- `PHASE_1K_DATA_BLOCKED`
- `PHASE_1K_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING`
- `PHASE_1K_RESEARCH_DATA_READY_FOR_FROZEN_RETEST`

Mark `PHASE_1K_RESEARCH_DATA_READY_FOR_FROZEN_RETEST` only if all are true:

1. Permanent/unresolved drops are <= 5% of watchlist trade candidates.
2. No unresolved alias remains among active research candidates.
3. No LOW-confidence taxonomy remains among active research candidates or SPY/QQQ proxies.
4. SPY and QQQ are explicitly valid regime/index proxies with usable OHLCV.
5. Recent listings or renamed symbols have explicit dynamic replay eligibility handling.
6. All active research candidates have usable OHLCV for the replay dates on which they are eligible.
7. At least 80% of active research candidates have secondary OHLCV `MATCH`, `WARN`, `CACHE_ONLY_MATCH`, or `CACHE_ONLY_WARN`.

If gates 1-6 pass but gate 7 fails only because no no-secret secondary OHLCV vendor is globally available, mark:

`PHASE_1K_SYMBOL_MASTER_READY_SECONDARY_VENDOR_MISSING`

If any of gates 1-6 fail, mark:

`PHASE_1K_DATA_BLOCKED`

Even if Phase 1K passes, do not start Phase 2, paper execution, live execution, daily-scan production changes, or automatic strategy adoption. The only allowed next step after GPT review is a frozen Candidate 34 vs Candidate 35 retest on the Phase 1K cleaned research universe.

## Tests

Add tests for:

1. Secondary vendor smoke test distinguishes `GLOBAL_SOURCE_UNAVAILABLE` from symbol-level no data.
2. Secondary validation never marks `MATCH` without overlap days and computed differences.
3. Cached secondary data is labeled as cache-based and never hidden as fresh network validation.
4. `SQ` / `XYZ` style ticker lifecycle alias mapping is represented without leaking future ticker eligibility into old replay dates.
5. SPY and QQQ taxonomy are resolved as ETF/index proxies and excluded as trade candidates.
6. Static taxonomy overrides fix the targeted LOW and incorrect MEDIUM rows.
7. Recent listings can be represented as `DYNAMIC_ALLOW_AFTER_DATE` instead of permanent quarantine when OHLCV is usable later.
8. Permanent drops and unresolved aliases do not appear in `phase1k_clean_watchlist_v2_candidate.txt`.
9. Phase 1K readiness statuses follow the gates above.
10. The CLI writes all required Phase 1K outputs.
11. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1k-data-remediation-gate
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1K Data Remediation Summary
- Secondary vendor smoke test result
- Secondary OHLCV validation coverage
- Ticker lifecycle / alias findings
- SQ / XYZ handling decision
- BITF handling decision
- SPY/QQQ proxy handling
- Phase 1J quarantine remediation results
- Taxonomy v2 confidence counts
- Clean watchlist v2 candidate count
- Phase 1K data readiness status
- Whether strategy research should remain paused
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2, Phase 3, paper execution, live execution, production daily-scan changes, Candidate 36, or any strategy retest.
