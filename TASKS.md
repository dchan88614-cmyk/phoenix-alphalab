# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1I — Data Quality, Vendor Validation, and Universe Design Audit

This task is historical research only.

Do not start Phase 2.
Do not start Phase 3.
Do not enable paper execution.
Do not enable real-money execution.
Do not change daily scan production behavior.
Do not loosen Candidate 34 thresholds.
Do not adopt Candidate 35 or any overlay as active policy.
Do not create Candidate 36 entry rules.
Do not perform another broad threshold sweep.
Do not produce financial advice or an operational recommendation.

## Why This Task

Phase 1H completed the trend-quality risk overlay sandbox.

The result was:

- `PHASE_1H_HOLDOUT_FAILED`
- Candidate 34 remains unstable.
- Candidate 35 trend-quality is directionally better than Candidate 34 but still fails risk gates.
- The best promoted overlay, `overlay_ticker_loss_cooldown_8pct_15`, still failed holdout gates.
- Drawdown improved only modestly, from about `-49.09%` to about `-46.04%`, still far worse than the `-35%` gate.
- Median simulated win rate remained below the `52%` gate.
- Top-theme loss concentration remained above the allowed gate.
- Excluded-trade counterfactuals showed missed winner dollars were greater than avoided loser dollars.
- Recent runs also reported yfinance metadata/download warnings, including rejected metadata, `BITF` 404, and `HUT` missing price data.

Therefore the highest-priority next step is **not** another entry-rule redesign and **not** another risk overlay sweep.

The next optimized research task is to determine whether Phoenix Nano is being blocked by:

1. unreliable retail-grade data,
2. an unstable or overly speculative watchlist universe,
3. theme/ticker concentration created by the universe itself,
4. survivorship / metadata / corporate-action issues,
5. or a true strategy-design failure that persists even after data and universe hygiene.

## Goal

Create Phase 1I research code that audits data and universe quality before any further candidate logic changes.

The output should answer:

- Is the current watchlist research-grade enough for replay testing?
- Which tickers have incomplete, stale, rejected, anomalous, or unreliable data?
- Are failures concentrated in universe construction rather than entry rules?
- Does a pre-declared data-quality-cleaned universe materially reduce drawdown without tuning entry rules?
- Should Phoenix Nano pause strategy iteration until a better data source or universe process exists?

## CLI

Add or update:

```bash
--phase1i-data-universe-audit
--replay-rounds 100
--replay-sample-count 30
```

Preferred command:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1i-data-universe-audit --replay-rounds 100 --replay-sample-count 30
```

If runtime is too high, support a clearly marked fallback:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1i-data-universe-audit --replay-rounds 100 --replay-sample-count 20
```

A fallback run cannot approve anything beyond `PHASE_1I_INSUFFICIENT_SAMPLE_WARNING`.

## Required Outputs

Create or update:

- `data/reports/phase1i_symbol_data_quality_audit.csv`
- `data/reports/phase1i_vendor_validation_matrix.csv`
- `data/reports/phase1i_universe_composition_audit.csv`
- `data/reports/phase1i_universe_variant_backtest_matrix.csv`
- `data/reports/phase1i_universe_variant_holdout_results.csv`
- `data/reports/phase1i_data_gap_incident_log.csv`
- `data/reports/phase1i_rejected_symbol_audit.csv`
- `data/reports/phase1i_strategy_vs_universe_attribution.csv`
- `data/reports/phase1i_data_universe_summary.md`
- `REPORT_TO_GPT.md`

Keep earlier Phase 1 reports intact unless regeneration is required.

The summary must start with:

```text
PHOENIX NANO PHASE 1I — DATA QUALITY, VENDOR VALIDATION, AND UNIVERSE DESIGN AUDIT
```

## Inputs

Reuse existing Phase 1 research code and outputs where useful:

- Phase 1A historical replay mechanics
- Phase 1B execution diagnostics
- Phase 1C robustness sampling
- Phase 1D pre-entry feature snapshots
- Phase 1E calibration / holdout structure
- Phase 1F taxonomy, failure attribution, and data-quality audit
- Phase 1G Candidate 35 trend-quality definition
- Phase 1H risk overlay results

Do not use future data for candidate selection, universe membership decisions, data-quality flags, regime labels, ranking, or trade decisions.

Future data may be used only after a decision is recorded, for verification.

## Part 1: Data Quality Audit

Create `phase1i_symbol_data_quality_audit.csv`.

Audit every ticker in `config/watchlists/us_liquid_growth_100.txt` and any index/proxy data used by Phase 1H, including SPY and QQQ.

For each symbol, report:

- ticker
- asset_type if available
- first_available_date
- last_available_date
- requested_start_date
- requested_end_date
- has_full_lookback_coverage
- has_full_forward_coverage
- missing_ohlcv_count
- missing_ohlcv_pct
- zero_volume_count
- zero_volume_pct
- abnormal_volume_flag
- stale_data_flag
- duplicate_date_count
- non_monotonic_date_flag
- split_or_adjustment_anomaly_flag
- extreme_gap_count
- extreme_gap_examples
- metadata_available_flag
- metadata_rejected_flag
- metadata_rejection_reason
- download_error_flag
- download_error_message
- yfinance_404_flag
- latest_close
- latest_price_under_50_flag
- avg_dollar_volume_20d
- avg_dollar_volume_60d
- data_quality_grade: `PASS`, `WARN`, or `FAIL`
- data_quality_reason

A symbol should be `FAIL` if:

- OHLCV cannot be downloaded,
- metadata is rejected and prevents safe use,
- adjusted OHLCV appears structurally broken,
- there is insufficient lookback for factors,
- there is no usable forward window for replay verification,
- or the symbol has severe missing/zero-volume issues.

A symbol should be `WARN` if:

- data is usable but has retail-grade limitations,
- forward window is incomplete only near the final replay dates,
- minor missing bars are calendar-related,
- or metadata is incomplete but price data appears usable for research diagnostics.

## Part 2: Vendor Validation Matrix

Create `phase1i_vendor_validation_matrix.csv`.

For each ticker where a second source is available through existing project dependencies or simple public download logic, compare yfinance OHLCV against the secondary source.

Acceptable secondary sources may include, if already feasible without secrets:

- Stooq daily prices
- Nasdaq public historical data if simple and stable
- exchange/Nasdaq symbol directory files for listing validation
- cached project data if it exists

Do not add paid APIs or secrets.
Do not block the run if no second vendor is available.

For each comparable symbol/date window, report:

- ticker
- primary_vendor
- secondary_vendor
- comparison_start_date
- comparison_end_date
- overlapping_trading_days
- close_price_median_abs_diff_pct
- close_price_max_abs_diff_pct
- volume_median_abs_diff_pct
- volume_max_abs_diff_pct
- adjusted_price_mismatch_flag
- corporate_action_mismatch_flag
- validation_status: `MATCH`, `WARN`, `FAIL`, or `NO_SECOND_SOURCE`
- validation_reason

If a secondary source is not available for most symbols, the summary must explicitly say that Phoenix Nano remains dependent on a single retail-grade data source and should not treat the research as execution-grade.

## Part 3: Data Gap Incident Log

Create `phase1i_data_gap_incident_log.csv`.

Log concrete incidents, including but not limited to:

- yfinance 404s such as `BITF`
- download failures such as `HUT`
- missing SPY/QQQ regime windows
- incomplete metadata for watchlist tickers
- stale latest dates
- suspicious split/adjustment jumps
- abnormal volume spikes/drops

Columns:

- incident_id
- ticker
- incident_type
- first_seen_run_phase
- affected_replay_dates
- affected_samples
- severity: `LOW`, `MEDIUM`, `HIGH`, `BLOCKER`
- likely_effect_on_results
- recommended_action

## Part 4: Universe Composition Audit

Create `phase1i_universe_composition_audit.csv`.

Analyze the current watchlist before any trading logic.

Report:

- total_tickers
- data_quality_pass_count
- data_quality_warn_count
- data_quality_fail_count
- price_under_50_count
- price_under_20_count
- avg_dollar_volume_pass_count
- theme_count
- tickers_per_theme
- top_theme_ticker_share
- high_beta_or_speculative_theme_share
- crypto_adjacent_count
- biotech_count
- EV_mobility_count
- AI_software_count
- semiconductor_hardware_count
- single_name_theme_count
- median_atr_pct
- median_volatility_20d
- 90th_percentile_atr_pct
- 90th_percentile_volatility_20d
- universe_quality_assessment

Use the Phase 1F taxonomy when available.
If any ticker is unmapped, map it conservatively and document it.

## Part 5: Pre-Declared Universe Variants

Do not create new entry rules.
Do not tune thresholds based on holdout.

Evaluate only these pre-declared universe variants:

1. `current_watchlist_full`
   - The current watchlist as-is.

2. `data_quality_pass_only`
   - Exclude `data_quality_grade = FAIL`.
   - Keep `PASS` and `WARN` only if they are usable for research.

3. `metadata_and_price_clean`
   - Exclude metadata-rejected symbols.
   - Exclude symbols that cannot be safely evaluated for $100 whole-share / max-entry logic.
   - Exclude symbols with structurally broken adjusted OHLCV.

4. `liquidity_and_price_clean`
   - Exclude symbols that fail a pre-declared liquidity floor.
   - Use only past data available before the replay date for liquidity checks.
   - Preserve the Phoenix Nano $100 whole-share / max-entry logic.

5. `theme_balanced_clean`
   - Start from `data_quality_pass_only`.
   - Limit overconcentrated themes using only static taxonomy and pre-entry universe membership.
   - Do not use future PnL to choose which tickers remain.
   - If too many tickers exist in a theme, choose deterministically using pre-entry liquidity and data-quality grade, not future returns.

6. `conservative_research_universe`
   - Intersection of data-quality, metadata/price, liquidity, and theme-balance rules.
   - Must be defined before validation/holdout.

The purpose is not to find a tradable universe. The purpose is to determine whether the current failures are partly caused by bad data or an unstable universe.

## Part 6: Frozen Strategy Re-Test Across Universe Variants

Create `phase1i_universe_variant_backtest_matrix.csv` and `phase1i_universe_variant_holdout_results.csv`.

For each universe variant, re-run only:

1. `candidate34_frozen_baseline`
2. `candidate35_trend_quality_frozen`

Do not test Phase 1H overlays except as a historical reference table if helpful.
Do not introduce Candidate 36.
Do not change entry scoring, stop/target, or ranking formulas.

Use deterministic replay samples.

Preferred 30-sample split:

- calibration/reference: samples 0-9
- validation/reference: samples 10-19
- holdout: samples 20-29

Fallback 20-sample split:

- calibration/reference: samples 0-6
- validation/reference: samples 7-13
- holdout: samples 14-19

For each sample and strategy/universe pair, report:

- universe_variant
- strategy_name
- sample_id
- split_name
- replay_rounds
- universe_size
- data_fail_excluded_count
- metadata_excluded_count
- liquidity_excluded_count
- theme_balance_excluded_count
- BUY count
- NO_TRADE count
- BUY rate
- simulated win rate
- 1d / 3d / 5d / 10d / 20d direction accuracy
- average and median forward returns by window
- average win dollars
- average loss dollars
- profit factor
- ending account value from $100
- max drawdown
- worst trade loss percent
- stopped-out-but-20d-positive rate
- top profit ticker contribution share
- top loss ticker contribution share
- top profit theme contribution share
- top loss theme contribution share
- median ending value excluding best trade

## Part 7: Strategy-vs-Universe Attribution

Create `phase1i_strategy_vs_universe_attribution.csv`.

For each universe variant, compare against `current_watchlist_full`:

- change_in_universe_size
- change_in_buy_count
- change_in_ending_account_value
- change_in_worst_drawdown
- change_in_win_rate
- change_in_20d_accuracy
- change_in_profit_factor
- change_in_top_theme_loss_share
- bad_data_removed_count
- high_risk_theme_removed_count
- winners_removed_count
- losers_removed_count
- winner_dollars_removed
- loser_dollars_removed
- net_counterfactual_effect
- diagnosis: `DATA_BLOCKER`, `UNIVERSE_BLOCKER`, `STRATEGY_BLOCKER`, or `MIXED`

A universe change should not be called an improvement unless:

- it reduces losses more than it removes winners,
- it does not trade too rarely,
- and it is based on pre-declared data/universe criteria rather than future PnL.

## Part 8: Research Gates

Do not advance to Phase 2, paper execution, or live execution from this task.

Phase 1I can only produce these statuses:

- `PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH`
- `PHASE_1I_UNIVERSE_BLOCKER_REBUILD_WATCHLIST`
- `PHASE_1I_STRATEGY_BLOCKER_REDESIGN_REQUIRED`
- `PHASE_1I_MIXED_BLOCKERS_NEED_REMEDIATION`
- `PHASE_1I_CLEAN_UNIVERSE_PROMISING_FOR_GPT_REVIEW`
- `PHASE_1I_INSUFFICIENT_SAMPLE_WARNING`

Mark `PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH` if:

- more than 10% of watchlist tickers are `data_quality_grade = FAIL`,
- or SPY/QQQ regime data is missing for key replay windows,
- or major ticker price histories cannot be validated against any secondary source and anomalies affect results materially,
- or repeated vendor incidents make historical replay unreliable.

Mark `PHASE_1I_UNIVERSE_BLOCKER_REBUILD_WATCHLIST` if:

- current failures materially improve under pre-declared clean universe variants,
- and the improvement comes from removing unstable/badly specified universe members rather than future-PnL cherry-picking.

Mark `PHASE_1I_STRATEGY_BLOCKER_REDESIGN_REQUIRED` if:

- data quality is acceptable,
- universe variants do not materially improve holdout failures,
- and Candidate 34 / Candidate 35 remain below gates.

Mark `PHASE_1I_CLEAN_UNIVERSE_PROMISING_FOR_GPT_REVIEW` only if all holdout conditions are met for `candidate35_trend_quality_frozen` on a pre-declared clean universe:

1. Full preferred 30-sample run completed.
2. Every holdout sample has at least 30 BUY decisions per 100 replay rounds.
3. Worst holdout sample ending account value > $110.
4. Median holdout ending account value > $130.
5. Worst holdout max drawdown better than -35%.
6. Median holdout simulated win rate >= 52%.
7. Median holdout 20d direction accuracy >= 58%.
8. Median holdout profit factor >= 1.30.
9. Worst trade loss better than -15%.
10. Max top ticker loss share <= 35%.
11. Max top theme loss share <= 45%.
12. Median ending value excluding the single best trade > $115.
13. Removed winners dollars must not exceed removed loser dollars.

Even if all conditions pass, do not activate the policy. Mark only for GPT review.

## Part 9: Tests

Add tests for:

1. `--phase1i-data-universe-audit` CLI dispatch works.
2. Symbol data-quality grading returns `PASS`, `WARN`, or `FAIL` deterministically.
3. Metadata-rejected and download-failed symbols are logged.
4. Vendor validation handles missing secondary sources without crashing.
5. Universe variants are generated using only pre-declared non-future criteria.
6. Theme-balanced universe selection does not use future returns or PnL.
7. Frozen Candidate 34 and Candidate 35 are re-run without changing core rules.
8. Holdout results include all required metrics.
9. Strategy-vs-universe attribution computes winner/loss removal correctly.
10. Phase 1I statuses cannot approve paper or live trading.
11. Reports are written.
12. Full pytest suite passes.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1i-data-universe-audit --replay-rounds 100 --replay-sample-count 30
```

## Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Test Results
- Phase 1I Data / Universe Summary
- Data quality PASS / WARN / FAIL counts
- Vendor validation coverage
- Data gap incidents
- Universe composition findings
- Universe variant holdout results
- Candidate 34 vs Candidate 35 across universe variants
- Strategy-vs-universe attribution
- Final Phase 1I status
- Problems
- Questions For GPT
- Next Suggested Tasks

## Stop Condition

Commit, push, and stop. Do not start Phase 2, Phase 3, paper execution, or live trading.
