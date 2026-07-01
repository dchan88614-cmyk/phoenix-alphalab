# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Completed Phoenix AlphaLab Sprint 3: Smoke Test.
- Added `src/backtest/smoke_test.py`.
- Implemented a recent eligible signal-day rolling smoke test with default `--smoke-days 60`.
- Added simple Top 5 ranking using only:
  - `relative_volume_prev20`
  - `return_5d`
  - `return_20d`
  - `distance_to_52w_high_prev`
  - `dollar_volume`
- Excluded forward returns, market cap, news, SEC data, short interest, and AI/Phoenix scores from ranking.
- Added CLI flags:
  - `--smoke-test`
  - `--smoke-days`
- Added CSV and Markdown smoke test outputs.
- Added smoke test unit coverage for no forward-return ranking leakage, max Top 5 per date, output file creation, and benchmark excess-return math.
- Ran the requested 60-day smoke test for `AAPL,NVDA,SMCI,PLTR` versus `SPY`.

## Files Changed

- `README.md`
- `REPORT_TO_GPT.md`
- `src/main.py`
- `src/backtest/smoke_test.py`
- `tests/test_smoke_test.py`
- `data/reports/smoke_test.csv`
- `data/reports/smoke_test.md`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --tickers AAPL,NVDA,SMCI,PLTR --start 2024-01-01 --end 2026-06-30 --smoke-test --smoke-days 60
```

If using the local virtual environment:

```bash
.venv/bin/python -m src.main --tickers AAPL,NVDA,SMCI,PLTR --start 2024-01-01 --end 2026-06-30 --smoke-test --smoke-days 60
```

Expected outputs:

- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/reports/smoke_test.csv`
- `data/reports/smoke_test.md`
- `data/processed/factor_dataset.csv`

## Output

Latest smoke test run:

- Test range: 2026-03-05 to 2026-05-29
- Signal days: 60
- Selected rows: 240
- 5d average return: 1.84%
- 5d average excess return vs SPY: 0.93%
- 5d win rate: 57.92%
- 5d days outperformed SPY: 31 / 60
- 10d average return: 2.77%
- 10d average excess return vs SPY: 0.97%
- 10d win rate: 56.25%
- 10d days outperformed SPY: 37 / 60
- 20d average return: 4.86%
- 20d average excess return vs SPY: 0.76%
- 20d win rate: 54.58%
- 20d days outperformed SPY: 31 / 60
- Best 20d trade: 2026-05-04 SMCI, 79.69%
- Worst 20d trade: 2026-05-29 SMCI, -38.92%
- Initial smoke-test judgment: worth continuing, but only as a simple research check.

## Test Results

```bash
.venv/bin/python -m pytest -q
# 9 passed in 0.34s
```

End-to-end smoke test command completed successfully and wrote both smoke test reports.

## Known Issues

- The smoke test used only four research tickers, so each day selected up to four names, not five.
- Recent eligible signal days exclude the latest dates without complete 5/10/20-day forward labels.
- The result is a small smoke test, not evidence of a deployable strategy.
- Current MVP still depends on yfinance metadata and OHLCV data.
- The local Python stack still emits a macOS LibreSSL warning from urllib3/yfinance; it did not block this run.

## Questions For GPT

- Is this small-ticker smoke test enough to justify trying a broader ticker basket, or should we stop until the universe source is stronger?
- Should the simple smoke rule be frozen for one broader run before any ranking tweaks are allowed?
- Should the continuation threshold be defined explicitly, such as positive average excess return in at least two horizons and more than half of days beating SPY?

## Next Suggested Tasks

- Run the same smoke test on a broader but still manually chosen common-stock basket.
- Keep the same ranking rule fixed for the next run so results, not tuning, drive the decision.
- Add run settings to the smoke report header for reproducibility.
- Do not add news, SEC, short interest, Phoenix Score, or AI ranking until the simple smoke test earns it.
