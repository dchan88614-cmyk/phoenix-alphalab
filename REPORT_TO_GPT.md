# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1B - Execution Risk, Stop-Out, and Drawdown Diagnostics.
- Built a Phase 1B diagnostic layer over the existing Phase 1A replay selection.
- Kept the selected ticker/date set fixed for execution-policy analysis.
- Added baseline trade diagnostics for each `HISTORICAL_BUY_CANDIDATE`.
- Added exit policy comparison across baseline, wider ATR stops, time-only exit, and close-based stop variants.
- Added ticker-level risk attribution.
- Added drawdown attribution for the worst peak-to-trough period.
- Added deterministic multi-sample robustness using `--replay-sample-count 5`.
- Added CLI flags:
  - `--phase1b-execution-diagnostics`
  - `--replay-sample-offset`
  - `--replay-sample-count`
- Created required outputs:
  - `data/reports/phase1b_execution_diagnostics.csv`
  - `data/reports/phase1b_execution_summary.md`
  - `data/reports/phase1b_exit_policy_comparison.csv`
  - `data/reports/phase1b_ticker_risk_attribution.csv`
- Did not change Candidate 34 entry thresholds.
- Did not start Phase 2.
- Did not start Phase 3.
- Did not start paper trading.
- Did not start live trading.

## Files Changed

- `src/research/execution_diagnostics.py`
- `src/research/historical_replay.py`
- `src/main.py`
- `tests/test_execution_diagnostics.py`
- `data/reports/phase1b_execution_diagnostics.csv`
- `data/reports/phase1b_execution_summary.md`
- `data/reports/phase1b_exit_policy_comparison.csv`
- `data/reports/phase1b_ticker_risk_attribution.csv`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1b-execution-diagnostics --replay-rounds 100 --replay-sample-count 5
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_execution_diagnostics.py -q
# 9 passed in 0.77s
```

```bash
.venv/bin/python -m pytest -q
# 87 passed, 1 warning in 2.09s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1b-execution-diagnostics --replay-rounds 100 --replay-sample-count 5
```

## Phase 1B Execution Diagnostic Summary

Baseline Phase 1A recap:

- Replay rounds: 100
- BUY count: 34
- NO_TRADE count: 66
- 20d accuracy: 58.82%
- Baseline ending account value: $179.61
- Baseline max drawdown: -45.86%
- Baseline trade-simulation accuracy: 41.18%

Core execution finding:

- Stopped-out-then-20d-positive count: 7
- Baseline stopped trades: 20
- Stopped trades later 20d-positive: 35.00% of stopped baseline trades
- Stopped-out-then-20d-positive as share of all BUYs: 20.59%

## Exit Policy Comparison

| policy | ending value | max drawdown | trade accuracy | profit factor | stop count |
|:--|--:|--:|--:|--:|--:|
| baseline_current | $179.61 | -45.86% | 41.18% | 1.2969 | 20 |
| atr_stop_1_5x | $179.61 | -45.86% | 41.18% | 1.2969 | 20 |
| atr_stop_2_0x | $243.89 | -52.45% | 44.44% | 1.4193 | 14 |
| atr_stop_2_5x | $294.54 | -36.41% | 52.00% | 1.5914 | 10 |
| atr_stop_3_0x | $174.65 | -64.76% | 50.00% | 1.2148 | 9 |
| time_exit_20d_no_intraday_stop | $232.74 | -45.35% | 57.89% | 1.5877 | 0 |
| close_based_stop_1_5x | $244.41 | -47.21% | 43.33% | 1.4655 | 16 |
| close_based_stop_2_0x | $483.59 | -31.46% | 53.85% | 2.0137 | 11 |

Best diagnostic policy, if any:

- Best diagnostic policy by ending value with max drawdown better than -35%: `close_based_stop_2_0x`
- Baseline vs best-policy ending account value: $179.61 vs $483.59
- Baseline vs best-policy max drawdown: -45.86% vs -31.46%
- Baseline vs best-policy trade-simulation accuracy: 41.18% vs 53.85%
- This is diagnostic only. It is not an adopted execution policy.

## Drawdown Attribution

- Biggest equity drawdown period: 2025-05-16 to 2026-03-30
- Worst drawdown: -45.86%
- Trades inside worst drawdown included RKLB, CORZ, JOBY, INTC, RIVN, BBAI, PATH, SOFI, F, and HPE.
- Ending value excluding best trade: $135.42
- Removing the single best trade leaves ending account value above $105: true
- Max drawdown excluding worst trade: -40.45%
- Removing the single worst trade improves max drawdown above -35%: false

## Ticker Concentration Findings

- Top ticker profit share: 16.36%
- Top ticker loss share: 15.88%
- Any one ticker contributes more than 50% of total profit: false
- Any one ticker contributes more than 50% of total loss: false
- Biggest positive contributor: HOOD, total pnl $56.89.
- Biggest negative contributor: RKLB, total pnl -$42.60.

## Robustness Across Samples

| sample | BUY count | 20d accuracy | baseline ending value | baseline max drawdown | baseline trade accuracy | best alternative policy | any policy passed Phase 1B gates |
|--:|--:|--:|--:|--:|--:|:--|:--|
| 0 | 34 | 58.82% | $179.61 | -45.86% | 41.18% | close_based_stop_2_0x | true |
| 1 | 34 | 52.94% | $325.24 | -27.04% | 58.82% | close_based_stop_2_0x | true |
| 2 | 36 | 58.33% | $287.06 | -34.77% | 50.00% | baseline_current | true |
| 3 | 38 | 52.63% | $60.49 | -61.50% | 28.95% | none | false |
| 4 | 32 | 43.75% | $43.16 | -64.14% | 25.81% | none | false |

## Phase 1B Status

- Status: `PHASE_1B_EXECUTION_POLICY_PROMISING_NOT_APPROVED`
- Reason: at least one diagnostic policy improved ending value, drawdown, trade-simulation accuracy, and concentration gates on the baseline sample.
- Not approved for Phase 2.
- Not approved for paper trading.
- Not approved for live trading.

## Problems

- Robustness is mixed: samples 3 and 4 failed badly even though samples 0-2 had promising policies.
- `close_based_stop_2_0x` may be optimistic because close-based stops can hide intraday stop risk.
- `time_exit_20d_no_intraday_stop` improved trade accuracy but still had large drawdown.
- Some improvements come from changing exit assumptions, not from proving the entry signal is stable across all samples.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- Existing pandas `pct_change` future warnings appeared during the end-to-end run; they did not block execution.
- yfinance data remains non-institutional retail data and should not be treated as an execution feed.

## Questions For GPT

- Should Phase 1C focus on close-based stop realism, next-open gap risk, or sample robustness first?
- Should `close_based_stop_2_0x` be treated only as a hypothesis to test, not as a candidate policy?
- Should samples 3 and 4 block any Phase 2 consideration until the entry rule is more robust?
- Should GPT require all deterministic samples to pass before manual paper validation?

## Next Suggested Tasks

- Do not start Phase 2 yet.
- Do not start Phase 3.
- Do not start paper trading.
- Run Phase 1C to stress-test the `close_based_stop_2_0x` hypothesis against stricter intraday assumptions.
- Add sample-level failure analysis for samples 3 and 4 before changing Candidate 34 thresholds.
