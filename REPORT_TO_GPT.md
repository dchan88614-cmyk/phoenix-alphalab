# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1H - Trend-Quality Risk Overlay and Drawdown Compression.
- Added a historical research-only Phase 1H risk overlay sandbox.
- Froze Candidate 34 as `candidate34_frozen_baseline`.
- Froze Phase 1G Candidate 35 trend-quality as `candidate35_trend_quality_frozen`.
- Added the requested CLI flag:
  - `--phase1h-risk-overlay-sandbox`
- Added pre-declared overlay families only:
  - `overlay_market_regime_risk_off_skip`
  - `overlay_high_volatility_tail_skip`
  - `overlay_theme_loss_cooldown`
  - `overlay_ticker_loss_cooldown`
  - `overlay_combined_conservative`
- Used deterministic 30-sample split:
  - calibration: samples 0-9
  - validation: samples 10-19
  - holdout: samples 20-29
- Added excluded-trade counterfactuals, drawdown compression attribution, and theme concentration audit.
- Created required outputs:
  - `data/reports/phase1h_overlay_definitions.md`
  - `data/reports/phase1h_overlay_calibration_matrix.csv`
  - `data/reports/phase1h_overlay_validation_matrix.csv`
  - `data/reports/phase1h_overlay_holdout_results.csv`
  - `data/reports/phase1h_candidate34_vs_35_vs_overlay.csv`
  - `data/reports/phase1h_drawdown_compression_attribution.csv`
  - `data/reports/phase1h_theme_concentration_audit.csv`
  - `data/reports/phase1h_excluded_trade_counterfactual.csv`
  - `data/reports/phase1h_risk_overlay_summary.md`
- Did not start Phase 2.
- Did not start Phase 3.
- Did not enable paper execution.
- Did not enable real-money execution.
- Did not change daily scan production behavior.
- Did not loosen Candidate 34 thresholds.
- Did not adopt Candidate 35 or any overlay as active policy.
- Did not produce financial advice or an operational recommendation.

## Files Changed

- `src/main.py`
- `src/research/phase1h_risk_overlay.py`
- `tests/test_phase1h_risk_overlay.py`
- `data/reports/phase1h_overlay_definitions.md`
- `data/reports/phase1h_overlay_calibration_matrix.csv`
- `data/reports/phase1h_overlay_validation_matrix.csv`
- `data/reports/phase1h_overlay_holdout_results.csv`
- `data/reports/phase1h_candidate34_vs_35_vs_overlay.csv`
- `data/reports/phase1h_drawdown_compression_attribution.csv`
- `data/reports/phase1h_theme_concentration_audit.csv`
- `data/reports/phase1h_excluded_trade_counterfactual.csv`
- `data/reports/phase1h_risk_overlay_summary.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1h-risk-overlay-sandbox --replay-rounds 100 --replay-sample-count 30
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_phase1h_risk_overlay.py -q
# 8 passed
```

```bash
.venv/bin/python -m pytest -q
# 141 passed, 1 warning in 23.14s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1h-risk-overlay-sandbox --replay-rounds 100 --replay-sample-count 30
```

## Phase 1H Risk Overlay Summary

- Summary file starts with the required heading:
  - `PHOENIX NANO PHASE 1H — TREND-QUALITY RISK OVERLAY AND DRAWDOWN COMPRESSION`
- Final status: `PHASE_1H_HOLDOUT_FAILED`
- The best overlay promoted to holdout was `overlay_ticker_loss_cooldown_8pct_15`.
- No overlay was adopted as active policy.
- No overlay is approved for paper execution or real-money execution.

## Baseline Reproducibility Check

- Candidate 34 was re-run as `candidate34_frozen_baseline`.
- Candidate 35 trend-quality was re-run as `candidate35_trend_quality_frozen`.
- Candidate 35 trend-quality core entry rules, ranking, and baseline exit policy were not changed.
- QQQ was downloaded for Phase 1H market regime context.

## Candidate 34 Baseline Results

Holdout:

- sample count: 10
- minimum BUY count: 29
- median BUY count: 32.0
- worst ending account value: 59.30
- median ending account value: 136.88
- worst max drawdown: -59.92%
- median simulated win rate: 39.92%
- median 20d accuracy: 50.00%
- median profit factor: 1.18
- status: FAIL

Candidate 34 remains unstable and not suitable for execution.

## Candidate 35 Trend-Quality Baseline Results

Holdout:

- sample count: 10
- minimum BUY count: 88
- median BUY count: 89.5
- worst ending account value: 191.39
- median ending account value: 237.40
- worst max drawdown: -49.09%
- median simulated win rate: 51.55%
- median 20d accuracy: 63.07%
- median profit factor: 1.51
- failed gates:
  - worst drawdown <= -35%
  - median win rate < 52%
  - top theme loss share > 45%

Trend-quality remains directionally better than Candidate 34, but it still fails risk gates.

## Overlay Calibration Results

- Calibration matrix rows: 230.
- Calibration evaluated Candidate 34, Candidate 35 trend-quality, standalone overlays, cooldown parameter grids, and combined conservative overlay.
- The strongest calibration behavior came from volatility/ticker cooldown variants that compressed drawdown in some samples.
- Calibration did not approve any policy; it only selected candidates for validation.

## Overlay Validation Results

- Validation matrix rows: 50.
- Validation evaluated frozen baselines plus promoted overlays.
- At most one final overlay policy was promoted to holdout.
- Final promoted overlay: `overlay_ticker_loss_cooldown_8pct_15`.

## Overlay Holdout Results

Holdout rows: 3.

| policy | gate | min BUY | median BUY | worst ending | median ending | worst drawdown | median win rate | median 20d accuracy | median PF | failed gates |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| `candidate34_frozen_baseline` | FAIL | 29 | 32.0 | 59.30 | 136.88 | -59.92% | 39.92% | 50.00% | 1.18 | overfilter/min BUY, ending, drawdown, win rate, accuracy, PF, worst trade, ticker concentration, ex-best |
| `candidate35_trend_quality_frozen` | FAIL | 88 | 89.5 | 191.39 | 237.40 | -49.09% | 51.55% | 63.07% | 1.51 | drawdown, win rate, theme concentration |
| `overlay_ticker_loss_cooldown_8pct_15` | FAIL | 78 | 83.0 | 197.65 | 237.30 | -46.04% | 51.17% | 63.82% | 1.64 | drawdown, win rate, theme concentration, missed winners >= avoided losers |

Interpretation:

- The overlay improved some risk/accuracy metrics versus frozen trend-quality.
- It did not reduce drawdown enough.
- It did not improve win rate enough.
- It did not reduce top-theme loss concentration enough.
- Excluded-trade counterfactuals show winner dollars missed were greater than loser dollars avoided.

## Drawdown Compression Attribution

- Drawdown attribution rows: 690.
- The best holdout overlay reduced worst holdout drawdown from -49.09% to -46.04%.
- This is not enough to pass the -35% drawdown gate.
- Drawdown compression appears partial and sample-path dependent, not a sufficient risk fix.

## Theme Concentration Audit

- Theme concentration audit rows: 5,601.
- Candidate 35 trend-quality still failed top-theme loss concentration.
- The promoted ticker cooldown overlay also failed the top-theme loss concentration gate.
- Phase 1H did not prove top-theme loss concentration can be reduced below the required 45% level without missing too many winners.

## Excluded Trade Counterfactual Summary

- Excluded trade counterfactual rows: 8,571.
- For the promoted holdout overlay, excluded winner dollars missed were greater than excluded loser dollars avoided.
- This means the overlay did not pass the required true-loss-avoidance test.
- Skipped trades are diagnostic only and are not an instruction to loosen or activate filters.

## BUY Count / NO_TRADE Count / BUY Rate

Holdout:

- Candidate 34:
  - median BUY count: 32.0
  - median NO_TRADE count: 68.0
  - median BUY rate: 32.0%
- Candidate 35 trend-quality:
  - median BUY count: 89.5
  - median NO_TRADE count: 10.5
  - median BUY rate: 89.5%
- Promoted overlay:
  - median BUY count: 83.0
  - median NO_TRADE count: 17.0
  - median BUY rate: 83.0%

## Accuracy: 1d / 3d / 5d / 10d / 20d

The output matrices include all requested accuracy columns:

- `accuracy_1d`
- `accuracy_3d`
- `accuracy_5d`
- `accuracy_10d`
- `accuracy_20d`

Promoted overlay holdout median 20d accuracy: 63.82%.

## Trade-Simulation Accuracy

- Candidate 34 holdout median simulated win rate: 39.92%.
- Candidate 35 trend-quality holdout median simulated win rate: 51.55%.
- Promoted overlay holdout median simulated win rate: 51.17%.
- The promoted overlay did not pass the 52% win-rate gate.

## Account Ending Value

- Candidate 34 holdout median ending account value: 136.88.
- Candidate 35 trend-quality holdout median ending account value: 237.40.
- Promoted overlay holdout median ending account value: 237.30.
- The overlay did not materially improve median ending value versus trend-quality.

## Max Drawdown

- Candidate 34 worst holdout drawdown: -59.92%.
- Candidate 35 trend-quality worst holdout drawdown: -49.09%.
- Promoted overlay worst holdout drawdown: -46.04%.
- The promoted overlay still failed the -35% gate.

## Profit Factor

- Candidate 34 holdout median profit factor: 1.18.
- Candidate 35 trend-quality holdout median profit factor: 1.51.
- Promoted overlay holdout median profit factor: 1.64.
- Profit factor improved but did not override drawdown, win-rate, concentration, and counterfactual failures.

## Worst Trade Loss

- Candidate 34 failed the worst-trade loss gate.
- Candidate 35 trend-quality and the promoted overlay did not make the system execution-ready because other risk gates failed.
- Worst trade loss remains tracked in `phase1h_overlay_holdout_results.csv`.

## Top Ticker/Theme Contribution Shares

- Candidate 34 failed ticker concentration.
- Candidate 35 trend-quality failed theme concentration.
- Promoted overlay failed theme concentration.
- The overlay did not solve concentration risk.

## Phase 1H Status

- Status: `PHASE_1H_HOLDOUT_FAILED`
- Do not start Phase 2.
- Do not start Phase 3.
- Do not enable paper execution.
- Do not enable real-money execution.
- Do not mark Phoenix Nano as live-tradable.
- Do not adopt Candidate 35 or any overlay as active policy.
- Reason: the best overlay still failed holdout risk gates and failed the excluded-trade counterfactual requirement.

## Problems

- Full 30-sample Phase 1H completed, but no overlay passed holdout.
- The promoted overlay reduced drawdown only modestly.
- Excluded-trade counterfactuals showed too many missed winners relative to avoided losers.
- yfinance metadata rejected several watchlist tickers.
- `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- `HUT` had a yfinance download error in this run, so no HUT price data was included in the generated dataset.
- yfinance data remains retail-grade research data, not an execution feed.

## Questions For GPT

- Should Phoenix Nano pause after Phase 1H instead of continuing rule/overlay iteration?
- Should the next task focus on data quality, vendor validation, and universe design before any more candidate logic?
- Should GPT retire the current Nano direction if trend-quality plus risk overlays cannot pass drawdown and concentration gates?
- Should future overlays require a stronger excluded-loss-dollars test before validation promotion?

## Next Suggested Tasks

- Do not start Phase 2.
- Do not start Phase 3.
- Do not enable paper execution.
- Do not enable real-money execution.
- Ask GPT whether to pause Phoenix Nano research.
- If GPT continues research, prioritize data/universe quality over another threshold or overlay sweep.
