# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Daily Scan v1 - Data-Derived Manual Candidate Only.
- Updated `--nano-daily-scan` to freeze Candidate 34 rules from `data/reports/auto_research_generations.csv`.
- Required exactly one row with `candidate_id == 34` and `nano_status == NANO_RESEARCH_QUALIFIED_NOT_LIVE`.
- Added `data/reports/nano_daily_candidate_34_frozen_rules.md`.
- Added `--candidate-id`, defaulting to `34`.
- Removed vague Candidate 34 fallback behavior from the daily scan path.
- If Candidate 34 extraction fails, daily scan outputs `NO_TRADE_MANUAL_REVIEW` with reason `MISSING_OR_AMBIGUOUS_CANDIDATE_34_RULES`.
- Added report status lines:
  - candidate result: `MANUAL_VERIFY_ONLY_NOT_TRADE_SIGNAL`
  - no-trade result: `RESEARCH_ONLY_NOT_TRADABLE`
- Added data source and scan timestamp to `nano_daily_scan.md`.
- Expanded daily scan tests to cover the v1 requirements.
- Did not hardcode ACHR, PLTR, RKLB, INTC, or any other ticker.
- Did not use GPT preference for ticker selection.
- Did not start paper trading.
- Did not start live trading.
- Did not label anything live-tradable.

## Files Changed

- `src/backtest/nano_daily_scan.py`
- `src/main.py`
- `tests/test_nano_daily_scan.py`
- `data/reports/nano_daily_candidate_34_frozen_rules.md`
- `data/reports/nano_daily_scan.csv`
- `data/reports/nano_daily_scan.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

Equivalent explicit Candidate 34 command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan --candidate-id 34
```

## Output

Generated files:

- `data/reports/nano_daily_candidate_34_frozen_rules.md`
- `data/reports/nano_daily_scan.csv`
- `data/reports/nano_daily_scan.md`

Daily scan report starts with:

```text
PHOENIX NANO DAILY SCAN
Action: NO_TRADE_MANUAL_REVIEW
Status: RESEARCH_ONLY_NOT_TRADABLE
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_nano_daily_scan.py -q
# 11 passed in 0.37s
```

```bash
.venv/bin/python -m pytest -q
# 62 passed, 1 warning in 1.23s
```

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-07-01 --nano-daily-scan
```

## Daily Scan Result

- Action: `NO_TRADE_MANUAL_REVIEW`
- Candidate ticker: none
- Latest data date used: `2026-06-30`
- Result stale/current: current, `is_stale = False`
- Reason: `NO_CANDIDATE_PASSED_RULES`
- Data source: `yfinance`
- Scan timestamp UTC: `2026-07-01T19:03:39.834664+00:00`
- Forward returns used for ranking: no
- Realized trade outcomes used for ranking: no

Top scanned candidates on the latest data date were AMAT, KLAC, LRCX, AMD, and PANW. None passed all rule checks. The top scanned names were rejected because they did not satisfy the frozen Candidate 34 Nano rule plus $50 max-entry and $100 whole-share affordability gates.

## Candidate 34 Frozen Rule Summary

- Source: `data/reports/auto_research_generations.csv`
- candidate_id: 34
- nano_status: `NANO_RESEARCH_QUALIFIED_NOT_LIVE`
- max_buy_rate: 0.30
- min_relative_volume_prev20: 1.5
- min_smoke_score: 0.85
- min_rank_gap: 0.0
- require_return_5d_positive: true
- require_return_20d_positive: false
- distance_to_52w_high_prev_min: -0.35
- dollar_volume_min: 20,000,000
- max_trades_per_ticker_per_year: none
- max_entry_price / nano_max_entry_price used for daily scan: $50.00
- account: $100, whole shares only, 10 bps slippage
- historical Nano summary: $100 -> $164.06, 27 executed trades, max drawdown -31.29%, profit factor 1.3075, win rate 48.15%, worst account trade loss -11.78%

## Problems

- No current manual-review candidate passed the frozen Candidate 34 daily scan gate.
- Latest top-scored names were all above the $50 Candidate 34 Nano max-entry cap and not affordable for a $100 whole-share account.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- Existing metadata filters still exclude some intended watchlist names because the MVP requires metadata pass purity.
- The run emitted existing pandas `pct_change` future warnings and the macOS LibreSSL warning; neither blocked execution.
- yfinance data remains non-institutional retail data and should not be treated as a live execution feed.

## Questions For GPT

- Should GPT define a separate daily scan rule that prioritizes sub-$50 names before ranking, or keep frozen Candidate 34 exactly as-is?
- Should the next task add a diagnostic table of the highest-ranked affordable sub-$50 names even when they fail Candidate 34?
- Should stale-date checks become market-calendar-aware before any paper-trading workflow is considered?

## Next Suggested Tasks

- Do not start live trading.
- Do not start paper trading until GPT explicitly approves.
- Keep daily scan output manual-review only.
- Add an affordable-sub-$50 diagnostics section without changing the selection rule.
- Add market-calendar-aware stale-date checks before any paper-trading workflow.
