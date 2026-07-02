# REPORT_TO_GPT

## Completed

- Updated and executed `TASKS.md`: Phoenix Nano Phase 1C - Continuous Account Growth Backtest.
- Added `--phase1c-continuous-account-backtest` CLI flag.
- Added a continuous $100 account backtest module that:
  - starts with $100 once;
  - runs across 2024-01-01 to 2026-06-30;
  - uses EOD information available on or before each replay date;
  - selects one stock or NO_TRADE each eligible replay day;
  - rejects unaffordable stocks before ranking;
  - enforces one open position at a time;
  - uses next-session open entry;
  - applies the requested partial-exit / stop / max-hold plan;
  - tracks account equity events and milestone dates.
- Generated required reports:
  - `data/reports/phase1c_continuous_account_trades.csv`
  - `data/reports/phase1c_continuous_account_equity_curve.csv`
  - `data/reports/phase1c_continuous_account_summary.md`
- Did not start paper trading.
- Did not start live trading.
- Did not mark Phoenix as live-tradable.

## Files Changed

- `TASKS.md`
- `src/main.py`
- `src/research/phase1c_continuous_account.py`
- `tests/test_phase1c_continuous_account.py`
- `data/reports/phase1c_continuous_account_trades.csv`
- `data/reports/phase1c_continuous_account_equity_curve.csv`
- `data/reports/phase1c_continuous_account_summary.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1c-continuous-account-backtest
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_phase1c_continuous_account.py -q
# 5 passed
```

```bash
.venv/bin/python -m pytest -q
# 210 passed, 1 warning in 30.93s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

The Phase 1C CLI completed successfully and wrote all required reports.

## Continuous Account Summary

- Starting account value: $100.00
- Ending account value: $92.15
- Total return: -7.85%
- Highest account value reached: $176.25
- $1000 reached: False
- Trade count: 30
- Win rate: 53.33%
- Max drawdown: -50.46%
- Longest flat period: 512 calendar days from 2025-02-05 to 2026-07-02

## Milestone Dates

- $150: 2024-12-04
- $200: not reached
- $300: not reached
- $500: not reached
- $1000: not reached

## Best Trade

- 2024-10-22 CORZ TARGET_30 return: 28.12%

## Worst Trade

- 2024-04-26 SOFI STOP return: -10.00%

## Main Bottleneck

- Most common block rule: `price_between_5_and_50`
- Blocked rows: 17,345

Top block counts:

| rule | count |
|---|---:|
| price_between_5_and_50 | 17,345 |
| return_5d_between_3_and_15 | 4,776 |
| relative_volume_prev20_min_1_5 | 973 |
| dollar_volume_min | 591 |
| green_days_5_min_3 | 455 |

## Problems

- The account did not sustain growth after reaching $176.25.
- The final account value ended below starting capital.
- Max drawdown was too large for a $100 account.
- The last BEAM position was marked `OPEN_AT_DATA_END`, so its final value is based on available data through the downloaded post-period rows.
- The result remains yfinance-based research data and is not independently vendor-validated.

## Questions For GPT

- Should the next task diagnose why drawdown reached -50.46% before adjusting rules?
- Should the price range remain $5-$50, or should GPT test a narrower price band in a separate task?
- Should entries be delayed or skipped after large account drawdowns?

## Next Suggested Tasks

- Run a failure attribution task on the 18 STOP exits and the long flat period.
- Analyze whether `price_between_5_and_50` is too broad or simply reflecting the universe mix.
- Do not start paper trading.
- Do not start live trading.
- Do not mark Phoenix as live-tradable.
