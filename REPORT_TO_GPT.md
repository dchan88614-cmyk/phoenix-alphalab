# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1C - Robustness Failure Analysis and Close-Stop Realism.
- Added Phase 1C robustness analysis without changing Candidate 34 entry thresholds.
- Kept each replay sample's selected ticker/date decisions frozen.
- Built a 10-sample policy robustness matrix across 8 execution policies.
- Added close-stop realism checks for intraday stop breaches, next-open stop exits, and hybrid catastrophic stops.
- Added failing-sample losing trade extraction.
- Added period/theme regime attribution using a deterministic local theme map.
- Added CLI flag:
  - `--phase1c-robustness-analysis`
- Created required outputs:
  - `data/reports/phase1c_policy_robustness_matrix.csv`
  - `data/reports/phase1c_sample_failure_trades.csv`
  - `data/reports/phase1c_close_stop_realism.csv`
  - `data/reports/phase1c_regime_attribution.csv`
  - `data/reports/phase1c_robustness_summary.md`
- Did not adopt `close_based_stop_2_0x` as a real policy.
- Did not start Phase 2.
- Did not start Phase 3.
- Did not start paper trading.
- Did not start live trading.

## Files Changed

- `src/research/phase1c_robustness.py`
- `src/main.py`
- `tests/test_phase1c_robustness.py`
- `data/reports/phase1c_policy_robustness_matrix.csv`
- `data/reports/phase1c_sample_failure_trades.csv`
- `data/reports/phase1c_close_stop_realism.csv`
- `data/reports/phase1c_regime_attribution.csv`
- `data/reports/phase1c_robustness_summary.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1c-robustness-analysis --replay-rounds 100 --replay-sample-count 10
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_phase1c_robustness.py -q
# 10 passed in 1.78s
```

```bash
.venv/bin/python -m pytest -q
# 97 passed, 1 warning in 3.63s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --phase1c-robustness-analysis --replay-rounds 100 --replay-sample-count 10
```

## Phase 1C Robustness Summary

- Samples tested: 10
- Policies tested per sample: 8
- Policy matrix rows: 80
- Failing-sample losing trade rows: 165
- Close-stop realism rows: 340
- Regime attribution rows: 1774
- Phase 1C status: `PHASE_1C_EXECUTION_HYPOTHESIS_NEEDS_REALISM_WORK`

## Policy Robustness Matrix Summary

| policy | median ending value | worst ending value | median max drawdown | worst max drawdown | median trade accuracy | passing samples |
|:--|--:|--:|--:|--:|--:|--:|
| baseline_current | $185.82 | $43.16 | -37.27% | -64.14% | 42.65% | 2 |
| close_based_stop_2_0x | $175.10 | $41.19 | -42.37% | -67.06% | 51.92% | 3 |
| close_based_stop_2_0x_with_intraday_breach_flag | $175.10 | $41.19 | -42.37% | -67.06% | 51.92% | 3 |
| hybrid_close_stop_2_0x_intraday_catastrophic_3_0x | $154.15 | $30.52 | -48.95% | -71.05% | 51.92% | 2 |
| close_confirmed_stop_2_0x_next_open_exit | $144.08 | $35.44 | -58.18% | -71.59% | 49.00% | 1 |
| atr_stop_2_5x | $131.42 | $34.37 | -51.81% | -68.99% | 49.91% | 2 |
| atr_stop_2_0x | $118.77 | $34.11 | -48.58% | -70.27% | 40.74% | 1 |
| time_exit_20d_no_intraday_stop | $101.64 | $15.16 | -66.73% | -84.84% | 47.21% | 0 |

## Best Policies

- Best policy by median ending account value: `baseline_current`
- Best realistic policy after intraday-breach penalties: `baseline_current`
- `close_based_stop_2_0x` did not remain robust after 10-sample and realism checks.

## Passing Sample Count Per Policy

- `close_based_stop_2_0x`: 3
- `close_based_stop_2_0x_with_intraday_breach_flag`: 3
- `baseline_current`: 2
- `atr_stop_2_5x`: 2
- `hybrid_close_stop_2_0x_intraday_catastrophic_3_0x`: 2
- `atr_stop_2_0x`: 1
- `close_confirmed_stop_2_0x_next_open_exit`: 1
- `time_exit_20d_no_intraday_stop`: 0

## Worst Sample Per Policy

- `baseline_current`: sample 4, ending value $43.16, max drawdown -64.14%.
- `close_based_stop_2_0x`: sample 3, ending value $41.19, max drawdown -60.38%.
- `close_confirmed_stop_2_0x_next_open_exit`: sample 3, ending value $35.44, max drawdown -71.59%.
- `hybrid_close_stop_2_0x_intraday_catastrophic_3_0x`: sample 3, ending value $30.52, max drawdown -71.05%.
- `time_exit_20d_no_intraday_stop`: sample 4, ending value $15.16, max drawdown -84.84%.

## Sample 3 And 4 Failure Explanation

- Failing trades concentrated in tickers including SMR, BBAI, F, INTC, CCJ, AFRM, HPE, and HOOD.
- Theme counts among captured failures included unmapped high-volatility names, EV/mobility, space/defense/nuclear, crypto-adjacent/high beta, and AI/software.
- Average entry gap among captured failing trades was about 0.50%, so bad entry gaps alone do not explain the failures.
- Evidence points to entry-rule weakness in multiple deterministic samples, not just execution-rule weakness.

## Close-Stop Realism Findings

- Close-stop realism rows: 340
- Intraday breaches ignored by close-stop candidates: 223
- Realism warnings: 234
- Warning mix:
  - `CLOSE_STOP_REQUIRES_NEXT_OPEN_SLIPPAGE`: 84
  - `POLICY_TOO_OPTIMISTIC_FOR_RESEARCH_GATE`: 83
  - `INTRADAY_STOP_BREACH_IGNORED_BY_CLOSE_STOP`: 56
  - `GAP_BEYOND_STOP`: 11
- Conclusion: `close_based_stop_2_0x` remains a hypothesis, but it is not realistic enough to use as a research gate without additional validation.

## Regime And Theme Attribution

- Worst period-policy rows included 2025-10, 2025-06, and other mid/late-2025 periods.
- Worst period examples:
  - sample 1 / 2025-10 / `time_exit_20d_no_intraday_stop` / BBAI: -$142.60
  - sample 0 / 2025-06 / `hybrid_close_stop_2_0x_intraday_catastrophic_3_0x` / CORZ: -$122.20
  - sample 0 / 2025-06 / `close_based_stop_2_0x` / RKLB: -$113.04
- Local deterministic theme mapping was used; no external lookup was used.

## Phase 1C Status

- Status: `PHASE_1C_EXECUTION_HYPOTHESIS_NEEDS_REALISM_WORK`
- Reason: close-based policies can look good in some samples, but realism checks show many intraday breaches and next-open slippage risks. Multiple deterministic samples still fail badly.
- Not approved for Phase 2.
- Not approved for paper trading.
- Not approved for live trading.

## Problems

- No policy delivered robust performance across all 10 deterministic samples.
- Worst-sample ending values were below $100 for every policy.
- Worst-sample max drawdowns were worse than -45% for every policy.
- Close-based stop variants produced many intraday breach warnings.
- Several weak samples appear to need entry-rule work, not just exit-policy tuning.
- yfinance metadata rejected several watchlist tickers; `BITF` emitted a yfinance 404 and was rejected as metadata incomplete.
- Existing pandas `pct_change` future warnings appeared during the end-to-end run; they did not block execution.
- yfinance data remains non-institutional retail data and should not be treated as an execution feed.

## Questions For GPT

- Should Phase 1D focus on entry-rule robustness rather than exit-policy variants?
- Should Candidate 34 be stress-tested by excluding unmapped/high-volatility themes that dominate failing samples?
- Should close-based stops be removed from gate consideration until next-open slippage modeling is stronger?
- Should GPT require worst-sample ending value above $100 before any Phase 2 discussion?

## Next Suggested Tasks

- Do not start Phase 2.
- Do not start Phase 3.
- Do not start paper trading.
- Build Phase 1D entry-rule failure analysis for samples 3 and 4.
- Add a stricter filter or diagnostic for repeated high-volatility theme losses before any threshold loosening.
