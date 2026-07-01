# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Daily Scan v1.1 — Executable-First Filtering

The previous daily scan surfaced AMAT/KLAC/LRCX/AMD/PANW in the main candidate list even though Phoenix Nano is a $100 whole-share account and Candidate 34 uses a max entry price around $50.

This is a product bug.

## Goal

Fix the daily scan so the main displayed candidates are filtered for account executability before ranking.

## Required Pipeline Order

1. Load latest available EOD OHLCV.
2. Compute signal-date-safe factors.
3. Determine latest completed data date.
4. Apply universe / metadata filters.
5. Apply Nano executable filters before ranking:
   - whole shares with $100 after slippage must be at least 1
   - estimated total cost must be <= $100
   - reference price must be <= Candidate 34 max_entry_price, expected $50
6. Rank only executable candidates.
7. Apply Candidate 34 rule checks.
8. Output exactly one final action:
   - MANUAL_REVIEW_CANDIDATE
   - or NO_TRADE_MANUAL_REVIEW

High-priced non-executable names must not appear in the main top candidate table.

## Report Requirements

Update:

- data/reports/nano_daily_scan.md
- data/reports/nano_daily_scan.csv

The markdown report must include:

- final action
- latest data date
- stale/current status
- executable universe count
- rejected not affordable count
- rejected above max entry price count
- Candidate 34 max entry price
- account setting: $100, whole shares only

If no full candidate passes, include a table named:

`Closest Executable Near-Misses`

This table may contain up to 5 rows, but every row must be both:

- affordable with $100 whole-share account
- below or equal to Candidate 34 max entry price

Columns:

- ticker
- reference_price
- shares_with_100
- estimated_total_cost
- estimated_cash_remaining
- smoke_score
- relative_volume_prev20
- return_5d
- return_20d
- distance_to_52w_high_prev
- dollar_volume
- failed_checks

Add a separate section:

`Rejected Before Nano Ranking`

This section may summarize AMAT/KLAC/LRCX/AMD/PANW-style names, but it must clearly say they were not eligible for Nano ranking.

## Tests

Add or update tests for:

1. A stock above $100 is excluded from the main executable table.
2. A stock above Candidate 34 max entry price is excluded from the main executable table.
3. The near-miss table contains only executable stocks.
4. Rejected high-priced names appear only in rejected summary, not in main top candidates.
5. If no executable stock passes all checks, action is NO_TRADE_MANUAL_REVIEW.
6. If an executable stock passes all checks, action is MANUAL_REVIEW_CANDIDATE.
7. Daily scan does not use forward returns or realized outcomes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

## Update REPORT_TO_GPT.md

Include:

- Completed
- Files Changed
- How To Run
- Test Results
- Final Daily Scan Action
- Candidate ticker, if any
- Latest data date used
- Executable universe count
- Rejected not affordable count
- Rejected above max entry price count
- Closest executable near-misses
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Keep outputs research/manual-review only.
