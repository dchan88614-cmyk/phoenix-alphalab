# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Daily Scan v1.4 - History Ledger and Calendar Stale Gate.
- Enriched `data/reports/nano_daily_scan.csv` into a machine-readable diagnostic CSV with scan metadata and factor diagnostics.
- Added required row types:
  - `FINAL`
  - `EXECUTABLE_NEAR_MISS`
  - `REJECTED_BEFORE_NANO_RANKING`
- Added append-only `data/reports/nano_daily_scan_history.csv`.
- Made history append idempotent by de-duplicating on `scan_timestamp_utc`, `latest_data_date`, `row_type`, and `ticker`.
- Preserved repeated scans of the same EOD date when the scan timestamp changes.
- Added market-calendar-aware `expected_latest_trading_date` for the daily scan.
- Added weekend and common NYSE holiday handling without adding a new dependency.
- Updated Markdown daily scan report with expected latest trading date, history rows written, history total row count, and history file path.
- Kept Candidate 34 thresholds frozen.
- Did not start paper trading.
- Did not start live trading.
- Kept outputs research/manual-review only.

## Files Changed

- `src/backtest/nano_daily_scan.py`
- `src/main.py`
- `tests/test_nano_daily_scan.py`
- `data/reports/nano_daily_candidate_34_frozen_rules.md`
- `data/reports/nano_daily_scan.csv`
- `data/reports/nano_daily_scan.md`
- `data/reports/nano_daily_scan_history.csv`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_nano_daily_scan.py -q
# 19 passed in 0.49s
```

```bash
.venv/bin/python -m pytest -q
# 71 passed, 1 warning in 1.38s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

## Final Daily Scan Action

- Action: `NO_TRADE_MANUAL_REVIEW`
- Status: `RESEARCH_ONLY_NOT_TRADABLE`
- Candidate ticker: none
- Latest data date used: `2026-06-30`
- Expected latest trading date: `2026-06-30`
- Is stale: false
- Reason: `NO_CANDIDATE_PASSED_RULES`
- Data source: `yfinance`
- Scan timestamp UTC: `2026-07-01T22:01:41.789282+00:00`

## Executable Diagnostics

- Executable universe count: 27
- Rejected not affordable count: 56
- Rejected above max_entry_price count: 70
- Candidate 34 max_entry_price: $50.00
- Account: $100, whole shares only, 10 bps slippage
- High-priced names in executable near-miss table: no

## Closest Executable Near-Misses

| ticker | reference_price | shares_with_100 | estimated_total_cost | smoke_score | decision_strength | failed_checks |
|:--|--:|--:|--:|--:|--:|:--|
| RIVN | 17.35 | 5 | 86.84 | 0.7926 | 0.5075 | smoke_score_below_min, relative_volume_prev20_below_min |
| SDGR | 16.25 | 6 | 97.60 | 0.7111 | 0.4419 | smoke_score_below_min |
| PATH | 10.87 | 9 | 97.93 | 0.6815 | 0.3705 | smoke_score_below_min, rank_gap_below_min, relative_volume_prev20_below_min, distance_to_52w_high_prev_below_min |
| S | 16.97 | 5 | 84.93 | 0.6741 | 0.3354 | smoke_score_below_min, rank_gap_below_min, relative_volume_prev20_below_min |
| F | 13.90 | 7 | 97.40 | 0.6667 | 0.3369 | smoke_score_below_min, rank_gap_below_min, relative_volume_prev20_below_min, return_5d_not_positive |

## Diagnostic CSV Row Counts By row_type

| row_type | rows |
|:--|--:|
| FINAL | 1 |
| EXECUTABLE_NEAR_MISS | 5 |
| REJECTED_BEFORE_NANO_RANKING | 10 |

## History CSV Row Counts By row_type

| row_type | rows |
|:--|--:|
| FINAL | 2 |
| EXECUTABLE_NEAR_MISS | 10 |
| REJECTED_BEFORE_NANO_RANKING | 20 |

## History Ledger

- History file: `data/reports/nano_daily_scan_history.csv`
- History rows written this run: 16
- History total row count: 32
- Unique scan timestamps in history: 2
- History append idempotent: yes, covered by tests for same timestamp de-duplication.
- Same latest_data_date with new scan timestamp appends a new run: yes, covered by tests and reflected in current history.

## Problems

- No executable candidate passed the frozen Candidate 34 daily scan gate.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- Existing pandas `pct_change` future warnings appeared during the end-to-end scan; they did not block execution.
- yfinance data remains non-institutional retail data and should not be treated as an execution feed.

## Questions For GPT

- Should GPT keep Candidate 34 frozen while the new history ledger accumulates more daily evidence?
- Should the next task review the longitudinal near-miss ledger before any threshold search is allowed?
- Should metadata quality issues be split into a separate watchlist hygiene task?

## Next Suggested Tasks

- Do not start live trading.
- Do not start paper trading until GPT explicitly approves.
- Keep daily scan output manual-review only.
- Let the history ledger accumulate multiple daily scans before changing Candidate 34 thresholds.
- Review rejected metadata names separately from signal quality.
