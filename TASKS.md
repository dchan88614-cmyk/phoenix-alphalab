# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Daily Scan v1 — Data-Derived Manual Candidate Only

David does not want a blind GPT-picked stock. The daily stock candidate must come from Phoenix Nano rules run on the latest available market data.

The latest reviewed research state is:

- Phoenix Nano now uses a $100 whole-share account.
- Fractional shares are disabled.
- Candidate 34 is the only historical `NANO_RESEARCH_QUALIFIED_NOT_LIVE` candidate so far.
- Candidate 34 historical account result: $100 -> $164.06, 27 executed trades, max drawdown -31.29%, profit factor 1.3075, win rate 48.15%, worst account trade loss -11.78%.
- Candidate 34 is not approved for paper trading or live trading.

Goal:

Run a current-date Phoenix Nano scan using **frozen Candidate 34 rules** and the latest available OHLCV data. Output either exactly one manual-review candidate or `NO_TRADE_MANUAL_REVIEW`.

This is **not live trading** and not financial advice. This is only a research-derived manual validation candidate for David.

Do not start paper trading.
Do not start live trading.
Do not label anything live-tradable.
Do not output an unconditional BUY.
Do not hardcode ACHR, PLTR, RKLB, INTC, or any other ticker.
Do not choose a ticker using GPT preference.

## Hard Account Constraint

The account is a $100 whole-share account.

Default settings:

- starting_capital: 100.0
- fractional_shares: false
- whole shares only
- max_entry_price: Candidate 34 max entry price, expected $50
- if the account cannot buy at least 1 share after slippage, output `NO_TRADE_MANUAL_REVIEW`

Every candidate output must include:

- ticker
- latest data date used
- action: `MANUAL_REVIEW_CANDIDATE` or `NO_TRADE_MANUAL_REVIEW`
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

## Part 1: Freeze Candidate 34 Rules Before Scanning

Extract Candidate 34 parameters from:

`data/reports/auto_research_generations.csv`

The extraction must return exactly one row with `candidate_id == 34` and `nano_status == NANO_RESEARCH_QUALIFIED_NOT_LIVE`.

Record the frozen parameters in:

`data/reports/nano_daily_candidate_34_frozen_rules.md`

Include at minimum:

- candidate_id
- max_buy_rate
- min_relative_volume_prev20
- min_smoke_score
- min_rank_gap
- require_return_5d_positive
- require_return_20d_positive
- distance_to_52w_high_prev_min
- dollar_volume_min
- max_trades_per_ticker_per_year
- max_entry_price / nano_max_entry_price
- account settings
- slippage
- stop / target / holding-period logic used by the current simulator

If Candidate 34 cannot be extracted exactly, do **not** fall back to a vague rule family. Instead output:

`NO_TRADE_MANUAL_REVIEW`

with reason:

`MISSING_OR_AMBIGUOUS_CANDIDATE_34_RULES`

## Part 2: Use Latest Available Market Data

Add or update a daily scan command that refreshes and uses the latest available OHLCV data.

Important:

- The system is still EOD-based unless the existing codebase already has safe intraday support.
- If today's EOD daily bar is unavailable, use the latest completed daily bar and explicitly report `latest_data_date`.
- Do not pretend intraday data is EOD data.
- If market data is stale, output `NO_TRADE_MANUAL_REVIEW` with reason `STALE_DATA`.
- Record data source and timestamp in the report.

Create output:

`data/reports/nano_daily_scan.csv`
`data/reports/nano_daily_scan.md`

## Part 3: Candidate 34 Daily Rule Application

Apply frozen Candidate 34 rules to every ticker in:

`config/watchlists/us_liquid_growth_100.txt`

Rules:

1. Use only signal-date-safe factors.
2. Do not use forward returns.
3. Do not use realized trade outcomes.
4. Do not use future OHLCV bars after the scan date.
5. Require price affordability for a $100 whole-share account.
6. Require reference entry price <= Candidate 34 max entry price.
7. Apply Candidate 34 smoke/rank/liquidity/momentum constraints exactly as available from the codebase.
8. If multiple candidates pass, choose the highest decision strength candidate using the existing deterministic Phoenix ranking logic.
9. If no candidates pass, output `NO_TRADE_MANUAL_REVIEW`.

The result must be data-derived and reproducible.

## Part 4: Output Exactly One Result

The markdown report must start with one of:

```text
PHOENIX NANO DAILY SCAN
Action: MANUAL_REVIEW_CANDIDATE
Status: MANUAL_VERIFY_ONLY_NOT_TRADE_SIGNAL
```

or

```text
PHOENIX NANO DAILY SCAN
Action: NO_TRADE_MANUAL_REVIEW
Status: RESEARCH_ONLY_NOT_TRADABLE
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
Why selected by rules:
Manual checks still required:
- Verify live quote manually before any action.
- Verify current volume / RVOL manually.
- Verify no fresh major negative news.
- Do not chase a large intraday spike.
```

Also include a table of the top 5 scanned candidates with pass/fail flags.

The report must include this warning:

`This is not active paper trading or live trading. It is only a research-derived manual verification candidate.`

## Part 5: CLI

Add CLI flag:

`--nano-daily-scan`

Example:

```bash
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end <CURRENT_DATE> --nano-daily-scan
```

If the implementation requires a specific candidate, support either:

```bash
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end <CURRENT_DATE> --nano-daily-scan --candidate-id 34
```

or document the closest clean command.

The command should write:

- `data/reports/nano_daily_candidate_34_frozen_rules.md`
- `data/reports/nano_daily_scan.csv`
- `data/reports/nano_daily_scan.md`

## Part 6: Tests

Add tests for:

1. Candidate 34 extraction returns exactly one qualified configuration.
2. Daily scan outputs exactly one final action.
3. A stock above $100 is rejected for the $100 whole-share account.
4. A stock above Candidate 34 max entry price is rejected.
5. An affordable ticker below max entry price can produce `MANUAL_REVIEW_CANDIDATE` when all Candidate 34 rule checks pass.
6. If latest data is stale, output `NO_TRADE_MANUAL_REVIEW`.
7. Daily scan does not use forward returns or realized trade outcomes.
8. Daily scan does not hardcode a ticker.
9. Daily report contains `MANUAL_VERIFY_ONLY_NOT_TRADE_SIGNAL` for a candidate result.
10. Daily report does not contain live-trading language.
11. Reports are written.

Run:

```bash
.venv/bin/python -m pytest -q
```

Also run the daily scanner command.

## Part 7: Update REPORT_TO_GPT.md

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
- Candidate 34 frozen rule summary
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop.
Do not start paper trading.
Do not start live trading.
Do not label Candidate 34 or any daily candidate live-tradable.
