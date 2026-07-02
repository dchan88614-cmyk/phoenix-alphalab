# Phoenix Vendor Credential Setup

Phoenix is blocked until at least one independent OHLCV vendor credential is supplied locally. This setup is for historical research data validation only. It does not authorize paper trading or live trading.

## Preferred Vendor Order

1. Tiingo via `TIINGO_API_TOKEN`
2. Polygon/Massive via `POLYGON_API_KEY` or `MASSIVE_API_KEY`
3. Alpha Vantage via `ALPHAVANTAGE_API_KEY`

## Secret Rules

- Provide credentials through environment variables only.
- Do not paste credentials into `TASKS.md`, `REPORT_TO_GPT.md`, code, reports, tests, markdown, screenshots, or chat.
- Do not commit `.env` or any local credential file.
- Use placeholders like `<YOUR_TIINGO_API_TOKEN>` in documentation.

## Current Terminal Session

```bash
export TIINGO_API_TOKEN=<YOUR_TIINGO_API_TOKEN>
```

Use only one vendor credential first. Tiingo is preferred.

## Local `.env`

```bash
cp .env.example .env
```

Edit `.env` locally and replace exactly one placeholder. Verify it is ignored:

```bash
git check-ignore .env
git status --short
```

`.env.example` must remain tracked because it contains placeholders only.

## Preflight

```bash
.venv/bin/python -m src.main --watchlist data/reports/phase1l_clean_watchlist_v3_candidate.txt --start 2024-01-01 --end 2026-06-30 --phase1n-credential-activation-gate
```

If Phase 1N reports ready, rerun Phase 1M:

```bash
.venv/bin/python -m src.main --watchlist data/reports/phase1l_clean_watchlist_v3_candidate.txt --start 2024-01-01 --end 2026-06-30 --phase1m-credentialed-vendor-gate
```

Passing vendor data readiness still does not authorize paper or live trading. GPT must review before any frozen retest or user-facing decision workflow.
