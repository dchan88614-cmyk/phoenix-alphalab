# Phoenix Nano Phase 1B Last Month Daily Replay Validation

Research-only historical replay. This does not start Phase 2, Phase 3, paper execution, or live execution.

## Replay Range

- Date range: 2026-06-01 to 2026-06-30
- Total trading days tested: 21
- BUY candidate count: 3
- NO_TRADE count: 18

## Daily Decisions

| replay_date   | decision                 | ticker   | reason                                                                         |
|:--------------|:-------------------------|:---------|:-------------------------------------------------------------------------------|
| 2026-06-01    | HISTORICAL_BUY_CANDIDATE | HPE      | Candidate 34 Nano rule passed with replay-date $100 whole-share affordability. |
| 2026-06-02    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-03    | HISTORICAL_BUY_CANDIDATE | RIVN     | Candidate 34 Nano rule passed with replay-date $100 whole-share affordability. |
| 2026-06-04    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-05    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-08    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-09    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-10    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-11    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-12    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-15    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-16    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-17    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-18    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-22    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-23    | HISTORICAL_BUY_CANDIDATE | BEAM     | Candidate 34 Nano rule passed with replay-date $100 whole-share affordability. |
| 2026-06-24    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-25    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-26    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-29    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |
| 2026-06-30    | HISTORICAL_NO_TRADE      |          | NO_CANDIDATE_PASSED_RULES                                                      |

## BUY Candidate Accuracy

- 1d accuracy: 66.67%
- 1d average return: 6.92%
- 1d median return: 2.11%
- 3d accuracy: 66.67%
- 3d average return: 3.75%
- 3d median return: 4.85%
- 5d accuracy: 66.67%
- 5d average return: -3.24%
- 5d median return: 3.37%
- 10d accuracy: 50.00%
- 10d average return: -3.35%
- 10d median return: -3.35%
- 20d accuracy: 50.00%
- 20d average return: 0.45%
- 20d median return: 0.45%

## Best And Worst

- Best selected stock: 2026-06-03 RIVN 20d=4.93%
- Worst selected stock: 2026-06-01 HPE 20d=-4.02%
- Most repeated selected tickers: HPE:1, RIVN:1, BEAM:1

## Near Miss Lessons

- Near-misses that later performed well: none
- Near-misses that failed badly: 2026-06-02 BBAI 20d=-28.77%, 2026-06-02 CORZ 20d=-18.38%, 2026-06-02 F 20d=-15.54%, 2026-06-02 PATH 20d=-5.17%, 2026-06-02 RIVN 20d=-0.64%

## Short Conclusion

The completed BUY candidates did not exceed a 50% positive 20d accuracy bar, so the month argues for caution before any further strategy expansion.
