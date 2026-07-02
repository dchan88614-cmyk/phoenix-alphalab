# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1D — Entry-Rule Failure Diagnostics

This task is **Phase 1D research only**.

Do not start Phase 2.
Do not start Phase 3.
Do not start paper trading.
Do not start live trading.
Do not loosen Candidate 34 thresholds.
Do not adopt close-based stops as the active policy.
Keep every output historical/simulated/manual-review only.

## Why This Task

Phase 1C showed that exit-policy tuning is not enough.

Latest evidence:

- 10 deterministic 100-round samples were tested.
- No policy was robust across all samples.
- `baseline_current` had the best median ending account value but only 2 passing samples.
- `close_based_stop_2_0x` had too many intraday-breach and next-open slippage realism warnings.
- Worst-sample ending values were below $100 for every policy.
- Worst-sample max drawdowns were worse than -45% for every policy.
- Failing samples were concentrated in repeated high-volatility names/themes including SMR, BBAI, F, INTC, CCJ, AFRM, HPE, HOOD, EV/mobility, AI/software, semiconductor/hardware, crypto-adjacent/high beta, and space/defense/nuclear.
- Average entry gap among captured failures was about 0.50%, so entry gaps alone do not explain the failures.

Highest-priority question:

**Which pre-entry features identify losing historical BUY candidates before entry, and can a conservative simulated filter reduce drawdown without destroying the edge?**

## Goal

Build a Phase 1D diagnostic layer that compares historical winners versus losers across deterministic replay samples, proposes conservative entry-filter hypotheses, and backtests those filters only as offline research.

This task may evaluate hypothetical filters, but it must not change the daily scan production behavior.

## CLI

Add or update CLI support:

```bash
--phase1d-entry-rule-analysis
--replay-rounds 100
--replay-sample-count 10
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1d-entry-rule-analysis --replay-rounds 100 --replay-sample-count 10
```

## Required Outputs

Create or update:

- `data/reports/phase1d_entry_rule_diagnostics.csv`
- `data/reports/phase1d_loser_feature_attribution.csv`
- `data/reports/phase1d_filter_backtest_matrix.csv`
- `data/reports/phase1d_filter_excluded_decisions.csv`
- `data/reports/phase1d_candidate_filter_summary.md`
- `data/reports/phase1d_entry_rule_summary.md`
- `REPORT_TO_GPT.md`

Keep Phase 1A, 1B, and 1C reports intact unless regeneration is required.

## Part 1: Reconstruct Pre-Entry Feature Snapshots

For every historical BUY decision in each deterministic sample, reconstruct only information available on or before the replay date / entry date.

`phase1d_entry_rule_diagnostics.csv` must include:

- sample_id
- replay_date
- ticker
- entry_date
- reference_price
- entry_price
- entry_gap_pct
- shares_with_100
- estimated_total_cost
- estimated_cash_remaining
- stop_loss
- target_1
- target_2
- stop_distance_pct
- target_1_distance_pct
- target_2_distance_pct
- max_dollar_risk
- decision_strength
- smoke_score
- failed_checks_at_selection if available
- sector_or_theme using the deterministic local mapping from Phase 1C when available
- latest_volume
- dollar_volume if available
- relative_volume_prev20 if available
- atr_14 if available
- atr_pct if available
- close_vs_sma20_pct if available
- close_vs_sma50_pct if available
- distance_from_20d_high_pct if available
- distance_from_52w_high_pct if available
- return_1d_prior if available
- return_5d_prior if available
- return_10d_prior if available
- return_20d_prior if available
- volatility_20d if available
- max_single_day_loss_20d if available
- forward_return_1d
- forward_return_3d
- forward_return_5d
- forward_return_10d
- forward_return_20d
- baseline_exit_reason
- baseline_pnl_dollars
- baseline_trade_return_pct
- baseline_account_return_pct
- stopped_out_then_20d_positive
- intraday_stop_breached
- winner_20d flag
- winner_baseline_simulation flag

If a feature is unavailable, leave it blank and explain why in the markdown summary.

## Part 2: Winner vs Loser Attribution

Create `phase1d_loser_feature_attribution.csv`.

Compare historical losing BUY decisions versus winning BUY decisions using only pre-entry features.

For each feature, compute all-sample and per-sample rows:

- feature_name
- sample_id or `ALL`
- winner_count
- loser_count
- winner_mean
- loser_mean
- winner_median
- loser_median
- loser_minus_winner_mean
- loser_minus_winner_median
- simple_separation_score
- missing_rate
- notes

Focus on:

- `atr_pct`
- `volatility_20d`
- `entry_gap_pct`
- `decision_strength`
- `smoke_score`
- `relative_volume_prev20`
- distance from 20d / 52w high
- short-term run-up before entry
- price near the max-entry limit
- repeated high-volatility themes
- repeated losing tickers

The summary must identify the top 5 suspicious pre-entry loser signals.

## Part 3: Candidate Filter Hypotheses

Create `phase1d_candidate_filter_summary.md`.

List conservative filters as offline diagnostics only. Include at least:

1. High `atr_pct` filter.
2. High `volatility_20d` filter.
3. Extreme `entry_gap_pct` filter.
4. Minimum `decision_strength` filter.
5. Minimum `smoke_score` filter.
6. Low `relative_volume_prev20` filter if the feature exists.
7. Weak distance-from-high filter if weakness predicts losers.
8. Extreme short-term run-up filter if chasing predicts losers.
9. Theme concentration cap.
10. Repeated-loser ticker cooldown inside a replay sample.

Every filter must be based only on information available at the replay date / entry date.

## Part 4: Simulated Filter Backtest Matrix

Create `phase1d_filter_backtest_matrix.csv`.

For each deterministic sample and each candidate filter, re-run the simulated account replay with `baseline_current` exits while skipping historical BUY decisions that the filter would have excluded using only pre-entry information.

Also test combinations of the best 2-3 simple filters when they are not redundant.

Required columns:

- sample_id
- filter_name
- filter_description
- replay_rounds
- original_buy_count
- filtered_buy_count
- excluded_decision_count
- excluded_loser_count
- excluded_winner_count
- excluded_stopped_out_then_20d_positive_count
- no_trade_count_after_filter
- trade_simulation_accuracy
- accuracy_1d
- accuracy_3d
- accuracy_5d
- accuracy_10d
- accuracy_20d
- average_return_20d
- median_return_20d
- average_win
- average_loss
- profit_factor
- ending_account_value
- max_drawdown
- worst_trade_account_loss
- ending_value_excluding_best_decision
- top_ticker_profit_share
- top_ticker_loss_share
- passes_phase1d_diagnostic_gate

Replay must remain chronological and must respect one open simulated position at a time.

## Part 5: Excluded Decision Audit

Create `phase1d_filter_excluded_decisions.csv`.

For every skipped historical BUY decision, record:

- sample_id
- filter_name
- replay_date
- ticker
- entry_date
- entry_price
- reference_price
- sector_or_theme
- reason_excluded
- decision_strength
- smoke_score
- atr_pct
- volatility_20d
- entry_gap_pct
- relative_volume_prev20
- baseline_exit_reason
- baseline_pnl_dollars
- forward_return_20d
- stopped_out_then_20d_positive
- would_have_been_winner_baseline_simulation
- would_have_been_winner_20d

The summary must call out filters that exclude too many winners.

## Part 6: Phase 1D Diagnostic Status

Mark Phase 1D status as one of:

- `PHASE_1D_FAILED`
- `PHASE_1D_ENTRY_FILTER_NEEDS_MORE_WORK`
- `PHASE_1D_FILTER_HYPOTHESIS_PROMISING_NOT_APPROVED`
- `PHASE_1D_ROBUSTNESS_IMPROVED_BUT_REQUIRES_GPT_REVIEW`

Do not mark Phase 2 ready from this task.

Suggested promising-filter diagnostic gate:

- median ending account value > $120 across samples
- worst-sample ending account value > $100
- median max drawdown better than -35%
- worst-sample max drawdown better than -45%
- median simulation accuracy >= 50%
- at least 15 BUY decisions in every sample after filtering
- ending value excluding best decision > $105 in the median sample
- no single ticker contributes more than 50% of total profit in any passing sample
- excluded loser count > excluded winner count
- median 20d average return remains above zero

If no filter passes, state exactly which gates failed.

## Part 7: Markdown Summary Requirements

`phase1d_entry_rule_summary.md` must start with:

```text
PHOENIX NANO PHASE 1D — ENTRY-RULE FAILURE DIAGNOSTICS
```

It must include:

- research/manual-review only statement
- Phase 1C recap
- total samples and BUY decisions analyzed
- winner vs loser feature findings
- top 5 suspicious loser signals
- filters tested
- best filter by median ending account value
- best filter by worst-sample ending account value
- best filter by drawdown reduction
- filters that excluded too many winners
- whether high-volatility themes/tickers explain the failures
- whether failures look fixable by conservative entry filters
- Phase 1D status
- explicit statement: `Do not start paper trading or live trading.`
- concrete recommendation for the next research task

## Part 8: Tests

Add or update tests for:

1. Phase 1D feature snapshots do not use future data.
2. Winner/loser attribution computes expected separation metrics.
3. Candidate filters use only pre-entry features.
4. Filtered replay is chronological and respects one open simulated position at a time.
5. Filter backtest matrix contains every sample-filter combination.
6. Excluded decision audit records excluded winners and losers.
7. Phase 1D status logic never approves Phase 2.
8. Reports are written.
9. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1d-entry-rule-analysis --replay-rounds 100 --replay-sample-count 10
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1D Entry-Rule Summary
- Samples analyzed
- BUY decisions analyzed
- Winner vs loser feature findings
- Top suspicious loser signals
- Filters tested
- Best filter by median ending value
- Best filter by worst-sample ending value
- Best filter by drawdown reduction
- Filter excluded decision audit summary
- Phase 1D status
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2, Phase 3, paper trading, or live trading.
