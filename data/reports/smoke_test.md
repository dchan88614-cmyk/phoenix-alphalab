# Phoenix AlphaLab Smoke Test

## Research Mode

- Factor timing: EOD
- Ranking rule: simple average percentile score across previous-window factors.
- Ranking factors: relative_volume_prev20, return_5d, return_20d, distance_to_52w_high_prev, dollar_volume
- Excluded from ranking: forward returns, market cap, news, SEC data, short interest, AI scores.
- Benchmark: SPY

## Test Range

- Start date: 2026-03-05
- End date: 2026-05-29
- Signal days: 60
- Selected rows: 240

## Summary

|   horizon_days | avg_return   | avg_excess_return   | win_rate   |   days_outperformed_spy |   eligible_days |
|---------------:|:-------------|:--------------------|:-----------|------------------------:|----------------:|
|              5 | 1.84%        | 0.93%               | 57.92%     |                      31 |              60 |
|             10 | 2.77%        | 0.97%               | 56.25%     |                      37 |              60 |
|             20 | 4.86%        | 0.76%               | 54.58%     |                      31 |              60 |

## Best And Worst

- Best trade (20d): 2026-05-04 SMCI 79.69%
- Worst trade (20d): 2026-05-29 SMCI -38.92%

## Initial Judgment

Yes, initial smoke test shows enough relative strength to keep researching.

## Daily Top 5

| date       | top_5                  |
|:-----------|:-----------------------|
| 2026-03-05 | NVDA, PLTR, AAPL, SMCI |
| 2026-03-06 | PLTR, NVDA, AAPL, SMCI |
| 2026-03-09 | NVDA, PLTR, AAPL, SMCI |
| 2026-03-10 | NVDA, PLTR, AAPL, SMCI |
| 2026-03-11 | NVDA, AAPL, PLTR, SMCI |
| 2026-03-12 | PLTR, NVDA, AAPL, SMCI |
| 2026-03-13 | NVDA, AAPL, PLTR, SMCI |
| 2026-03-16 | NVDA, SMCI, AAPL, PLTR |
| 2026-03-17 | NVDA, PLTR, AAPL, SMCI |
| 2026-03-18 | NVDA, AAPL, PLTR, SMCI |
| 2026-03-19 | AAPL, PLTR, NVDA, SMCI |
| 2026-03-20 | AAPL, NVDA, PLTR, SMCI |
| 2026-03-23 | AAPL, PLTR, NVDA, SMCI |
| 2026-03-24 | AAPL, PLTR, NVDA, SMCI |
| 2026-03-25 | AAPL, NVDA, PLTR, SMCI |
| 2026-03-26 | AAPL, NVDA, PLTR, SMCI |
| 2026-03-27 | AAPL, NVDA, PLTR, SMCI |
| 2026-03-30 | AAPL, NVDA, PLTR, SMCI |
| 2026-03-31 | NVDA, AAPL, PLTR, SMCI |
| 2026-04-01 | AAPL, NVDA, PLTR, SMCI |
| 2026-04-02 | AAPL, NVDA, PLTR, SMCI |
| 2026-04-06 | AAPL, NVDA, PLTR, SMCI |
| 2026-04-07 | AAPL, NVDA, PLTR, SMCI |
| 2026-04-08 | AAPL, NVDA, PLTR, SMCI |
| 2026-04-09 | NVDA, AAPL, PLTR, SMCI |
| 2026-04-10 | NVDA, AAPL, PLTR, SMCI |
| 2026-04-13 | NVDA, AAPL, PLTR, SMCI |
| 2026-04-14 | NVDA, AAPL, PLTR, SMCI |
| 2026-04-15 | NVDA, AAPL, PLTR, SMCI |
| 2026-04-16 | NVDA, AAPL, PLTR, SMCI |
| 2026-04-17 | NVDA, AAPL, PLTR, SMCI |
| 2026-04-20 | NVDA, AAPL, SMCI, PLTR |
| 2026-04-21 | AAPL, NVDA, PLTR, SMCI |
| 2026-04-22 | AAPL, NVDA, PLTR, SMCI |
| 2026-04-23 | AAPL, NVDA, PLTR, SMCI |
| 2026-04-24 | NVDA, AAPL, SMCI, PLTR |
| 2026-04-27 | NVDA, AAPL, PLTR, SMCI |
| 2026-04-28 | NVDA, AAPL, SMCI, PLTR |
| 2026-04-29 | NVDA, AAPL, SMCI, PLTR |
| 2026-04-30 | NVDA, AAPL, SMCI, PLTR |
| 2026-05-01 | AAPL, NVDA, PLTR, SMCI |
| 2026-05-04 | AAPL, NVDA, PLTR, SMCI |
| 2026-05-05 | AAPL, SMCI, NVDA, PLTR |
| 2026-05-06 | NVDA, AAPL, SMCI, PLTR |
| 2026-05-07 | NVDA, SMCI, AAPL, PLTR |
| 2026-05-08 | NVDA, AAPL, SMCI, PLTR |
| 2026-05-11 | NVDA, SMCI, AAPL, PLTR |
| 2026-05-12 | NVDA, AAPL, SMCI, PLTR |
| 2026-05-13 | NVDA, AAPL, PLTR, SMCI |
| 2026-05-14 | NVDA, AAPL, SMCI, PLTR |
| 2026-05-15 | NVDA, AAPL, PLTR, SMCI |
| 2026-05-18 | NVDA, AAPL, PLTR, SMCI |
| 2026-05-19 | AAPL, NVDA, PLTR, SMCI |
| 2026-05-20 | AAPL, NVDA, SMCI, PLTR |
| 2026-05-21 | AAPL, NVDA, PLTR, SMCI |
| 2026-05-22 | AAPL, SMCI, NVDA, PLTR |
| 2026-05-26 | AAPL, NVDA, SMCI, PLTR |
| 2026-05-27 | AAPL, NVDA, SMCI, PLTR |
| 2026-05-28 | AAPL, SMCI, PLTR, NVDA |
| 2026-05-29 | SMCI, AAPL, PLTR, NVDA |
