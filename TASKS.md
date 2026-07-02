# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1H — Trend-Quality Risk Overlay and Drawdown Compression

This task is historical research only.

Do not start Phase 2.
Do not start Phase 3.
Do not enable paper execution.
Do not enable real-money execution.
Do not change daily scan production behavior.
Do not loosen Candidate 34 thresholds.
Do not adopt Candidate 35 or any overlay as active policy.
Do not produce financial advice or an operational recommendation.

## Why This Task

Phase 1G completed the Candidate 35 redesign sandbox.

The result was:

- `PHASE_1G_HOLDOUT_FAILED`
- Candidate 34 frozen baseline failed all major robustness gates.
- Candidate 35 did not earn promotion to active policy.
- The strongest redesigned family was `candidate35_trend_quality`.
- `candidate35_trend_quality` materially improved ending-value, 20d direction accuracy, and profit factor versus Candidate 34.
- But it still failed risk gates:
  - worst holdout max drawdown was about `-49.09%`
  - median simulated win rate was about `51.55%`, below the 52% gate
  - top-theme loss share was about `53.20%`, above the 50% concentration gate

Therefore the highest-priority improvement is **not another broad Candidate 36 redesign** and not another unbounded threshold sweep.

The next optimized research step is to keep `candidate35_trend_quality` frozen as a sandbox base family and test a very small number of auditable, pre-declared **risk overlays** whose only purpose is to reduce drawdown and theme concentration without overfitting or trading too rarely.

This task must remain research-only even if one overlay looks strong.

## Goal

Create Phase 1H research code that:

1. Freezes `candidate35_trend_quality` from Phase 1G as the base sandbox family.
2. Re-runs Candidate 34 frozen baseline and Candidate 35 trend-quality baseline for comparison.
3. Tests a small set of pre-declared risk overlays on top of Candidate 35 trend-quality.
4. Uses only data available on or before each replay date for decisions, overlays, cooldowns, and regime gates.
5. Uses calibration / validation / holdout separation.
6. Explains whether any overlay reduces drawdown by avoiding bad trades or merely overfilters.
7. Does **not** activate any overlay in daily scan.

## CLI

Add or update:

```bash
--phase1h-risk-overlay-sandbox
--replay-rounds 100
--replay-sample-count 30
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1h-risk-overlay-sandbox --replay-rounds 100 --replay-sample-count 30
```

If runtime is too high, support a clearly marked fallback:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1h-risk-overlay-sandbox --replay-rounds 100 --replay-sample-count 20
```

A fallback run cannot approve anything beyond `PHASE_1H_INSUFFICIENT_SAMPLE_WARNING`.

## Required Outputs

Create or update:

- `data/reports/phase1h_overlay_definitions.md`
- `data/reports/phase1h_overlay_calibration_matrix.csv`
- `data/reports/phase1h_overlay_validation_matrix.csv`
- `data/reports/phase1h_overlay_holdout_results.csv`
- `data/reports/phase1h_candidate34_vs_35_vs_overlay.csv`
- `data/reports/phase1h_drawdown_compression_attribution.csv`
- `data/reports/phase1h_theme_concentration_audit.csv`
- `data/reports/phase1h_excluded_trade_counterfactual.csv`
- `data/reports/phase1h_risk_overlay_summary.md`
- `REPORT_TO_GPT.md`

Keep earlier Phase 1 reports intact unless regeneration is required.

## Inputs

Reuse existing Phase 1 research code and outputs where useful:

- Phase 1A historical replay mechanics
- Phase 1B execution diagnostics
- Phase 1C robustness sampling
- Phase 1D pre-entry feature snapshots
- Phase 1E calibration / holdout structure
- Phase 1F taxonomy, failure attribution, and data-quality audit
- Phase 1G Candidate 35 family definitions and results

Do not use future data for candidate selection, overlay decisions, feature generation, regime labels, cooldowns, or ranking.
Future data may be used only after a decision is recorded, for verification.

## Part 1: Freeze Baselines

Create or update reusable functions so Phase 1H can evaluate:

1. `candidate34_frozen_baseline`
2. `candidate35_trend_quality_frozen`
3. Candidate 35 trend-quality plus each Phase 1H overlay

Requirements:

- Do not change Candidate 34 rules.
- Do not change Phase 1G `candidate35_trend_quality` core entry rules, ranking formula, or baseline exit policy.
- If a bug fix is required to reproduce Phase 1G, document the bug and re-run Candidate 34 and Candidate 35 baselines on the same samples.
- Store any reproducibility warning in `REPORT_TO_GPT.md`.

## Part 2: Overlay Definitions

Create `phase1h_overlay_definitions.md`.

Define only the following overlays. Do not create dozens of variants.

### Overlay A: Market Regime Risk-Off Skip

Name:

- `overlay_market_regime_risk_off_skip`

Intent:

- Skip trend-quality candidates when SPY/QQQ regime is clearly weak before the replay decision.

Allowed pre-entry inputs:

- SPY close relative to 50d and 200d SMA
- QQQ close relative to 50d and 200d SMA
- SPY / QQQ 20d return
- SPY / QQQ 20d realized volatility

Do not use future index returns.

### Overlay B: High Volatility / ATR Tail Skip

Name:

- `overlay_high_volatility_tail_skip`

Intent:

- Skip candidate entries with extreme pre-entry volatility or ATR risk tails.

Allowed pre-entry inputs:

- candidate `atr_pct`
- candidate `volatility_20d`
- candidate `max_adverse_recent_window` if already available from past-only bars
- candidate gap/extension features available before entry

### Overlay C: Theme Loss Cooldown

Name:

- `overlay_theme_loss_cooldown`

Intent:

- Reduce repeated losses from the same theme without hard-coding future losers.

Allowed inputs:

- only prior simulated decisions and exits in the same sequential replay account path
- theme taxonomy from Phase 1F
- realized prior trade result known before the current replay date

Rules:

- If the most recent closed trade in a theme lost more than a configurable threshold, skip that theme for a configurable number of completed replay decisions.
- Calibration may test only a small grid: loss threshold in `[-5%, -8%, -10%]`; cooldown length in `[3, 5, 8]` replay decisions.
- Validation / holdout must use the fixed selected parameters.

### Overlay D: Ticker Loss Cooldown

Name:

- `overlay_ticker_loss_cooldown`

Intent:

- Avoid repeated losses from the same ticker without permanently banning any ticker.

Allowed inputs:

- only prior simulated decisions and exits in the same sequential replay account path
- ticker identity
- realized prior trade result known before the current replay date

Rules:

- If the prior trade in the same ticker was a loss greater than a configurable threshold, skip that ticker for a configurable number of completed replay decisions.
- Calibration may test only a small grid: loss threshold in `[-5%, -8%, -10%]`; cooldown length in `[5, 10, 15]` replay decisions.
- Validation / holdout must use the fixed selected parameters.

### Overlay E: Combined Conservative Overlay

Name:

- `overlay_combined_conservative`

Intent:

- Combine only the best one or two overlays from calibration if, and only if, they independently improve drawdown without excessive overfiltering.

Rules:

- At most two overlays may be combined.
- Do not combine overlays that both mainly reduce BUY count without improving loss avoidance quality.
- The combined overlay must be frozen before validation and unchanged in holdout.

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

1. Overlay parameters may be selected only using calibration results.
2. At most 2 standalone overlays may be promoted from calibration to validation.
3. At most 1 combined overlay may be promoted from calibration to validation.
4. At most 1 final overlay policy may be promoted from validation to holdout.
5. Once an overlay reaches holdout, do not adjust thresholds, ranking formula, stop/target rules, theme mapping, ticker exclusions, or cooldown parameters.
6. Compare all promoted overlays against Candidate 34 frozen baseline and Candidate 35 trend-quality frozen baseline on the same sample split.
7. Do not allow an overlay to pass by trading too rarely.

## Part 4: Evaluation Metrics

For each family / overlay and sample, report:

- sample_id
- split_name
- replay_rounds
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
- number of trades excluded by overlay
- excluded-loser count
- excluded-winner count
- excluded-loser dollars avoided
- excluded-winner dollars missed
- overlay false-positive rate: excluded winners / all excluded trades
- overlay false-negative rate: accepted losers / all accepted trades

## Part 5: Drawdown Compression Attribution

Create `phase1h_drawdown_compression_attribution.csv`.

For Candidate 35 trend-quality baseline and each tested overlay, identify the largest drawdown episodes per sample.

Columns should include:

- sample_id
- policy_name
- drawdown_start_replay_date
- drawdown_end_replay_date
- drawdown_depth
- number_of_trades_in_drawdown
- tickers_in_drawdown
- themes_in_drawdown
- worst_trade_in_drawdown
- whether_overlay_excluded_worst_trade
- whether_overlay_reduced_drawdown
- whether_overlay_delayed_or_shifted_drawdown

The summary must explicitly say whether drawdown reduction came from true loss avoidance, smaller trade count, or luck/sample path changes.

## Part 6: Theme Concentration Audit

Create `phase1h_theme_concentration_audit.csv`.

For Candidate 35 trend-quality baseline and each overlay, report:

- sample_id
- policy_name
- theme
- theme_buy_count
- theme_total_pnl
- theme_loss_share
- theme_profit_share
- largest_losing_ticker_in_theme
- largest_losing_trade_date
- overlay_effect_on_theme_buy_count
- overlay_effect_on_theme_pnl

The summary must specifically assess whether top-theme loss concentration can be reduced below 50% without destroying account performance.

## Part 7: Excluded Trade Counterfactual

Create `phase1h_excluded_trade_counterfactual.csv`.

For each trade skipped by an overlay, record:

- sample_id
- replay_date
- overlay_name
- ticker
- theme
- reference_price
- baseline_candidate35_action
- overlay_action
- skip_reason
- pre_entry_features_used
- forward_return_20d
- simulated_pnl_if_taken_with_baseline_exit
- whether_skip_avoided_loss
- whether_skip_missed_win
- whether_skip_missed_large_win

A skipped trade must not be counted as improvement unless the counterfactual outcome is clearly measured after the baseline decision would have been recorded.

## Part 8: Research Gates

Do not advance to Phase 2, paper execution, or live execution from this task.

An overlay may only be marked `PHASE_1H_RISK_OVERLAY_PROMISING_FOR_GPT_REVIEW` if all holdout gates pass:

1. Full preferred 30-sample run completed.
2. Every holdout sample has at least 30 BUY decisions per 100 replay rounds.
3. Median holdout BUY count is at least 45 per 100 replay rounds.
4. Worst holdout sample ending account value > $110.
5. Median holdout ending account value > $130.
6. Worst holdout max drawdown better than -35%.
7. Median holdout simulated win rate >= 52%.
8. Median holdout 20d direction accuracy >= 58%.
9. Median holdout profit factor >= 1.30.
10. Worst trade loss better than -15%.
11. No single ticker contributes more than 35% of holdout total losses.
12. No single theme contributes more than 45% of holdout total losses.
13. Removing the single best holdout trade still leaves median holdout ending account value > $115.
14. Excluded-trade audit shows the overlay avoided more losing dollars than winning dollars missed.
15. No data/regime preflight blocker.

If any gate fails, mark the result as research-only and not approved.

Final status must be exactly one of:

- `PHASE_1H_DATA_BLOCKED`
- `PHASE_1H_NO_OVERLAY_SURVIVED_VALIDATION`
- `PHASE_1H_HOLDOUT_FAILED`
- `PHASE_1H_OVERFILTERED`
- `PHASE_1H_INSUFFICIENT_SAMPLE_WARNING`
- `PHASE_1H_RISK_OVERLAY_PROMISING_FOR_GPT_REVIEW`

Even the strongest status does not approve paper/live trading. GPT review is required.

## Part 9: Report Requirements

`phase1h_risk_overlay_summary.md` must start with:

```text
PHOENIX NANO PHASE 1H — TREND-QUALITY RISK OVERLAY AND DRAWDOWN COMPRESSION
```

It must include:

- research-only statement
- Phase 1G recap
- frozen baseline reproducibility check
- overlay definitions summary
- calibration results
- validation results
- holdout results
- Candidate 34 vs Candidate 35 vs overlay comparison
- drawdown compression attribution
- theme concentration audit
- excluded trade counterfactual summary
- whether improvement came from true risk reduction, fewer trades, or overfitting
- final Phase 1H status
- explicit statement: `Do not start paper execution or real-money execution.`
- concrete recommendation for the next research task

## Part 10: Tests

Add or update tests for:

1. Candidate 34 baseline remains frozen and unchanged.
2. Candidate 35 trend-quality baseline is reproducible from Phase 1G definitions.
3. All overlay decisions use only pre-entry data and prior closed simulated trades.
4. Market regime overlay never uses future SPY/QQQ returns.
5. Theme/ticker cooldown overlays only use information known before the current replay date.
6. Calibration / validation / holdout split is deterministic.
7. Holdout parameters cannot be changed after validation selection.
8. Overlay outputs include excluded trade counterfactuals.
9. Drawdown attribution reports are written.
10. Theme concentration audit reports are written.
11. Overfiltering is detected when BUY count falls below gates.
12. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1h-risk-overlay-sandbox --replay-rounds 100 --replay-sample-count 30
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1H Risk Overlay Summary
- Baseline reproducibility check
- Candidate 34 baseline results
- Candidate 35 trend-quality baseline results
- Overlay calibration results
- Overlay validation results
- Overlay holdout results
- Drawdown compression attribution
- Theme concentration audit
- Excluded trade counterfactual summary
- BUY count / NO_TRADE count / BUY rate
- Accuracy: 1d / 3d / 5d / 10d / 20d
- Trade-simulation accuracy
- Account ending value
- Max drawdown
- Profit factor
- Worst trade loss
- Top ticker/theme contribution shares
- Phase 1H status
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2 or Phase 3.
