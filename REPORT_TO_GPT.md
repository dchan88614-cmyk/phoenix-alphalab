# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Auto Research Loop v0.3 - Concentration Risk + Robustness Before Gate Tuning.
- Added `src/research/concentration.py`.
- Added ticker-level concentration diagnostics.
- Added robustness variants:
  - base trades
  - excluding MSTR
  - excluding most selected ticker
  - excluding top 3 selected tickers
  - per-ticker cap 10 full period
  - per-ticker cap 5 per year
  - equal-ticker-weighted summary
- Added active candidate parameter `max_trades_per_ticker_per_year`.
- Applied active per-ticker/year caps after candidate filters and active max BUY rate enforcement, using only signal-date-safe `decision_strength`.
- Added market regime diagnostics for SPY 50dma and 200dma using signal-date/prior OHLCV data.
- Updated v0.3 gate with robustness requirements.
- Added reports:
  - `data/reports/concentration_report.csv`
  - `data/reports/concentration_report.md`
  - `data/reports/robustness_report.csv`
  - `data/reports/regime_diagnostics.csv`
  - `data/reports/regime_diagnostics.md`
- Updated `auto_research_generations.csv`, `auto_research_summary.md`, and `trade_simulation_trades.csv`.
- Kept alpha sources unchanged.
- Did not add news, SEC, short interest, options, LLM ranking, paid data, or external APIs.
- Did not start paper trading or live trade generation.
- Did not label anything live-tradable.

## Files Changed

- `src/main.py`
- `src/research/auto_loop.py`
- `src/research/concentration.py`
- `src/trading/trade_simulator.py`
- `tests/test_concentration.py`
- `data/reports/auto_research_generations.csv`
- `data/reports/auto_research_summary.md`
- `data/reports/trade_simulation_trades.csv`
- `data/reports/concentration_report.csv`
- `data/reports/concentration_report.md`
- `data/reports/robustness_report.csv`
- `data/reports/regime_diagnostics.csv`
- `data/reports/regime_diagnostics.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

Local virtual environment:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

## Output

Latest v0.3 run:

- Data start requested: 2023-03-07
- Research start: 2024-01-01
- Research end: 2026-06-30
- Warmup limitation: earliest available data was 2023-04-03.
- Total candidates available: 100
- Total candidates evaluated: 50
- Candidates passed v0.3 gate: 0
- Candidates failed v0.3 gate: 50
- Stop reason: `10_consecutive_candidates_failed_to_improve_best_score`
- Trade rows written: 11,877
- Active BUY rate distribution: min 6.95%, median 29.47%, max 90.23%
- Realized return distribution by candidate: min 1.24%, median 1.88%, max 3.58%

Generated files:

- `data/reports/trade_simulation_trades.csv`
- `data/reports/auto_research_generations.csv`
- `data/reports/auto_research_summary.md`
- `data/reports/concentration_report.csv`
- `data/reports/concentration_report.md`
- `data/reports/robustness_report.csv`
- `data/reports/regime_diagnostics.csv`
- `data/reports/regime_diagnostics.md`
- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/processed/factor_dataset.csv`

## Test Results

```bash
.venv/bin/python -m pytest -q
# 43 passed, 1 warning in 1.64s
```

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

## Trade Simulation Summary

Best candidate even if failed:

- Candidate ID: 35
- Status: `RESEARCH_ONLY_NOT_TRADABLE`
- Final BUY days: 87
- Final BUY rate: 14.40%
- Average realized return: 3.58%
- Average realized excess return: 3.12%
- Realized win rate: 51.72%
- Worst realized return: -14.65%
- Stop hit rate: 47.13%
- Target 1 hit rate: 39.08%
- Target 2 hit rate: 2.30%
- Time exit rate: 11.49%
- Base fail reason: `realized_win_rate_lt_52pct`

Whether any candidate became `RESEARCH_QUALIFIED_NOT_LIVE`:

- No. 0 of 50 evaluated candidates passed all v0.3 gates.

Worst realized trade:

- 2024-03-28 MSTR signal.
- Entry: 2024-04-01 at 164.5010.
- Exit: 2024-04-16 at stop loss 131.6810.
- Realized return: -19.95%.
- Realized excess return: -16.08%.

Best realized trade:

- 2024-10-24 MSTR signal.
- Entry: 2024-10-25 at 236.3900.
- Exit: 2024-11-11 at Target 2, 341.2914.
- Realized return: 44.38%.
- Realized excess return: 41.41%.

## Concentration Summary

Best candidate concentration:

- Most selected ticker: DELL
- DELL trade count: 7
- Top 1 ticker trade share: 8.05%
- Top 3 ticker trade share: 18.39%
- MSTR trade count: 3
- MSTR average realized excess: -10.98%
- Best candidate is not primarily carried by MSTR.

Overall concentration across all candidate trades:

- Most selected ticker: MU
- Overall top 1 ticker trade share: 6.11%
- Overall top 3 ticker trade share: 15.57%
- Top 1 realized excess contribution share: 23.30%
- Top 3 realized excess contribution share: 59.57%

Top positive contributors included INTC, SMCI, DELL, HOOD, COIN, and APP depending on candidate.
Top negative contributors included OKLO, MSTR, AVGO, and MU depending on candidate.

## Robustness Summary

Best candidate robustness:

- Base average realized excess: 3.12%
- Excluding MSTR average realized excess: 3.63%
- Excluding MSTR realized win rate: 53.57%
- Excluding most selected ticker average realized excess: 2.61%
- Excluding top 3 selected tickers average realized excess: 2.39%
- Per-ticker cap 10 full period average realized excess: 3.12%
- Per-ticker cap 5 per year average realized excess: 3.12%
- Equal-ticker-weighted average realized excess: 1.14%

Interpretation:

- Candidate 35 remains positive after excluding MSTR.
- Candidate 35 remains positive after excluding its most selected ticker.
- Candidate 35 remains positive after excluding its top 3 selected tickers.
- Per-ticker caps do not materially change candidate 35 because it is already diversified.
- Equal-ticker-weighted performance remains positive for candidate 35, but 27 of 50 candidates fail the equal-weighted robustness requirement.
- The remaining problem for candidate 35 is not MSTR concentration; it is the base realized win rate at 51.72%, just below 52%.

## Regime Diagnostics Summary

Regime tags use only signal-date or prior data. No regime gate was added.

- SPY above 50dma: 9,728 trades, avg realized excess 1.59%, win rate 44.44%, stop hit 54.62%.
- SPY below 50dma: 2,149 trades, avg realized excess 0.57%, win rate 40.02%, stop hit 58.12%.
- SPY above 200dma: 10,918 trades, avg realized excess 1.38%, win rate 42.97%, stop hit 55.82%.
- SPY below 200dma: 959 trades, avg realized excess 1.66%, win rate 51.20%, stop hit 48.80%.
- QQQ regime diagnostics were not available because QQQ was not downloaded in this run.

Interpretation:

- SPY 50dma regime shows weaker performance below the 50dma, but not catastrophic enough to add a gate in this task.
- SPY 200dma below regime has higher win rate in this sample, so a simple bullish-only regime gate is not supported by this run.

## Problems

- No candidate passed the v0.3 research-qualified gate.
- All 50 candidates still failed `realized_win_rate_lt_52pct`.
- 27 candidates failed `equal_ticker_weighted_excess_not_positive`.
- 13 candidates still exceeded the 50% final BUY rate gate.
- 4 candidates had fewer than 6 windows with positive realized excess.
- QQQ regime diagnostics were unavailable because the run did not include QQQ data.
- yfinance metadata filtering still rejects some intended watchlist names and may falsely exclude names such as `U`.
- The run emitted existing pandas `pct_change` future warnings and the macOS LibreSSL warning; neither blocked execution.

## Questions For GPT

- Since candidate 35 survives MSTR and top-ticker exclusion, should the next task focus on exit design rather than concentration controls?
- Should QQQ be explicitly added as a benchmark/regime-only download so QQQ regime diagnostics are always available?
- Should the next iteration examine stop placement and target sequencing to improve win rate without loosening the 52% gate?
- Should metadata filtering be fixed before expanding the candidate search?

## Next Suggested Tasks

- Do not add new alpha sources yet.
- Add QQQ as a regime-only data dependency without using it as an alpha factor.
- Analyze losing trades for candidate 35 by exit reason and holding-day path.
- Compare alternative exit designs while keeping entry signals unchanged.
- Keep Phoenix labeled research-only and not live-tradable.
