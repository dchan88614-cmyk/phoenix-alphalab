# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1B — Execution Risk, Stop-Out, and Drawdown Diagnostics

David's clarified roadmap remains:

1. Phase 1: simulate old dates, select a stock or NO TRADE using only past data, reveal future outcome, repeat until accuracy and risk improve.
2. Phase 2: current-market manual paper validation only after Phase 1 gates improve.
3. Phase 3: real-money execution only after Phase 1 and Phase 2 gates are satisfied.

This task is **Phase 1B only**.

Do not start Phase 2.
Do not start Phase 3.
Do not start paper trading.
Do not start live trading.
Do not loosen Candidate 34 entry thresholds yet.
Keep all output research/manual-review only.

## Why This Task

The completed Phase 1A 100-round replay found a useful but risky pattern:

- 100 replay rounds
- 34 BUY candidates
- 66 NO_TRADE rounds
- 20d forward-return accuracy: 58.82%
- 20d average forward return: 13.61%
- trade-simulation accuracy: 41.18%
- ending account value: $179.61
- max drawdown: -45.86%
- status: `PHASE_1A_NEEDS_MORE_ITERATION`

The highest-priority problem is not signal generation yet. It is execution quality and drawdown. Several picks appear to have positive 20d forward returns but were stopped out under the current simulator. Phase 1B must explain whether the drawdown comes from:

- stop placement too tight
- next-open entry gap behavior
- target/stop ordering assumptions
- volatile tickers dominating risk
- one or two path-dependent trades such as early-2024 SMCI
- sample-selection luck

## Goal

Build an execution-risk diagnostic layer over the existing Phase 1A historical replay outputs.

Use the existing 100-round replay decision process as the baseline. Do not change which ticker is selected. Only analyze what happened after selection under different execution assumptions.

## Required New Outputs

Create or update:

- `data/reports/phase1b_execution_diagnostics.csv`
- `data/reports/phase1b_execution_summary.md`
- `data/reports/phase1b_exit_policy_comparison.csv`
- `data/reports/phase1b_ticker_risk_attribution.csv`
- `REPORT_TO_GPT.md`

Keep existing Phase 1A reports intact unless regeneration is required by the command.

## Part 1: Baseline Replay Diagnostics

Read or regenerate:

- `data/reports/phase1_historical_replay_decisions.csv`
- `data/reports/phase1_historical_replay_near_misses.csv`

For every `HISTORICAL_BUY_CANDIDATE`, compute and record:

- replay_date
- ticker
- reference_price
- entry_date
- entry_price
- entry_gap_pct = entry_price / reference_price - 1
- current stop_loss
- current target_1
- current target_2
- current exit_date
- current exit_reason
- current pnl_dollars
- current trade_return_pct
- current account_return_pct
- forward_return_1d / 3d / 5d / 10d / 20d
- max_favorable_excursion_20d
- max_adverse_excursion_20d
- stopped_out_then_20d_positive
- stopped_out_then_20d_above_target_1
- stopped_out_then_20d_above_target_2
- recovered_after_stop_within_20d
- days_to_stop
- days_to_target_1_if_any
- days_to_target_2_if_any
- days_to_max_favorable_20d
- days_to_max_adverse_20d

Use future data only for diagnostics after the historical decision has already been recorded. Do not let future data affect selection or ranking.

## Part 2: Exit Policy Comparison

Compare baseline selection under multiple execution policies. The selected ticker/date set must stay fixed.

At minimum compare:

1. `baseline_current`: existing simulator behavior.
2. `atr_stop_1_5x`: current 1.5 ATR stop and current targets.
3. `atr_stop_2_0x`: 2.0 ATR stop, target_1 = 2R, target_2 = 4R.
4. `atr_stop_2_5x`: 2.5 ATR stop, target_1 = 2R, target_2 = 4R.
5. `atr_stop_3_0x`: 3.0 ATR stop, target_1 = 2R, target_2 = 4R.
6. `time_exit_20d_no_intraday_stop`: buy next session, hold to 20 trading days or last available bar; diagnostic only.
7. `close_based_stop_1_5x`: stop only if close <= stop; diagnostic only.
8. `close_based_stop_2_0x`: stop only if close <= stop; diagnostic only.

For each policy report:

- buy_count
- executed_count
- win_rate
- trade_simulation_accuracy
- average win
- average loss
- profit factor
- ending account value
- max drawdown
- worst trade account loss
- stop count
- target_1 count
- target_2 count
- time_exit count
- median holding days
- average entry_gap_pct
- percentage of stopped trades that were 20d-positive

Important: these are diagnostics only. Do not automatically adopt any policy.

## Part 3: Drawdown Attribution

Create ticker and trade-level attribution.

For each ticker selected in Phase 1A, report:

- selection count
- total pnl_dollars
- average pnl_dollars
- win rate
- worst trade pnl_dollars
- worst account_return_pct
- contribution_to_total_profit_pct
- contribution_to_total_loss_pct
- max consecutive losses if selected multiple times

Also report:

- biggest equity peak-to-trough drawdown period
- trades inside the worst drawdown period
- whether removing the single best trade leaves ending account value above $105
- whether removing the single worst trade improves max drawdown above -35%
- whether any one ticker contributes more than 50% of total profit
- whether any one ticker contributes more than 50% of total loss

## Part 4: Robustness Check Across Samples

Add optional CLI flags:

```bash
--phase1b-execution-diagnostics
--replay-rounds 100
--replay-sample-offset 0
--replay-sample-count 5
```

If `--replay-sample-count 5` is used, run five deterministic 100-round samples across the same date range using offsets 0 through 4. Each sample should still cover the full 2024-01-01 to 2026-06-30 period.

Report for each sample:

- sample_id
- replay_rounds
- buy_count
- 20d accuracy
- baseline ending account value
- baseline max drawdown
- baseline trade-simulation accuracy
- best alternative policy by ending account value subject to max drawdown better than -35%
- whether any policy achieved all Phase 1B research gates below

Do not use random sampling unless a fixed seed is explicitly provided. Deterministic reproducibility is required.

## Part 5: Phase 1B Research Gates

Mark Phase 1B status as one of:

- `PHASE_1B_FAILED`
- `PHASE_1B_NEEDS_MORE_ITERATION`
- `PHASE_1B_EXECUTION_POLICY_PROMISING_NOT_APPROVED`

Do not mark Phase 2 ready from this task.

Suggested status logic:

- `PHASE_1B_FAILED` if no tested policy has ending account value > $100 across the baseline sample.
- `PHASE_1B_NEEDS_MORE_ITERATION` if returns improve but max drawdown remains <= -35%, or trade-simulation accuracy remains < 50%.
- `PHASE_1B_EXECUTION_POLICY_PROMISING_NOT_APPROVED` only if at least one policy has:
  - ending account value > $120
  - max drawdown better than -35%
  - trade-simulation accuracy >= 50%
  - worst trade account loss better than -15%
  - at least 20 BUY decisions
  - removing the single best trade leaves ending account value > $105
  - no single ticker contributes more than 50% of total profit

Even if promising, this is not paper-trading approval. GPT review required.

## Part 6: Markdown Summary Requirements

`phase1b_execution_summary.md` must start with:

```text
PHOENIX NANO PHASE 1B — EXECUTION RISK AND DRAWDOWN DIAGNOSTICS
```

It must include:

- baseline Phase 1A recap
- core problem diagnosis
- exit policy comparison table
- drawdown attribution
- stopped-out-but-later-positive count and rate
- ticker concentration analysis
- sample robustness results if multiple samples were run
- Phase 1B status
- explicit statement: `Research/manual-review only. Do not start paper trading or live trading.`
- concrete recommendation for the next research task

## Part 7: Tests

Add or update tests for:

1. Execution diagnostics do not change the selected ticker/date decisions.
2. Future data is used only after decisions are recorded.
3. Entry gap is computed correctly.
4. Stopped-out-then-20d-positive detection is correct.
5. Exit policy comparison computes win rate, profit factor, ending value, and drawdown correctly.
6. One-position-at-a-time account replay is respected for each policy.
7. Ticker risk attribution identifies concentration.
8. Sample offsets are deterministic and produce exactly the requested number of rounds.
9. Reports are written.
10. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1b-execution-diagnostics --replay-rounds 100 --replay-sample-count 5
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1B Execution Diagnostic Summary
- Baseline Phase 1A recap
- Exit policy comparison
- Best diagnostic policy, if any
- Baseline vs best-policy ending account value
- Baseline vs best-policy max drawdown
- Baseline vs best-policy trade-simulation accuracy
- Stopped-out-then-20d-positive rate
- Drawdown attribution
- Ticker concentration findings
- Robustness across samples
- Phase 1B status
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2 or Phase 3.
