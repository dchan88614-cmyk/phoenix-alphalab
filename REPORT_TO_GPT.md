# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Daily Scan v0 - Current Data Manual-Review Candidate.
- Added `--nano-daily-scan` CLI support.
- Added latest EOD Nano daily scan logic.
- Applied Candidate 34 Nano rule family with `max_entry_price: 50`.
- Enforced $100 whole-share affordability with slippage.
- Wrote exactly one daily scan result: `MANUAL_REVIEW_CANDIDATE` or `NO_TRADE_MANUAL_REVIEW`.
- Added stale-data handling with explicit `STALE_DATA` no-trade output.
- Added top 5 scanned candidates with pass/fail flags in the Markdown report.
- Added tests for action count, affordability rejection, valid candidate selection, stale data, no forward-return ranking, and report writing.
- Did not add news, SEC, short interest, options, LLM ranking, paid data, or external APIs.
- Did not start paper trading.
- Did not start live trading.
- Did not label anything live-tradable.

## Files Changed

- `src/backtest/nano_daily_scan.py`
- `src/main.py`
- `tests/test_nano_daily_scan.py`
- `data/reports/nano_daily_scan.csv`
- `data/reports/nano_daily_scan.md`
- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

Local virtual environment:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

## Output

Generated files:

- `data/reports/nano_daily_scan.csv`
- `data/reports/nano_daily_scan.md`
- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/processed/factor_dataset.csv`

Daily scan report starts with:

```text
PHOENIX NANO DAILY SCAN
Action: NO_TRADE_MANUAL_REVIEW
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_nano_daily_scan.py -q
# 6 passed in 0.55s
```

```bash
.venv/bin/python -m pytest -q
# 57 passed, 1 warning in 1.53s
```

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

## Daily Scan Result

- Action: `NO_TRADE_MANUAL_REVIEW`
- Candidate ticker: none
- Latest data date used: `2026-06-30`
- Result stale/current: current, `is_stale = False`
- Reason: `NO_CANDIDATE_PASSED_RULES`
- Account: $100 whole-share account
- Candidate rule: Candidate 34 Nano, `max_entry_price = 50`
- Forward returns used for ranking: no
- Realized trade outcomes used for ranking: no

Top scanned candidates on the latest data date were AMAT, KLAC, LRCX, AMD, and PANW. None passed all rule checks. The top scanned names were rejected because they did not satisfy the full Candidate 34 Nano rule plus $50 max-entry and $100 whole-share affordability gates.

## Problems

- No current manual-review candidate passed the Nano Daily Scan gate.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- Existing metadata filters still exclude some intended watchlist names because the MVP requires metadata pass purity.
- The run emitted existing pandas `pct_change` future warnings and the macOS LibreSSL warning; neither blocked execution.
- yfinance data remains non-institutional retail data and should not be treated as a live execution feed.

## Questions For GPT

- Should the next task inspect why the latest top-scored candidates are above the $50 Nano entry cap?
- Should GPT keep Candidate 34 as the daily scan rule, or define a separate Nano daily scan rule with the same safety constraints?
- Should the stale-data threshold be made stricter around market holidays and weekends?

## Next Suggested Tasks

- Do not start live trading.
- Do not start paper trading until GPT explicitly approves.
- Keep daily scan output manual-review only.
- Add a small diagnostic table for the highest-ranked affordable names under $50.
- Add market-calendar-aware stale-date checks before any paper-trading workflow.
