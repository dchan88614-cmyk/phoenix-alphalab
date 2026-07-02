# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1O — Credential-Gated Phase 1M Rerun Authorization

This task is **data-readiness gating only**. It exists because Phase 1N proved that the credential activation path is safe, but the repository still has no independent vendor credential available.

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
Do not commit, print, cache, hash, prefix/suffix-log, length-log, or expose any API secret, token, or key.

## Why This Task

Latest Phase 1N result:

`PHASE_1N_WAITING_FOR_CREDENTIAL`

Evidence from the latest reports:

- tests passed: `200 passed, 1 warning`
- credential preflight: `MISSING`: 4
- adapter contract tests: `PASS`: 3
- live smoke tests: `CREDENTIAL_MISSING`: 21
- no-secret audit: `PASS`: 10
- Phase 1M rerun allowed: `False`
- reason: `no non-suspicious vendor credential present`

This means the highest-priority blocker is no longer code structure, parser contracts, or secret safety. The blocker is that the operator must add exactly one independent vendor credential locally, preferably `TIINGO_API_TOKEN`, and then rerun the credential gate.

Do not keep inventing new strategy filters, overlays, universes, or data vendors while this blocker is unresolved. More strategy research without independent OHLCV validation is not useful.

## Operator Prerequisite

Before this task can meaningfully pass, the operator must add a local credential outside git, preferably:

```bash
export TIINGO_API_TOKEN=<YOUR_TIINGO_API_TOKEN>
```

or copy `.env.example` to an untracked `.env` file and fill only the local placeholder there.

Never paste a real credential into `TASKS.md`, `REPORT_TO_GPT.md`, source code, tests, reports, screenshots, or commit messages.

## Goal

Create a clean decision gate that answers:

1. Has a non-suspicious independent vendor credential been supplied locally?
2. Does Phase 1N pass live smoke for that vendor?
3. If Phase 1N passes, can Phase 1M be rerun for independent secondary OHLCV validation?
4. If Phase 1M passes data-readiness gates, should GPT be asked to authorize a separate frozen Candidate 34 vs Candidate 35 retest task?

This task may only authorize a **future GPT review**. It must not authorize paper or live trading.

Possible final statuses:

- `PHASE_1O_BLOCKED_WAITING_FOR_CREDENTIAL`
- `PHASE_1O_BLOCKED_PHASE1N_NOT_READY`
- `PHASE_1O_BLOCKED_PHASE1M_DATA_NOT_READY`
- `PHASE_1O_READY_FOR_GPT_REVIEW_OF_FROZEN_RETEST`

## Step 1: Rerun Phase 1N Credential Gate

Run:

```bash
.venv/bin/python -m src.main --watchlist data/reports/phase1l_clean_watchlist_v3_candidate.txt --start 2024-01-01 --end 2026-06-30 --phase1n-credential-activation-gate
```

Then inspect:

- `data/reports/phase1n_credentials_preflight.csv`
- `data/reports/phase1n_live_smoke_tests.csv`
- `data/reports/phase1n_phase1m_rerun_readiness.csv`
- `data/reports/phase1n_no_secret_audit.csv`
- `data/reports/phase1n_data_readiness_summary.md`

If `phase1m_rerun_allowed` is not `True`, stop immediately and report the most specific blocker. Do not change strategy code. Do not run Phase 1M. Do not run any retest.

## Step 2: If Phase 1N Allows It, Rerun Phase 1M Vendor Gate

Only if Phase 1N says `phase1m_rerun_allowed=True`, run:

```bash
.venv/bin/python -m src.main --watchlist data/reports/phase1l_clean_watchlist_v3_candidate.txt --start 2024-01-01 --end 2026-06-30 --phase1m-credentialed-vendor-gate
```

Then inspect:

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

## Step 3: Data-Readiness Decision

Phase 1O may recommend GPT review for a separate frozen Candidate 34 vs Candidate 35 retest only if Phase 1M demonstrates all of the following:

- at least one independent credentialed vendor passes smoke tests;
- AAPL, MSFT, SPY, and QQQ pass vendor smoke;
- independent secondary OHLCV coverage is at least 90% for active candidates;
- SPY and QQQ proxy coverage is 100%;
- no clean-watchlist alias/date-gate failures remain;
- no adjustment mismatch blocker remains;
- no secret-safety failure exists;
- the clean watchlist candidate is non-empty and reproducible.

If any gate fails, stop with `PHASE_1O_BLOCKED_PHASE1M_DATA_NOT_READY` and explain the exact blocker.

## Required Outputs

Create or update:

- `data/reports/phase1o_rerun_authorization_decision.md`
- `data/reports/phase1o_gate_status.csv`
- `REPORT_TO_GPT.md`

`phase1o_gate_status.csv` must include at least:

- `gate_name`
- `status`: `PASS`, `WARN`, `FAIL`, or `BLOCKED`
- `source_report`
- `evidence`
- `next_action`

`phase1o_rerun_authorization_decision.md` must include:

- latest Phase 1N status;
- whether a credential was present;
- whether live smoke passed;
- whether Phase 1M was rerun;
- latest Phase 1M data-readiness status if Phase 1M ran;
- whether GPT review of a frozen Candidate 34 vs Candidate 35 retest is justified;
- explicit statement that no Phase 2, Phase 3, paper execution, or live execution is authorized.

Update `REPORT_TO_GPT.md` with:

- files changed;
- commands run;
- test results;
- credential status without exposing secrets;
- whether Phase 1N allowed Phase 1M rerun;
- whether Phase 1M was rerun;
- final Phase 1O status;
- exact next action for GPT/operator;
- explicit statement that no strategy retest, paper execution, or live execution was started.

## Acceptance Criteria

- Missing credentials produce `PHASE_1O_BLOCKED_WAITING_FOR_CREDENTIAL` or `PHASE_1O_BLOCKED_PHASE1N_NOT_READY`, not a crash.
- Present but invalid credentials produce a clear auth/config blocker, not a strategy failure.
- No secrets are printed, committed, cached, hashed, prefix/suffix-logged, or length-logged.
- Phase 1M is only rerun if Phase 1N explicitly allows it.
- No Candidate 34 vs Candidate 35 retest is run in this task.
- No strategy threshold sweep is run.
- No production daily scan behavior is changed.
- No paper or live trading path is enabled.
- `REPORT_TO_GPT.md` gives GPT/operator one concrete next action.

## Stop Conditions

Stop and report blockers if:

- no non-suspicious credential is available;
- live smoke does not pass;
- Phase 1N does not allow Phase 1M rerun;
- Phase 1M data-readiness gates do not pass;
- any generated report would expose a token, key, prefix, suffix, hash, or length;
- any task would require a strategy retest before independent data readiness is satisfied.
