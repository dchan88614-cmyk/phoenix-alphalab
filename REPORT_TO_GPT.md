# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Completed Phoenix AlphaLab Sprint 2: Backtest Safety Upgrade.
- Documented that Phoenix AlphaLab is currently an End-of-Day research system.
- Clarified that EOD factors may use data known after the same day's close, but must not be used as same-day intraday trading signals.
- Added explicit EOD and previous-window factor names:
  - `relative_volume_eod`
  - `relative_volume_prev20`
  - `distance_to_52w_high_eod`
  - `distance_to_52w_high_prev`
- Set `universe.require_metadata_pass` to `true` by default.
- Changed missing or incomplete metadata handling to reject by default when strict metadata is enabled.
- Added a runtime WARNING when `min_market_cap` or `max_market_cap` is configured.
- Documented in code that market cap is current metadata, not point-in-time, and must not be treated as a historical factor.
- Upgraded Markdown factor report header with Research Mode details.
- Added tests for ticker-safe forward returns, previous-window factor timing, and price/liquidity filters.
- Regenerated tracked sample reports in `data/reports/`.

## Files Changed

- `README.md`
- `BRAIN.md`
- `REPORT_TO_GPT.md`
- `config/settings.yaml`
- `src/backtest/factor_test.py`
- `src/data/filters.py`
- `src/data/universe.py`
- `src/factors/momentum.py`
- `src/factors/volume.py`
- `src/main.py`
- `src/reports/markdown_report.py`
- `tests/test_forward_returns.py`
- `tests/test_factor_timing.py`
- `tests/test_filters.py`
- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --tickers AAPL,NVDA,SMCI,PLTR --start 2024-01-01 --end 2026-06-30
```

If using the local virtual environment:

```bash
.venv/bin/python -m src.main --tickers AAPL,NVDA,SMCI,PLTR --start 2024-01-01 --end 2026-06-30
```

Expected outputs:

- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/processed/factor_dataset.csv`

## Test Results

```bash
.venv/bin/python -m pytest -q
# 5 passed in 0.36s
```

End-to-end command also completed successfully and wrote the CSV/Markdown reports.

## Known Issues

- Strict metadata filtering improves research purity but may reduce ticker coverage because missing or incomplete metadata is rejected by default.
- Current MVP still depends on yfinance metadata, which is not a fully authoritative security master.
- Market cap metadata is not point-in-time and should not be treated as a bias-free historical filter.
- If market cap filters are configured, the run prints a warning, but the test output still needs GPT review before any factor interpretation.
- The local Python stack still emits a macOS LibreSSL warning from urllib3/yfinance; it did not block this run.

## Questions For GPT

- Should the next research pass use only `*_prev` factors for stricter tradeability, or keep both EOD and previous-window variants for comparison?
- Should market cap filters remain available behind explicit configuration, or be removed until point-in-time market cap data is available?
- Should metadata strictness be relaxed only for benchmark tickers, or should benchmark metadata remain outside the research universe logic?

## Next Suggested Tasks

- Add a `signal_time` design note before any pre-market or intraday factor work.
- Add a small fixture-based integration test for `build_factor_report` using both EOD and previous-window factor columns.
- Add provider abstraction notes for replacing yfinance metadata with a proper security master.
- Add report metadata that records the exact settings used for each run.
