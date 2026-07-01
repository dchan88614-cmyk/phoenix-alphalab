# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Roadmap + Phase 1 Historical Replay Engine

David clarified the actual product roadmap.

Phoenix Nano must follow three stages:

1. **Phase 1: Historical replay training**
   - Pick old historical dates.
   - Pretend each date is “today.”
   - Use only data available up to that date.
   - Select one stock or NO TRADE.
   - Then reveal the future and verify what happened.
   - Repeat many times to improve accuracy and rule quality.

2. **Phase 2: Current-market paper validation**
   - Run the same logic on current/latest market data.
   - Output one manual-review candidate or NO TRADE.
   - Track real future outcomes as they happen.
   - Repeat until confidence improves.

3. **Phase 3: Real-money execution**
   - Only after Phase 1 and Phase 2 gates are satisfied.
   - Still use $100 whole-share constraints unless explicitly changed.

The current task is Phase 1 only.

Do not start Phase 2 paper validation.
Do not start Phase 3 live trading.
Do not loosen Candidate 34 or any thresholds yet.
Keep all output research/manual-review only.

## Phase 1 Goal

Build a historical replay engine that repeatedly simulates old “today” dates.

For each replay date:

- scan the watchlist using only data available on or before that date
- enforce Phoenix Nano account constraints
- output exactly one historical decision:
  - HISTORICAL_BUY_CANDIDATE
  - or HISTORICAL_NO_TRADE
- then verify forward outcome after 1, 3, 5, 10, and 20 trading days
- aggregate results into accuracy and account-level metrics

## Account Rules

Use Phoenix Nano settings:

- starting capital: $100
- fractional shares: false
- whole shares only
- no margin
- no shorting
- max open positions: 1 for account simulation
- default max entry price: Candidate 34 max entry price, expected $50
- slippage: current project setting, expected 10 bps

Any ticker that cannot be bought with $100 whole-share account must be rejected before ranking.

## Part 1: Historical Replay Dates

Create a replay date generator.

Default replay period:

- start: 2024-01-01
- end: 2026-06-30
- frequency: every completed trading day, or every 3rd trading day if runtime is too high

Each replay date must be a completed trading date with enough lookback data for factors.

No future data may be used to choose the candidate.

## Part 2: Replay Decision Engine

Create or update:

`src/research/historical_replay.py`

For each replay date:

1. Use OHLCV/factors available only up to replay date.
2. Apply executable-first Nano filters.
3. Apply Candidate 34 frozen rules if available.
4. If one or more stocks pass, choose the highest deterministic decision_strength.
5. If none pass, output HISTORICAL_NO_TRADE.
6. Save top executable near-misses for diagnostics.

## Part 3: Forward Verification

After a historical decision is made, use future bars only for verification.

For BUY candidates, compute:

- forward_return_1d
- forward_return_3d
- forward_return_5d
- forward_return_10d
- forward_return_20d
- max_favorable_excursion_20d
- max_adverse_excursion_20d
- hit_plus_5pct
- hit_plus_10pct
- hit_minus_5pct
- hit_minus_10pct
- simulated_exit_reason using current stop/target/time-exit rules
- simulated_pnl_dollars
- simulated_account_equity_after_exit

For NO_TRADE dates, optionally record whether the top near-miss later performed well.

## Part 4: Outputs

Create:

- `data/reports/phase1_historical_replay_decisions.csv`
- `data/reports/phase1_historical_replay_summary.md`
- `data/reports/phase1_historical_replay_near_misses.csv`

Decision CSV required columns:

- replay_date
- action
- ticker
- reference_price
- shares_with_100
- estimated_total_cost
- estimated_cash_remaining
- stop_loss
- target_1
- target_2
- max_dollar_risk
- decision_strength
- smoke_score
- failed_checks
- forward_return_1d
- forward_return_3d
- forward_return_5d
- forward_return_10d
- forward_return_20d
- max_favorable_excursion_20d
- max_adverse_excursion_20d
- simulated_exit_reason
- simulated_pnl_dollars
- data_complete_20d

Summary markdown must include:

- total replay dates
- BUY candidate count
- NO_TRADE count
- buy rate
- win rate by 1d / 3d / 5d / 10d / 20d
- average return by window
- median return by window
- max drawdown in account replay
- ending account value if one-position-at-a-time was followed
- best historical pick
- worst historical pick
- most selected tickers
- whether results are good enough for Phase 2 consideration

## Phase 1 Advancement Gate

Do not move to Phase 2 unless the historical replay meets all gates:

1. At least 100 replay dates tested.
2. At least 20 BUY candidates generated.
3. 20d average return > 0.
4. 20d median return > 0 or account ending value > $120.
5. Worst simulated account trade loss better than -15%.
6. Max account drawdown better than -35%.
7. Ending account value > $120.
8. Removing the single best trade still leaves ending account value > $105.
9. No single ticker contributes more than 50% of total profit.

If not all gates pass, mark:

`PHASE_1_NOT_READY`

If all gates pass, mark:

`PHASE_1_REPLAY_QUALIFIED_FOR_GPT_REVIEW`

Even if qualified, do not start Phase 2 automatically. GPT review required.

## Part 5: CLI

Add CLI flag:

```bash
--phase1-historical-replay
```

Example:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1-historical-replay
```

## Part 6: Tests

Add tests for:

1. Replay decision for a date does not use data after that replay date.
2. Non-affordable stocks are rejected before ranking.
3. Replay outputs exactly one decision per replay date.
4. Forward returns are used only after the decision is recorded.
5. Account simulation respects one open position at a time.
6. Phase 1 gate fails when sample count is too small.
7. Phase 1 gate passes only when all conditions are met.
8. Reports are written.
9. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1-historical-replay
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1 Historical Replay Summary
- Total replay dates
- BUY count
- NO_TRADE count
- Account ending value
- Max drawdown
- Best pick
- Worst pick
- Top selected tickers
- Phase 1 status: `PHASE_1_NOT_READY` or `PHASE_1_REPLAY_QUALIFIED_FOR_GPT_REVIEW`
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2 or Phase 3.
