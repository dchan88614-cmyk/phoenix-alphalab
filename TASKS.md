# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Daily Scan v0 — Current Data Manual-Review Candidate

David does not want a blind GPT-picked stock. The daily stock candidate must come from Phoenix Nano rules run on the latest available market data.

Goal:
Run a current-date Phoenix Nano scan using the best currently reviewed rule family, especially Candidate 34 / Nano constraints, and output either exactly one manual-review candidate or `NO_TRADE_MANUAL_REVIEW`.

This is **not live trading** and not financial advice. This is for David's manual validation only.

Do not add news, SEC, short interest, options, LLM ranking, paid data, or external APIs.
Do not start live trading.
Do not label anything live-tradable.

## Hard Account Constraint

The account is a $100 whole-share account.

Default:

- starting_capital: 100.0
- fractional_shares: false
- whole shares only
- max_entry_price: use Candidate 34 max entry price if available, otherwise $50
- if the account cannot buy at least 1 share, output NO_TRADE_MANUAL_REVIEW

Every candidate output must include:

- ticker
- latest data date used
- action: MANUAL_REVIEW_CANDIDATE or NO_TRADE_MANUAL_REVIEW
- reference price
- estimated shares with $100
- estimated total cost
- estimated cash remaining
- stop loss
- target 1
- target 2
- max dollar risk
- expected holding period
- reason
- all rule checks passed/failed

## Part 1: Use Latest Available Market Data

Add or update a daily scan command that fetches the latest available OHLCV data.

Important:

- The system is still EOD-based.
- If today's EOD daily bar is unavailable, use the latest completed daily bar and explicitly report the `latest_data_date`.
- Do not pretend intraday data is EOD data.
- If market data is stale, output `NO_TRADE_MANUAL_REVIEW` with reason `STALE_DATA`.

Create output:

`data/reports/nano_daily_scan.csv`
`data/reports/nano_daily_scan.md`

## Part 2: Candidate 34 Rule Application

Use Candidate 34 parameters if they can be extracted from prior generated files. If not available, use the Nano v1 rule family that produced Candidate 34:

- max_entry_price: 50
- $100 whole-share affordability
- same smoke ranking factors as current system
- do not use forward returns
- do not use realized returns
- use only signal-date-safe factors

Apply the rule to the latest available date.

If multiple candidates pass, choose the highest decision strength candidate.

If no candidates pass, output `NO_TRADE_MANUAL_REVIEW`.

## Part 3: Output Exactly One Result

The markdown report must start with one of:

```text
PHOENIX NANO DAILY SCAN
Action: MANUAL_REVIEW_CANDIDATE
```

or

```text
PHOENIX NANO DAILY SCAN
Action: NO_TRADE_MANUAL_REVIEW
```

If there is a candidate, include:

```text
Ticker:
Latest data date:
Reference price:
Shares with $100:
Estimated total cost:
Estimated cash remaining:
Stop loss:
Target 1:
Target 2:
Max dollar risk:
Expected holding period:
Reason:
```

Also include a table of top 5 scanned candidates with pass/fail flags.

## Part 4: CLI

Add CLI flag:

`--nano-daily-scan`

Example:

```bash
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

The command should write:

- `data/reports/nano_daily_scan.csv`
- `data/reports/nano_daily_scan.md`

## Part 5: Tests

Add tests for:

1. Daily scan outputs exactly one action.
2. A stock above $100 is rejected for whole-share $100 account.
3. A candidate below max_entry_price and affordable can produce MANUAL_REVIEW_CANDIDATE.
4. If latest data is stale, output NO_TRADE_MANUAL_REVIEW.
5. Daily scan does not use forward returns or realized trade outcomes.
6. Reports are written.

## Part 6: Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Output
- Test Results
- Daily Scan Result
- Candidate Ticker, if any
- Latest data date used
- Whether result is stale or current
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop.
Do not start paper trading.
Do not start live trading.
Do not label anything live-tradable.
