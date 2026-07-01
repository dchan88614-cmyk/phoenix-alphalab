# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1A - Run 100 Historical Replay Rounds.
- Added a Phase 1A historical replay engine that samples 100 completed historical trading dates across 2024-01-01 to 2026-06-30.
- Each replay date pretends that date is today, applies replay-date EOD factors, rejects unaffordable symbols before ranking, and outputs exactly one decision.
- Kept the frozen Candidate 34 / current Nano rule set.
- Used forward returns only after each decision row was recorded.
- Added one-position-at-a-time account replay with $100 whole-share constraints.
- Added Phase 1A CLI flags:
  - `--phase1-historical-replay`
  - `--replay-rounds 100`
- Created Phase 1A outputs:
  - `data/reports/phase1_historical_replay_decisions.csv`
  - `data/reports/phase1_historical_replay_summary.md`
  - `data/reports/phase1_historical_replay_near_misses.csv`
- Did not start Phase 2.
- Did not start Phase 3.
- Did not start paper trading.
- Did not start live trading.

## Files Changed

- `src/research/historical_replay.py`
- `src/main.py`
- `tests/test_historical_replay.py`
- `data/reports/phase1_historical_replay_decisions.csv`
- `data/reports/phase1_historical_replay_summary.md`
- `data/reports/phase1_historical_replay_near_misses.csv`
- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1-historical-replay --replay-rounds 100
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_historical_replay.py -q
# 7 passed in 0.59s
```

```bash
.venv/bin/python -m pytest -q
# 78 passed, 1 warning in 1.62s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1-historical-replay --replay-rounds 100
```

## Phase 1A 100-Round Summary

- Total replay rounds: 100
- BUY count: 34
- NO_TRADE count: 66
- BUY rate: 34.00%
- Accuracy 1d: 55.88%
- Accuracy 3d: 55.88%
- Accuracy 5d: 50.00%
- Accuracy 10d: 52.94%
- Accuracy 20d: 58.82%
- Trade-simulation accuracy: 41.18%
- Account ending value: $179.61
- Max drawdown: -45.86%
- Profit factor: 1.2969
- Average win size: $24.84
- Average loss size: $-13.41
- Worst trade account loss: -11.66%
- Best pick: 2024-01-10 SMCI 20d=103.87%
- Worst pick: 2025-06-27 CORZ 20d=-17.45%
- Top selected tickers: HPE:4, SMCI:3, RIVN:3, PLTR:3, CORZ:2, HOOD:2, F:2, INTC:2, RKLB:2, PATH:1

## Phase 1A Status

- Status: `PHASE_1A_NEEDS_MORE_ITERATION`
- Reason: ending account value was above $100, but max drawdown was worse than -35% and trade-simulation accuracy was below 50%.
- This result is not Phase 2 ready.
- This result is not paper-trading approval.

## Problems

- The 20d forward-return accuracy was positive at 58.82%, but simulated execution quality was weak at 41.18%.
- Ending account value reached $179.61, but max drawdown was severe at -45.86%.
- The strongest single 20d pick was SMCI early in 2024, so GPT should review concentration and path dependency before trusting the result.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- Existing pandas `pct_change` future warnings appeared during the end-to-end run; they did not block execution.
- yfinance data remains non-institutional retail data and should not be treated as an execution feed.

## Questions For GPT

- Should Phase 1A repeat with several different evenly spaced samples before changing any Candidate 34 thresholds?
- Should GPT require max drawdown improvement before allowing Phase 2 manual paper validation?
- Should replay analysis separate close-to-close forward accuracy from stop/target execution accuracy?
- Should SMCI-heavy early-2024 contribution be stress-tested before any rule iteration?

## Next Suggested Tasks

- Do not start Phase 2 yet.
- Do not start Phase 3.
- Do not start paper trading.
- Run additional Phase 1 replay batches or a full-date replay before changing thresholds.
- Add a drawdown-focused replay diagnostic to identify whether losses come from stop placement, entry timing, or ticker concentration.
