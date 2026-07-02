# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1B — Last Month Daily Replay Validation

Goal: review the most recent completed month day by day. For each historical trading day, pretend that day was today, select the stock that met Phoenix Nano standards, then verify the later outcome using already-known future data.

Use the last completed month based on available EOD data. If latest available EOD data is 2026-06-30, use 2026-06-01 through 2026-06-30.

Keep this research-only. Do not start Phase 2 or Phase 3.

## Daily Replay Rule

For each trading day in the month:

1. Use only data available on or before that date.
2. Apply $100 whole-share account constraints.
3. Reject unaffordable stocks before ranking.
4. Apply the current Phoenix Nano / Candidate 34 standards.
5. Output exactly one result:
   - `HISTORICAL_BUY_CANDIDATE`
   - or `HISTORICAL_NO_TRADE`
6. If no full candidate passed, still record up to 5 closest executable near-misses.
7. After the decision is recorded, verify future returns using later data.

## Verification Windows

For each selected BUY candidate and near-miss, compute:

- 1 trading day return
- 3 trading day return
- 5 trading day return
- 10 trading day return
- 20 trading day return
- max favorable move within 20 trading days
- max adverse move within 20 trading days
- data_complete flag for each window

If not enough future data exists, mark incomplete rather than inventing values.

## Outputs

Create:

- `data/reports/phase1b_last_month_daily_replay.csv`
- `data/reports/phase1b_last_month_daily_replay.md`
- `data/reports/phase1b_last_month_near_misses.csv`

The markdown summary must include:

- replay date range
- total trading days tested
- BUY candidate count
- NO_TRADE count
- list of each day and selected ticker, if any
- 1d / 3d / 5d / 10d / 20d accuracy for BUY candidates
- average and median returns by window
- best selected stock
- worst selected stock
- most repeated selected tickers
- near-misses that later performed well
- near-misses that failed badly
- short conclusion: what this month taught us

## Important Accuracy Rule

Forward returns may only be used after the daily decision is recorded. They must never be used to pick the stock for that day.

## CLI

Add or update CLI flag:

```bash
--phase1b-last-month-replay
```

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2026-06-01 --end 2026-06-30 --phase1b-last-month-replay
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Last Month Replay Summary
- Date range
- Total trading days
- BUY count
- NO_TRADE count
- Accuracy by window
- Best pick
- Worst pick
- Top repeated tickers
- Near-miss lessons
- What should be adjusted next
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop.
