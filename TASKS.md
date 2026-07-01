# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Daily Scan v1.3 — Machine-Readable Scan Ledger

The latest report shows the executable-first filter is now working. High-priced names such as AMAT and AMD no longer appear in the main executable candidate table. The daily scan result remains `NO_TRADE_MANUAL_REVIEW` with no candidate approved for paper trading or live trading.

Highest-priority improvement: the Markdown report now contains useful executable near-misses, but `data/reports/nano_daily_scan.csv` still contains only the final one-line result. That makes the daily scan hard to audit, compare, or trend over time.

Do not loosen Candidate 34 thresholds yet. Do not start paper trading. Do not start live trading. Keep all outputs research/manual-review only.

## Goal

Create a durable, machine-readable daily scan ledger so GPT can review how executable near-misses evolve over time before considering any threshold change or paper-trading gate.

The system must preserve:

1. the final daily action,
2. the top executable near-misses,
3. rejected-before-ranking samples,
4. scan metadata and stale/current status,
5. enough rule-check columns to analyze why no candidate passed.

## Required Outputs

Update or create:

- `data/reports/nano_daily_scan.csv`
- `data/reports/nano_daily_scan.md`
- `data/reports/nano_daily_scan_history.csv`
- `REPORT_TO_GPT.md`

`nano_daily_scan.csv` must become a multi-row diagnostic CSV, not just the final result row.

Required `row_type` values:

- `FINAL`
- `EXECUTABLE_NEAR_MISS`
- `REJECTED_BEFORE_NANO_RANKING`

Required columns for every row where applicable:

- scan_timestamp_utc
- latest_data_date
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

## History File

Create or update `data/reports/nano_daily_scan_history.csv` as an append-only ledger.

Rules:

- Append one `FINAL` row for each scan run.
- Append up to 5 `EXECUTABLE_NEAR_MISS` rows for each scan run.
- Do not append unlimited rejected rows; include at most 10 `REJECTED_BEFORE_NANO_RANKING` samples per scan run.
- Make reruns idempotent by de-duplicating on:
  - scan_timestamp_utc
  - latest_data_date
  - row_type
  - ticker
- Preserve previous history rows.
- If the file does not exist, create it.

## Market Calendar Stale Check

Improve stale detection so it is market-calendar-aware.

Requirements:

- A latest data date should not be considered stale merely because the scan runs on a weekend or US market holiday.
- If no reliable market-calendar dependency is available, implement a simple NYSE weekday/holiday helper with tests for common holidays.
- Report both:
  - `latest_data_date`
  - `expected_latest_trading_date`
- If the latest data date is older than the expected latest trading date, output `NO_TRADE_MANUAL_REVIEW` with reason `STALE_DATA`.

## Markdown Report Changes

Keep the existing clear Markdown sections:

- `PHOENIX NANO DAILY SCAN`
- `Closest Executable Near-Misses`
- `Rejected Before Nano Ranking`

Add:

- `Expected latest trading date`
- `History rows written`
- `History file path`

Do not include any BUY language or live-trading language.

## Tests

Add or update tests for:

1. `nano_daily_scan.csv` contains row_type values `FINAL` and `EXECUTABLE_NEAR_MISS` when near-misses exist.
2. The diagnostic CSV contains no high-priced rejected ticker in `EXECUTABLE_NEAR_MISS` rows.
3. The diagnostic CSV includes `failed_checks` for each executable near-miss.
4. The history CSV is created if missing.
5. Re-running the same scan does not duplicate the same history rows.
6. History appends a new scan when scan timestamp or latest data date changes.
7. Weekend or holiday scans use the prior market trading day as expected latest trading date.
8. Stale data older than the expected latest trading date produces `NO_TRADE_MANUAL_REVIEW` with `STALE_DATA`.
9. No report contains live-trading or unconditional BUY language.
10. Full pytest suite passes.

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
- Whether history append was idempotent
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start paper trading. Do not start live trading. Do not output live-tradable language.
