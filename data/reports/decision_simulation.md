# Phoenix AlphaLab Decision Simulation

## Research Mode

- Factor timing: EOD
- Entry proxy: same-day close
- Decision rule: Generation 1 baseline BUY / NO_TRADE rule
- New alpha factors: none

## Summary

- Total signal days: 60
- BUY days: 59
- NO_TRADE days: 1
- BUY rate: 98.33%
- Best BUY: 2026-04-07 INTC 104.40% (20d)
- Worst BUY: 2026-03-05 AVGO -5.48% (20d)
- Comparison: BUY filtering improved performance versus always buying smoke rank 1.

## BUY vs Always Buy Smoke Rank 1

|   horizon_days | buy_avg_forward_return   | buy_avg_excess_return   | buy_win_rate   | rank1_avg_forward_return   | rank1_avg_excess_return   | rank1_win_rate   |
|---------------:|:-------------------------|:------------------------|:---------------|:---------------------------|:--------------------------|:-----------------|
|              5 | 8.44%                    | 7.52%                   | 71.19%         | 8.19%                      | 7.28%                     | 70.00%           |
|             10 | 13.25%                   | 11.45%                  | 76.27%         | 12.72%                     | 10.92%                    | 75.00%           |
|             20 | 32.10%                   | 28.00%                  | 91.53%         | 31.31%                     | 27.22%                    | 90.00%           |

## Decisions

| date       | action   | ticker   |   entry_price |   entry_low |   entry_high |   stop_loss |   target_1 |   target_2 |   confidence | reason                                                                               |
|:-----------|:---------|:---------|--------------:|------------:|-------------:|------------:|-----------:|-----------:|-------------:|:-------------------------------------------------------------------------------------|
| 2026-03-05 | BUY      | AVGO     |        332.77 |    331.106  |     334.434  |    312.592  |   373.126  |   413.483  |           82 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-06 | BUY      | MRVL     |         89.57 |     89.1221 |      90.0178 |     83.1693 |   102.371  |   115.173  |           91 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-09 | BUY      | MRVL     |         92.65 |     92.1868 |      93.1133 |     85.7093 |   106.531  |   120.413  |           92 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-10 | BUY      | MRVL     |         93.3  |     92.8335 |      93.7665 |     86.1964 |   107.507  |   121.714  |           91 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-11 | BUY      | MU       |        418.69 |    416.597  |     420.783  |    381.915  |   492.239  |   565.789  |           88 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-12 | BUY      | SO       |         97.84 |     97.3508 |      98.3292 |     95.4454 |   102.629  |   107.419  |           79 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-13 | BUY      | MU       |        426.13 |    423.999  |     428.261  |    387.834  |   502.722  |   579.314  |           87 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-16 | BUY      | MU       |        441.8  |    439.591  |     444.009  |    403.103  |   519.194  |   596.587  |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-17 | BUY      | MU       |        461.69 |    459.382  |     463.998  |    422.774  |   539.523  |   617.356  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-18 | BUY      | MU       |        461.73 |    459.421  |     464.039  |    424.849  |   535.491  |   609.253  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-19 | BUY      | MU       |        444.27 |    442.049  |     446.491  |    404.835  |   523.14   |   602.01   |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-20 | BUY      | DELL     |        157.67 |    156.882  |     158.458  |    146.699  |   179.613  |   201.556  |           92 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-23 | BUY      | GEV      |        882.64 |    878.227  |     887.053  |    824.166  |   999.588  |  1116.54   |           91 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-24 | BUY      | DELL     |        176.91 |    176.025  |     177.795  |    165.309  |   200.113  |   223.316  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-25 | BUY      | DELL     |        184.01 |    183.09   |     184.93   |    172.319  |   207.393  |   230.776  |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-26 | BUY      | MRVL     |         97.68 |     97.1916 |      98.1684 |     90.9632 |   111.114  |   124.547  |           93 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-27 | BUY      | ARM      |        144.13 |    143.409  |     144.851  |    131.11   |   170.171  |   196.212  |           89 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-30 | BUY      | DELL     |        164.66 |    163.837  |     165.483  |    152.215  |   189.549  |   214.439  |           85 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-03-31 | BUY      | MRVL     |         99.05 |     98.5548 |      99.5453 |     91.1675 |   114.815  |   130.58   |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-01 | BUY      | MRVL     |        106.71 |    106.176  |     107.244  |     98.2146 |   123.701  |   140.691  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-02 | BUY      | INTC     |         50.38 |     50.1281 |      50.6319 |     46.0246 |    59.0907 |    67.8014 |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-06 | BUY      | INTC     |         50.78 |     50.5261 |      51.0339 |     46.5275 |    59.285  |    67.79   |           93 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-07 | BUY      | INTC     |         52.91 |     52.6454 |      53.1745 |     48.6232 |    61.4836 |    70.0571 |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-08 | BUY      | INTC     |         58.95 |     58.6553 |      59.2448 |     54.1704 |    68.5093 |    78.0686 |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-09 | BUY      | INTC     |         61.72 |     61.4114 |      62.0286 |     56.8439 |    71.4721 |    81.2243 |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-10 | BUY      | MRVL     |        128.49 |    127.848  |     129.132  |    118.375  |   148.721  |   168.951  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-13 | BUY      | MRVL     |        131.3  |    130.644  |     131.957  |    121.073  |   151.754  |   172.207  |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-14 | BUY      | MRVL     |        133.83 |    133.161  |     134.499  |    123.421  |   154.648  |   175.466  |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-15 | BUY      | AVGO     |        396.72 |    394.736  |     398.704  |    377.383  |   435.394  |   474.069  |           86 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-16 | BUY      | AMD      |        278.26 |    276.869  |     279.651  |    262.521  |   309.739  |   341.217  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-17 | NO_TRADE | HOOD     |         90.75 |     90.2963 |      91.2037 |     83.5362 |   105.178  |   119.605  |           79 | Top ranked EOD candidate failed one or more baseline BUY filters.                    |
| 2026-04-20 | BUY      | MRVL     |        147.84 |    147.101  |     148.579  |    137.087  |   169.346  |   190.851  |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-21 | BUY      | MRVL     |        151.31 |    150.553  |     152.067  |    141.054  |   171.821  |   192.333  |           89 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-22 | BUY      | AMD      |        303.46 |    301.943  |     304.977  |    286.271  |   337.838  |   372.216  |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-23 | BUY      | ARM      |        204.61 |    203.587  |     205.633  |    189.731  |   234.369  |   264.128  |           93 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-24 | BUY      | INTC     |         82.54 |     82.1273 |      82.9527 |     75.7321 |    96.1557 |   109.771  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-27 | BUY      | INTC     |         84.99 |     84.565  |      85.4149 |     77.9604 |    99.0493 |   113.109  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-28 | BUY      | INTC     |         84.52 |     84.0974 |      84.9426 |     77.7121 |    98.1357 |   111.751  |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-29 | BUY      | INTC     |         94.75 |     94.2763 |      95.2237 |     87.22   |   109.81   |   124.87   |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-04-30 | BUY      | INTC     |         94.48 |     94.0076 |      94.9524 |     86.7839 |   109.872  |   125.264  |           93 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-01 | BUY      | INTC     |         99.62 |     99.1219 |     100.118  |     91.4557 |   115.949  |   132.277  |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-04 | BUY      | MU       |        576.45 |    573.568  |     579.332  |    532.002  |   665.346  |   754.243  |           92 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-05 | BUY      | MU       |        640.2  |    636.999  |     643.401  |    590.507  |   739.586  |   838.971  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-06 | BUY      | AMD      |        421.39 |    419.283  |     423.497  |    385.989  |   492.192  |   562.994  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-07 | BUY      | DDOG     |        188.73 |    187.786  |     189.674  |    173.689  |   218.812  |   248.893  |           93 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-08 | BUY      | MU       |        746.81 |    743.076  |     750.544  |    683.944  |   872.542  |   998.274  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-11 | BUY      | MU       |        795.33 |    791.353  |     799.307  |    726.535  |   932.921  |  1070.51   |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-12 | BUY      | MU       |        766.58 |    762.747  |     770.413  |    692.842  |   914.056  |  1061.53   |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-13 | BUY      | MU       |        803.63 |    799.612  |     807.648  |    727.048  |   956.795  |  1109.96   |           92 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-14 | BUY      | PANW     |        238.21 |    237.019  |     239.401  |    224.809  |   265.013  |   291.816  |           92 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-15 | BUY      | PANW     |        242.83 |    241.616  |     244.044  |    228.569  |   271.351  |   299.873  |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-18 | BUY      | CRWD     |        618.83 |    615.736  |     621.924  |    582.449  |   691.591  |   764.352  |           94 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-19 | BUY      | CRWD     |        616.88 |    613.796  |     619.964  |    579.514  |   691.613  |   766.345  |           93 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-20 | BUY      | ARM      |        256.73 |    255.446  |     258.014  |    229.881  |   310.427  |   364.125  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-21 | BUY      | ARM      |        298.23 |    296.739  |     299.721  |    267.869  |   358.951  |   419.672  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-22 | BUY      | DELL     |        295.19 |    293.714  |     296.666  |    268.547  |   348.476  |   401.763  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-26 | BUY      | MU       |        895.88 |    891.401  |     900.359  |    796.578  |  1094.48   |  1293.09   |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-27 | BUY      | MU       |        928.41 |    923.768  |     933.052  |    826.116  |  1133      |  1337.58   |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-28 | BUY      | DELL     |        317.05 |    315.465  |     318.635  |    289.438  |   372.274  |   427.497  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
| 2026-05-29 | BUY      | DELL     |        420.91 |    418.805  |     423.015  |    384.9    |   492.929  |   564.949  |           95 | Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume. |
