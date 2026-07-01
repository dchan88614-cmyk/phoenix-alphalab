# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Completed Phoenix AlphaLab Sprint 3.2: Multi-Window Smoke Test.
- Added `src/backtest/multi_window_smoke_test.py`.
- Added CLI support for `--multi-window-smoke-test`.
- Reused the exact Sprint 3 smoke ranking rule without adding or changing factors.
- Added default non-overlapping windows from 2024-01-02 through 2026-06-30.
- Added per-window outputs:
  - universe ticker count
  - selected unique ticker count
  - signal days
  - 5d/10d/20d average return
  - 5d/10d/20d average excess return vs SPY
  - 5d/10d/20d win rate
  - 20d days outperformed SPY
  - best trade
  - worst trade
  - top 5 most selected tickers
- Added cross-window summary outputs:
  - count of windows with 20d average excess above 0
  - count of windows where 20d days_outperformed_spy is above 50%
  - best window
  - worst window
  - initial cross-window judgment
- Added `insufficient_data` status for windows without enough eligible rows.
- Added tests for independent window stats, non-overlapping windows, output files, and insufficient-data marking.
- Re-ran the requested watchlist multi-window smoke test.

## Files Changed

- `README.md`
- `REPORT_TO_GPT.md`
- `src/main.py`
- `src/backtest/multi_window_smoke_test.py`
- `tests/test_multi_window_smoke_test.py`
- `data/reports/multi_window_smoke_test.csv`
- `data/reports/multi_window_smoke_test.md`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --multi-window-smoke-test
```

If using the local virtual environment:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --multi-window-smoke-test
```

Expected outputs:

- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/reports/multi_window_smoke_test.csv`
- `data/reports/multi_window_smoke_test.md`
- `data/processed/factor_dataset.csv`

## Output

Latest multi-window smoke test run:

- Windows tested: 10
- Windows with sufficient data: 10
- Universe ticker count: 98
- Windows with 20d average excess > 0: 6 / 10
- Windows with 20d days_outperformed_spy above 50%: 7 / 10
- Best window by 20d average excess: 2026-04-01 to 2026-06-30, 23.45%
- Worst window by 20d average excess: 2025-01-02 to 2025-03-31, -5.93%
- Cross-window judgment: initial cross-window strength exists, but it still needs stricter universe and data validation.

Window-level 20d average excess:

- 2024-01-02 to 2024-03-29: -1.30%
- 2024-04-01 to 2024-06-28: 0.82%
- 2024-07-01 to 2024-09-30: -0.32%
- 2024-10-01 to 2024-12-31: 9.35%
- 2025-01-02 to 2025-03-31: -5.93%
- 2025-04-01 to 2025-06-30: 6.19%
- 2025-07-01 to 2025-09-30: 7.11%
- 2025-10-01 to 2025-12-31: -1.55%
- 2026-01-02 to 2026-03-31: 4.00%
- 2026-04-01 to 2026-06-30: 23.45%

## Test Results

```bash
.venv/bin/python -m pytest -q
# 17 passed, 1 warning in 0.70s
```

End-to-end multi-window smoke test command completed successfully and wrote both multi-window reports.

## Known Issues

- The first window has only 1 eligible signal day because previous-window factors need warmup data from the 2024-01-01 start.
- Current windows use the same downloaded dataset ending 2026-06-30; latest dates without complete forward labels are not eligible signal rows.
- The watchlist remains manually curated and not point-in-time.
- Strict yfinance metadata filtering still rejects some names and has false exclusions such as `U` via keyword matching.
- The run emitted pandas `pct_change` future warnings and the existing macOS LibreSSL warning; neither blocked this run.

## Questions For GPT

- Should the first window be rerun with earlier warmup data, such as starting downloads from 2023-01-01, before judging 2024 Q1?
- Is 6 / 10 positive 20d excess windows enough to continue, or should the stop/go threshold be stricter?
- Should the next step be fixing universe/filter precision before any more result interpretation?

## Next Suggested Tasks

- Add a warmup-start option so window tests can score early windows without losing signal days.
- Fix instrument-type filtering precision without changing alpha factors.
- Add rejected ticker count/reasons to multi-window reports.
- Keep the ranking rule frozen until cross-window and warmup-adjusted results are reviewed.
