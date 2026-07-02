PHOENIX NANO PHASE 1J — SYMBOL MASTER, SECONDARY VENDOR VALIDATION, AND DATA READINESS GATE

Research-only. No symbol, vendor, watchlist, or strategy is approved for daily scan, paper execution, or real-money execution.

## Phase 1I Recap

- Phase 1I ended as PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH.
- Phase 1J builds a symbol master and readiness gate before more strategy research.

## Symbol Master Status Counts

{'ACTIVE_LISTED_EQUITY': 115, 'UNKNOWN': 2, 'ETF_OR_INDEX_PROXY': 2}

## Listing Validation Status Counts

{'MATCH': 100, 'WARN': 19}

## Secondary OHLCV Validation Coverage

{'SOURCE_UNAVAILABLE': 119}

## Quarantine Count And Top Reasons

{'ALLOW_RESEARCH': 98, 'QUARANTINE': 19, 'RESEARCH_WARN': 2}
- clean_research_symbol: 98
- insufficient_factor_lookback;insufficient_forward_window: 17
- symbol_master_status:UNKNOWN;insufficient_factor_lookback;insufficient_forward_window: 2
- recent_listing_requires_earliest_safe_replay_date: 2

## Taxonomy Resolution Status

{'HIGH': 98, 'MEDIUM': 17, 'LOW': 4}

## Clean Watchlist Candidate Count

- 98

## Data Readiness Scorecard

|   total_symbols |   active_listed_equity_count |   etf_or_index_proxy_count |   unknown_or_source_unavailable_count |   quarantined_count |   research_warn_count |   allow_research_count |   secondary_ohlcv_match_count |   secondary_ohlcv_warn_count |   secondary_ohlcv_fail_count |   no_second_source_count |   taxonomy_resolved_high_count |   taxonomy_resolved_medium_count |   taxonomy_resolved_low_count |   unresolved_taxonomy_count |   symbols_with_sufficient_lookback_count |   symbols_with_earliest_safe_replay_date_count | data_readiness_status   |
|----------------:|-----------------------------:|---------------------------:|--------------------------------------:|--------------------:|----------------------:|-----------------------:|------------------------------:|-----------------------------:|-----------------------------:|-------------------------:|-------------------------------:|---------------------------------:|------------------------------:|----------------------------:|-----------------------------------------:|-----------------------------------------------:|:------------------------|
|             119 |                          115 |                          2 |                                     2 |                  19 |                     2 |                     98 |                             0 |                            0 |                            0 |                      119 |                             98 |                               17 |                             4 |                           4 |                                       98 |                                              2 | PHASE_1J_DATA_BLOCKED   |

## Final Phase 1J Status: PHASE_1J_DATA_BLOCKED

Do not start paper execution or real-money execution.

## Next Research Task Recommendation

Ask GPT whether to continue data/vendor remediation or run a frozen retest only if GPT accepts the data-readiness status.
