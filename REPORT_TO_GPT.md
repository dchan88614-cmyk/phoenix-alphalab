# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Completed Phoenix AlphaLab Sprint 3.1: Real Smoke Test Universe.
- Added `config/watchlists/us_liquid_growth_100.txt`.
- Added CLI support for `--watchlist`; when both `--tickers` and `--watchlist` are supplied, `--watchlist` wins.
- Kept the smoke test ranking rule unchanged:
  - `relative_volume_prev20`
  - `return_5d`
  - `return_20d`
  - `distance_to_52w_high_prev`
  - `dollar_volume`
- Added smoke report realism checks:
  - Universe ticker count
  - Selected unique ticker count
  - Top 10 most selected tickers
  - Best/worst trade excluding the most selected ticker
  - Result excluding best single trade
  - Result excluding worst single trade
  - Result excluding SMCI if SMCI appears
  - Small-universe warning when universe count is below 30
- Added tests for watchlist reading, universe count reporting, small-universe warning, and excluding-best-trade output.
- Re-ran the requested watchlist smoke test.

## Files Changed

- `README.md`
- `REPORT_TO_GPT.md`
- `config/watchlists/us_liquid_growth_100.txt`
- `src/main.py`
- `src/backtest/smoke_test.py`
- `tests/test_smoke_test.py`
- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/reports/smoke_test.csv`
- `data/reports/smoke_test.md`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --smoke-test --smoke-days 60
```

If using the local virtual environment:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --smoke-test --smoke-days 60
```

Expected outputs:

- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/reports/smoke_test.csv`
- `data/reports/smoke_test.md`
- `data/processed/factor_dataset.csv`

## Output

Latest watchlist smoke test run:

- Test range: 2026-03-05 to 2026-05-29
- Universe ticker count after strict metadata filter: 98
- Selected unique ticker count: 45
- Signal days: 60
- Selected rows: 300
- 5d average return: 5.50%
- 5d average excess return vs SPY: 4.59%
- 5d win rate: 62.33%
- 5d days outperformed SPY: 43 / 60
- 10d average return: 9.61%
- 10d average excess return vs SPY: 7.81%
- 10d win rate: 68.00%
- 10d days outperformed SPY: 49 / 60
- 20d average return: 22.79%
- 20d average excess return vs SPY: 18.69%
- 20d win rate: 77.00%
- 20d days outperformed SPY: 57 / 60
- Top selected ticker: MRVL, selected 29 times
- Best 20d trade: 2026-04-07 INTC, 104.40%
- Worst 20d trade: 2026-05-27 RKLB, -46.29%
- Result excluding best single trade, 20d average return: 22.52%
- Result excluding worst single trade, 20d average return: 23.02%
- Result excluding SMCI: Not applicable because SMCI was not selected in the latest smoke test output.

## Test Results

```bash
.venv/bin/python -m pytest -q
# 13 passed, 1 warning in 0.60s
```

End-to-end watchlist smoke test command completed successfully and wrote both smoke test reports.

## Known Issues

- The watchlist file contains a broad manually curated basket, not a formal point-in-time universe.
- yfinance metadata rejected several tickers under strict metadata filtering; this improves purity but can exclude valid names.
- The existing keyword filter rejected `U` because `UNIT` matches the company name text for Unity; this needs a more precise instrument-type filter later.
- The run emitted pandas `pct_change` future warnings and the existing macOS LibreSSL warning; neither blocked the run.
- Strong smoke results are not proof of a deployable strategy. This is still a recent-window sanity check.

## Questions For GPT

- Is the broader watchlist smoke result enough to justify one larger fixed-rule basket run?
- Should the instrument-type filtering be upgraded before any more smoke tests, specifically to avoid false exclusions like `U`?
- Should the current smoke rule be frozen and rerun across multiple historical windows before any ranking tweak is allowed?

## Next Suggested Tasks

- Fix instrument-type filtering precision without adding new alpha factors.
- Add run metadata to smoke reports, including watchlist path, rejected ticker count, and rejected reasons.
- Run the same fixed rule across several non-overlapping 60-day windows.
- Do not add news, SEC, short interest, Phoenix Score, or AI ranking until the simple smoke evidence survives out-of-sample windows.
