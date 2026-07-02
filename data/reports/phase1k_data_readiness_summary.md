PHOENIX NANO PHASE 1K — DATA REMEDIATION, TICKER LIFECYCLE, AND SECONDARY VENDOR SMOKE TESTS

Historical research and data-readiness remediation only. No daily scan, paper execution, or real-money execution is approved.

## Secondary Vendor Smoke Test Result

{'GLOBAL_SOURCE_UNAVAILABLE': 4}
- source_global_status: GLOBAL_SOURCE_UNAVAILABLE

## Secondary OHLCV Validation Coverage

{'GLOBAL_SOURCE_UNAVAILABLE': 119}

## Ticker Lifecycle / Alias Findings

{'UNCHANGED': 115, 'ETF_OR_INDEX_PROXY': 2, 'UNKNOWN': 1, 'RENAMED': 1}

## SQ / XYZ Handling Decision

| original_watchlist_ticker   | canonical_current_ticker   | historical_ticker   | effective_start_date   | effective_end_date   | alias_status   | replay_handling                   | evidence_source                  | evidence_notes                                                                                                                     |
|:----------------------------|:---------------------------|:--------------------|:-----------------------|:---------------------|:---------------|:----------------------------------|:---------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------|
| SQ                          | XYZ                        | SQ                  | 2015-11-19             | 2025-01-20           | RENAMED        | USE_HISTORICAL_THEN_CURRENT_ALIAS | Block ticker-change announcement | Block Class A common stock began NYSE trading under XYZ on 2025-01-21; SQ must not leak XYZ eligibility before the effective date. |

## BITF Handling Decision

| ticker   | phase1j_quarantine_status   | phase1j_quarantine_reason                                                             | phase1j_suggested_action   | phase1j_earliest_safe_replay_date   | phase1k_listing_status   | phase1k_ohlcv_status      | phase1k_alias_status   | phase1k_taxonomy_confidence   |   factor_lookback_available_days_at_requested_start |   forward_window_available_days_at_requested_end | dynamic_earliest_safe_replay_date   | remediation_class          | phase1k_recommended_research_action   | rationale                                                                                                               |
|:---------|:----------------------------|:--------------------------------------------------------------------------------------|:---------------------------|:------------------------------------|:-------------------------|:--------------------------|:-----------------------|:------------------------------|----------------------------------------------------:|-------------------------------------------------:|:------------------------------------|:---------------------------|:--------------------------------------|:------------------------------------------------------------------------------------------------------------------------|
| BITF     | QUARANTINE                  | symbol_master_status:UNKNOWN;insufficient_factor_lookback;insufficient_forward_window | DROP_FROM_RESEARCH         |                                     | UNKNOWN                  | GLOBAL_SOURCE_UNAVAILABLE | UNKNOWN                | HIGH                          |                                                   0 |                                                0 |                                     | DATA_DOWNLOAD_RETRY_NEEDED | MANUAL_REVIEW                         | BITF has metadata/price download failure and static taxonomy is resolved; data source retry is needed before inclusion. |

## SPY/QQQ Proxy Handling

- SPY and QQQ are resolved as ETF/index proxies.
- They are retained for regime/index context and excluded from trade candidates.

## Phase 1J Quarantine Remediation Results

{'PERMANENT_DROP': 17, 'DYNAMIC_ALLOW_AFTER_DATE': 2, 'DATA_DOWNLOAD_RETRY_NEEDED': 1, 'ALIASED_OR_RENAMED': 1}
{'DROP': 17, 'ALLOW_DYNAMIC_DATE_GATED': 3, 'MANUAL_REVIEW': 1}

## Taxonomy V2 Confidence Counts

{'HIGH': 120}

## Clean Watchlist V2 Candidate Count

- 99

## Phase 1K Data Readiness Status

|   total_symbols |   phase1j_quarantined_count |   phase1k_permanent_drop_count |   phase1k_dynamic_allow_after_date_count |   phase1k_allow_with_warning_count |   unresolved_alias_count |   unresolved_low_taxonomy_count |   active_trade_candidate_count |   proxy_count |   secondary_smoke_pass_count |   secondary_global_unavailable_count |   secondary_ohlcv_match_count |   secondary_ohlcv_warn_count |   secondary_ohlcv_fail_count |   secondary_no_data_for_symbol_count |   secondary_global_source_unavailable_count | data_readiness_status   |
|----------------:|----------------------------:|-------------------------------:|-----------------------------------------:|-----------------------------------:|-------------------------:|--------------------------------:|-------------------------------:|--------------:|-----------------------------:|-------------------------------------:|------------------------------:|-----------------------------:|-----------------------------:|-------------------------------------:|--------------------------------------------:|:------------------------|
|             119 |                          19 |                             17 |                                        3 |                                  0 |                        0 |                               0 |                             99 |             2 |                            0 |                                    4 |                             0 |                            0 |                            0 |                                    0 |                                         119 | PHASE_1K_DATA_BLOCKED   |

## Final Phase 1K Status: PHASE_1K_DATA_BLOCKED

Strategy research should remain paused unless GPT explicitly accepts this data-readiness status and requests a frozen retest.

Do not start Phase 2, Phase 3, paper execution, live execution, Candidate 36, or any strategy retest.
