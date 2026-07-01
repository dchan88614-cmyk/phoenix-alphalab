# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Auto Research Loop v0.2 - Historical Trade Simulator + Selective Decisions.
- Added `src/trading/trade_simulator.py`.
- Simulated historical virtual trades using:
  - EOD signal date.
  - Next trading day entry.
  - Next day open as entry price, with close fallback.
  - ATR-based stop loss, with 8% fallback stop.
  - Target 1 and Target 2 based on entry risk.
  - 20-trading-day max holding period.
  - Worst-case same-day stop/target ordering.
- Changed auto research candidate evaluation to use realized trade outcomes instead of 20d forward-return labels.
- Added active max BUY rate enforcement that reduces trades before simulation instead of only failing a gate afterward.
- Added rank gap calculation and candidate filtering by rank gap.
- Added candidate parameters for:
  - `max_buy_rate`
  - `min_relative_volume_prev20`
  - `min_smoke_score`
  - `min_rank_gap`
  - return filters
  - distance to 52w high
  - dollar volume
- Added `data/reports/trade_simulation_trades.csv`.
- Updated `auto_research_generations.csv` and `auto_research_summary.md` for realized trade metrics.
- Kept alpha sources unchanged.
- Did not add news, SEC, short interest, options, LLM ranking, paid data, or external APIs.
- Did not label anything live-tradable.

## Files Changed

- `src/main.py`
- `src/research/auto_loop.py`
- `src/trading/__init__.py`
- `src/trading/trade_simulator.py`
- `tests/test_auto_loop.py`
- `tests/test_trade_simulator.py`
- `data/reports/auto_research_generations.csv`
- `data/reports/auto_research_summary.md`
- `data/reports/trade_simulation_trades.csv`
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

Latest v0.2 run:

- Data start requested: 2023-03-07
- Research start: 2024-01-01
- Research end: 2026-06-30
- Warmup limitation: earliest available data was 2023-04-03.
- Total candidates available: 100
- Total candidates evaluated: 50
- Candidates passed gate: 0
- Candidates failed gate: 50
- Stop reason: `10_consecutive_candidates_failed_to_improve_best_score`
- Trade rows written: 11,981
- Active BUY rate distribution: min 6.95%, median 29.47%, max 91.72%
- Realized return distribution by candidate: min 1.26%, median 1.92%, max 3.58%

Generated files:

- `data/reports/trade_simulation_trades.csv`
- `data/reports/auto_research_generations.csv`
- `data/reports/auto_research_summary.md`
- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/processed/factor_dataset.csv`

## Test Results

```bash
.venv/bin/python -m pytest -q
# 34 passed, 1 warning in 0.84s
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
- Best realized return: 37.76%
- Stop hit rate: 47.13%
- Target 1 hit rate: 39.08%
- Target 2 hit rate: 2.30%
- Time exit rate: 11.49%
- Fail reason: `realized_win_rate_lt_52pct`

Whether any candidate became `RESEARCH_QUALIFIED_NOT_LIVE`:

- No. 0 of 50 evaluated candidates passed all v0.2 gates.

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

Stop/target/time-exit breakdown across all simulated trades:

- STOP: 55.19%
- TARGET_1: 34.86%
- TARGET_2: 1.97%
- TIME_EXIT: 7.99%

Interpretation:

- Stop/target simulation reduced realized tail risk versus the prior -63.53% 20d forward-return tail observation.
- Active max BUY rate enforcement materially reduced selectivity for stricter candidates.
- The best candidate still missed the 52% realized win-rate gate, so Phoenix remains research-only and not tradable.

## Problems

- No candidate passed the v0.2 research-qualified gate.
- The best candidate missed the win-rate gate by a small margin: 51.72% vs required 52%.
- MSTR dominates both worst and best realized trade examples, so concentration risk still needs review.
- Some candidate sets still have high BUY rates when `max_buy_rate` is loose.
- yfinance metadata filtering still rejects some intended watchlist names and may falsely exclude names such as `U`.
- The run emitted existing pandas `pct_change` future warnings and the macOS LibreSSL warning; neither blocked execution.

## Questions For GPT

- Should the next task inspect concentration by ticker before changing any gate?
- Should stop/target parameters remain fixed for another run, or should only exit diagnostics be expanded first?
- Should the next candidate search explicitly penalize MSTR concentration without using future returns?
- Should metadata filtering be fixed before judging the universe again?

## Next Suggested Tasks

- Do not add new alpha sources yet.
- Add concentration diagnostics by ticker and by sector/theme.
- Report candidate performance excluding the most selected ticker and excluding MSTR.
- Review why realized win rate remains below 52% despite positive average realized excess.
- Keep Phoenix labeled research-only and not live-tradable.
