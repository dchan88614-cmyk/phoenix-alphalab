# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1D - Entry-Rule Failure Diagnostics.
- Added Phase 1D entry-rule diagnostic analysis as historical/manual-review research only.
- Reconstructed pre-entry feature snapshots for deterministic replay BUY decisions.
- Compared baseline simulation winners versus losers using only replay-date or entry-date features.
- Added conservative offline entry-filter hypotheses without changing daily scan behavior.
- Re-ran filtered historical account replay with `baseline_current` exits.
- Added excluded-decision audit rows for skipped historical BUY decisions.
- Added CLI flag:
  - `--phase1d-entry-rule-analysis`
- Created required outputs:
  - `data/reports/phase1d_entry_rule_diagnostics.csv`
  - `data/reports/phase1d_loser_feature_attribution.csv`
  - `data/reports/phase1d_filter_backtest_matrix.csv`
  - `data/reports/phase1d_filter_excluded_decisions.csv`
  - `data/reports/phase1d_candidate_filter_summary.md`
  - `data/reports/phase1d_entry_rule_summary.md`
- Did not loosen Candidate 34 thresholds.
- Did not adopt close-based stops.
- Did not start Phase 2.
- Did not start Phase 3.
- Did not start paper trading.
- Did not start live trading.

## Files Changed

- `src/research/phase1d_entry_rules.py`
- `src/main.py`
- `tests/test_phase1d_entry_rules.py`
- `data/reports/phase1d_entry_rule_diagnostics.csv`
- `data/reports/phase1d_loser_feature_attribution.csv`
- `data/reports/phase1d_filter_backtest_matrix.csv`
- `data/reports/phase1d_filter_excluded_decisions.csv`
- `data/reports/phase1d_candidate_filter_summary.md`
- `data/reports/phase1d_entry_rule_summary.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1d-entry-rule-analysis --replay-rounds 100 --replay-sample-count 10
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_phase1d_entry_rules.py -q
# 8 passed
```

```bash
.venv/bin/python -m pytest -q
# 105 passed, 1 warning in 4.08s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1d-entry-rule-analysis --replay-rounds 100 --replay-sample-count 10
```

## Phase 1D Entry-Rule Summary

- Phase 1D status: `PHASE_1D_FILTER_HYPOTHESIS_PROMISING_NOT_APPROVED`
- Samples analyzed: 10
- BUY decisions analyzed: 344
- Baseline simulation winners: 146
- Baseline simulation losers: 198
- Filter backtest matrix rows: 130
- Excluded decision audit rows: 1345

## Samples Analyzed

- Deterministic replay sample count: 10
- Replay rounds per sample: 100
- Candidate rule: Candidate 34, unchanged.
- Exit policy for filter backtests: `baseline_current`.

## BUY Decisions Analyzed

- Total historical BUY decisions: 344
- Winner flag definitions:
  - `winner_20d`: 20-day forward return above zero.
  - `winner_baseline_simulation`: baseline simulated trade PnL above zero.
- All diagnostic feature snapshots are reconstructed from data available on or before the replay date / entry date.

## Winner vs Loser Feature Findings

Top all-sample loser/winner separations:

| feature | winner mean | loser mean | separation |
|:--|--:|--:|--:|
| distance_from_52w_high_pct | -0.0446 | -0.0753 | 0.2395 |
| decision_strength | 0.7076 | 0.6788 | 0.2344 |
| near_max_entry_price_pct | 0.5271 | 0.4737 | 0.1995 |
| smoke_score | 0.9293 | 0.9210 | 0.1930 |
| return_10d_prior | 0.2935 | 0.3337 | 0.1387 |

Interpretation:

- Losers were, on average, farther below the prior 52-week high.
- Losers had slightly weaker `decision_strength` and `smoke_score`.
- Losers showed somewhat stronger 10-day prior run-up.
- Separation scores are modest; no single pre-entry feature cleanly explains the failures.

## Top Suspicious Loser Signals

- Weaker distance from 52-week high: losers averaged -7.53% versus winners at -4.46%.
- Lower decision strength: losers averaged 0.6788 versus winners at 0.7076.
- Lower smoke score: losers averaged 0.9210 versus winners at 0.9293.
- Stronger 10-day prior run-up: losers averaged 33.37% versus winners at 29.35%.
- Lower relative volume: losers averaged 2.9434 versus winners at 3.3410.

## Filters Tested

- `high_atr_pct`
- `high_volatility_20d`
- `extreme_entry_gap_pct`
- `minimum_decision_strength`
- `minimum_smoke_score`
- `low_relative_volume_prev20`
- `weak_distance_from_high`
- `extreme_short_term_runup`
- `theme_concentration_cap`
- `repeated_loser_ticker_cooldown`
- `atr_plus_decision_strength`
- `volatility_plus_smoke_score`
- `risk_stack_filter`

## Best Filter By Median Ending Value

- `weak_distance_from_high`
- Median ending account value: $196.02
- Still failed Phase 1D gates because worst-sample ending value remained below $100, worst drawdown remained worse than -45%, and median simulation accuracy remained below 50%.

## Best Filter By Worst-Sample Ending Value

- `volatility_plus_smoke_score`
- Worst-sample ending account value: $95.43
- This is improved relative to many alternatives, but still below the required $100 worst-sample gate.

## Best Filter By Drawdown Reduction

- `volatility_plus_smoke_score`
- Median max drawdown: -28.36%
- It still failed the worst-sample ending-value gate and did not justify Phase 2.

## Filter Excluded Decision Audit Summary

- Excluded decision audit rows: 1345
- No tested filter had all-sample excluded winners greater than or equal to excluded losers in the summary.
- Some filters produced promising sample-level results, but none proved robust enough across all 10 deterministic samples.
- Passing sample counts by filter:
  - `low_relative_volume_prev20`: 3
  - `minimum_decision_strength`: 3
  - `theme_concentration_cap`: 3
  - `volatility_plus_smoke_score`: 3
  - `extreme_short_term_runup`: 2
  - `atr_plus_decision_strength`: 1
  - `high_volatility_20d`: 1
  - `minimum_smoke_score`: 1
  - `repeated_loser_ticker_cooldown`: 1
  - `weak_distance_from_high`: 1
  - `extreme_entry_gap_pct`: 0
  - `high_atr_pct`: 0
  - `risk_stack_filter`: 0

## Phase 1D Status

- Status: `PHASE_1D_FILTER_HYPOTHESIS_PROMISING_NOT_APPROVED`
- Do not mark Phase 2 ready.
- Do not start paper trading or live trading.
- Reason: some filters improved median or drawdown metrics, but no filter cleared the required robustness gates across all deterministic samples.

## Problems

- No filter cleared all Phase 1D diagnostic gates.
- Worst-sample ending account value remained below $100 for the best worst-sample filter.
- Worst-sample drawdowns remained worse than -45% for top median-ending filters.
- Median simulation accuracy remained below 50% for several top filters.
- Feature separation between winners and losers is real but modest.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- yfinance data remains non-institutional retail data and should not be treated as an execution feed.

## Questions For GPT

- Should Phase 1E test only `volatility_plus_smoke_score`, since it had the best worst-sample ending value and drawdown profile?
- Should `weak_distance_from_high` be considered too fragile because it led median ending value but failed worst-sample gates?
- Should GPT require a filter to improve worst-sample ending value above $100 before any additional entry-rule refinement?
- Should high-volatility theme concentration be handled by a hard cap, or only used as a diagnostic warning?

## Next Suggested Tasks

- Do not start Phase 2.
- Do not start Phase 3.
- Do not start paper trading.
- Do not start live trading.
- Ask GPT to review Phase 1D results and approve one narrow Phase 1E entry-filter experiment.
- If GPT approves Phase 1E, test only one or two conservative filters without loosening Candidate 34.
