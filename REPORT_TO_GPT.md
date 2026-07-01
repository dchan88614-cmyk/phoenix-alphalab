# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Completed Generation 1: Decision Engine Prototype.
- Added the first explicit BUY / NO_TRADE decision-generation layer.
- Added `src/decision/decision_engine.py`.
- Added structured decision records with:
  - date
  - action
  - ticker
  - entry price/range
  - stop loss
  - target 1
  - target 2
  - expected holding period
  - confidence
  - reason
  - smoke score
  - rank
- Used same-day close as the historical EOD proxy entry price.
- Implemented baseline v0 BUY rule using only rank 1 smoke candidates and existing smoke fields.
- Did not add news, SEC, short interest, options, LLM ranking, or new alpha factors.
- Did not change the smoke ranking rule.
- Added `--decision-simulation` CLI flag.
- Added `data/reports/decision_simulation.csv`.
- Added `data/reports/decision_simulation.md`.
- Updated `README.md` and `BRAIN.md` to clarify that research reports are internal diagnostics and the product goal is daily BUY / NO_TRADE decision quality.
- Added tests for BUY/NO_TRADE logic, stop/target calculations, forward-return non-leakage, and report file output.

## Files Changed

- `README.md`
- `BRAIN.md`
- `REPORT_TO_GPT.md`
- `src/main.py`
- `src/backtest/smoke_test.py`
- `src/decision/__init__.py`
- `src/decision/decision_engine.py`
- `tests/test_decision_engine.py`
- `data/reports/smoke_test.csv`
- `data/reports/decision_simulation.csv`
- `data/reports/decision_simulation.md`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --smoke-test --decision-simulation
```

If using the local virtual environment:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --smoke-test --decision-simulation
```

Expected outputs:

- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/reports/smoke_test.csv`
- `data/reports/smoke_test.md`
- `data/reports/decision_simulation.csv`
- `data/reports/decision_simulation.md`
- `data/processed/factor_dataset.csv`

## Output

Latest Generation 1 decision simulation run:

- Universe ticker count after strict metadata filter: 98
- Decision date range: 2026-03-05 to 2026-05-29
- Total signal days: 60
- BUY days: 59
- NO_TRADE days: 1
- BUY rate: 98.33%
- Best BUY: 2026-04-07 INTC, 20d +104.40%
- Worst BUY: 2026-03-05 AVGO, 20d -5.48%
- Comparison: BUY filtering improved performance versus always buying smoke rank 1.

BUY decisions:

- 5d average forward return: 8.44%
- 5d average excess return vs SPY: 7.52%
- 5d win rate: 71.19%
- 10d average forward return: 13.25%
- 10d average excess return vs SPY: 11.45%
- 10d win rate: 76.27%
- 20d average forward return: 32.10%
- 20d average excess return vs SPY: 28.00%
- 20d win rate: 91.53%

Always buy smoke rank 1 comparison:

- 5d average forward return: 8.19%
- 5d average excess return vs SPY: 7.28%
- 10d average forward return: 12.72%
- 10d average excess return vs SPY: 10.92%
- 20d average forward return: 31.31%
- 20d average excess return vs SPY: 27.22%

## Test Results

```bash
.venv/bin/python -m pytest -q
# 22 passed, 1 warning in 0.72s
```

End-to-end decision simulation command completed successfully and wrote both decision reports.

## Problems

- BUY rate is 98.33%, so Generation 1 filtering barely narrows the smoke rank 1 stream.
- The reported improvement versus always buying smoke rank 1 is small relative to the already strong smoke result.
- Decision simulation currently uses only the latest 60 eligible smoke days because it is built on the current smoke test flow.
- The v0 stop/target levels are mechanical ATR/risk multiples and are not evaluated as intraperiod hit/miss outcomes.
- Current watchlist and yfinance metadata are not point-in-time.
- Strict yfinance metadata filtering still rejects some names and has false exclusions such as `U` via keyword matching.
- The run emitted pandas `pct_change` future warnings and the existing macOS LibreSSL warning; neither blocked the run.

## Questions For GPT

- Is Generation 1 useful enough if it emits BUY on 59 of 60 signal days?
- Should Generation 2 focus on reducing BUY frequency, or first evaluate whether mechanical stop/target levels were hit before forward close labels?
- Should the decision simulation be extended to multi-window before tuning any BUY rule thresholds?
- Should rank 1 only remain the decision candidate, or should NO_TRADE be allowed when rank 1 fails while lower ranks pass?

## Next Suggested Tasks

- Review Generation 1 output before changing thresholds.
- Add multi-window decision simulation using the same v0 rule before any tuning.
- Add stop/target path evaluation using OHLC data if GPT wants to judge trade plan quality rather than close-to-close labels.
- Fix instrument-type filtering precision before expanding the watchlist further.
- Do not start Generation 2 until GPT reviews this report.
