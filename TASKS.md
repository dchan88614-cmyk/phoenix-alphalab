# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano v1.5 — Near-Miss Outcome Tracker

Latest state:

- Executable-first daily scan is working.
- Daily scan history ledger exists.
- The latest final action remains `NO_TRADE_MANUAL_REVIEW`.
- The latest closest executable near-miss list included RIVN, SDGR, PATH, S, and F.
- No candidate is approved for paper trading or live trading.

David may manually watch the top near-miss, but Phoenix must continue training from data, not from subjective preference.

## Goal

Build a near-miss outcome tracker so Phoenix can learn whether rejected but executable near-misses were actually worth watching.

Do not loosen Candidate 34 thresholds in this task.
Do not start paper trading.
Do not start live trading.
Keep all outputs research/manual-review only.

## Key Question

For each executable near-miss from the daily scan history, what happened after the signal date?

Track forward outcomes for 1, 3, 5, 10, and 20 trading days, but use them only for post-hoc research diagnostics. Do not use forward outcomes to create today's signal.

## Required Outputs

Create or update:

- `data/reports/nano_near_miss_outcomes.csv`
- `data/reports/nano_near_miss_outcomes.md`
- `REPORT_TO_GPT.md`

## Part 1: Read History Ledger

Read:

`data/reports/nano_daily_scan_history.csv`

Use rows where:

- row_type == `EXECUTABLE_NEAR_MISS`
- affordability_pass == true
- max_entry_price_pass == true
- latest_data_date is present
- ticker is present

Each near-miss observation should be uniquely identified by:

- scan_timestamp_utc
- latest_data_date
- ticker

## Part 2: Add Outcome Windows

For each near-miss observation, compute forward outcomes from the latest_data_date close/reference price using available OHLCV data.

Windows:

- 1 trading day
- 3 trading days
- 5 trading days
- 10 trading days
- 20 trading days

For each window, compute:

- forward_return_close_to_close
- max_favorable_excursion
- max_adverse_excursion
- hit_plus_5pct
- hit_plus_10pct
- hit_minus_5pct
- hit_minus_10pct
- data_complete flag

If insufficient future bars exist, mark data_complete false and do not invent values.

## Part 3: Explain Which Rule Failed

Group outcomes by failed_checks.

Questions to answer:

1. Are near-misses that failed only `smoke_score_below_min` actually performing well afterward?
2. Are near-misses that failed `relative_volume_prev20_below_min` underperforming or just early?
3. Are near-misses with positive 5d and 20d return better than other near-misses?
4. Does any failed check look too strict or useful?

Do not change the rules yet. Only report evidence.

## Part 4: Markdown Summary

`nano_near_miss_outcomes.md` must include:

- total near-miss observations
- observations with complete 1d / 3d / 5d / 10d / 20d data
- best near-miss by 5d return
- worst near-miss by 5d return
- best near-miss by 20d return if complete
- worst near-miss by 20d return if complete
- average forward return by window
- hit rate for +5%, +10%, -5%, -10%
- outcome summary by failed_checks
- explicit statement: `Post-hoc research only. Do not use this as a live signal.`

## Part 5: Tests

Add or update tests for:

1. Near-miss outcomes are computed only for EXECUTABLE_NEAR_MISS rows.
2. Insufficient future data sets data_complete false.
3. Forward outcomes are not used by the daily scan ranking.
4. Outcome report groups by failed_checks.
5. Reports are written.
6. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

If a new CLI flag is needed, add:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-near-miss-outcomes
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Near-Miss Outcome Summary
- Best and Worst Near-Misses
- Outcome by Failed Check
- Whether any rule looks too strict based on evidence
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Keep outputs research/manual-review only.
