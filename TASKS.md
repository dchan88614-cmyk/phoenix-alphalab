# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1G — Candidate 35 Redesign Sandbox

This task is historical research only.

Do not start Phase 2.
Do not start Phase 3.
Do not enable paper execution.
Do not enable real-money execution.
Do not change daily scan production behavior.
Do not loosen Candidate 34 thresholds.
Do not adopt any new filter or redesigned rule as active policy.
Do not produce financial advice or an operational recommendation.

## Why This Task

Phase 1F completed the failure attribution, taxonomy, and data quality audit.

The result was:

- `PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN`
- data quality blockers: 0
- data quality warnings remain, but they did not invalidate the Phase 1E/1F conclusion
- failures were broad across themes, tickers, and regimes
- top theme loss share was only about 27.10%
- top ticker loss share was only about 10.49%
- prior `UNMAPPED` loss contribution was eliminated for accepted candidate losses
- Candidate 34 did not survive cross-validated conservative filtering

Therefore the highest-priority improvement is **not another threshold sweep** on Candidate 34.

The next research step is to build a **Candidate 35 redesign sandbox**: a small set of simple, auditable, interpretable entry-rule families, tested against Candidate 34 with strict calibration / validation / holdout separation.

This task must remain research-only even if a redesigned candidate family looks promising.

## Goal

Create Phase 1G research code that:

1. Keeps Candidate 34 as a frozen baseline.
2. Performs a small data/regime preflight cleanup before redesign testing.
3. Builds several simple Candidate 35 entry-rule families from first principles.
4. Uses only pre-entry data for all decision-side features.
5. Tests the redesigns across deterministic historical replay samples.
6. Uses calibration / validation / holdout separation to reduce overfitting.
7. Reports whether any redesign is promising enough for GPT review.
8. Does **not** activate any redesigned rule in daily scan.

## CLI

Add or update:

```bash
--phase1g-redesign-sandbox
--replay-rounds 100
--replay-sample-count 30
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1g-redesign-sandbox --replay-rounds 100 --replay-sample-count 30
```

If runtime is too high, support a clearly marked fallback:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1g-redesign-sandbox --replay-rounds 100 --replay-sample-count 20
```

A fallback run cannot approve anything beyond `PHASE_1G_INSUFFICIENT_SAMPLE_WARNING` or `PHASE_1G_REDESIGN_PROMISING_REQUIRES_FULL_SAMPLE`.

## Required Outputs

Create or update:

- `data/reports/phase1g_data_regime_preflight.csv`
- `data/reports/phase1g_candidate_family_definitions.md`
- `data/reports/phase1g_redesign_calibration_matrix.csv`
- `data/reports/phase1g_redesign_validation_matrix.csv`
- `data/reports/phase1g_redesign_holdout_results.csv`
- `data/reports/phase1g_candidate34_vs_35_comparison.csv`
- `data/reports/phase1g_rejected_decision_audit.csv`
- `data/reports/phase1g_redesign_summary.md`
- `REPORT_TO_GPT.md`

Keep earlier Phase 1 reports intact unless regeneration is required.

## Inputs

Reuse existing Phase 1 research code and outputs where useful:

- Phase 1A historical replay mechanics
- Phase 1B execution diagnostics
- Phase 1C robustness sampling
- Phase 1D pre-entry feature snapshots
- Phase 1E calibration/holdout structure
- Phase 1F taxonomy, failure attribution, and data-quality audit

Do not use future data for candidate selection, feature generation, regime labels, or ranking.
Future data may be used only after a decision is recorded, for verification.

## Part 1: Data and Regime Preflight Cleanup

Before redesign testing, improve the auditability of the replay environment.

Requirements:

1. Include SPY and QQQ market data in the Phase 1G data download / replay context, even if they are not tradable candidates.
2. Use actual available trading sessions from the downloaded market index data, or a market-calendar-aware mechanism, instead of naive business-day gap counting where possible.
3. Keep yfinance as the current retail research data source, but label it explicitly as non-institutional.
4. Create `phase1g_data_regime_preflight.csv` with:
   - `symbol`
   - `role` (`candidate`, `market_regime_index`, or `benchmark`)
   - `first_data_date`
   - `last_data_date`
   - `bar_count`
   - `missing_session_count`
   - `zero_volume_count`
   - `abnormal_volume_count`
   - `split_or_adjustment_anomaly_count`
   - `metadata_status`
   - `warnings`
5. If SPY or QQQ is unavailable, mark regime-based families as unavailable and report the blocker. Do not silently run them with `UNKNOWN_QQQ_DATA`.
6. If candidate OHLCV data has material blockers, mark the run as data-preflight blocked rather than claiming a redesign result.

This preflight is for research quality only. Do not change production daily scan behavior.

## Part 2: Candidate 35 Family Definitions

Create `phase1g_candidate_family_definitions.md`.

Define a small number of simple, auditable candidate families. Do not create dozens of variants.

Required baseline:

- `candidate34_frozen_baseline`

Required redesigned families:

1. `candidate35_trend_quality`
   - prioritizes stable uptrend quality
   - requires price above simple moving average trend checks when available
   - avoids entries too far below prior highs
   - avoids extreme volatility tails

2. `candidate35_pullback_continuation`
   - looks for a controlled pullback inside a broader uptrend
   - avoids very sharp 5d/10d pre-entry spikes
   - requires volatility and ATR to remain within conservative ranges

3. `candidate35_breakout_confirmation`
   - looks for breakout / momentum confirmation
   - requires relative volume or recent strength confirmation
   - blocks extremely extended names after a large short-term run

4. `candidate35_regime_gated_momentum`
   - uses SPY and QQQ regime labels available on or before replay_date
   - becomes more selective in mixed or risk-off regimes
   - may output more `HISTORICAL_NO_TRADE` decisions when regime is weak

5. `candidate35_low_volatility_compounder`
   - favors lower-volatility names that still pass growth/momentum-style checks
   - intentionally trades less if the watchlist is dominated by speculative high-beta names

For every family, document:

- intent
- required pre-entry features
- exact rule conditions
- ranking formula
- NO_TRADE behavior
- why it is different from Candidate 34
- expected failure mode

All ranking formulas must be deterministic and interpretable.
No black-box ML model.
No future data leakage.

## Part 3: Calibration / Validation / Holdout Design

Use deterministic replay samples.

Preferred 30-sample split:

- calibration: samples 0-9
- validation: samples 10-19
- holdout: samples 20-29

Fallback 20-sample split:

- calibration: samples 0-6
- validation: samples 7-13
- holdout: samples 14-19

Rules:

1. Candidate families may be adjusted only using calibration results.
2. At most 2 redesigned families may be promoted from calibration to validation.
3. At most 1 redesigned family may be promoted from validation to holdout.
4. Once a family reaches holdout, do not adjust thresholds, ranking formula, stop/target rules, or theme/ticker exclusions.
5. Compare all promoted families against the frozen Candidate 34 baseline.
6. Do not allow a family to pass by trading too rarely. Each evaluated sample must include enough BUY decisions to be meaningful.

## Part 4: Evaluation Metrics

For each family and sample, report:

- replay sample id
- replay rounds
- BUY count
- NO_TRADE count
- BUY rate
- simulated win rate
- 1d / 3d / 5d / 10d / 20d direction accuracy
- average and median forward returns by window
- average win dollars
- average loss dollars
- profit factor
- ending account value from $100
- max drawdown
- worst trade loss percent
- stopped-out-but-20d-positive rate
- best trade
- worst trade
- top profit ticker contribution share
- top loss ticker contribution share
- top profit theme contribution share
- top loss theme contribution share
- number of rejected decisions
- primary reject reasons

## Part 5: Rejected Decision Audit

Create `phase1g_rejected_decision_audit.csv`.

For each redesigned family, record at least the top rejected near-misses per replay date where useful.

Columns should include:

- sample_id
- replay_date
- family_name
- ticker
- reference_price
- action_if_candidate34
- action_if_candidate35
- reject_reason
- pre_entry_features used by the rule
- forward_return_20d
- simulated_pnl_if_taken_with_baseline_exit
- whether rejection avoided a loss
- whether rejection missed a win

The summary must explicitly discuss whether the redesigned family improves by avoiding losers or by accidentally removing too many trades.

## Part 6: Candidate 34 vs Candidate 35 Comparison

Create `phase1g_candidate34_vs_35_comparison.csv`.

Compare Candidate 34 baseline against each redesigned family on the same sample split.

Must include:

- family_name
- split_name (`calibration`, `validation`, `holdout`)
- sample_count
- total_buy_count
- median_buy_count_per_sample
- worst_sample_ending_value
- median_ending_value
- best_sample_ending_value
- worst_max_drawdown
- median_max_drawdown
- median_simulated_win_rate
- median_20d_accuracy
- median_profit_factor
- worst_top_ticker_loss_share
- worst_top_theme_loss_share
- pass_fail_status
- failed_gates

## Part 7: Research Gates

Do not advance to Phase 2, paper execution, or live execution from this task.

A redesigned family may only be marked `PHASE_1G_REDESIGN_PROMISING_FOR_GPT_REVIEW` if all holdout gates pass:

1. Full preferred 30-sample run completed.
2. Every holdout sample has at least 15 BUY decisions per 100 replay rounds.
3. Worst holdout sample ending account value > $105.
4. Median holdout ending account value > $120.
5. Worst holdout max drawdown better than -35%.
6. Median holdout simulated win rate >= 52%.
7. Median holdout 20d direction accuracy >= 55%.
8. Median holdout profit factor >= 1.25.
9. Worst trade loss better than -15%.
10. No single ticker contributes more than 40% of holdout total losses.
11. No single theme contributes more than 50% of holdout total losses.
12. Removing the single best holdout trade still leaves median holdout ending account value > $110.
13. Data/regime preflight has no material blocker.

If any gate fails, mark the result as research-only and not approved.

Final status must be exactly one of:

- `PHASE_1G_DATA_PREFLIGHT_BLOCKED`
- `PHASE_1G_NO_REDESIGN_SURVIVED_VALIDATION`
- `PHASE_1G_HOLDOUT_FAILED`
- `PHASE_1G_INSUFFICIENT_SAMPLE_WARNING`
- `PHASE_1G_REDESIGN_PROMISING_REQUIRES_FULL_SAMPLE`
- `PHASE_1G_REDESIGN_PROMISING_FOR_GPT_REVIEW`

Even the strongest status does not approve paper/live trading. GPT review is required.

## Part 8: Report Requirements

`phase1g_redesign_summary.md` must start with:

```text
PHOENIX NANO PHASE 1G — CANDIDATE 35 REDESIGN SANDBOX
```

It must include:

- research-only statement
- Phase 1F recap
- data/regime preflight summary
- Candidate 35 family definitions summary
- calibration results
- validation results
- holdout results
- Candidate 34 vs Candidate 35 comparison
- rejected decision audit summary
- whether improvement came from better selection, fewer trades, or over-filtering
- final Phase 1G status
- explicit statement: `Do not start paper execution or real-money execution.`
- concrete recommendation for the next research task

## Part 9: Tests

Add or update tests for:

1. Phase 1G preflight includes SPY and QQQ as regime inputs.
2. Candidate family definitions are written and include all required families.
3. Candidate 34 baseline remains frozen and unchanged.
4. Candidate 35 decision logic uses only pre-entry data.
5. Calibration / validation / holdout split is deterministic and non-overlapping.
6. Holdout evaluation does not mutate family thresholds or ranking formulas.
7. Minimum BUY-count gate prevents a family from passing by over-filtering.
8. Concentration gates are computed correctly.
9. Best-trade removal gate is computed correctly.
10. No active daily scan behavior is changed.
11. Phase 1G status never approves Phase 2, paper execution, or live execution.
12. Reports are written.
13. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1g-redesign-sandbox --replay-rounds 100 --replay-sample-count 30
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1G Redesign Summary
- Data/regime preflight summary
- Candidate family definitions
- Calibration results
- Validation results
- Holdout results
- Candidate 34 vs Candidate 35 comparison
- Rejected decision audit summary
- Phase 1G status
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2, Phase 3, paper execution, or real-money execution.
