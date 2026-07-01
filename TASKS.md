# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano v1.1 — Candidate 34 Robustness Review Before Paper Trading

Phoenix Nano v1 correctly reset the system around a $100 whole-share account.

Important result:

- 250 Nano candidate variants were evaluated.
- 1 candidate became `NANO_RESEARCH_QUALIFIED_NOT_LIVE`.
- Candidate 34 is the first historically research-qualified Nano candidate.
- Candidate 34: max entry price $50, 27 executed trades, ending equity $164.06, total return 64.06%, max drawdown -31.29%, profit factor 1.3075, win rate 48.15%, worst account trade loss -11.78%, 14 traded tickers.

This is progress, but Candidate 34 is not approved for paper trading yet.

Reasons:

- Only 27 executed trades.
- Max drawdown is close to the -35% gate.
- Ending equity excluding best trade is only about $120.59, barely above the $120 gate.
- Top ticker profit share is 31.95%, acceptable but still meaningful.

Do not start paper trading.
Do not start live trading.
Do not label anything live-tradable.
Do not change Candidate 34 rules in this task.

## Goal

Perform a deep robustness and path review of Candidate 34 exactly as-is.

The output should answer:

1. Is Candidate 34 strong enough to freeze for paper-trading review?
2. Is performance stable by year, quarter, and month?
3. Does the equity curve depend too much on one trade, one ticker, or one short period?
4. Are the drawdowns survivable for a $100 account?
5. What exact trade template would Candidate 34 produce if later approved for paper trading?

## Part 1: Freeze Candidate 34 Parameters

Extract and record Candidate 34’s exact rule parameters from `auto_research_generations.csv`.

Create:

`data/reports/nano_candidate_34_parameters.md`

Include:

- candidate_id
- max_entry_price
- all smoke/decision rule parameters
- account settings
- max position settings
- stop/target settings
- exact historical run date range

Do not modify the rules.

## Part 2: Candidate 34 Trade List

Create:

`data/reports/nano_candidate_34_trades.csv`

This should include only Candidate 34 executed trades and all relevant fields:

- signal_date
- entry_date
- exit_date
- ticker
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

## Part 3: Monthly / Quarterly / Yearly Robustness

Create:

`data/reports/nano_candidate_34_period_review.csv`
`data/reports/nano_candidate_34_period_review.md`

For Candidate 34, report by:

- year
- quarter
- month

Metrics:

- starting equity
- ending equity
- period return
- executed trades
- win rate
- profit factor
- max drawdown within period
- worst trade
- best trade
- stop hit count
- target 1 hit count
- target 2 hit count
- time exit count

## Part 4: Dependency / Fragility Tests

For Candidate 34, compute:

- ending equity excluding single best trade
- ending equity excluding single worst trade
- ending equity excluding top profit ticker
- ending equity excluding top 3 profit tickers
- ending equity excluding worst loss ticker
- ending equity excluding best month
- ending equity excluding best quarter
- ending equity using only 2024 trades
- ending equity using only 2025 trades
- ending equity using only 2026 trades
- first-half period result versus second-half period result

Create:

`data/reports/nano_candidate_34_fragility.md`

This report must explicitly say whether Candidate 34 is:

- `ROBUST_ENOUGH_FOR_PAPER_REVIEW`
- or `NOT_ROBUST_ENOUGH`

Criteria for `ROBUST_ENOUGH_FOR_PAPER_REVIEW`:

1. Ending equity excluding best single trade remains above $115.
2. Ending equity excluding top profit ticker remains above $110.
3. No single month contributes more than 50% of total profit.
4. At least 2 different calendar years are profitable or approximately flat, defined as ending equity >= $95 if run standalone.
5. Max drawdown remains better than -35% in the base run.
6. Worst trade account loss remains better than -15%.

If any fail, mark `NOT_ROBUST_ENOUGH`.

## Part 5: Paper Trading Template, But Do Not Start Paper Trading

Create:

`data/reports/nano_candidate_34_paper_template.md`

This is only a template, not a live signal.

It should show what a future paper-trading signal would look like:

```text
PHOENIX NANO PAPER CANDIDATE
Status: NOT ACTIVE UNTIL GPT APPROVAL
Account: $100 whole-share account
Action: BUY / NO TRADE
Ticker:
Entry:
Shares:
Total Cost:
Cash Remaining:
Stop Loss:
Target 1:
Target 2:
Max Dollar Risk:
Expected Holding:
Reason:
```

Include a clear warning:

`This is not active paper trading yet.`

## Part 6: Tests

Add tests for:

1. Candidate 34 extraction returns exactly one candidate configuration.
2. Candidate 34 trade list includes only candidate_id 34.
3. Fragility test fails if excluding best trade drops equity below threshold.
4. Period review groups by year, quarter, and month correctly.
5. Paper template does not contain a live BUY recommendation.
6. Reports are written.

## Part 7: Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Output
- Test Results
- Candidate 34 Parameter Summary
- Candidate 34 Period Review Summary
- Candidate 34 Fragility Summary
- Final Candidate 34 status: `ROBUST_ENOUGH_FOR_PAPER_REVIEW` or `NOT_ROBUST_ENOUGH`
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop.
Do not start paper trading.
Do not start live trading.
Do not label Candidate 34 live-tradable.
