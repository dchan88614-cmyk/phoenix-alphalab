# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Daily Scan v1.2 - Fix Ranking Order and Executable Diagnostics.
- Confirmed daily scan now splits latest rows into executable candidates and rejected-before-ranking rows before ranking.
- Ranked only executable candidates.
- Applied Candidate 34 checks only after executable filtering.
- Kept high-priced or unaffordable names out of `Closest Executable Near-Misses`.
- Added deterministic CSV row types:
  - `FINAL`
  - `EXECUTABLE_NEAR_MISS`
  - `REJECTED_BEFORE_NANO_RANKING`
- Added required CSV columns including affordability flags, max-entry flags, `signal_rule_pass`, `full_rule_pass`, and `failed_checks`.
- Added `decision_strength` and `signal_rule_pass` to the Markdown near-miss table.
- Verified Markdown no longer contains `Top 5 Scanned Candidates`.
- Did not use forward returns or realized outcomes.
- Did not start paper trading.
- Did not start live trading.
- Did not output live-tradable language.

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

## Test Results

```bash
.venv/bin/python -m pytest tests/test_nano_daily_scan.py -q
# 14 passed in 0.66s
```

```bash
.venv/bin/python -m pytest -q
# 65 passed, 1 warning in 1.32s
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
- Is stale: false
- Reason: `NO_CANDIDATE_PASSED_RULES`
- Data source: `yfinance`
- Scan timestamp UTC: `2026-07-01T20:55:45.486831+00:00`

## Executable Diagnostics

- Executable universe count: 27
- Rejected not affordable count: 56
- Rejected above max_entry_price count: 70
- Candidate 34 max_entry_price: $50.00
- Account: $100, whole shares only, 10 bps slippage
- High-priced names in executable table: no

## Closest Executable Near-Misses

| ticker | reference_price | shares_with_100 | estimated_total_cost | smoke_score | decision_strength | failed_checks |
|:--|--:|--:|--:|--:|--:|:--|
| RIVN | 17.35 | 5 | 86.84 | 0.7926 | 0.5075 | smoke score below min, relative volume below min |
| SDGR | 16.25 | 6 | 97.60 | 0.7111 | 0.4419 | smoke score below min |
| PATH | 10.87 | 9 | 97.93 | 0.6815 | 0.3705 | smoke score/rank gap/RVOL/52w distance checks failed |
| S | 16.97 | 5 | 84.93 | 0.6741 | 0.3354 | smoke score/rank gap/RVOL checks failed |
| F | 13.90 | 7 | 97.40 | 0.6667 | 0.3369 | smoke score/rank gap/RVOL/5d return checks failed |

## Rejected-Before-Ranking Summary

- CSV includes 10 sample `REJECTED_BEFORE_NANO_RANKING` rows.
- Sample rejected names include ASML, GEV, MU, AMAT, PWR, AMD, APP, LMT, NOC, and TER.
- These rows were not eligible for Nano ranking because they failed affordability, max-entry, or both gates.
- AMAT/AMD-style high-priced names remain only in rejected diagnostics, not in the executable near-miss table.

## Problems

- No executable candidate passed the frozen Candidate 34 daily scan gate.
- The executable universe exists, but the best executable names failed Candidate 34 strength or momentum/liquidity checks.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- Existing pandas `pct_change` future warnings and macOS LibreSSL warning remain; neither blocked execution.
- yfinance data remains non-institutional retail data and should not be treated as a live execution feed.

## Questions For GPT

- Should GPT keep Candidate 34 frozen while daily near-misses accumulate, or request a separate Nano-specific candidate rule search constrained to executable stocks first?
- Should daily scan history be appended over time so near-miss quality can be reviewed longitudinally?
- Should stale-date checks become market-calendar-aware before any paper-trading workflow is considered?

## Next Suggested Tasks

- Do not start live trading.
- Do not start paper trading until GPT explicitly approves.
- Keep daily scan output manual-review only.
- Add market-calendar-aware stale-date checks.
- Add an append-only `nano_daily_scan_history.csv` if GPT wants longitudinal review.
