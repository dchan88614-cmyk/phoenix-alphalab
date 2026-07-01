# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1C — Robustness Failure Analysis and Close-Stop Realism

David's product roadmap remains:

1. **Phase 1: historical replay training** — simulate old dates using only data available up to each date, select one stock or `NO_TRADE`, reveal future outcome, and improve accuracy/risk.
2. **Phase 2: current-market manual paper validation** — only after Phase 1 gates are materially stronger and GPT reviews the evidence.
3. **Phase 3: real-money execution** — only after Phase 1 and Phase 2 gates are satisfied.

This task is **Phase 1C only**.

Do not start Phase 2.
Do not start Phase 3.
Do not start paper trading.
Do not start live trading.
Do not loosen Candidate 34 entry thresholds.
Do not adopt `close_based_stop_2_0x` as a real policy yet.
Keep all output research/manual-review only.

## Why This Task

Phase 1B found a promising but not approved execution hypothesis:

- Baseline Phase 1A sample: 100 replay rounds, 34 BUYs, 66 NO_TRADE.
- Baseline 20d accuracy: 58.82%.
- Baseline ending account value: $179.61.
- Baseline max drawdown: -45.86%.
- Baseline trade-simulation accuracy: 41.18%.
- `close_based_stop_2_0x` improved the baseline sample to ending value about $483.59, max drawdown about -31.46%, and trade-simulation accuracy about 53.85%.

But robustness was mixed:

- Samples 0, 1, and 2 were promising or passed a diagnostic policy gate.
- Samples 3 and 4 failed badly, with ending account values near $60.49 and $43.16 and max drawdowns worse than -60%.
- `close_based_stop_2_0x` may be optimistic because close-based stops can hide intraday stop breaches.

The highest-priority research question is:

**Is the Phase 1B improvement real and robust, or was it caused by one favorable sample and an unrealistic close-based stop assumption?**

## Goal

Build a Phase 1C robustness layer that explains why deterministic samples 3 and 4 failed and stress-tests the `close_based_stop_2_0x` hypothesis under more realistic stop assumptions.

The selected ticker/date decisions must remain frozen for each replay sample. Phase 1C may analyze execution, regimes, sample failures, stop behavior, and diagnostics, but must not change the Candidate 34 entry rules yet.

## CLI

Add or update CLI support:

```bash
--phase1c-robustness-analysis
--replay-rounds 100
--replay-sample-count 10
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1c-robustness-analysis --replay-rounds 100 --replay-sample-count 10
```

If runtime is too high, use 5 deterministic samples but keep the implementation capable of 10.

## Required Outputs

Create or update:

- `data/reports/phase1c_policy_robustness_matrix.csv`
- `data/reports/phase1c_sample_failure_trades.csv`
- `data/reports/phase1c_close_stop_realism.csv`
- `data/reports/phase1c_regime_attribution.csv`
- `data/reports/phase1c_robustness_summary.md`
- `REPORT_TO_GPT.md`

Keep Phase 1A and Phase 1B reports intact unless regeneration is required by the command.

## Part 1: Full Policy Robustness Matrix

For each deterministic sample and each execution policy, compute one row in `phase1c_policy_robustness_matrix.csv`.

Use at least these policies:

1. `baseline_current`
2. `atr_stop_2_0x`
3. `atr_stop_2_5x`
4. `time_exit_20d_no_intraday_stop`
5. `close_based_stop_2_0x`
6. `close_based_stop_2_0x_with_intraday_breach_flag`
7. `close_confirmed_stop_2_0x_next_open_exit`
8. `hybrid_close_stop_2_0x_intraday_catastrophic_3_0x`

Definitions:

- `close_based_stop_2_0x_with_intraday_breach_flag`: same exit behavior as close-based stop, but records every trade where intraday low breached the stop before the close-based exit.
- `close_confirmed_stop_2_0x_next_open_exit`: stop triggers only when close <= stop; exit at next trading day's open if available, otherwise close.
- `hybrid_close_stop_2_0x_intraday_catastrophic_3_0x`: primary stop is close-based 2.0x ATR; catastrophic intraday stop exits if price breaches 3.0x ATR intraday.

Required columns:

- sample_id
- replay_rounds
- policy
- buy_count
- no_trade_count
- executed_count
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
- ending_value_excluding_best_trade
- top_ticker_profit_share
- top_ticker_loss_share
- stop_count
- target_1_count
- target_2_count
- time_exit_count
- median_holding_days
- average_entry_gap_pct
- intraday_stop_breach_count
- intraday_stop_breach_rate
- passes_phase1c_policy_gate

## Part 2: Sample Failure Analysis

Create `phase1c_sample_failure_trades.csv`.

Focus especially on samples that fail:

- ending account value <= $100
- max drawdown <= -35%
- trade_simulation_accuracy < 50%
- 20d accuracy <= 50%

For every losing trade in failing samples, record:

- sample_id
- replay_date
- ticker
- entry_date
- entry_price
- reference_price
- entry_gap_pct
- exit_date
- exit_reason
- pnl_dollars
- trade_return_pct
- account_return_pct
- forward_return_20d
- max_favorable_excursion_20d
- max_adverse_excursion_20d
- stopped_out_then_20d_positive
- intraday_stop_breached
- close_recovered_after_intraday_breach
- days_to_stop
- days_to_max_adverse_20d
- failed_checks_at_selection if available
- decision_strength
- smoke_score
- sector_or_theme if available, otherwise blank

The summary must explain whether failing samples were caused mostly by:

- a few outlier tickers
- repeated losses in one theme, such as EV, AI, small-cap momentum, crypto-adjacent, or semiconductor
- bad entry gaps
- broad market regime
- stop assumptions
- weak entry signal quality
- sample-selection luck

## Part 3: Close-Based Stop Realism

Create `phase1c_close_stop_realism.csv`.

For every BUY candidate where `close_based_stop_2_0x` differs from `baseline_current` or where intraday low breaches the close-based stop, record:

- sample_id
- replay_date
- ticker
- policy
- baseline_exit_reason
- close_based_exit_reason
- baseline_pnl_dollars
- close_based_pnl_dollars
- intraday_low_breached_close_stop
- breach_date
- breach_low
- breach_stop_price
- same_day_close
- same_day_recovered_above_stop
- next_day_open_after_close_stop
- close_confirmed_exit_pnl_dollars
- hybrid_catastrophic_exit_pnl_dollars
- realism_warning

`realism_warning` should be one of:

- `NO_WARNING`
- `INTRADAY_STOP_BREACH_IGNORED_BY_CLOSE_STOP`
- `GAP_BEYOND_STOP`
- `CLOSE_STOP_REQUIRES_NEXT_OPEN_SLIPPAGE`
- `POLICY_TOO_OPTIMISTIC_FOR_RESEARCH_GATE`

The markdown summary must explicitly state whether `close_based_stop_2_0x` remains a plausible hypothesis after realism checks.

## Part 4: Regime and Theme Attribution

Create `phase1c_regime_attribution.csv`.

For each sample and quarter/month, aggregate:

- sample_id
- period
- policy
- trade_count
- win_count
- loss_count
- total_pnl_dollars
- average_pnl_dollars
- max_drawdown_contribution
- tickers_in_period
- worst_ticker
- worst_trade_pnl_dollars
- average_entry_gap_pct
- average_forward_return_20d

If sector/theme metadata is available or easy to derive, also aggregate by ticker theme. If not available, use a deterministic local mapping for repeated tickers in the report, for example:

- EV / mobility: RIVN, F, ACHR, JOBY
- AI / software: AI, PLTR, PATH, BBAI
- semiconductor / hardware: SMCI, INTC, HPE
- crypto-adjacent / high beta: CORZ, IREN, HOOD
- space / defense / nuclear: RKLB, KTOS, OKLO, CCJ

Do not use external web lookup for theme mapping unless already available; keep it deterministic and documented.

## Part 5: Phase 1C Research Gates

Mark Phase 1C status as one of:

- `PHASE_1C_FAILED`
- `PHASE_1C_NEEDS_ENTRY_RULE_WORK`
- `PHASE_1C_EXECUTION_HYPOTHESIS_NEEDS_REALISM_WORK`
- `PHASE_1C_ROBUSTNESS_PROMISING_NOT_APPROVED`

Do not mark Phase 2 ready from this task.

Suggested status logic:

- `PHASE_1C_FAILED` if no policy has median ending account value > $100 across all samples.
- `PHASE_1C_NEEDS_ENTRY_RULE_WORK` if execution variants cannot prevent repeated failing samples or if 20d accuracy is weak in multiple samples.
- `PHASE_1C_EXECUTION_HYPOTHESIS_NEEDS_REALISM_WORK` if close-based policies look good only when intraday breaches are ignored.
- `PHASE_1C_ROBUSTNESS_PROMISING_NOT_APPROVED` only if at least one realistic policy has:
  - median ending account value > $120 across samples
  - worst-sample ending account value > $100
  - median max drawdown better than -35%
  - worst-sample max drawdown better than -45%
  - median trade-simulation accuracy >= 50%
  - at least 20 BUY decisions in each sample
  - ending value excluding best trade > $105 in the median sample
  - no single ticker contributes more than 50% of total profit in any passing sample

Even if promising, this is not paper-trading approval. GPT review required.

## Part 6: Markdown Summary Requirements

`phase1c_robustness_summary.md` must start with:

```text
PHOENIX NANO PHASE 1C — ROBUSTNESS FAILURE ANALYSIS AND CLOSE-STOP REALISM
```

It must include:

- research/manual-review only statement
- Phase 1B recap
- policy robustness matrix summary
- best policy by median ending value
- best realistic policy after intraday-breach penalties
- number of passing samples per policy
- worst sample per policy
- sample 3 and 4 failure explanation
- close-based stop realism findings
- regime/theme attribution
- whether the current problem is mostly entry-rule weakness or execution-rule weakness
- Phase 1C status
- explicit statement: `Do not start paper trading or live trading.`
- concrete recommendation for the next research task

## Part 7: Tests

Add or update tests for:

1. Phase 1C sample generation is deterministic and creates the requested number of rounds per sample.
2. Policy robustness matrix contains every sample-policy combination.
3. Close-based stop realism flags intraday breaches correctly.
4. Close-confirmed next-open stop exits at the next open, not the same close.
5. Hybrid catastrophic stop exits on intraday catastrophic breach.
6. Failing sample trades are captured when sample gates fail.
7. Regime attribution aggregates trades by period and policy.
8. Phase 1C status logic does not approve Phase 2.
9. Reports are written.
10. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1c-robustness-analysis --replay-rounds 100 --replay-sample-count 10
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1C Robustness Summary
- Policy robustness matrix summary
- Best policy by median ending account value
- Best realistic policy after intraday-breach penalties
- Passing sample count per policy
- Worst sample per policy
- Sample 3 and 4 failure explanation
- Close-stop realism findings
- Regime/theme attribution
- Phase 1C status
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2 or Phase 3.
