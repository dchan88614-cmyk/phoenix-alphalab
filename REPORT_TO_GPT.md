# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano v1 - 100 Dollar Account Reset.
- Added account settings to `config/settings.yaml`.
- Added `src/account/account_simulator.py`.
- Added $100 account affordability checks.
- Added whole-share share calculation with slippage.
- Added one-position-at-a-time Nano account equity simulation.
- Added Nano candidate price family via `max_entry_price`.
- Added CLI flag `--nano-account-simulation`.
- Added Nano reports:
  - `data/reports/nano_account_trades.csv`
  - `data/reports/nano_account_equity_curve.csv`
  - `data/reports/nano_account_summary.md`
- Updated `auto_research_generations.csv` with Nano fields.
- Updated `README.md` and `BRAIN.md` to make Phoenix Nano the active research objective.
- Added tests for affordability, cash updates, one-position rule, Nano gate, and summary output.
- Did not start paper trading.
- Did not start live trade generation.
- Did not label anything live-tradable.

## Files Changed

- `README.md`
- `BRAIN.md`
- `config/settings.yaml`
- `src/account/__init__.py`
- `src/account/account_simulator.py`
- `src/main.py`
- `src/research/auto_loop.py`
- `tests/test_account_simulator.py`
- `tests/test_auto_loop.py`
- `data/reports/auto_research_generations.csv`
- `data/reports/auto_research_summary.md`
- `data/reports/nano_account_trades.csv`
- `data/reports/nano_account_equity_curve.csv`
- `data/reports/nano_account_summary.md`
- regenerated existing research reports from the requested run

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop --nano-account-simulation
```

Local virtual environment:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop --nano-account-simulation
```

## Output

Latest Phoenix Nano run:

- Account starting capital: $100.00
- Fractional shares: false
- Whole-share affordability required: yes
- Slippage: 10 bps
- Nano candidate variants evaluated: 250
- Candidates in `auto_research_generations.csv`: 50
- `NANO_RESEARCH_QUALIFIED_NOT_LIVE` candidates: 1
- `NANO_RESEARCH_ONLY_NOT_TRADABLE` candidates: 49
- Nano account trade rows: 12,275
- Executed account trades: 4,871
- Not-affordable rejections: 3,104
- Skipped due to one-position rule: 4,300

Generated files:

- `data/reports/nano_account_trades.csv`
- `data/reports/nano_account_equity_curve.csv`
- `data/reports/nano_account_summary.md`
- `data/reports/auto_research_generations.csv`
- `data/reports/auto_research_summary.md`
- `data/reports/trade_simulation_trades.csv`
- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/processed/factor_dataset.csv`

## Test Results

```bash
.venv/bin/python -m pytest -q
# 51 passed, 1 warning in 1.26s
```

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop --nano-account-simulation
```

## Phoenix Nano Summary

Best Nano candidate by score:

- Candidate ID: 44
- Max entry price: $100.00
- Status: `NANO_RESEARCH_ONLY_NOT_TRADABLE`
- Executed trades: 57
- Rejected not affordable: 0
- Ending equity: $196.47
- Total return: 96.47%
- Max drawdown: -50.39%
- Profit factor: 1.3067
- Win rate: 38.60%
- Worst account trade loss: -12.13%
- Traded ticker count: 28
- Top ticker profit share: 26.36%
- Failed because: `max_drawdown_lte_minus_35pct`, `win_rate_lt_45pct`

Best Nano research-qualified candidate:

- Candidate ID: 34
- Max entry price: $50.00
- Status: `NANO_RESEARCH_QUALIFIED_NOT_LIVE`
- Executed trades: 27
- Rejected not affordable: 17
- Ending equity: $164.06
- Total return: 64.06%
- Max drawdown: -31.29%
- Profit factor: 1.3075
- Win rate: 48.15%
- Worst account trade loss: -11.78%
- Traded ticker count: 14
- Top ticker profit share: 31.95%

Whether any candidate became `NANO_RESEARCH_QUALIFIED_NOT_LIVE`:

- Yes. Candidate 34 passed the Nano historical research gate.
- This is not live-tradable. GPT review and paper trading are still required.

Top executed tickers across Nano account simulations:

- ACHR: 543
- PLTR: 492
- RKLB: 425
- INTC: 397
- RIVN: 333
- PATH: 313
- XPEV: 262
- SMR: 227
- F: 226
- IREN: 196

## Problems

- Candidate 44 had the highest ending equity but failed Nano gate due to deep drawdown and low win rate.
- Candidate 34 is research-qualified historically, but only after the Nano constraints and still requires GPT review.
- The Nano simulation still depends on yfinance OHLCV and current metadata limitations.
- Some intended watchlist names are rejected by metadata filtering, including possible false exclusions such as `U`.
- The run emitted existing pandas `pct_change` future warnings and the macOS LibreSSL warning; neither blocked execution.

## Questions For GPT

- Should Candidate 34 become the first paper-trading candidate, or should Nano v1 require one more robustness pass first?
- Should max drawdown be reviewed more deeply before any paper trading, given Candidate 44's high return but unacceptable drawdown?
- Should fractional shares remain disabled for all Nano research, or should a separate explicit fractional-share branch be tested later?
- Should the next task inspect Candidate 34's exact trade list and path behavior?

## Next Suggested Tasks

- Do not start live trading.
- Do not start paper trading until GPT explicitly approves.
- Review Candidate 34 trade list manually.
- Add a Nano-specific report excluding the single best ticker and the single best trade.
- Add monthly equity curve diagnostics for Candidate 34.
- Keep Phoenix labeled research-only and not live-tradable.
