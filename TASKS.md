# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano v1 — 100 Dollar Account Reset

We found a fundamental product bug: Phoenix was optimizing as if it were managing a large account. The real project constraint is a starting account of **$100**.

This changes the objective.

Stop optimizing for a generic portfolio. Re-run the research as **Phoenix Nano**, a small-account trading simulator where every BUY must be executable by a $100 account.

Do not add news, SEC, short interest, options, LLM ranking, paid data, or external APIs.
Do not start paper trading.
Do not label anything live-tradable.

## Highest Priority Rule

A BUY that cannot be executed by a $100 account is invalid, no matter how good the backtest looks.

Every future BUY output must eventually include:

- ticker
- entry price
- shares
- total cost
- cash remaining
- stop loss
- target 1
- target 2
- maximum dollar risk
- expected holding period

If shares cannot be calculated, it is not a BUY.

## Part 1: Add Account Configuration

Add account settings to config, preferably in `config/settings.yaml`:

```yaml
account:
  starting_capital: 100.0
  fractional_shares: false
  max_position_fraction: 1.0
  min_cash_reserve: 0.0
  commission_per_trade: 0.0
  slippage_bps: 10
```

Default assumption for Phoenix Nano v1:

- `starting_capital = 100`
- `fractional_shares = false`
- Only whole shares are allowed.

If fractional shares are later enabled, it must be explicit.

## Part 2: Add Account-Aware Eligibility

Create or update a module:

`src/account/account_simulator.py`

For each candidate BUY decision:

- Use next trading day entry price from the trade simulator.
- Calculate affordable whole shares:
  - `shares = floor(available_cash / adjusted_entry_price)`
- Adjusted entry price should include slippage.
- If shares < 1, reject the trade as `NOT_AFFORDABLE`.
- Total cost = shares * adjusted_entry_price + commission.
- Cash remaining = account cash - total cost.
- Dollar risk = shares * (entry_price - stop_loss).

A trade is executable only if:

- shares >= 1
- total cost <= available cash
- entry price <= available cash, if fractional_shares is false

## Part 3: Add Price / Account Filters

Add candidate filter families for Phoenix Nano:

- max_entry_price: 20, 30, 50, 75, 100
- min_entry_price: 1, 2, 5
- fractional_shares: false only for this run
- max_position_fraction: 1.0 only for this run

Do not allow a candidate to buy stocks above the max_entry_price.

The key comparison should include:

- price <= 20
- price <= 30
- price <= 50
- price <= 75
- price <= 100

## Part 4: Account Equity Curve Simulation

Historical trade results are not enough. Simulate an actual account:

- Start cash: $100
- At most one open position at a time for v1.
- Use EOD signal, next trading day entry.
- If already holding a position, ignore new BUY signals until current trade exits.
- Use existing stop / target / time-exit rules.
- On exit, update cash.
- Record equity after every exit.

Create:

`data/reports/nano_account_trades.csv`
`data/reports/nano_account_equity_curve.csv`
`data/reports/nano_account_summary.md`

Each trade row must include:

- candidate_id
- signal_date
- entry_date
- exit_date
- ticker
- entry_price
- adjusted_entry_price
- shares
- total_cost
- cash_before
- cash_after_entry
- exit_price
- exit_reason
- cash_after_exit
- trade_return_pct
- account_return_pct
- dollar_pnl
- stop_loss
- target_1
- target_2
- dollar_risk
- affordability_status

## Part 5: Nano Research Gate

A candidate is `NANO_RESEARCH_QUALIFIED_NOT_LIVE` only if all are true:

1. Starts with $100 and respects whole-share affordability.
2. At least 20 executed trades across 2024-2026.
3. Ending equity > $120.
4. Max drawdown better than -35%.
5. Worst trade account loss better than -25%.
6. Win rate >= 45%.
7. Profit factor > 1.15.
8. Positive ending equity after excluding the single best trade.
9. At least 5 different tickers traded.
10. No single ticker contributes more than 50% of total profit.

If it fails, label:

`NANO_RESEARCH_ONLY_NOT_TRADABLE`

Nothing may be labeled live-tradable.

## Part 6: Compare With Prior Non-Nano System

In `nano_account_summary.md`, include a clear section:

`Why prior results were invalid for $100 account`

Explain:

- large-account candidate results may select stocks above $100
- DELL/MSTR style trades may be impossible for whole-share $100 account
- account equity growth must be simulated, not just average trade return

## Part 7: Outputs

Update or create:

- `data/reports/nano_account_trades.csv`
- `data/reports/nano_account_equity_curve.csv`
- `data/reports/nano_account_summary.md`
- `data/reports/auto_research_generations.csv` with Nano fields:
  - max_entry_price
  - executed_trade_count
  - rejected_not_affordable_count
  - ending_equity
  - total_return
  - max_drawdown
  - profit_factor
  - win_rate
  - worst_account_trade_loss
  - traded_ticker_count
  - status
  - fail_reasons

## Part 8: CLI

Add CLI flag:

`--nano-account-simulation`

Example:

```bash
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop --nano-account-simulation
```

This command should run the Phoenix Nano account-aware loop.

## Part 9: Tests

Add tests for:

1. A $100 account cannot buy a $400 stock when fractional_shares is false.
2. Whole-share share count is calculated correctly.
3. Cash updates correctly after entry and exit.
4. One-position-at-a-time rule works.
5. Not-affordable trades are rejected before simulation.
6. Nano gate fails if ending equity <= $120.
7. Nano gate passes only when all conditions are met.
8. Summary explains why prior non-nano results are invalid.
9. Reports are written.

## Part 10: Update Documentation

Update `README.md` and `BRAIN.md`:

- Add Phoenix Nano as the active research objective.
- State that the active starting capital is $100.
- State that whole-share affordability is required unless explicitly configured otherwise.
- State that average trade return is not enough; account equity must be simulated.
- State that no version is live-tradable until historical research and paper trading are both passed.

## Part 11: Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Output
- Test Results
- Phoenix Nano Summary
- Best Nano Candidate, if any
- Whether any candidate became `NANO_RESEARCH_QUALIFIED_NOT_LIVE`
- Ending equity of best candidate
- Max drawdown of best candidate
- Top traded tickers
- Not-affordable rejection count
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop.
Do not start paper trading.
Do not start live trade generation.
Do not label anything live-tradable.
