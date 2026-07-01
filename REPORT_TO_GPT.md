# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Daily Scan v1.1 - Executable-First Filtering.
- Fixed the daily scan product bug where high-priced non-executable names appeared in the main candidate table.
- Changed daily scan order so Nano executable filters run before ranking:
  - whole shares with $100 after slippage must be at least 1
  - estimated total cost must be <= $100
  - reference price must be <= frozen Candidate 34 max entry price
- Ranked only executable candidates.
- Applied frozen Candidate 34 rule checks after executable-first filtering.
- Added `Closest Executable Near-Misses` for executable candidates that fail Candidate 34 checks.
- Added `Rejected Before Nano Ranking` for high-priced or not-affordable names, clearly marked as ineligible for Nano ranking.
- Added report counts for executable universe, rejected not affordable, and rejected above max entry price.
- Updated tests for executable-first behavior.
- Did not start paper trading.
- Did not start live trading.
- Did not label anything live-tradable.

## Files Changed

- `src/backtest/nano_daily_scan.py`
- `tests/test_nano_daily_scan.py`
- `data/reports/nano_daily_candidate_34_frozen_rules.md`
- `data/reports/nano_daily_scan.csv`
- `data/reports/nano_daily_scan.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

Equivalent explicit Candidate 34 command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan --candidate-id 34
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_nano_daily_scan.py -q
# 13 passed in 0.57s
```

```bash
.venv/bin/python -m pytest -q
# 64 passed, 1 warning in 1.37s
```

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

## Final Daily Scan Action

- Action: `NO_TRADE_MANUAL_REVIEW`
- Status: `RESEARCH_ONLY_NOT_TRADABLE`
- Candidate ticker: none
- Latest data date used: `2026-06-30`
- Result stale/current: current, `is_stale = False`
- Reason: `NO_CANDIDATE_PASSED_RULES`
- Data source: `yfinance`
- Scan timestamp UTC: `2026-07-01T19:57:03.828548+00:00`

## Executable Filtering

- Executable universe count: 27
- Rejected not affordable count: 56
- Rejected above max entry price count: 70
- Candidate 34 max entry price: $50.00
- Account setting: $100, whole shares only, 10 bps slippage

High-priced names such as AMAT and AMD no longer appear in the main executable candidate table. They appear only in `Rejected Before Nano Ranking`.

## Closest Executable Near-Misses

Top executable near-misses:

| ticker | reference_price | shares_with_100 | estimated_total_cost | smoke_score | failed_checks |
|:--|--:|--:|--:|--:|:--|
| RIVN | 17.35 | 5 | 86.84 | 0.7926 | smoke score below min, relative volume below min |
| SDGR | 16.25 | 6 | 97.60 | 0.7111 | smoke score below min |
| PATH | 10.87 | 9 | 97.93 | 0.6815 | smoke score/rank gap/RVOL/52w distance checks failed |
| S | 16.97 | 5 | 84.93 | 0.6741 | smoke score/rank gap/RVOL checks failed |
| F | 13.90 | 7 | 97.40 | 0.6667 | smoke score/rank gap/RVOL/5d return checks failed |

## Problems

- No executable candidate passed the frozen Candidate 34 daily scan gate.
- The executable universe exists, but the best executable names failed Candidate 34 strength or momentum/liquidity checks.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- Existing pandas `pct_change` future warnings and macOS LibreSSL warning remain; neither blocked execution.
- yfinance data remains non-institutional retail data and should not be treated as a live execution feed.

## Questions For GPT

- Should the next task add a stable CSV export for `Closest Executable Near-Misses`, or is Markdown-only sufficient for manual review?
- Should GPT adjust Candidate 34 thresholds for the $100 account, or keep the frozen rule strict until more daily scans accumulate?
- Should stale-date checks become market-calendar-aware before any paper-trading workflow is considered?

## Next Suggested Tasks

- Do not start live trading.
- Do not start paper trading until GPT explicitly approves.
- Keep daily scan output manual-review only.
- Add market-calendar-aware stale-date checks.
- Track daily scan history over time so GPT can inspect whether near-misses later become valid candidates.
