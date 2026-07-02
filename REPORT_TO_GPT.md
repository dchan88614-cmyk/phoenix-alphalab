# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1G - Candidate 35 Redesign Sandbox.
- Added a historical research-only Candidate 35 redesign sandbox.
- Preserved Candidate 34 as a frozen baseline; Candidate 34 thresholds and production scan behavior were not loosened.
- Added deterministic calibration, validation, and holdout splits for 100 replay rounds with sample count 30.
- Added data/regime preflight coverage, including `SPY` benchmark and `QQQ` market regime context.
- Added five Candidate 35 sandbox families:
  - `candidate35_trend_quality`
  - `candidate35_pullback_continuation`
  - `candidate35_breakout_confirmation`
  - `candidate35_regime_gated_momentum`
  - `candidate35_low_volatility_compounder`
- Added CLI flag:
  - `--phase1g-redesign-sandbox`
- Created required outputs:
  - `data/reports/phase1g_data_regime_preflight.csv`
  - `data/reports/phase1g_candidate_family_definitions.md`
  - `data/reports/phase1g_redesign_calibration_matrix.csv`
  - `data/reports/phase1g_redesign_validation_matrix.csv`
  - `data/reports/phase1g_redesign_holdout_results.csv`
  - `data/reports/phase1g_candidate34_vs_35_comparison.csv`
  - `data/reports/phase1g_rejected_decision_audit.csv`
  - `data/reports/phase1g_redesign_summary.md`
- Did not start Phase 2.
- Did not start Phase 3.
- Did not enable paper execution.
- Did not enable real-money execution.
- Did not change daily scan production behavior.
- Did not adopt Candidate 35 as active policy.
- Did not produce financial advice or an operational recommendation.

## Files Changed

- `src/main.py`
- `src/research/phase1g_redesign_sandbox.py`
- `tests/test_phase1g_redesign_sandbox.py`
- `data/reports/phase1g_data_regime_preflight.csv`
- `data/reports/phase1g_candidate_family_definitions.md`
- `data/reports/phase1g_redesign_calibration_matrix.csv`
- `data/reports/phase1g_redesign_validation_matrix.csv`
- `data/reports/phase1g_redesign_holdout_results.csv`
- `data/reports/phase1g_candidate34_vs_35_comparison.csv`
- `data/reports/phase1g_rejected_decision_audit.csv`
- `data/reports/phase1g_redesign_summary.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1g-redesign-sandbox --replay-rounds 100 --replay-sample-count 30
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_phase1g_redesign_sandbox.py -q
# 11 passed, 1 warning
```

```bash
.venv/bin/python -m pytest -q
# 133 passed, 1 warning in 11.98s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1g-redesign-sandbox --replay-rounds 100 --replay-sample-count 30
```

## Phase 1G Redesign Summary

- Summary file starts with the required heading:
  - `PHOENIX NANO PHASE 1G — CANDIDATE 35 REDESIGN SANDBOX`
- Final status: `PHASE_1G_HOLDOUT_FAILED`
- Candidate 35 did not earn promotion to active policy.
- The best surviving holdout family was `candidate35_trend_quality`, but it still failed holdout gates.
- Research-only conclusion: redesign produced useful evidence, but the system remains blocked for any execution phase.

## Data/Regime Preflight Summary

- Preflight rows: 100.
- `SPY` benchmark data:
  - bars: 624
  - missing sessions: 0
  - warnings: none
- `QQQ` regime context data:
  - bars: 624
  - missing sessions: 0
  - warnings: none
- Data/regime preflight did not block Phase 1G.
- yfinance remains a non-institutional research data source and should not be treated as an execution feed.

## Candidate Family Definitions

- `candidate34_frozen_baseline`: frozen prior Candidate 34 rule family used only as baseline comparison.
- `candidate35_trend_quality`: requires trend alignment and controlled volatility/extension.
- `candidate35_pullback_continuation`: tests controlled pullbacks inside broader uptrends.
- `candidate35_breakout_confirmation`: tests near-high continuation with volume/momentum confirmation.
- `candidate35_regime_gated_momentum`: uses SPY/QQQ regime labels to tighten or relax momentum gates.
- `candidate35_low_volatility_compounder`: tests lower-volatility continuation behavior.

All Candidate 35 families are sandbox candidates only.

## Calibration Results

- Calibration matrix rows: 60.
- Split: 10 deterministic calibration samples.
- Candidate 34 and five Candidate 35 families were evaluated.
- No family was approved as policy from calibration alone.

## Validation Results

- Validation matrix rows: 30.
- Split: 10 deterministic validation samples.
- Validation was used to select only families worth holdout review.
- `candidate35_trend_quality` and `candidate35_pullback_continuation` reached validation review, but only `candidate35_trend_quality` survived to final holdout comparison.

## Holdout Results

Holdout rows: 2.

| family | holdout gate | worst ending | median ending | worst drawdown | median win rate | median 20d accuracy | median profit factor | failed gates |
|:--|:--|--:|--:|--:|--:|--:|--:|:--|
| `candidate34_frozen_baseline` | FAIL | 62.37 | 140.00 | -56.37% | 40.66% | 49.14% | 1.20 | worst ending, drawdown, win rate, 20d accuracy, worst trade loss, ex-best, profit factor |
| `candidate35_trend_quality` | FAIL | 196.23 | 245.77 | -49.09% | 51.55% | 63.48% | 1.51 | drawdown, win rate, theme concentration |

Interpretation:

- `candidate35_trend_quality` improved ending-value and 20d accuracy versus Candidate 34.
- It still failed holdout due to large drawdown, sub-52% median simulated win rate, and top-theme loss concentration above 50%.
- This is not sufficient for Phase 2, paper execution, or daily-scan adoption.

## Candidate 34 vs Candidate 35 Comparison

- Comparison rows: 18.
- Candidate 34 failed calibration, validation, and holdout.
- All Candidate 35 families also failed at least one split-level gate.
- `candidate35_trend_quality` was the strongest redesigned family by holdout ending-value and accuracy, but still failed the risk gates.
- `candidate35_low_volatility_compounder` reduced drawdown versus other families but failed ending-value and win-rate gates.
- `candidate35_pullback_continuation` had strong ending values but failed drawdown and win-rate gates.

## Rejected Decision Audit Summary

- Rejected audit rows: 74,961.
- Top rejection reasons:
  - `breakout_failed_near_high_or_momentum`: 10,689
  - `regime_failed_positive_momentum`: 9,649
  - `trend_quality_failed_sma_stack`: 8,937
  - `pullback_failed_broader_uptrend`: 8,323
  - `compounder_failed_low_volatility`: 8,193
  - `compounder_failed_quality_momentum`: 6,807
  - `pullback_failed_controlled_pullback`: 6,677
  - `trend_quality_failed_risk_bounds`: 6,063

The rejected-decision audit is diagnostic. It is not an instruction to loosen filters or create live trades.

## Phase 1G Status

- Status: `PHASE_1G_HOLDOUT_FAILED`
- Do not start Phase 2.
- Do not start Phase 3.
- Do not enable paper execution.
- Do not enable real-money execution.
- Do not mark Phoenix Nano as live-tradable.
- Do not adopt Candidate 35 as daily scan policy.
- Reason: the best redesigned family improved some metrics but still failed holdout risk gates.

## Problems

- Candidate 35 did not survive holdout.
- `candidate35_trend_quality` still had a worst holdout drawdown of -49.09%.
- `candidate35_trend_quality` median simulated win rate was 51.55%, below the 52% gate.
- `candidate35_trend_quality` top-theme loss share was 53.20%, above the 50% concentration gate.
- Candidate 34 remains unstable and is not suitable for execution.
- `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- yfinance data remains retail-grade research data, not an execution feed.

## Questions For GPT

- Should Phoenix Nano pause after Candidate 35 holdout failure instead of continuing iterative redesign?
- Should the next task focus on data/vendor quality and universe design before any more model/rule changes?
- Should GPT require lower drawdown before considering any future Candidate 36 sandbox?
- Should the rejected-decision audit be extended to include counterfactual PnL for rejected near-misses, or should it remain a pre-entry audit only?

## Next Suggested Tasks

- Do not start Phase 2.
- Do not start Phase 3.
- Do not enable paper execution.
- Do not enable real-money execution.
- Ask GPT whether to pause Nano research or authorize one clearly bounded Candidate 36 sandbox.
- If GPT authorizes another sandbox, require stricter drawdown and concentration gates before any discussion of promotion.
