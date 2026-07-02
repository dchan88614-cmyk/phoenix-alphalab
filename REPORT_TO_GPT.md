# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1F - Failure Attribution, Taxonomy, and Data Quality Audit.
- Added Phase 1F historical failure audit as diagnostic research only.
- Built a complete accepted-candidate failure ledger across 20 deterministic samples.
- Added deterministic ticker/theme/subtheme taxonomy cleanup.
- Added drawdown attribution by ticker, theme, time bucket, feature bucket, and exit reason.
- Added simple auditable market-regime attribution using only data available on or before replay dates.
- Added data-quality audit for missing bars, volume anomalies, forward-window gaps, rejected metadata symbols, and missing QQQ regime data.
- Added CLI flag:
  - `--phase1f-failure-audit`
- Created required outputs:
  - `data/reports/phase1f_failure_trade_ledger.csv`
  - `data/reports/phase1f_theme_taxonomy.csv`
  - `data/reports/phase1f_drawdown_attribution.csv`
  - `data/reports/phase1f_regime_attribution.csv`
  - `data/reports/phase1f_data_quality_audit.csv`
  - `data/reports/phase1f_viability_summary.md`
- Did not start Phase 2.
- Did not start Phase 3.
- Did not change daily scan production behavior.
- Did not loosen Candidate 34 thresholds.
- Did not adopt any new filter as active policy.
- Did not produce financial advice or an operational recommendation.

## Files Changed

- `src/research/phase1f_failure_audit.py`
- `src/main.py`
- `tests/test_phase1f_failure_audit.py`
- `data/reports/phase1f_failure_trade_ledger.csv`
- `data/reports/phase1f_theme_taxonomy.csv`
- `data/reports/phase1f_drawdown_attribution.csv`
- `data/reports/phase1f_regime_attribution.csv`
- `data/reports/phase1f_data_quality_audit.csv`
- `data/reports/phase1f_viability_summary.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1f-failure-audit --replay-rounds 100 --replay-sample-count 20
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_phase1f_failure_audit.py -q
# 8 passed
```

```bash
.venv/bin/python -m pytest -q
# 122 passed, 1 warning in 7.82s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1f-failure-audit --replay-rounds 100 --replay-sample-count 20
```

## Phase 1F Viability Summary

- Phase 1F status: `PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN`
- Samples audited: 20
- Failure ledger rows: 667
- Losing simulated candidates: 384
- Theme taxonomy rows: 53
- Low-confidence mappings: 19
- Drawdown attribution rows: 667
- Regime attribution rows: 156
- Data quality audit rows: 515
- Data quality blockers: 0
- Data quality warnings: 230

## Failure Sample Summary

- The ledger covers all accepted historical candidates across the requested 20 deterministic samples.
- Remaining losses are not dominated by one ticker or one theme.
- Top theme loss share: 27.10%.
- Top ticker loss share: 10.49%.
- This supports the conclusion that failures are broad rather than cleanly isolated.

## Theme Taxonomy Cleanup Results

- The prior `UNMAPPED` loss bucket was eliminated for accepted candidate losses using deterministic static taxonomy.
- Remaining unmapped loss dollars: $0.00.
- Remaining unmapped loss share: 0.00%.
- Low-confidence taxonomy rows remain for rejected or untraded symbols where no confident project mapping exists.

Top theme losses:

| theme | loss dollars |
|:--|--:|
| EV / mobility | $1231.31 |
| AI / software | $928.16 |
| space / defense / nuclear | $786.84 |
| crypto-adjacent / high beta | $554.65 |
| biotech | $283.78 |
| semiconductor / hardware | $277.83 |
| fintech | $251.61 |
| AI infrastructure | $177.12 |

Top ticker losses:

| ticker | loss dollars |
|:--|--:|
| RKLB | $476.65 |
| BBAI | $475.06 |
| RIVN | $474.92 |
| XPEV | $323.09 |
| CORZ | $286.88 |
| INTC | $277.83 |
| PATH | $270.17 |
| IREN | $211.79 |

## Drawdown Attribution Summary

- Losses are spread across EV/mobility, AI/software, space/defense/nuclear, crypto-adjacent/high beta, biotech, semiconductor/hardware, fintech, and AI infrastructure.
- No single theme reaches a concentration level strong enough to justify a simple research-only exclusion by itself.
- No single ticker dominates enough to explain the Candidate 34 instability by itself.
- Samples 3, 4, 10, and 16 remain important failure samples, but the issue is broader than those samples alone.

## Market Regime Attribution Summary

Aggregate regime PnL:

- MIXED: -$278.95
- RISK_OFF: -$272.48
- UNKNOWN_MARKET_DATA: $91.20
- RISK_ON: $1986.97

Interpretation:

- Losses are not only a simple risk-off problem.
- Positive aggregate PnL in RISK_ON does not offset broad failure behavior across samples and candidate groups.
- QQQ labels are marked unknown because QQQ is not currently downloaded in the main pipeline for this command.

## Data Quality Audit Summary

- Data quality blockers: 0
- Data quality warnings: 230
- Major warning counts:
  - missing OHLCV bars: 2574
  - incomplete 20d forward windows: 1980
  - metadata rejected symbols: 19
  - abnormal volume days: 7
  - split/adjustment anomaly flags: 7
  - missing QQQ regime data: 1

Conclusion:

- Data issues should be cleaned up before institutional-grade research.
- Current audit did not find a blocker strong enough to invalidate the Phase 1E conclusion.
- The missing QQQ data affects QQQ regime labels, not accepted-candidate replay mechanics.

## Phase 1F Status

- Status: `PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN`
- Do not start Phase 2.
- Do not start Phase 3.
- Do not start paper execution.
- Do not start real-money execution.
- Reason: failures are broad across themes, tickers, and regimes; data quality warnings exist but are not the primary blocker.

## Problems

- Candidate 34 failure behavior appears broad rather than a single clean theme/ticker/regime issue.
- QQQ regime labeling is incomplete because QQQ is not downloaded by the main command.
- The data-quality audit uses business-day gap approximation, so market holidays may inflate missing-bar warnings.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- yfinance data remains non-institutional retail data and should not be treated as an execution feed.

## Questions For GPT

- Should Candidate 34 now be redesigned instead of applying more threshold filters?
- Should the next research task first improve data/regime inputs, especially QQQ regime data, before redesign?
- Should GPT retire the current Nano entry-rule family if broad failure persists after one redesign attempt?
- Should theme taxonomy become a maintained config file instead of static code?

## Next Suggested Tasks

- Do not start Phase 2.
- Do not start Phase 3.
- Do not enable paper execution.
- Do not enable real-money execution.
- Ask GPT whether to redesign Candidate 34 or pause Nano tuning.
- If GPT approves more research, make it a redesign task rather than another threshold sweep.
