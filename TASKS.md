# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Auto Research Loop v0.1 — Fix Coverage Before Judging

The previous auto research loop ran, but it stopped after only 10 candidates. Those candidates were too similar and too loose, with BUY rates around 95.40%. This is not enough to judge Phoenix.

Do not change alpha factors.
Do not add news, SEC, short interest, options, LLM ranking, or external paid data.
Do not label anything live-tradable.

## Goal

Fix the auto research loop so it actually tests a broad enough candidate set before stopping.

The previous result is useful but not final:

- 10 candidates tested
- 0 passed gate
- early stop triggered too soon
- top candidates had positive 20d excess but failed risk gate because worst 20d return was -63.53%

## Part 1: Remove Premature Early Stop

Modify the loop so it always evaluates at least 50 candidate configurations before any early stop is allowed.

For v0.1:

- minimum candidates before early stop: 50
- max candidates: 100
- if fewer than 50 candidates exist, generate enough combinations to reach at least 50

Do not stop just because no candidate passed yet.

## Part 2: Improve Candidate Ordering

Candidate ordering must test diverse rules early.

The first 20 candidates must include a mix of:

- smoke_score_threshold: 0.65, 0.70, 0.75, 0.80
- max_buy_rate: 1.0, 0.7, 0.5, 0.3
- distance_to_52w_high_prev_min: -0.35, -0.25, -0.15
- dollar_volume_min: 10,000,000 / 20,000,000 / 50,000,000
- require_return_5d_positive: true/false
- require_return_20d_positive: true/false

Avoid evaluating 10 nearly identical loose rules first.

## Part 3: Add Stop / Target Path Evaluation Placeholder

Do not optimize stop/target yet, but add columns to candidate reports showing whether BUY signals would have hit:

- stop_loss within 20 trading days
- target_1 within 20 trading days
- target_2 within 20 trading days

Use available historical high/low path after signal date.

For now this is diagnostic only and must not be used to decide BUY / NO_TRADE.

## Part 4: Add Warmup Support

The first 2024 window only had 1 eligible signal day because the run starts too close to the window.

Add warmup support:

- CLI still accepts start date as research start.
- Internally download or use at least 300 calendar days before start date for factor warmup when possible.
- Reports should distinguish:
  - data_start
  - research_start
  - research_end

If yfinance cannot provide enough warmup, report the limitation.

## Part 5: Report Improvements

Update `auto_research_summary.md` to include:

- total candidates available
- total candidates evaluated
- why the loop stopped
- distribution of BUY rates across candidates
- top 10 candidates by 20d avg excess even if they failed gates
- top 10 candidates by risk-adjusted score even if they failed gates
- explicit list of most common fail reasons
- whether the -60% worst-trade gate is the only reason top candidates failed

Update `auto_research_generations.csv` to include:

- all candidate parameters
- all gate failures
- BUY count
- BUY rate
- valid window count
- windows with positive 20d excess
- windows with 20d outperformance ratio > 50%
- overall 20d avg return
- overall 20d avg excess
- overall 20d win rate
- worst 20d return
- avg excess excluding best BUY
- stop hit rate diagnostic
- target 1 hit rate diagnostic
- target 2 hit rate diagnostic

## Part 6: Tests

Add or update tests for:

1. At least 50 candidates are evaluated before early stop.
2. First 20 candidates are not all identical except max_buy_rate.
3. Warmup data does not create signals before research_start.
4. Path diagnostics are calculated but not used in BUY / NO_TRADE decisions.
5. Reports include common fail reasons.

## Part 7: Run

Run:

```bash
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

## Part 8: Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- total candidates evaluated
- candidates passed gate
- top candidate even if failed
- whether any failed only because of worst_20d_return gate
- best 20d avg excess after excluding best BUY
- stop/target diagnostic summary
- whether Phoenix remains not tradable

## Stop Condition

Commit, push, and stop.
Do not start live trade generation.
Do not label anything live-tradable.
