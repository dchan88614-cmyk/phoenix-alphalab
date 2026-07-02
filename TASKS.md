# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1N — Credential Activation, Adapter Verification, and Retest Authorization Gate

This task is **historical research and data-readiness remediation only**.

Do not start Phase 2.
Do not start Phase 3.
Do not enable paper execution.
Do not enable real-money execution.
Do not change daily scan production behavior.
Do not loosen Candidate 34 thresholds.
Do not adopt Candidate 35, Phase 1H overlays, or any universe variant as active policy.
Do not create Candidate 36 entry rules.
Do not run a strategy threshold sweep.
Do not run a Candidate 34 vs Candidate 35 retest in this task.
Do not produce financial advice or an operational recommendation.
Do not commit, print, cache, or expose any API secret, token, key, prefix, suffix, or length.

## Why This Task

Phase 1M completed implementation but ended as:

`PHASE_1M_CREDENTIAL_MISSING`

Latest Phase 1M evidence:

- tests passed: `192 passed, 1 warning`
- credential status: `MISSING`: 4, `PRESENT_REDACTED`: 0
- missing credential env vars:
  - `TIINGO_API_TOKEN`
  - `POLYGON_API_KEY`
  - `MASSIVE_API_KEY`
  - `ALPHAVANTAGE_API_KEY`
- authenticated vendor network calls were skipped because credentials were missing
- vendor capability summary:
  - `tiingo_eod`: `CREDENTIAL_MISSING`
  - `polygon_aggs`: `CREDENTIAL_MISSING`
  - `alpha_vantage_daily_adjusted`: `CREDENTIAL_MISSING`
  - `stooq_daily_csv`: `GLOBAL_UNAVAILABLE`
  - `yahoo_chart_api`: `TRANSPORT_FALLBACK_ONLY`
- independent secondary validation coverage: `0.0%`
- active trade candidate coverage: `0.0%`
- proxy coverage: `0.0%`
- research-only clean watchlist v4 candidate count: `0`
- strategy research remains paused

This means the highest-priority issue is **not** strategy testing. The next bottleneck is operational data readiness: Phoenix needs a safe, reproducible way for a human operator to add exactly one independent vendor credential locally, verify adapter behavior, and rerun the vendor gate without leaking secrets or accidentally starting strategy research.

The next optimized task is to harden the credential activation path and adapter verification harness so that the project can move from `CREDENTIAL_MISSING` to either:

1. a clean, reproducible rerun of Phase 1M after a credential is supplied, or
2. a precise vendor/adapter failure report if a supplied credential does not work.

Do not use realized future returns, realized PnL, holdout performance, prior winning/losing status, or strategy outcomes to make vendor, alias, or watchlist inclusion decisions.

## Vendor Preference Decision

Prefer adding **Tiingo first** if only one credential will be configured, because Phase 1M already selected it as the first-choice candidate and it exposes explicit adjusted OHLCV fields plus split/dividend-related fields.

Keep Polygon/Massive as the second-choice path and Alpha Vantage as a backup path. Do not remove support for any of them.

Vendor preference order for this task:

1. `tiingo_eod`
2. `polygon_aggs`
3. `alpha_vantage_daily_adjusted`

Important caveats:

- The repo must support any configured independent vendor from the list above.
- The repo must not assume the user has paid access.
- If credentials are absent, the command must finish with an explicit waiting-for-credential status, not a crash.
- If credentials are present but invalid, the command must finish with an explicit auth/config status, not a strategy failure.
- Yahoo Chart remains same-vendor transport fallback only and must not count as independent validation.
- Stooq remains globally unavailable unless real CSV rows are obtained in a later environment.

## Goal

Create a safe credential activation and adapter verification layer that answers:

1. Which vendor credential should the operator add first?
2. How exactly should the operator add it locally without committing secrets?
3. Are the parser/normalizer contracts for Tiingo, Polygon/Massive, and Alpha Vantage testable without live credentials?
4. If a live credential is present, does the selected vendor pass a minimal smoke test on AAPL, MSFT, SPY, QQQ, SQ, GEV, and RDDT?
5. Is Phoenix ready to rerun Phase 1M, or still blocked waiting for credentials / auth / adapter fixes?

Possible final statuses:

- `PHASE_1N_WAITING_FOR_CREDENTIAL`
- `PHASE_1N_SECRET_SAFETY_BLOCKER`
- `PHASE_1N_ADAPTER_CONTRACT_FAILED`
- `PHASE_1N_VENDOR_AUTH_FAILED`
- `PHASE_1N_VENDOR_RATE_LIMITED`
- `PHASE_1N_READY_TO_RERUN_PHASE_1M_WITH_CREDENTIAL`
- `PHASE_1N_VENDOR_GATE_PASSED_NEEDS_GPT_REVIEW`

Even if Phase 1N passes, do **not** run any strategy retest in this task. A passing Phase 1N may only recommend a Phase 1M rerun or GPT review.

## CLI

Add or update:

```bash
--phase1n-credential-activation-gate
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist data/reports/phase1l_clean_watchlist_v3_candidate.txt --start 2024-01-01 --end 2026-06-30 --phase1n-credential-activation-gate
```

The command must complete when credentials are missing. Missing credentials should produce explicit `PHASE_1N_WAITING_FOR_CREDENTIAL`, not a crash.

If one or more credentials are present, the command may run live smoke tests for configured vendors, but must still avoid any strategy retest.

## Required Outputs

Create or update:

- `docs/VENDOR_CREDENTIAL_SETUP.md`
- `.env.example`
- `data/reports/phase1n_vendor_selection_decision.md`
- `data/reports/phase1n_credentials_preflight.csv`
- `data/reports/phase1n_adapter_contract_tests.csv`
- `data/reports/phase1n_live_smoke_tests.csv`
- `data/reports/phase1n_phase1m_rerun_readiness.csv`
- `data/reports/phase1n_no_secret_audit.csv`
- `data/reports/phase1n_data_readiness_summary.md`
- `REPORT_TO_GPT.md`

Optional but useful:

- `scripts/check_vendor_credentials.py`
- `scripts/run_phase1m_vendor_gate.sh`
- `src/research/phase1n_credential_activation.py`
- `tests/test_phase1n_credential_activation.py`
- `tests/fixtures/vendor_payloads/tiingo_eod_aapl.json`
- `tests/fixtures/vendor_payloads/polygon_aggs_aapl.json`
- `tests/fixtures/vendor_payloads/alpha_vantage_daily_adjusted_ibm.json`

Keep earlier Phase 1 reports intact unless regeneration is required.

The summary must start with:

```text
PHOENIX NANO PHASE 1N — CREDENTIAL ACTIVATION, ADAPTER VERIFICATION, AND RETEST AUTHORIZATION GATE
```

## Inputs

Reuse Phase 1M outputs:

- `data/reports/phase1m_vendor_capability_matrix.csv`
- `data/reports/phase1m_credentials_status.csv`
- `data/reports/phase1m_vendor_smoke_tests.csv`
- `data/reports/phase1m_secondary_ohlcv_validation.csv`
- `data/reports/phase1m_coverage_by_symbol.csv`
- `data/reports/phase1m_adjustment_consistency_audit.csv`
- `data/reports/phase1m_rate_limit_and_error_audit.csv`
- `data/reports/phase1m_clean_watchlist_v4_candidate.txt`
- `data/reports/phase1m_data_readiness_scorecard.csv`
- `data/reports/phase1m_data_readiness_summary.md`

Also reuse Phase 1L / 1K outputs where helpful:

- `data/reports/phase1l_clean_watchlist_v3_candidate.txt`
- `data/reports/phase1l_alias_clean_watchlist_audit.csv`
- `data/reports/phase1k_symbol_lifecycle_alias_map.csv`
- `data/reports/phase1k_taxonomy_resolution_v2.csv`

## Part 1: Operator Credential Setup Guide

Create `docs/VENDOR_CREDENTIAL_SETUP.md`.

The guide must explain:

- Phoenix is blocked until at least one independent OHLCV vendor credential is supplied locally.
- Preferred vendor order:
  1. Tiingo via `TIINGO_API_TOKEN`
  2. Polygon/Massive via `POLYGON_API_KEY` or `MASSIVE_API_KEY`
  3. Alpha Vantage via `ALPHAVANTAGE_API_KEY`
- Credentials must be provided through environment variables only.
- Do not paste credentials into `TASKS.md`, `REPORT_TO_GPT.md`, code, reports, tests, markdown, or screenshots.
- How to export a credential for the current terminal session.
- How to store credentials locally in an untracked `.env` file if the repo supports it.
- How to verify `.env` is ignored by git.
- How to run the Phase 1N preflight command.
- How to rerun Phase 1M only after Phase 1N says it is ready.
- That passing vendor data readiness still does not authorize paper or live trading.

Do not include any real credential value or fake value that resembles a real token. Use placeholders such as `<YOUR_TIINGO_API_TOKEN>`.

## Part 2: Safe `.env.example` and Git Ignore Audit

Create or update `.env.example` with placeholders only:

```bash
# Phoenix independent vendor credentials — placeholders only.
# Copy this file to .env locally and fill exactly one credential first.
TIINGO_API_TOKEN=<YOUR_TIINGO_API_TOKEN>
POLYGON_API_KEY=<YOUR_POLYGON_API_KEY>
MASSIVE_API_KEY=<YOUR_MASSIVE_API_KEY>
ALPHAVANTAGE_API_KEY=<YOUR_ALPHAVANTAGE_API_KEY>
```

Audit `.gitignore` and any project ignore rules.

Ensure local secret files are ignored, including at minimum:

- `.env`
- `.env.*`
- `*.env`
- any local credential override file if added

Do not ignore `.env.example`.

Create `phase1n_no_secret_audit.csv` with at least:

- `checked_path_or_pattern`
- `check_type`: `gitignore`, `report_content`, `example_file`, `code_redaction`, `cache_path`
- `status`: `PASS`, `WARN`, `FAIL`
- `secret_exposure_detected`: True / False
- `reason`

The audit should scan generated reports and docs for obvious accidental credential exposure patterns. Do not print any suspected secret; only report redacted findings.

## Part 3: Credential Preflight

Create `phase1n_credentials_preflight.csv`.

For each credential env var, report:

- `env_var_name`
- `vendor`
- `present`: True / False
- `value_redacted`: always True if present
- `format_hint_status`: `MISSING`, `PRESENT_REDACTED`, `SUSPICIOUS_EMPTY`, `SUSPICIOUS_PLACEHOLDER`, `SUSPICIOUS_WHITESPACE`, `SUSPICIOUS_TOO_SHORT`, `UNKNOWN_FORMAT_PRESENT_REDACTED`
- `selected_for_live_smoke`: True / False
- `selection_reason`

Credential selection rules:

- Prefer Tiingo if `TIINGO_API_TOKEN` is present and not suspicious.
- Otherwise prefer Polygon/Massive if `POLYGON_API_KEY` or `MASSIVE_API_KEY` is present and not suspicious.
- Otherwise prefer Alpha Vantage if `ALPHAVANTAGE_API_KEY` is present and not suspicious.
- If multiple credentials are present, smoke-test all non-suspicious configured vendors, but clearly report which is preferred first.
- Never print, hash, store, prefix, suffix, or length-report credential values.

## Part 4: Adapter Contract Tests Without Credentials

Create `phase1n_adapter_contract_tests.csv`.

Add fixture-based parser/normalizer tests that do not require network calls or credentials.

At minimum, cover:

### Tiingo EOD

Expected normalized fields:

- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `adj_open`
- `adj_high`
- `adj_low`
- `adj_close`
- `adj_volume`
- `split_factor`
- `div_cash`

### Polygon/Massive Aggregates

Expected normalized fields:

- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `vwap` if available
- `transaction_count` if available
- `adjusted_response_flag`

### Alpha Vantage Daily Adjusted

Expected normalized fields:

- `date`
- `open`
- `high`
- `low`
- `close`
- `adjusted_close`
- `volume`
- `dividend_amount`
- `split_coefficient`

For each adapter, report:

- `source_name`
- `fixture_name`
- `parse_status`: `PASS`, `WARN`, `FAIL`
- `normalized_rows`
- `required_fields_present`: True / False
- `adjusted_fields_present`: True / False
- `date_order_valid`: True / False
- `positive_price_volume_check`: True / False
- `reason`

These tests must be deterministic and run without credentials.

## Part 5: Live Smoke Tests When Credentials Are Present

Create `phase1n_live_smoke_tests.csv`.

If no non-suspicious credential is present, create rows with `CREDENTIAL_MISSING` and do not attempt network calls.

If credentials are present, smoke-test these symbols for each configured independent vendor:

- `AAPL`
- `MSFT`
- `SPY`
- `QQQ`
- `SQ`
- `GEV`
- `RDDT`

For each row, report:

- `source_name`
- `ticker`
- `lookup_symbol`
- `attempted_network_fetch`
- `http_status_if_available`
- `parsed_rows`
- `first_date`
- `last_date`
- `required_start_date`
- `required_end_date`
- `overlap_trading_days`
- `has_adjusted_close`
- `has_adjusted_ohlc`
- `has_volume`
- `smoke_status`: `PASS`, `CREDENTIAL_MISSING`, `SUSPICIOUS_CREDENTIAL_SKIPPED`, `AUTH_FAILED`, `RATE_LIMITED`, `NO_DATA_FOR_SYMBOL`, `PARSE_ERROR`, `FAIL`
- `safe_to_retry_later`
- `reason`

Vendor-level live smoke pass:

- `PASS` only if at least 5 of 7 smoke tickers parse with positive rows and positive overlap, including AAPL, MSFT, SPY, and QQQ.
- `RATE_LIMITED` if the vendor is reachable but quota prevents a meaningful smoke result.
- `AUTH_FAILED` if the credential is present but rejected.
- `CREDENTIAL_MISSING` if no non-suspicious credential is present.

## Part 6: Phase 1M Rerun Readiness

Create `phase1n_phase1m_rerun_readiness.csv`.

Report:

- `preferred_vendor`
- `credential_ready`: True / False
- `adapter_contract_ready`: True / False
- `live_smoke_ready`: True / False
- `secret_safety_ready`: True / False
- `phase1m_rerun_allowed`: True / False
- `recommended_next_command`
- `reason`

Only set `phase1m_rerun_allowed=True` if:

- at least one independent credential is present and not suspicious;
- adapter contract tests pass for that vendor;
- live smoke passes for that vendor;
- no secret safety failure is detected.

Recommended next command, if allowed:

```bash
.venv/bin/python -m src.main --watchlist data/reports/phase1l_clean_watchlist_v3_candidate.txt --start 2024-01-01 --end 2026-06-30 --phase1m-credentialed-vendor-gate
```

If Phase 1M rerun is not allowed, explain the most specific blocker.

## Part 7: Vendor Selection Decision

Create `phase1n_vendor_selection_decision.md`.

Include:

- latest Phase 1M blocker summary;
- why strategy research remains paused;
- vendor preference order;
- what local credential the operator should add first;
- exact commands for the operator to run locally;
- what status would allow the next GPT review;
- explicit statement that no paper or live execution is authorized.

## Part 8: Summary and REPORT_TO_GPT.md

Create `phase1n_data_readiness_summary.md`.

Include:

- credential preflight summary;
- adapter contract test summary;
- live smoke summary;
- no-secret audit summary;
- Phase 1M rerun readiness summary;
- final Phase 1N status;
- whether strategy research remains paused;
- exact next action for GPT / operator.

Update `REPORT_TO_GPT.md` with:

- files changed;
- commands run;
- test results;
- credential status without exposing secrets;
- whether adapter contract tests passed;
- whether live smoke ran or was skipped;
- whether Phase 1M rerun is allowed;
- final Phase 1N status;
- explicit statement that no Phase 2, Phase 3, strategy retest, paper execution, or live execution was started;
- clear recommendation:
  - add a Tiingo credential and rerun Phase 1N, or
  - if a credential is already present and Phase 1N passes, rerun Phase 1M, or
  - if Phase 1M later passes data-readiness gates, return to GPT for a separate frozen Candidate 34 vs Candidate 35 retest decision.

## Acceptance Criteria

- All tests pass.
- Phase 1N CLI completes with and without credentials.
- Missing credentials are reported cleanly as `PHASE_1N_WAITING_FOR_CREDENTIAL`.
- Suspicious placeholder credentials are detected and skipped.
- No secrets are printed, cached, committed, or exposed in reports.
- `.env.example` contains placeholders only.
- `.env` and local secret files are ignored.
- Fixture-based adapter contract tests pass without network access.
- Live smoke tests run only when non-suspicious credentials are present.
- Yahoo Chart remains transport fallback only.
- Stooq remains blocked unless real CSV rows are obtained.
- No strategy retest is run.
- No production daily scan behavior changes are made.
- No paper or live trading path is enabled.
- `REPORT_TO_GPT.md` gives GPT and the operator a concrete next action.

## Stop Conditions

Stop and report blockers if:

- credential handling would risk leaking secrets;
- a generated report would expose a token, key, prefix, suffix, hash, or length;
- fixture-based adapter tests fail;
- vendor rate limits prevent meaningful live smoke tests;
- a vendor's adjusted price semantics cannot be represented safely;
- the repo cannot guarantee local credential files are ignored.

These stop conditions should not fail the test suite; they should produce explicit non-ready statuses.
