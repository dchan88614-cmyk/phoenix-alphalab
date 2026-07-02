# Phase 1N Vendor Selection Decision

Latest Phase 1M blocker: `PHASE_1M_CREDENTIAL_MISSING`.
Strategy research remains paused because independent secondary OHLCV validation is unavailable.

## Vendor Preference Order

1. Tiingo via `TIINGO_API_TOKEN`
2. Polygon/Massive via `POLYGON_API_KEY` or `MASSIVE_API_KEY`
3. Alpha Vantage via `ALPHAVANTAGE_API_KEY`

## Operator Next Step

Add `TIINGO_API_TOKEN` locally first, using `.env` or an exported environment variable. Do not paste credentials into repo files or reports.

```bash
.venv/bin/python -m src.main --watchlist data/reports/phase1l_clean_watchlist_v3_candidate.txt --start 2024-01-01 --end 2026-06-30 --phase1n-credential-activation-gate
```

Current Phase 1N status: `PHASE_1N_WAITING_FOR_CREDENTIAL`.

No paper execution or live execution is authorized.
