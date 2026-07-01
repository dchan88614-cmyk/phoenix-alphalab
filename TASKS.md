# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Active Protocol

Before every execution:

1. Read `README.md`.
2. Read `BRAIN.md`.
3. Read `TASKS.md`.
4. Read the previous `REPORT_TO_GPT.md`.

After every completed task:

1. Update `REPORT_TO_GPT.md`.
2. Include `Completed`, `Files Changed`, `How To Run`, `Output`, `Test Results`, `Problems`, `Questions For GPT`, and `Next Suggested Tasks`.
3. Commit and push to GitHub.
4. Stop and wait for GPT review.

## Highest Product Principle

Phoenix AlphaLab is not trying to produce beautiful research reports.

The final user-facing product is a daily trading decision:

- `BUY`
- or `NO TRADE`

If `BUY`, the final output must eventually include:

- ticker
- entry range
- stop loss
- target 1
- target 2
- expected holding period
- confidence score
- one-sentence reason

All research, backtests, factors, reports, and code exist only to improve the quality of that final BUY / NO TRADE decision.

Do not add complexity unless it improves decision quality.

## Current Task: Generation 1 — Decision Engine Prototype

Goal:
Build the first explicit decision-generation layer on top of the existing smoke test engine.

This is not live trading yet. It is a historical decision simulator that converts daily rankings into BUY / NO TRADE decisions and measures whether those decisions improve over simple ranking.

Do not add news, SEC, short interest, options, LLM ranking, or new alpha factors.
Do not change the current smoke ranking rule.

### Part 1: Add Decision Output Model

Create a new module:

`src/decision/decision_engine.py`

It should define a structured decision record with at least:

- date
- action: BUY or NO_TRADE
- ticker
- entry_price
- entry_low
- entry_high
- stop_loss
- target_1
- target_2
- expected_holding_days
- confidence
- reason
- smoke_score
- rank

For historical simulation, use close price as the proxy entry price because the system is currently End-of-Day.

Set:

- entry_price = close
- entry_low = close * 0.995
- entry_high = close * 1.005
- stop_loss = close - 1.5 * ATR, if ATR exists
- fallback stop_loss = close * 0.92
- target_1 = close + 2 * (close - stop_loss)
- target_2 = close + 4 * (close - stop_loss)
- expected_holding_days = 20

This is only a first baseline. Do not optimize these numbers yet.

### Part 2: BUY / NO TRADE Rule v0

For each signal date:

- start from smoke test Top 5 candidates
- choose only rank 1 candidate
- emit BUY only if:
  - smoke_score >= 0.70
  - relative_volume_prev20 is not null
  - return_5d > 0
  - return_20d > 0
  - distance_to_52w_high_prev >= -0.25
  - dollar_volume >= 20,000,000
- otherwise emit NO_TRADE

Confidence baseline:

- confidence = min(95, max(50, round(smoke_score * 100)))

Reason should be one short sentence, for example:

`Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume.`

### Part 3: Decision Simulation Report

Add reports:

`data/reports/decision_simulation.csv`
`data/reports/decision_simulation.md`

Report must include:

- total signal days
- BUY days
- NO_TRADE days
- BUY rate
- average 5d / 10d / 20d forward return for BUY decisions
- average 5d / 10d / 20d excess return vs SPY for BUY decisions
- win rate for BUY decisions
- worst BUY
- best BUY
- average result if every day bought smoke rank 1, for comparison
- whether BUY filtering improved or hurt performance versus always buying rank 1

### Part 4: CLI

Add CLI flag:

`--decision-simulation`

Example command:

```bash
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --smoke-test --decision-simulation
```

### Part 5: Tests

Add tests for:

1. Decision engine emits BUY when all baseline conditions pass.
2. Decision engine emits NO_TRADE when smoke_score is too low.
3. Stop loss and targets are calculated correctly.
4. Decision simulation does not use forward returns to decide BUY / NO_TRADE.
5. Decision report files are written.

### Part 6: Update Documentation

Update `README.md` and `BRAIN.md` to explain:

- Research reports are internal engine diagnostics.
- The product goal is improving daily BUY / NO TRADE decision quality.
- Generation-based improvement is preferred over adding random features.
- Each generation should change only a small number of rules so GPT can judge what improved or broke.

### Part 7: Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Output
- Test Results
- Decision Simulation Summary
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

After Generation 1 is complete, commit, push, and stop.
Do not start Generation 2 until GPT reviews the result.
