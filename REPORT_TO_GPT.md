# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1E - Cross-Validated Conservative Filter Validation.
- Added Phase 1E historical filter validation as research-only analysis.
- Reused Phase 1D pre-entry diagnostics and baseline-current replay mechanics.
- Generated 20 deterministic samples with 100 replay rounds each.
- Split samples into calibration IDs 0-9 and holdout IDs 10-19.
- Tested the required baseline, Phase 1D fixed filter, and volatility/smoke threshold grid.
- Selected top diagnostic calibration filters without using holdout data.
- Validated frozen filters and selected overlays on holdout samples.
- Added CLI flag:
  - `--phase1e-filter-validation`
- Created required outputs:
  - `data/reports/phase1e_threshold_sweep.csv`
  - `data/reports/phase1e_filter_validation_matrix.csv`
  - `data/reports/phase1e_holdout_results.csv`
  - `data/reports/phase1e_excluded_decision_audit.csv`
  - `data/reports/phase1e_filter_summary.md`
- Did not loosen Candidate 34 thresholds.
- Did not change daily scan production behavior.
- Did not adopt close-based stops.
- Did not start Phase 2.
- Did not start Phase 3.
- Did not enable paper execution.
- Did not enable real-money execution.

## Files Changed

- `src/research/phase1e_filter_validation.py`
- `src/main.py`
- `tests/test_phase1e_filter_validation.py`
- `data/reports/phase1e_threshold_sweep.csv`
- `data/reports/phase1e_filter_validation_matrix.csv`
- `data/reports/phase1e_holdout_results.csv`
- `data/reports/phase1e_excluded_decision_audit.csv`
- `data/reports/phase1e_filter_summary.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1e-filter-validation --replay-rounds 100 --replay-sample-count 20
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_phase1e_filter_validation.py -q
# 9 passed
```

```bash
.venv/bin/python -m pytest -q
# 114 passed, 1 warning in 7.97s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1e-filter-validation --replay-rounds 100 --replay-sample-count 20
```

## Phase 1E Filter Validation Summary

- Phase 1E status: `PHASE_1E_FILTER_NEEDS_MORE_WORK`
- Threshold sweep rows: 440
- Threshold-sweep filters: 22
- Threshold-sweep samples: 20
- Holdout validation rows: 90
- Holdout result rows: 9
- Excluded decision audit rows: 10289
- Calibration filters passing all gates: 0
- Holdout filters passing all gates: 0

## Sample Split Used

- Calibration samples: 0-9
- Holdout samples: 10-19
- Fallback split used: false
- Holdout data was not used for threshold selection.

## Filters Tested

- `no_filter_baseline_current`
- `phase1d_volatility_plus_smoke_score`
- 20 grid filters:
  - `volatility_20d_max`: 0.055, 0.060, 0.065, 0.070, 0.075
  - `smoke_score_min`: 0.880, 0.900, 0.920, 0.940
- Overlays for selected diagnostic filters:
  - `theme_cap_3_overlay`
  - `repeated_loser_ticker_cooldown_overlay`

## Calibration Results

No filter passed all calibration gates.

Top diagnostic calibration filters by worst-sample ending value:

| filter | worst ending | median ending | median drawdown | median win rate | min BUY count | excluded losers | excluded winners | median profit factor |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| `vol_0.055_smoke_0.900` | $114.72 | $143.85 | -21.84% | 54.20% | 10 | 139 | 82 | 2.0414 |
| `vol_0.055_smoke_0.940` | $114.04 | $136.92 | -14.95% | 57.14% | 4 | 169 | 112 | 2.4961 |
| `phase1d_volatility_plus_smoke_score` | $113.87 | $146.68 | -26.69% | 48.91% | 16 | 100 | 57 | 1.4566 |

Primary calibration failures:

- Strict filters improved drawdown but reduced minimum BUY count below 15.
- Phase 1D fixed filter kept minimum BUY count at 16 but median simulated win rate was below 50%.
- No calibration filter met every gate at once.

## Holdout Results

No selected holdout filter passed all Phase 1E holdout gates.

Best holdout filters by worst-sample ending value:

| filter | worst ending | median ending | median drawdown | median win rate | min BUY count | median profit factor | holdout pass |
|:--|--:|--:|--:|--:|--:|--:|:--|
| `vol_0.055_smoke_0.900_theme_cap_3_overlay` | $100.80 | $127.38 | -18.79% | 44.95% | 9 | 1.6040 | false |
| `vol_0.055_smoke_0.900` | $99.36 | $133.64 | -20.56% | 46.15% | 9 | 1.7408 | false |
| `vol_0.055_smoke_0.900_repeated_loser_ticker_cooldown_overlay` | $99.36 | $132.27 | -21.87% | 43.06% | 9 | 1.7526 | false |

## Best Calibration Filter

- `vol_0.055_smoke_0.900`
- Best by calibration worst-sample ending account value.
- Failed calibration because minimum BUY count was 10, below the required 15.

## Best Holdout Filter

- `vol_0.055_smoke_0.900_theme_cap_3_overlay`
- Worst-sample ending value: $100.80
- Median ending value: $127.38
- Median max drawdown: -18.79%
- Failed holdout because median simulated win rate was 44.95%, minimum BUY count was 9, and top ticker profit share exceeded 50%.

## Whether `volatility_plus_smoke_score` Survived Holdout

- It did not survive holdout.
- Phase 1D fixed filter holdout metrics:
  - Median ending account value: $131.21
  - Worst-sample ending account value: $94.44
  - Median max drawdown: -27.99%
  - Worst-sample max drawdown: -34.54%
  - Median simulated win rate: 46.25%
  - Minimum BUY count: 15
  - Median profit factor: 1.3257
  - Holdout gate pass: false

## Excluded Winner vs Loser Summary

- Excluded losers: 6323
- Excluded winners: 3966
- The filters exclude more losers than winners overall, but the remaining holdout trades still do not meet robustness requirements.

## Top Remaining Failure Samples

Worst remaining failure rows in the threshold sweep included:

- sample 4 / `no_filter_baseline_current`: ending value $43.16, max drawdown -64.14%.
- sample 16 / `no_filter_baseline_current`: ending value $56.70, max drawdown -57.20%.
- sample 10 / `no_filter_baseline_current`: ending value $57.53, max drawdown -67.57%.
- sample 3 / `no_filter_baseline_current`: ending value $60.49, max drawdown -61.50%.
- sample 3 / `vol_0.075_smoke_0.940`: ending value $66.22, max drawdown -45.81%.

## Top Remaining Failure Tickers/Themes

Top losing themes:

- UNMAPPED: 124
- EV / mobility: 65
- AI / software: 57
- semiconductor / hardware: 52
- space / defense / nuclear: 47
- crypto-adjacent / high beta: 40

Top losing tickers:

- RIVN: 29
- RKLB: 27
- F: 24
- INTC: 24
- BBAI: 23
- XPEV: 23
- HPE: 19
- CORZ: 19

## Phase 1E Status

- Status: `PHASE_1E_FILTER_NEEDS_MORE_WORK`
- Never mark Phase 2 ready from this task.
- Do not start paper execution or real-money execution.
- Reason: the narrow volatility/smoke family improves some risk metrics but fails calibration and holdout robustness gates.

## Problems

- No calibration filter passed all required gates.
- No holdout filter passed all required gates.
- The best holdout overlay had worst-sample ending above $100 but failed minimum BUY count, win-rate, and top-profit-concentration gates.
- The Phase 1D fixed filter failed holdout with worst-sample ending below $100 and median win rate below 50%.
- Strict thresholds reduce trade count too much for Nano approval.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- yfinance data remains non-institutional retail data and should not be treated as an execution feed.

## Questions For GPT

- Should Phoenix Nano stop tuning this volatility/smoke entry-filter family?
- Should the next task focus on the repeated failure samples 3, 4, 10, and 16 rather than broad threshold sweeps?
- Should GPT require a minimum BUY count of 15 per sample, or is that gate intentionally forcing broader robustness?
- Should unmapped and EV/mobility names be separately diagnosed before any further filter work?

## Next Suggested Tasks

- Do not start Phase 2.
- Do not start Phase 3.
- Do not enable paper execution.
- Do not enable real-money execution.
- Ask GPT whether to stop Nano entry-filter tuning or run one narrow failure-regime analysis.
- If GPT approves another research task, focus on failure samples and themes rather than adding new factor families.
