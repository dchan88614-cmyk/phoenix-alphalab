# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1E — Cross-Validated Conservative Filter Validation

This task is historical research only.

Do not start Phase 2.
Do not start Phase 3.
Do not enable paper execution.
Do not enable real-money execution.
Do not loosen Candidate 34 thresholds.
Do not change daily scan production behavior.
Do not adopt close-based stops as the active policy.

## Why This Task

Phase 1D found promising but unapproved filter hypotheses:

- 10 deterministic samples were analyzed.
- 344 historical BUY decisions were diagnosed.
- No filter cleared all robustness gates.
- `weak_distance_from_high` had the best median ending value but failed worst-sample and drawdown gates.
- `volatility_plus_smoke_score` had the best worst-sample ending value and best drawdown profile, but still failed the required worst-sample gate.
- Winner/loser feature separation was useful but modest.

Highest-priority question:

Can a narrow conservative filter family around `volatility_20d` plus `smoke_score` survive holdout validation without overfitting?

## Goal

Create Phase 1E validation for conservative entry filters.

The task must:

1. Reuse Phase 1D pre-entry feature snapshots where possible.
2. Generate deterministic replay samples.
3. Split samples into calibration and holdout sets.
4. Tune only on calibration samples.
5. Validate frozen filters on holdout samples.
6. Report whether any filter is robust enough for GPT review.

This task may recommend a filter for future review, but must not activate it in the daily scan.

## CLI

Add or update:

```bash
--phase1e-filter-validation
--replay-rounds 100
--replay-sample-count 20
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1e-filter-validation --replay-rounds 100 --replay-sample-count 20
```

If runtime is too high, support 10 samples as a fallback and clearly mark it as insufficient for approval.

## Required Outputs

Create or update:

- `data/reports/phase1e_threshold_sweep.csv`
- `data/reports/phase1e_filter_validation_matrix.csv`
- `data/reports/phase1e_holdout_results.csv`
- `data/reports/phase1e_excluded_decision_audit.csv`
- `data/reports/phase1e_filter_summary.md`
- `REPORT_TO_GPT.md`

Keep earlier Phase 1 reports intact unless regeneration is required.

## Part 1: Deterministic Sample Split

Generate 20 deterministic samples if possible.

Each sample has 100 replay rounds across 2024-01-01 through 2026-06-30.

Use only data available on or before each replay date for selection and filtering.

Split:

- calibration: sample IDs 0-9
- holdout: sample IDs 10-19

Fallback split for 10 samples:

- calibration: sample IDs 0-4
- holdout: sample IDs 5-9

Holdout data must never influence threshold selection.

## Part 2: Filter Family

Test these filters only.

### Baseline

`no_filter_baseline_current`

Candidate 34 unchanged, baseline current exit policy.

### Phase 1D fixed candidate

`phase1d_volatility_plus_smoke_score`

- Require `volatility_20d <= 0.0697`
- Require `smoke_score >= 0.8839`

### Small threshold grid

Test all combinations:

- `volatility_20d_max`: 0.055, 0.060, 0.065, 0.070, 0.075
- `smoke_score_min`: 0.880, 0.900, 0.920, 0.940

Filter passes only when both conditions pass.

### Limited overlays

For only the top 3 calibration filters, test:

1. `theme_cap_3_overlay`: at most 3 accepted BUY decisions per deterministic theme per sample.
2. `repeated_loser_ticker_cooldown_overlay`: after a ticker has a prior accepted losing simulated result inside a sample, skip that ticker for 60 calendar days.

The cooldown must use only prior simulated outcomes within chronological replay order. If that cannot be implemented without lookahead, skip it and explain why.

## Part 3: Calibration Rules

For each filter on calibration samples, compute:

- median ending account value
- worst-sample ending account value
- median max drawdown
- worst-sample max drawdown
- median simulated win rate
- worst-sample simulated win rate
- median BUY count
- minimum BUY count
- median 20d average return
- median profit factor
- excluded loser count
- excluded winner count

A filter is eligible for holdout only if calibration meets:

1. median ending account value > 120
2. worst-sample ending account value > 100
3. median max drawdown better than -35%
4. worst-sample max drawdown better than -45%
5. median simulated win rate >= 50%
6. minimum BUY count >= 15
7. excluded loser count > excluded winner count
8. median 20d average return > 0
9. median profit factor > 1.2

If no filter passes, still send the top 3 diagnostic filters to holdout, but mark them as `CALIBRATION_NOT_PASSED_DIAGNOSTIC_ONLY`.

Rank top 3 by:

1. best worst-sample ending account value
2. best worst-sample max drawdown
3. best median simulated win rate
4. best median ending account value
5. fewer excluded winners

## Part 4: Holdout Rules

Run selected filters on holdout samples with frozen thresholds.

A filter may be marked `PHASE_1E_FILTER_ROBUSTNESS_IMPROVED_REQUIRES_GPT_REVIEW` only if holdout meets:

1. median ending account value > 120
2. worst-sample ending account value > 100
3. median max drawdown better than -35%
4. worst-sample max drawdown better than -45%
5. median simulated win rate >= 50%
6. every holdout sample has at least 15 accepted BUY decisions
7. median 20d average return > 0
8. median profit factor > 1.2
9. no single ticker contributes more than 50% of total profit in any passing holdout sample
10. no single ticker contributes more than 50% of total loss in any passing holdout sample
11. excluded loser count > excluded winner count

Even if this passes, do not activate the filter. GPT review is required.

## Part 5: Report Requirements

`phase1e_filter_summary.md` must start with:

```text
PHOENIX NANO PHASE 1E — CROSS-VALIDATED CONSERVATIVE FILTER VALIDATION
```

It must include:

- research-only statement
- Phase 1D recap
- sample split used
- filters tested
- calibration results
- selected holdout filters
- holdout results
- whether `volatility_plus_smoke_score` survived holdout
- whether overlays helped or overfit
- excluded winner vs loser summary
- top remaining failure samples
- top remaining failure tickers/themes
- final Phase 1E status
- explicit statement: `Do not start paper execution or real-money execution.`
- concrete recommendation for the next research task

CSV files must contain enough columns to audit every threshold, sample, selected holdout filter, excluded decision, and gate failure.

## Part 6: Phase 1E Status

Mark one of:

- `PHASE_1E_FAILED`
- `PHASE_1E_FILTER_OVERFIT_NOT_APPROVED`
- `PHASE_1E_FILTER_NEEDS_MORE_WORK`
- `PHASE_1E_FILTER_ROBUSTNESS_IMPROVED_REQUIRES_GPT_REVIEW`

Never mark Phase 2 ready from this task.

## Part 7: Tests

Add or update tests for:

1. deterministic sample split
2. holdout samples are not used for threshold selection
3. filters use only pre-entry features
4. holdout filters use frozen thresholds
5. filtered replay is chronological and one-position-at-a-time
6. calibration and holdout gates
7. excluded decision audit records excluded winners and losers
8. Phase 1E status never approves Phase 2 or execution
9. reports are written
10. full pytest suite passes

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1e-filter-validation --replay-rounds 100 --replay-sample-count 20
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1E Filter Validation Summary
- Sample split used
- Filters tested
- Calibration results
- Holdout results
- Best calibration filter
- Best holdout filter
- Whether `volatility_plus_smoke_score` survived holdout
- Excluded winner vs loser summary
- Top remaining failure samples
- Top remaining failure tickers/themes
- Phase 1E status
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2, Phase 3, paper execution, or real-money execution.
