PHOENIX NANO PHASE 1F — FAILURE ATTRIBUTION, TAXONOMY, AND DATA QUALITY AUDIT

Research-only. This does not change daily scan behavior and does not approve any policy.

## Phase 1E Recap

- Phase 1E found no calibration or holdout filter passed all gates.
- Phase 1F audits whether remaining failures are explainable by ticker, theme, regime, or data quality.

## Failure Sample Summary

- Samples audited: 20
- Accepted historical candidates in ledger: 667
- Losing simulated candidates: 384

## Theme Taxonomy Cleanup Results

- Taxonomy rows: 53
- Low-confidence mappings: 19

## Remaining Unmapped Loss Contribution

- Unmapped loss dollars: $0.00
- Unmapped loss share: 0.00%

## Drawdown Attribution Summary

Theme losses:
- EV / mobility: $1231.31
- AI / software: $928.16
- space / defense / nuclear: $786.84
- crypto-adjacent / high beta: $554.65
- biotech: $283.78
- semiconductor / hardware: $277.83
- fintech: $251.61
- AI infrastructure: $177.12
- software: $46.50
- power / electrification: $6.19

Ticker losses:
- RKLB: $476.65
- BBAI: $475.06
- RIVN: $474.92
- XPEV: $323.09
- CORZ: $286.88
- INTC: $277.83
- PATH: $270.17
- IREN: $211.79
- SMR: $198.29
- SOFI: $163.53

## Market Regime Attribution Summary

- MIXED: $-278.95
- RISK_OFF: $-272.48
- UNKNOWN_MARKET_DATA: $91.20
- RISK_ON: $1986.97

## Data Quality Audit Summary

- Data quality blockers: 0
- Data quality warnings: 230
- missing_ohlcv_bars: 2574
- incomplete_20d_forward_windows: 1980
- metadata_rejected_symbol: 19
- abnormal_volume_days: 7
- split_or_adjustment_anomaly: 7
- missing_qqq_regime_data: 1

## Concentration Assessment

- Failures are assessed as: broad
- Top theme loss share: 27.10%
- Top ticker loss share: 10.49%

## Final Phase 1F Status: PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN

Do not start paper execution or real-money execution.

## Next Research Task Recommendation

Recommend Candidate 34 redesign rather than more threshold tuning.
