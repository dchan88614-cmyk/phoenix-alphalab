# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1F — Failure Attribution, Taxonomy, and Data Quality Audit

This task is historical research only.

Do not start Phase 2.
Do not start Phase 3.
Do not change daily scan production behavior.
Do not loosen Candidate 34 thresholds.
Do not adopt any new filter as active policy.
Do not produce financial advice or an operational recommendation.

## Why This Task

Phase 1E completed cross-validated conservative filter validation. The result was not strong enough for advancement:

- 20 deterministic samples were run.
- 100 replay rounds per sample were used.
- Samples 0-9 were used for calibration.
- Samples 10-19 were used for holdout.
- No calibration filter passed all gates.
- No holdout filter passed all gates.
- The best holdout reference improved drawdown but failed minimum sample activity, simulated win-rate, and concentration checks.
- The Phase 1D fixed volatility/smoke filter did not survive holdout.
- Remaining losses were concentrated around repeated failure samples and themes, but the largest losing theme bucket was still `UNMAPPED`.

Highest-priority question:

Are the remaining failures caused by identifiable historical regimes, themes, tickers, or data-quality problems, or is the current Candidate 34 family too unstable to continue without redesign?

This task must answer that question before any additional tuning.

## Goal

Create a Phase 1F audit layer that explains the Phase 1E failures without changing the trading logic.

The task must:

1. Build a complete historical failure ledger for all accepted historical candidates across the 20 deterministic samples.
2. Clean up ticker/theme taxonomy so `UNMAPPED` losses are explainable.
3. Attribute losses and drawdowns by ticker, theme, time period, market regime, and pre-entry features.
4. Identify data-quality issues that may distort the replay results.
5. Decide whether the next research step should be redesign, pause, or one narrow hypothesis test.

This task is diagnostic only. It must not activate any policy in daily scan.

## CLI

Add or update:

```bash
--phase1f-failure-audit
--replay-rounds 100
--replay-sample-count 20
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1f-failure-audit --replay-rounds 100 --replay-sample-count 20
```

If runtime is too high, support 10 samples as a fallback and clearly mark it as insufficient for approval.

## Required Outputs

Create or update:

- `data/reports/phase1f_failure_trade_ledger.csv`
- `data/reports/phase1f_theme_taxonomy.csv`
- `data/reports/phase1f_drawdown_attribution.csv`
- `data/reports/phase1f_regime_attribution.csv`
- `data/reports/phase1f_data_quality_audit.csv`
- `data/reports/phase1f_viability_summary.md`
- `REPORT_TO_GPT.md`

Keep earlier Phase 1 reports intact unless regeneration is required.

## Inputs

Reuse existing Phase 1 research code and outputs where possible:

- Phase 1A historical replay mechanics
- Phase 1B execution diagnostics
- Phase 1C robustness samples
- Phase 1D pre-entry feature snapshots
- Phase 1E calibration/holdout reports

Do not use future data for decision-side diagnostics.

## Part 1: Historical Failure Trade Ledger

Build a ledger of all accepted historical candidates across the 20 deterministic Phase 1E-style samples.

Required columns:

- `sample_id`
- `replay_date`
- `ticker`
- `theme`
- `subtheme`
- `reference_price`
- `entry_price`
- `entry_gap_pct`
- `shares_with_100`
- `estimated_total_cost`
- `decision_strength`
- `smoke_score`
- `volatility_20d`
- `atr_pct`
- `distance_from_52w_high`
- `relative_volume_prev20`
- `pre_entry_return_5d`
- `pre_entry_return_10d`
- `market_regime_label`
- `spy_trend_label`
- `qqq_trend_label`
- `market_volatility_label`
- `simulated_exit_reason`
- `simulated_pnl_dollars`
- `simulated_return_pct`
- `forward_return_20d`
- `stopped_out_but_20d_positive`
- `running_equity_before_trade`
- `running_equity_after_trade`
- `drawdown_after_trade`
- `drawdown_contribution_dollars`
- `is_worst_drawdown_trade_for_sample`

Focus especially on failure samples:

- sample 3
- sample 4
- sample 10
- sample 16

But still generate the ledger for every sample.

## Part 2: Theme Taxonomy Cleanup

Create `phase1f_theme_taxonomy.csv`.

Requirements:

1. Build a deterministic mapping for every ticker that appears in Phase 1E accepted historical candidates or excluded audit rows.
2. Include:
   - `ticker`
   - `company_name_if_available`
   - `theme`
   - `subtheme`
   - `mapping_source`
   - `mapping_confidence`
   - `notes`
3. Use available project metadata, watchlist names, existing code mappings, or conservative static mappings.
4. If a ticker cannot be confidently mapped, label it `UNMAPPED_LOW_CONFIDENCE` and explain why.
5. Report how much loss contribution remains unmapped after cleanup.

## Part 3: Drawdown Attribution

Create `phase1f_drawdown_attribution.csv`.

Group historical losses and drawdown contribution by:

- sample_id
- ticker
- theme
- subtheme
- calendar month / quarter
- entry_gap_pct bucket
- volatility_20d bucket
- atr_pct bucket
- smoke_score bucket
- decision_strength bucket
- exit reason

Metrics required:

- candidate count
- win count
- loss count
- simulated win rate
- total pnl dollars
- average pnl dollars
- median pnl dollars
- average 20d forward return
- median 20d forward return
- max single-candidate loss dollars
- max drawdown contribution dollars

The report must say whether failures are concentrated or broad.

## Part 4: Market Regime Attribution

Create `phase1f_regime_attribution.csv`.

Use only market data available on or before each replay date.

Compute simple, auditable labels:

- SPY above/below 20-day moving average
- SPY above/below 50-day moving average
- QQQ above/below 20-day moving average
- QQQ above/below 50-day moving average
- SPY 20-day realized volatility bucket
- SPY drawdown-from-50-day-high bucket
- broad risk-on / risk-off / mixed label derived only from the above

Do not introduce complex black-box regime models.

## Part 5: Data Quality Audit

Create `phase1f_data_quality_audit.csv`.

Audit for:

- missing OHLCV bars
- stale symbol metadata
- delisted or renamed symbols
- split or adjustment anomalies
- zero-volume or abnormal-volume days
- incomplete 20-trading-day forward windows
- symbols rejected by metadata lookup
- repeated yfinance warnings or 404s

The summary must explain whether data issues materially affect Phase 1E conclusions.

## Part 6: Viability Decision

Mark exactly one final Phase 1F status:

- `PHASE_1F_DATA_QUALITY_BLOCKER`
- `PHASE_1F_FAILURES_CONCENTRATED_RESEARCH_ONLY`
- `PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN`

Use these rules:

### Data Quality Blocker

Use `PHASE_1F_DATA_QUALITY_BLOCKER` if replay conclusions are materially unreliable because of missing data, symbol issues, adjustment anomalies, or stale metadata.

### Failures Concentrated Research Only

Use `PHASE_1F_FAILURES_CONCENTRATED_RESEARCH_ONLY` if failures are clearly concentrated by explainable theme, ticker, or market regime, but no operational change is approved.

### Failures Broad Recommend Redesign

Use `PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN` if failures are broad across themes, tickers, and regimes, or if the evidence suggests Candidate 34 entry logic needs redesign rather than more threshold filtering.

## Part 7: Report Requirements

`phase1f_viability_summary.md` must start with:

```text
PHOENIX NANO PHASE 1F — FAILURE ATTRIBUTION, TAXONOMY, AND DATA QUALITY AUDIT
```

It must include:

- research-only statement
- Phase 1E recap
- failure sample summary
- theme taxonomy cleanup results
- remaining unmapped loss contribution
- drawdown attribution summary
- market regime attribution summary
- data quality audit summary
- whether failures are concentrated or broad
- final Phase 1F status
- explicit statement: `Do not start paper execution or real-money execution.`
- concrete recommendation for the next research task

CSV files must contain enough columns to audit every sample, historical candidate, attribution group, and data-quality issue.

## Part 8: Tests

Add or update tests for:

1. failure ledger contains all accepted historical candidates across requested samples
2. failure ledger uses only pre-entry features for decision-side diagnostics
3. theme taxonomy eliminates avoidable `UNMAPPED` values or explains low-confidence mappings
4. market regime labels use only data available on or before replay_date
5. data quality audit catches missing and abnormal data cases
6. no active scan behavior is changed
7. Phase 1F status never approves Phase 2 or deployment
8. reports are written
9. full pytest suite passes

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1f-failure-audit --replay-rounds 100 --replay-sample-count 20
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1F Viability Summary
- Failure sample summary
- Theme taxonomy cleanup results
- Drawdown attribution summary
- Market regime attribution summary
- Data quality audit summary
- Phase 1F status
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2, Phase 3, paper execution, or real-money execution.
