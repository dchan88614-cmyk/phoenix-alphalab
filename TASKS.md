# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1A — Run 100 Historical Replay Rounds

David's clarified roadmap:

1. Phase 1: simulate old dates, select a stock or NO TRADE, reveal future outcome, repeat until accuracy improves.
2. Phase 2: use current/latest market data for manual paper validation.
3. Phase 3: real-money execution only after Phase 1 and Phase 2 gates are satisfied.

This task is **Phase 1A only**.

Run exactly the first controlled historical replay batch: **100 replay rounds**.

Do not start Phase 2.
Do not start Phase 3.
Do not loosen Candidate 34 thresholds yet.
Keep all output research/manual-review only.

## Goal

For 100 historical dates, pretend each date is “today.”

For each round:

1. Use only market data available on or before that historical replay date.
2. Apply Phoenix Nano $100 whole-share constraints.
3. Apply the frozen Candidate 34 / current Nano rule set.
4. Output exactly one decision:
   - `HISTORICAL_BUY_CANDIDATE`
   - or `HISTORICAL_NO_TRADE`
5. Then use future data only for verification.
6. Report accuracy.

## Replay Sample

Use 100 replay dates from:

- start: 2024-01-01
- end: 2026-06-30

Sampling rule:

- Use completed trading days only.
- Use enough spacing to cover different market periods.
- Prefer evenly spaced dates across the full period rather than 100 consecutive dates.
- Each replay date must have enough lookback data for factors and enough future data for at least 20 trading-day verification when possible.

## Account Rules

Use Phoenix Nano settings:

- starting capital: $100
- fractional shares: false
- whole shares only
- no margin
- no shorting
- max open positions: 1 for account replay
- max entry price: Candidate 34 max entry price, expected $50
- slippage: current project setting, expected 10 bps

Reject unaffordable tickers before ranking.

## Accuracy Definition

Report multiple accuracy metrics, not just one number.

For BUY decisions:

- 1d accuracy = percentage of BUY picks with forward_return_1d > 0
- 3d accuracy = percentage of BUY picks with forward_return_3d > 0
- 5d accuracy = percentage of BUY picks with forward_return_5d > 0
- 10d accuracy = percentage of BUY picks with forward_return_10d > 0
- 20d accuracy = percentage of BUY picks with forward_return_20d > 0
- trade-simulation accuracy = percentage of simulated exits with pnl_dollars > 0

Also report:

- BUY count
- NO_TRADE count
- BUY rate
- average and median forward return by window
- average win size
- average loss size
- profit factor
- ending account value from $100 using one-position-at-a-time replay
- max drawdown
- worst trade account loss
- best pick
- worst pick
- top selected tickers

## Implementation

Create or update:

`src/research/historical_replay.py`

Add CLI support:

```bash
--phase1-historical-replay
--replay-rounds 100
```

Command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1-historical-replay --replay-rounds 100
```

## Outputs

Create or update:

- `data/reports/phase1_historical_replay_decisions.csv`
- `data/reports/phase1_historical_replay_summary.md`
- `data/reports/phase1_historical_replay_near_misses.csv`

The summary must start with:

```text
PHOENIX NANO PHASE 1A — 100 HISTORICAL REPLAY ROUNDS
```

The summary must include a clear section:

```text
Accuracy
```

with all accuracy metrics listed above.

## Phase 1A Status

Mark the result as one of:

- `PHASE_1A_FAILED`
- `PHASE_1A_NEEDS_MORE_ITERATION`
- `PHASE_1A_PROMISING_NOT_READY`

Do not mark Phase 2 ready yet from only one 100-round batch.

Suggested labels:

- Failed if ending account value <= $100 or 20d accuracy <= 45%.
- Needs more iteration if ending account value > $100 but max drawdown <= -35% or trade-simulation accuracy < 50%.
- Promising not ready if ending account value > $120, max drawdown better than -35%, trade-simulation accuracy >= 50%, and at least 20 BUY decisions.

## Tests

Add tests for:

1. Exactly 100 replay rounds are generated when `--replay-rounds 100` is used.
2. Replay decisions do not use data after replay_date.
3. Non-affordable tickers are rejected before ranking.
4. Forward returns are used only after the decision is recorded.
5. Accuracy metrics are computed correctly.
6. Account replay respects one open position at a time.
7. Reports are written.
8. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1-historical-replay --replay-rounds 100
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1A 100-Round Summary
- Total replay rounds
- BUY count
- NO_TRADE count
- BUY rate
- Accuracy: 1d / 3d / 5d / 10d / 20d
- Trade-simulation accuracy
- Account ending value
- Max drawdown
- Profit factor
- Best pick
- Worst pick
- Top selected tickers
- Phase 1A status
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2 or Phase 3.
