# Phoenix AlphaLab Smoke Test

## Research Mode

- Factor timing: EOD
- Ranking rule: simple average percentile score across previous-window factors.
- Ranking factors: relative_volume_prev20, return_5d, return_20d, distance_to_52w_high_prev, dollar_volume
- Excluded from ranking: forward returns, market cap, news, SEC data, short interest, AI scores.
- Benchmark: SPY
- Universe ticker count: 98
- Selected unique ticker count: 45

## Test Range

- Start date: 2026-03-05
- End date: 2026-05-29
- Signal days: 60
- Selected rows: 300

## Summary

|   horizon_days | avg_return   | avg_excess_return   | win_rate   |   days_outperformed_spy |   eligible_days |
|---------------:|:-------------|:--------------------|:-----------|------------------------:|----------------:|
|              5 | 5.50%        | 4.59%               | 62.33%     |                      43 |              60 |
|             10 | 9.61%        | 7.81%               | 68.00%     |                      49 |              60 |
|             20 | 22.79%       | 18.69%              | 77.00%     |                      57 |              60 |

## Top 10 Most Selected Tickers

| ticker   |   selected_count |
|:---------|-----------------:|
| MRVL     |               29 |
| MU       |               26 |
| INTC     |               25 |
| AMD      |               21 |
| DELL     |               19 |
| ARM      |               18 |
| GEV      |               14 |
| RKLB     |               13 |
| QCOM     |               12 |
| HPE      |               11 |

## Best And Worst

- Best trade (20d): 2026-04-07 INTC 104.40%
- Worst trade (20d): 2026-05-27 RKLB -46.29%
- Best trade excluding most selected ticker (MRVL, 20d): 2026-04-07 INTC 104.40%
- Worst trade excluding most selected ticker (MRVL, 20d): 2026-05-27 RKLB -46.29%

## Result Excluding Best Single Trade

|   horizon_days |   rows | avg_return   | avg_excess_return   | win_rate   |
|---------------:|-------:|:-------------|:--------------------|:-----------|
|              5 |    299 | 5.45%        | 4.55%               | 62.21%     |
|             10 |    299 | 9.56%        | 7.77%               | 67.89%     |
|             20 |    299 | 22.52%       | 18.44%              | 76.92%     |

## Result Excluding Worst Single Trade

|   horizon_days |   rows | avg_return   | avg_excess_return   | win_rate   |
|---------------:|-------:|:-------------|:--------------------|:-----------|
|              5 |    299 | 5.60%        | 4.68%               | 62.54%     |
|             10 |    299 | 9.74%        | 7.93%               | 68.23%     |
|             20 |    299 | 23.02%       | 18.90%              | 77.26%     |

## Result Excluding SMCI

Not applicable.

## Initial Judgment

Yes, initial smoke test shows enough relative strength to keep researching.

## Daily Top 5

| date       | top_5                        |
|:-----------|:-----------------------------|
| 2026-03-05 | AVGO, MRNA, CRWD, APP, TSM   |
| 2026-03-06 | MRVL, PLTR, RTX, AVGO, LMT   |
| 2026-03-09 | MRVL, AVGO, MRNA, PWR, LMT   |
| 2026-03-10 | MRVL, MU, NIO, AVGO, RIVN    |
| 2026-03-11 | MU, MRVL, INTC, AVGO, NIO    |
| 2026-03-12 | SO, MU, PLTR, MRVL, GEV      |
| 2026-03-13 | MU, PWR, KLAC, NIO, INTC     |
| 2026-03-16 | MU, PWR, DELL, NIO, NVDA     |
| 2026-03-17 | MU, RKLB, UBER, CAVA, DELL   |
| 2026-03-18 | MU, NET, GEV, LRCX, BWXT     |
| 2026-03-19 | MU, GEV, KLAC, LRCX, DELL    |
| 2026-03-20 | DELL, GEV, AMAT, KLAC, LRCX  |
| 2026-03-23 | GEV, DELL, PLTR, ARM, NET    |
| 2026-03-24 | DELL, GEV, HPE, PLTR, ARM    |
| 2026-03-25 | DELL, HPE, ARM, MRVL, GEV    |
| 2026-03-26 | MRVL, ARM, DELL, GEV, HPE    |
| 2026-03-27 | ARM, AAPL, HPE, GEV, SO      |
| 2026-03-30 | DELL, AMD, ARM, SO, PANW     |
| 2026-03-31 | MRVL, ARM, NEE, AAPL, NIO    |
| 2026-04-01 | MRVL, INTC, AAPL, ARM, PANW  |
| 2026-04-02 | INTC, MRVL, AMD, NEE, GEV    |
| 2026-04-06 | INTC, MRVL, AMD, MU, RKLB    |
| 2026-04-07 | INTC, MRVL, AVGO, AMD, NET   |
| 2026-04-08 | INTC, TER, MRVL, HUT, ANET   |
| 2026-04-09 | INTC, MRVL, TER, LRCX, HUT   |
| 2026-04-10 | MRVL, INTC, AMD, AVGO, AMAT  |
| 2026-04-13 | MRVL, INTC, DELL, HUT, LRCX  |
| 2026-04-14 | MRVL, INTC, MU, ASML, KLAC   |
| 2026-04-15 | AVGO, MRVL, INTC, HOOD, LRCX |
| 2026-04-16 | AMD, RKLB, INTC, DELL, HOOD  |
| 2026-04-17 | HOOD, AMD, INTC, MSTR, MRVL  |
| 2026-04-20 | MRVL, RKLB, AMD, HPE, HOOD   |
| 2026-04-21 | MRVL, ANET, AMD, DELL, HPE   |
| 2026-04-22 | AMD, ARM, GEV, MRVL, ANET    |
| 2026-04-23 | ARM, MRVL, AMD, GEV, INTC    |
| 2026-04-24 | INTC, AMD, ARM, MRVL, TSM    |
| 2026-04-27 | INTC, AMD, ARM, NVDA, GEV    |
| 2026-04-28 | INTC, MU, AMD, GEV, NVDA     |
| 2026-04-29 | INTC, AMD, MU, QCOM, KLAC    |
| 2026-04-30 | INTC, PWR, QCOM, AMD, MU     |
| 2026-05-01 | INTC, MU, PWR, ROKU, QCOM    |
| 2026-05-04 | MU, PWR, QCOM, INTC, AMD     |
| 2026-05-05 | MU, INTC, AMD, QCOM, LRCX    |
| 2026-05-06 | AMD, HUT, MU, ARM, QCOM      |
| 2026-05-07 | DDOG, QCOM, NET, MU, IREN    |
| 2026-05-08 | MU, RKLB, INTC, DELL, AMD    |
| 2026-05-11 | MU, RKLB, QCOM, INTC, DELL   |
| 2026-05-12 | MU, RKLB, CRWD, QCOM, PANW   |
| 2026-05-13 | MU, PANW, MRVL, RKLB, HPE    |
| 2026-05-14 | PANW, NVDA, MRVL, HPE, F     |
| 2026-05-15 | PANW, CRWD, NVDA, AMAT, AAPL |
| 2026-05-18 | CRWD, RKLB, PANW, NVDA, HPE  |
| 2026-05-19 | CRWD, PANW, RKLB, DDOG, ARM  |
| 2026-05-20 | ARM, CRWD, MRVL, PANW, RKLB  |
| 2026-05-21 | ARM, CRWD, QCOM, AAPL, LRCX  |
| 2026-05-22 | DELL, ARM, HPE, QCOM, RKLB   |
| 2026-05-26 | MU, MRVL, DELL, AMD, QCOM    |
| 2026-05-27 | MU, IREN, DELL, RKLB, MRVL   |
| 2026-05-28 | DELL, ARM, SNOW, F, MU       |
| 2026-05-29 | DELL, HPE, OKTA, SNOW, MU    |
