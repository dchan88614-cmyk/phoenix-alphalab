# REPORT_TO_GPT

## Completed

- Executed the latest `TASKS.md`: Phoenix Nano Phase 1B - Last Month Daily Replay Validation.
- Added `--phase1b-last-month-replay` CLI flag.
- Added a Phase 1B last-month replay module that:
  - treats each replay date as an independent historical "today";
  - uses only same-date and prior EOD-derived factors for selection;
  - applies $100 whole-share affordability before ranking;
  - applies frozen Candidate 34 standards;
  - outputs exactly one daily decision: `HISTORICAL_BUY_CANDIDATE` or `HISTORICAL_NO_TRADE`;
  - records up to 5 closest executable near-misses on NO_TRADE days;
  - attaches 1d / 3d / 5d / 10d / 20d future verification only after the decision row is formed;
  - marks incomplete verification windows instead of inventing values.
- Adjusted Phase 1B data download behavior so the CLI replay range remains `--start` to `--end`, while post-range rows can be downloaded for verification windows.
- Generated required reports:
  - `data/reports/phase1b_last_month_daily_replay.csv`
  - `data/reports/phase1b_last_month_daily_replay.md`
  - `data/reports/phase1b_last_month_near_misses.csv`
- Did not start Phase 2.
- Did not start Phase 3.
- Did not enable paper execution.
- Did not enable real-money execution.
- Did not change daily scan production behavior.
- Did not produce financial advice or an operational recommendation.

## Files Changed

- `src/main.py`
- `src/research/phase1b_last_month_replay.py`
- `tests/test_phase1b_last_month_replay.py`
- `data/reports/phase1b_last_month_daily_replay.csv`
- `data/reports/phase1b_last_month_daily_replay.md`
- `data/reports/phase1b_last_month_near_misses.csv`
- `REPORT_TO_GPT.md`

## How To Run

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2026-06-01 --end 2026-06-30 --phase1b-last-month-replay
```

## Test Results

```bash
.venv/bin/python -m pytest tests/test_phase1b_last_month_replay.py -q
# 5 passed
```

```bash
.venv/bin/python -m pytest -q
# 205 passed, 1 warning in 31.37s
```

Remaining warning:

- macOS LibreSSL / urllib3 warning from the local Python environment.

The required Phase 1B CLI completed successfully and wrote all required reports.

## Last Month Replay Summary

- Date range: 2026-06-01 to 2026-06-30
- Total trading days: 21
- BUY count: 3
- NO_TRADE count: 18
- Selected tickers:
  - 2026-06-01: HPE
  - 2026-06-03: RIVN
  - 2026-06-23: BEAM

## Accuracy By Window

Accuracy is calculated only on BUY candidates with complete data for that window.

| window | complete BUY rows | accuracy | average return | median return |
|---|---:|---:|---:|---:|
| 1d | 3 | 66.67% | 6.92% | 2.11% |
| 3d | 3 | 66.67% | 3.75% | 4.85% |
| 5d | 3 | 66.67% | -3.24% | 3.37% |
| 10d | 2 | 50.00% | -3.35% | -3.35% |
| 20d | 2 | 50.00% | 0.45% | 0.45% |

## Best Pick

- 2026-06-03 RIVN: 20d return 4.93%

## Worst Pick

- 2026-06-01 HPE: 20d return -4.02%

## Top Repeated Tickers

- HPE: 1
- RIVN: 1
- BEAM: 1

## Near-Miss Lessons

- Near-misses that later performed well: none with complete positive 20d return.
- Near-misses that failed badly:
  - 2026-06-02 BBAI: -28.77%
  - 2026-06-02 CORZ: -18.38%
  - 2026-06-02 F: -15.54%
  - 2026-06-02 PATH: -5.17%
  - 2026-06-02 RIVN: -0.64%

## What Should Be Adjusted Next

- Do not loosen Candidate 34 from this one-month result alone.
- Review why 18 of 21 trading days were NO_TRADE before adding any new complexity.
- Investigate whether the June 2 near-miss cluster shows a useful rejection pattern or just broad weakness.
- Wait for more complete 20d data for BEAM before treating June's full-month replay as final.

## Problems

- One selected BUY candidate, BEAM on 2026-06-23, does not yet have complete 10d or 20d verification data in the downloaded history.
- Some watchlist symbols were rejected by existing universe rules or incomplete metadata, including the yfinance metadata failure for BITF.
- This remains yfinance-based research data, not independently credentialed vendor validation.

## Questions For GPT

- Should Phase 1B be rerun after BEAM has complete 20d verification?
- Should GPT ask Codex to analyze the June 2 near-miss failures before changing Candidate 34?
- Should the next task stay on historical validation until independent vendor credentials are available?

## Next Suggested Tasks

- Rerun Phase 1B after all June BUY candidates have complete 20d outcomes.
- Add a local independent vendor credential and rerun Phase 1N / Phase 1M data-readiness gates.
- Do not start Phase 2.
- Do not start Phase 3.
- Do not enable paper execution.
- Do not enable real-money execution.
