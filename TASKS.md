# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Daily Scan v1.4 — History Ledger and Calendar Stale Gate

Latest review state:

- The executable-first daily scan is working.
- High-priced symbols such as AMAT and AMD are no longer shown as executable near-misses.
- The latest final action remains `NO_TRADE_MANUAL_REVIEW`.
- No candidate is approved for paper trading or live trading.
- `nano_daily_scan.csv` is now multi-row, but it is still not a durable research ledger.
- `data/reports/nano_daily_scan_history.csv` does not exist yet.
- Stale-data detection still needs a market-calendar-aware expected trading date.

## Highest-Priority Improvement

Create a reliable longitudinal research ledger and calendar-aware stale-data gate before considering any rule change, threshold tuning, paper trading, or live trading.

Do not loosen Candidate 34 thresholds in this task.
Do not start paper trading.
Do not start live trading.
Keep all output research/manual-review only.

## Required Outputs

Update or create:

- `data/reports/nano_daily_scan.csv`
- `data/reports/nano_daily_scan.md`
- `data/reports/nano_daily_scan_history.csv`
- `REPORT_TO_GPT.md`

## Part 1: Enrich Current Diagnostic CSV

`data/reports/nano_daily_scan.csv` must include machine-readable scan metadata and factor diagnostics on each applicable row.

Required columns:

- scan_timestamp_utc
- latest_data_date
- expected_latest_trading_date
- is_stale
- data_source
- row_type
- ticker
- action
- status
- reference_price
- shares_with_100
- estimated_total_cost
- estimated_cash_remaining
- affordability_pass
- max_entry_price_pass
- signal_rule_pass
- full_rule_pass
- smoke_score
- decision_strength
- relative_volume_prev20
- return_5d
- return_20d
- distance_to_52w_high_prev
- dollar_volume
- failed_checks
- rejection_reason

Required row_type values:

- FINAL
- EXECUTABLE_NEAR_MISS
- REJECTED_BEFORE_NANO_RANKING

Rules:

- Keep up to 5 `EXECUTABLE_NEAR_MISS` rows.
- Keep at most 10 `REJECTED_BEFORE_NANO_RANKING` sample rows.
- Every `EXECUTABLE_NEAR_MISS` row must be affordable for a $100 whole-share account and must pass Candidate 34 max_entry_price.
- High-priced or unaffordable symbols may appear only as rejected diagnostics.

## Part 2: Add Append-Only History Ledger

Create or update:

`data/reports/nano_daily_scan_history.csv`

Rules:

- Append the latest diagnostic CSV rows after each scan.
- Preserve previous history rows.
- Make reruns idempotent by de-duplicating on:
  - scan_timestamp_utc
  - latest_data_date
  - row_type
  - ticker
- If the same EOD date is rescanned with a new timestamp, keep the new scan so GPT can compare repeated runs.
- Include row counts by row_type in `REPORT_TO_GPT.md`.

## Part 3: Market-Calendar-Aware Stale Gate

Implement `expected_latest_trading_date` for the daily scan.

Requirements:

- A weekend or US market holiday should not automatically make the latest completed EOD bar stale.
- If a reliable market-calendar package is already available in the repo environment, use it.
- If not, implement a small NYSE helper that handles weekdays plus common US market holidays.
- Report both:
  - `latest_data_date`
  - `expected_latest_trading_date`
- If `latest_data_date` is older than `expected_latest_trading_date`, output final action `NO_TRADE_MANUAL_REVIEW` with reason `STALE_DATA`.

## Part 4: Markdown Report

Update `data/reports/nano_daily_scan.md` to include:

- Final action
- Latest data date
- Expected latest trading date
- Stale/current status
- Data source
- Executable universe count
- Rejected not affordable count
- Rejected above max_entry_price count
- History file path
- History rows written in this run
- History total row count
- Closest Executable Near-Misses
- Rejected Before Nano Ranking

Do not include unconditional trade language.

## Part 5: Tests

Add or update tests for:

1. Diagnostic CSV contains `scan_timestamp_utc`, `latest_data_date`, `expected_latest_trading_date`, `is_stale`, and `data_source`.
2. Diagnostic CSV has row types `FINAL`, `EXECUTABLE_NEAR_MISS`, and `REJECTED_BEFORE_NANO_RANKING` when those rows exist.
3. `EXECUTABLE_NEAR_MISS` rows contain only affordable symbols under Candidate 34 max_entry_price.
4. High-priced symbols appear only in rejected diagnostics.
5. History CSV is created if missing.
6. History CSV preserves previous rows.
7. Re-running the same scan timestamp does not duplicate rows.
8. Re-scanning the same latest_data_date with a new scan timestamp appends a new run.
9. Weekend and holiday scans use the prior valid market trading date as expected latest trading date.
10. Data older than expected latest trading date returns `NO_TRADE_MANUAL_REVIEW` with reason `STALE_DATA`.
11. Reports remain research/manual-review only.
12. Full pytest suite passes.

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
- Expected latest trading date
- Is stale
- Executable universe count
- Rejected not affordable count
- Rejected above max_entry_price count
- Closest executable near-misses
- Diagnostic CSV row counts by row_type
- History CSV row counts by row_type
- History rows written this run
- Whether history append was idempotent
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Keep outputs research/manual-review only.
