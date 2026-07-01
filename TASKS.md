# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Daily Scan v1.2 — Fix Ranking Order and Executable Diagnostics

Latest GPT review found the daily scan still ranks the full high-priced universe before applying Nano executability. This caused AMAT/KLAC/LRCX/AMD/PANW-style names to appear in the main Top 5 even though Phoenix Nano is a $100 whole-share account and Candidate 34 has a max_entry_price of about $50.

This is a blocker for any useful manual-review output. Fix this before any new research expansion.

Do not start paper trading.
Do not start live trading.
Do not label any output tradable.
Keep all outputs research/manual-review only.

## Evidence To Address

Current implementation problem:

- `build_nano_daily_scan()` calls `_score_latest_candidates(latest, rule, account_settings)` before any executable filtering.
- `_score_latest_candidates()` ranks all latest rows first.
- `_metadata()` stores `scanned.head(5)` as `top_candidates`, which is therefore the top high-priced universe, not the executable Nano universe.
- `nano_daily_scan.md` currently shows high-priced non-executable names in `Top 5 Scanned Candidates`.

## Goal

Make the daily scan answer David's actual account question:

1. Which tickers are executable for a $100 whole-share account?
2. Which executable tickers are also <= Candidate 34 max_entry_price?
3. Among executable tickers only, does any ticker pass Candidate 34?
4. If none passes, what are the closest executable near-misses?

## Required Implementation

Update `src/backtest/nano_daily_scan.py` so the effective pipeline is:

1. Load latest available EOD OHLCV.
2. Compute only signal-date-safe factors.
3. Determine latest completed data date.
4. Apply universe / metadata filters.
5. Calculate affordability and max-entry flags for every latest row.
6. Split rows into:
   - `executable_candidates`: `affordability_pass == True` and `max_entry_price_pass == True`
   - `rejected_before_nano_ranking`: all rows failing either gate
7. Rank only `executable_candidates`.
8. Apply Candidate 34 checks only after the executable split.
9. Select final candidate only from executable rows that pass all checks.
10. If no executable row passes all checks, output `NO_TRADE_MANUAL_REVIEW` plus executable near-misses.

Important: High-priced or unaffordable names must never appear in the main candidate or near-miss table.

## Required Report Output

Update both:

- `data/reports/nano_daily_scan.md`
- `data/reports/nano_daily_scan.csv`

The markdown must include:

- `Action`
- `Latest data date`
- `Is stale`
- `Data source`
- `Account: $100, whole shares only`
- `Candidate 34 max_entry_price`
- `Executable universe count`
- `Rejected not affordable count`
- `Rejected above max_entry_price count`

Replace the old section name:

`Top 5 Scanned Candidates`

with:

`Closest Executable Near-Misses`

Rules for this table:

- maximum 5 rows
- every row must have `affordability_pass == True`
- every row must have `max_entry_price_pass == True`
- every row must include failed Candidate 34 checks

Columns:

- ticker
- reference_price
- shares_with_100
- estimated_total_cost
- estimated_cash_remaining
- smoke_score
- decision_strength
- relative_volume_prev20
- return_5d
- return_20d
- distance_to_52w_high_prev
- dollar_volume
- signal_rule_pass
- failed_checks

Add a separate section:

`Rejected Before Nano Ranking`

This section may show summary counts and up to 10 sample rejected tickers. It must clearly say these names were not eligible for Nano ranking. It may include AMAT/KLAC/LRCX/AMD/PANW if they are rejected, but not in the executable table.

## Required CSV Output

`data/reports/nano_daily_scan.csv` must include a row type column:

- `FINAL`
- `EXECUTABLE_NEAR_MISS`
- `REJECTED_BEFORE_NANO_RANKING`

Required columns:

- row_type
- ticker
- action
- reference_price
- shares_with_100
- estimated_total_cost
- estimated_cash_remaining
- affordability_pass
- max_entry_price_pass
- signal_rule_pass
- full_rule_pass
- failed_checks

## Failed Check Diagnostics

Implement or update a deterministic failed-check helper for Candidate 34. It should identify at least:

- affordability
- max_entry_price
- min_smoke_score
- min_relative_volume_prev20
- require_return_5d_positive
- require_return_20d_positive
- distance_to_52w_high_prev_min
- dollar_volume_min
- min_rank_gap

Do not use forward returns or realized trade outcomes in this helper.

## Tests

Add or update tests for:

1. A stock above $100 is excluded from `Closest Executable Near-Misses`.
2. A stock above Candidate 34 max_entry_price is excluded from `Closest Executable Near-Misses`.
3. High-priced rejected names may appear only under `Rejected Before Nano Ranking`.
4. `Closest Executable Near-Misses` contains only rows where affordability and max-entry both pass.
5. If no executable stock passes full Candidate 34 checks, action is `NO_TRADE_MANUAL_REVIEW`.
6. If an executable stock passes all Candidate 34 checks, action is `MANUAL_REVIEW_CANDIDATE`.
7. `failed_checks` is populated for near-misses.
8. Daily scan still does not use forward returns or realized trade outcomes.
9. The markdown no longer contains `Top 5 Scanned Candidates`.
10. Reports are written.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Final Daily Scan Action
- Candidate ticker, if any
- Latest data date used
- Is stale
- Executable universe count
- Rejected not affordable count
- Rejected above max_entry_price count
- Closest executable near-misses
- Rejected-before-ranking summary
- Whether any high-priced names remain in the executable table
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop.
Do not start paper trading.
Do not start live trading.
Do not output live-tradable language.
