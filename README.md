# Phoenix AlphaLab

Phoenix AlphaLab is a local research system for US common stocks. Its first goal is not live trading. It is built to test whether simple, explainable factors have predictive value for future 5, 10, and 20 trading day returns.

The project focuses on high-elasticity opportunities that a small account might realistically research, while keeping the research process reproducible and explicit.

## Scope

Included:

- US listed common stocks on NASDAQ, NYSE, and NYSE American
- Long-only research
- Historical OHLCV based factor testing
- CSV and Markdown reports

Excluded:

- Options
- Short selling
- Leveraged ETFs
- ETFs and ETNs
- Preferred shares
- Warrants
- Units
- Pre-merger SPAC targets
- OTC and Pink Sheet symbols
- Crypto

## Research Rules

- Avoid look-ahead bias. Factors are computed from same-day and prior historical data only.
- Forward returns are labels for validation, not inputs to factors.
- Reports must be exportable, explainable, and reproducible.
- Missing metadata is treated conservatively by the universe filter when configured to do so.

## Factor Timing

Phoenix AlphaLab is currently an End-of-Day research system. Factors may use data that is only known after the same trading day's close, such as final close, high, low, and total daily volume. These EOD factors are valid for historical research labels, but they must not be used as same-day intraday trading signals.

If the project later adds pre-market or intraday signals, it must add a separate `signal_time` module so every factor declares exactly when it would have been knowable.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
python -m src.main --tickers AAPL,NVDA,SMCI,PLTR --start 2024-01-01 --end 2026-06-30
```

Run the simple recent-window smoke test:

```bash
python -m src.main --tickers AAPL,NVDA,SMCI,PLTR --start 2024-01-01 --end 2026-06-30 --smoke-test --smoke-days 60
```

Run the smoke test from a watchlist file:

```bash
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --smoke-test --smoke-days 60
```

Outputs:

- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/reports/smoke_test.csv`
- `data/reports/smoke_test.md`
- `data/processed/factor_dataset.csv`
- `data/raw/prices/*.csv`

## Data Sources

The first version uses `yfinance` for public historical OHLCV data and basic ticker metadata. This is suitable for local research prototypes but should be validated before production research. API key based providers can be added through `config/settings.yaml` and `.env`.

## First-Stage Factors

- Relative Volume EOD and previous-20-day Relative Volume
- 20-day volume change
- 5-day, 10-day, and 20-day returns
- Distance from 52-week high EOD and previous-window 52-week high distance
- ATR volatility
- Gap percent
- Market cap filter interface
- Dollar volume

## Report Metrics

For each factor and quantile group, the report includes:

- Average forward return
- Win rate
- Maximum drawdown of the grouped forward-return series
- Average excess return versus SPY or QQQ
- Number of observations

## Important Limitations

- `yfinance` metadata can be incomplete or inconsistent. The code includes filtering interfaces, but exchange and instrument-type validation should be upgraded for institutional-grade research.
- Market cap history is not point-in-time in this version. It is used only as a configurable filter interface and should not be treated as a bias-free historical factor.
- The system does not claim any factor works until you run and inspect real reports.
