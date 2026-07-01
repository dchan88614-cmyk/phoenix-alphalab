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
4. Stop and wait for GPT review unless this task explicitly says to run an internal loop.

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

## Current Task: Autonomous Research Loop v0

Goal:
Build an automated offline research loop that can run multiple candidate decision-rule experiments, evaluate them, reject weak versions, and report only versions that meet a minimum “research-qualified” threshold.

This is still historical research only. Do not output live trade recommendations.
Do not add news, SEC, short interest, options, LLM ranking, or external paid data.
Do not optimize on future data inside a signal date.

The purpose is to let Codex run many controlled experiments without requiring GPT to manually review every single generation.

## Core Principle

Do not try to find a perfect model.
Find whether any simple decision rule is even barely usable after historical validation.

A version that has not passed validation must be labeled:

`RESEARCH_ONLY_NOT_TRADABLE`

Only a version that passes the minimum threshold may be labeled:

`RESEARCH_QUALIFIED_NOT_LIVE`

Nothing may be labeled live-tradable yet.

## Part 1: Create Auto Research Module

Create:

`src/research/auto_loop.py`

It should define:

- candidate rule configurations
- evaluation logic
- pass/fail gates
- generation results table
- best qualified rule selection

The loop should run up to 50 candidate experiments, but stop early if:

- 10 consecutive candidates fail to improve the best score, or
- fewer than 3 candidates pass the minimum threshold after all experiments.

For v0, candidates should be simple variations of BUY / NO_TRADE filters only. Do not change the underlying smoke rank factors.

Candidate parameters may vary:

- smoke_score threshold: 0.65, 0.70, 0.75, 0.80
- require return_5d > 0: true/false
- require return_20d > 0: true/false
- distance_to_52w_high_prev minimum: -0.35, -0.25, -0.15
- dollar_volume minimum: 10,000,000 / 20,000,000 / 50,000,000
- max BUY rate: 100%, 70%, 50%, 30%

Do not add more parameter families unless needed to reach 50 experiments.

## Part 2: Multi-Window Validation

Use fixed, non-overlapping historical windows:

- 2024-01-02 to 2024-03-29
- 2024-04-01 to 2024-06-28
- 2024-07-01 to 2024-09-30
- 2024-10-01 to 2024-12-31
- 2025-01-02 to 2025-03-31
- 2025-04-01 to 2025-06-30
- 2025-07-01 to 2025-09-30
- 2025-10-01 to 2025-12-31
- 2026-01-02 to 2026-03-31
- 2026-04-01 to 2026-06-30

Each candidate rule must be evaluated across all windows using the same watchlist:

`config/watchlists/us_liquid_growth_100.txt`

For each window, record:

- signal days
- BUY days
- BUY rate
- average 5d / 10d / 20d BUY return
- average 5d / 10d / 20d excess return vs SPY
- 20d win rate
- 20d days outperforming SPY
- best BUY
- worst BUY
- whether removing best BUY keeps 20d average excess positive

## Part 3: Minimum Research-Qualified Gate

A candidate is `RESEARCH_QUALIFIED_NOT_LIVE` only if all are true:

1. At least 8 windows have sufficient data.
2. At least 6 out of 8+ valid windows have 20d avg excess return > 0.
3. At least 6 out of 8+ valid windows have 20d days-outperforming-SPY ratio > 50%.
4. Overall 20d avg excess return > 0.
5. Overall 20d win rate >= 52%.
6. BUY count >= 40 across all windows.
7. Removing the single best BUY still leaves overall 20d avg excess return > 0.
8. Worst BUY 20d return must be greater than -60%.

If a candidate fails any gate, label it:

`RESEARCH_ONLY_NOT_TRADABLE`

## Part 4: Scoring

For candidates that pass the gate, compute a simple score:

`score = overall_20d_avg_excess * 100 + overall_20d_win_rate * 20 + valid_window_pass_rate * 20 - abs(worst_20d_return) * 10`

The exact score is only for ranking candidates, not for trading.

## Part 5: Outputs

Create:

`data/reports/auto_research_generations.csv`
`data/reports/auto_research_summary.md`

The summary must include:

- total candidates tested
- candidates passed gate
- candidates failed gate
- early stop reason if any
- best candidate parameters
- best candidate score
- best candidate status
- cross-window summary for best candidate
- top 10 candidate table
- explicit warning: no version is live-tradable yet

If zero candidates pass gate, the summary must clearly say:

`No research-qualified version found. Do not use Phoenix for live trading.`

## Part 6: CLI

Add CLI flag:

`--auto-research-loop`

Example:

```bash
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

This command should generate the auto research reports.

It may reuse existing price/factor/forward-return pipeline.

## Part 7: Tests

Add tests for:

1. A candidate that fails BUY count gate is labeled `RESEARCH_ONLY_NOT_TRADABLE`.
2. A candidate that passes all gates is labeled `RESEARCH_QUALIFIED_NOT_LIVE`.
3. Removing best BUY is included in the gate logic.
4. Auto loop writes both CSV and Markdown outputs.
5. Candidate scoring is deterministic.
6. The loop does not use forward returns to decide whether a row is BUY; forward returns are only used after BUY/NO_TRADE decisions are generated.

## Part 8: Documentation

Update `README.md` and `BRAIN.md` to explain:

- Auto Research Loop is an offline historical research process.
- It may run many experiments automatically.
- It cannot mark anything live-tradable.
- GPT must review before any rule becomes user-facing.
- “Research-qualified” means worth deeper review, not safe to trade.

## Part 9: Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Output
- Test Results
- Auto Research Summary
- Best Candidate, if any
- Whether any candidate passed the gate
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

After Auto Research Loop v0 is complete, commit, push, and stop.
Do not start live daily trade generation.
Do not label any result as live-tradable.
