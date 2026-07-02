# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1I - Data Quality, Vendor Validation, and Universe Design Audit.
- Added historical research-only Phase 1I data/universe audit code.
- Added CLI flag:
  - `--phase1i-data-universe-audit`
- Audited watchlist symbols plus SPY/QQQ.
- Added symbol-level data quality grading.
- Added vendor validation matrix with explicit `NO_SECOND_SOURCE` handling.
- Added data gap incident log.
- Added universe composition audit.
- Added pre-declared universe variants.
- Re-ran only frozen strategies:
  - `candidate34_frozen_baseline`
  - `candidate35_trend_quality_frozen`
- Added strategy-vs-universe attribution.
- Created required outputs:
  - `data/reports/phase1i_symbol_data_quality_audit.csv`
  - `data/reports/phase1i_vendor_validation_matrix.csv`
  - `data/reports/phase1i_universe_composition_audit.csv`
  - `data/reports/phase1i_universe_variant_backtest_matrix.csv`
  - `data/reports/phase1i_universe_variant_holdout_results.csv`
  - `data/reports/phase1i_data_gap_incident_log.csv`
  - `data/reports/phase1i_rejected_symbol_audit.csv`
  - `data/reports/phase1i_strategy_vs_universe_attribution.csv`
  - `data/reports/phase1i_data_universe_summary.md`
- Did not start Phase 2.
- Did not start Phase 3.
- Did not enable paper execution.
- Did not enable real-money execution.
- Did not change daily scan production behavior.
- Did not loosen Candidate 34 thresholds.
- Did not adopt Candidate 35 or any overlay as active policy.
- Did not create Candidate 36 entry rules.
- Did not perform another threshold sweep.
- Did not produce financial advice or an operational recommendation.

## Files Changed

- `src/main.py`
- `src/research/phase1i_data_universe_audit.py`
- `tests/test_phase1i_data_universe_audit.py`
- `data/reports/phase1i_symbol_data_quality_audit.csv`
- `data/reports/phase1i_vendor_validation_matrix.csv`
- `data/reports/phase1i_universe_composition_audit.csv`
- `data/reports/phase1i_universe_variant_backtest_matrix.csv`
- `data/reports/phase1i_universe_variant_holdout_results.csv`
- `data/reports/phase1i_data_gap_incident_log.csv`
- `data/reports/phase1i_rejected_symbol_audit.csv`
- `data/reports/phase1i_strategy_vs_universe_attribution.csv`
- `data/reports/phase1i_data_universe_summary.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1i-data-universe-audit --replay-rounds 100 --replay-sample-count 30
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_phase1i_data_universe_audit.py -q
# 9 passed, 1 warning
```

```bash
.venv/bin/python -m pytest -q
# 150 passed, 1 warning in 29.21s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1i-data-universe-audit --replay-rounds 100 --replay-sample-count 30
```

## Phase 1I Data / Universe Summary

- Summary file starts with the required heading:
  - `PHOENIX NANO PHASE 1I — DATA QUALITY, VENDOR VALIDATION, AND UNIVERSE DESIGN AUDIT`
- Final status: `PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH`
- Phase 1I did not approve any strategy, universe, data source, daily scan change, paper execution, or real-money execution.

## Data Quality PASS / WARN / FAIL Counts

Symbol audit rows: 119.

- PASS: 0
- WARN: 98
- FAIL: 21

Interpretation:

- Most usable rows are still WARN because they rely on yfinance as a single retail-grade vendor.
- FAIL count is above the 10% Phase 1I data-blocker threshold.
- This supports pausing strategy iteration until data/vendor and universe hygiene improve.

## Vendor Validation Coverage

- `NO_SECOND_SOURCE`: 119
- No stable secondary OHLCV source is configured without secrets.
- Phoenix Nano remains dependent on a single retail-grade data source.
- The current research should not be treated as execution-grade.

## Data Gap Incidents

- Incident rows: 32.
- Severity counts:
  - HIGH: 1
  - MEDIUM: 25
  - LOW: 6
- Key incidents:
  - `BITF` yfinance 404.
  - `BITF` metadata incomplete.
  - multiple metadata rejections from exchange/keyword filters.
  - split/adjustment anomaly flags on APP, ARM, EDIT, NVAX, OKLO, and UPST.
  - abnormal volume flags on AVAV, DASH, DDOG, DUOL, EDIT, and NVAX.

## Universe Composition Findings

- Watchlist tickers audited: 117.
- Data-quality WARN: 96.
- Data-quality FAIL: 21.
- Price under $50 count: 27.
- Price under $20 count: 19.
- Avg dollar volume pass count: 98.
- Theme count: 15.
- Top theme ticker share: 16.24%.
- High-beta or speculative theme share: 29.91%.
- Crypto-adjacent count: 5.
- Biotech count: 7.
- EV/mobility count: 10.
- AI/software count: 4.
- Semiconductor/hardware count: 14.
- Universe quality assessment: `DATA_QUALITY_BLOCKER`.

## Universe Variant Holdout Results

No universe variant passed holdout gates.

Candidate 35 trend-quality holdout:

| universe variant | median size | worst ending | median ending | worst drawdown | median win rate | median 20d accuracy | median PF | status |
|:--|--:|--:|--:|--:|--:|--:|--:|:--|
| current_watchlist_full | 98 | 196.23 | 245.77 | -49.09% | 51.55% | 63.48% | 1.51 | FAIL |
| data_quality_pass_only | 96 | 196.23 | 245.77 | -49.09% | 51.55% | 63.48% | 1.51 | FAIL |
| theme_balanced_clean | 90 | 204.90 | 245.77 | -49.09% | 52.38% | 64.24% | 1.55 | FAIL |
| metadata_and_price_clean | 27 | 104.74 | 159.54 | -63.41% | 47.21% | 58.05% | 1.26 | FAIL |
| liquidity_and_price_clean | 27 | 104.74 | 159.54 | -63.41% | 47.21% | 58.05% | 1.26 | FAIL |
| conservative_research_universe | 26 | 104.74 | 159.54 | -63.41% | 47.21% | 58.05% | 1.26 | FAIL |

Main failure modes:

- Current full universe still fails drawdown, win rate, and theme loss concentration.
- Theme-balanced universe slightly improves win rate and 20d accuracy but still fails drawdown and theme concentration.
- Price/liquidity/metadata-clean variants reduce universe size sharply and worsen performance.

## Candidate 34 vs Candidate 35 Across Universe Variants

- Candidate 34 failed every universe variant.
- Candidate 35 trend-quality remained stronger than Candidate 34 on the full and theme-balanced universes.
- Candidate 35 still failed required holdout gates across every variant.
- No clean universe result justifies promotion or paper execution.

## Strategy-vs-Universe Attribution

- Attribution rows: 10.
- Most universe variants removed more winner dollars than loser dollars.
- `data_quality_pass_only` removed only 2 symbols and did not change Candidate 35 results.
- `theme_balanced_clean` improved Candidate 35 win rate and 20d accuracy slightly, but did not reduce drawdown or theme concentration enough.
- Diagnosis rows classify as `STRATEGY_BLOCKER`, but the final status is data-blocked because the symbol audit exceeds the data-quality failure threshold and vendor validation has no secondary source.

## Final Phase 1I Status

- Status: `PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH`
- Do not start Phase 2.
- Do not start Phase 3.
- Do not enable paper execution.
- Do not enable real-money execution.
- Do not mark Phoenix Nano as live-tradable.
- Do not adopt Candidate 35, Phase 1H overlays, or any universe variant as active policy.
- Reason: the watchlist has too many FAIL-grade data/universe rows and no secondary vendor validation, while clean universe variants do not pass holdout.

## Problems

- 21 of 119 audited symbols are FAIL-grade.
- 119 of 119 vendor validation rows are `NO_SECOND_SOURCE`.
- yfinance remains a single retail-grade data dependency.
- `BITF` continues to produce yfinance 404 / metadata incomplete behavior.
- Several symbols have split/adjustment or abnormal-volume warnings that need secondary validation.
- Current taxonomy still has 19 `UNMAPPED_LOW_CONFIDENCE` symbols.
- Universe cleaning did not solve Candidate 35 drawdown or theme concentration.

## Questions For GPT

- Should Phoenix Nano pause strategy iteration until a secondary data source is added?
- Should the watchlist be rebuilt from a cleaner listing/universe process instead of hand-curated high-beta names?
- Should unmapped taxonomy rows be resolved before any further strategy tests?
- Should Phase 1J focus on data vendor integration and symbol-master hygiene rather than factor/rule changes?

## Next Suggested Tasks

- Do not start Phase 2.
- Do not start Phase 3.
- Do not enable paper execution.
- Do not enable real-money execution.
- Pause candidate-rule iteration.
- Add secondary vendor validation or a symbol-master/listing-validation process before more Phoenix Nano strategy work.
