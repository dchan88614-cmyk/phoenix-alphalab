# Phoenix AlphaLab Multi-Window Smoke Test

## Research Mode

- Factor timing: EOD
- Ranking rule: same Sprint 3 smoke ranking rule, unchanged across windows.
- Benchmark: SPY
- New alpha factors: none

## Cross-Window Summary

- Windows tested: 10
- Windows with sufficient data: 10
- Windows with 20d avg excess > 0: 6
- Windows with 20d days_outperformed_spy above 50%: 7
- Best window by 20d avg excess: 2026-04-01 to 2026-06-30 (23.45% 20d avg excess)
- Worst window by 20d avg excess: 2025-01-02 to 2025-03-31 (-5.93% 20d avg excess)
- Cross-window judgment: Yes, the simple rule shows initial cross-window strength, but it still needs stricter universe and data validation.

## Window Results

| window_start   | window_end   | status   |   universe_ticker_count |   selected_unique_ticker_count |   signal_days | best_trade              | worst_trade             | top_5_most_selected                         | avg_return_5d   | avg_excess_return_5d   | win_rate_5d   | avg_return_10d   | avg_excess_return_10d   | win_rate_10d   | avg_return_20d   | avg_excess_return_20d   | win_rate_20d   |   days_outperformed_spy_20d |   eligible_days_20d |
|:---------------|:-------------|:---------|------------------------:|-------------------------------:|--------------:|:------------------------|:------------------------|:--------------------------------------------|:----------------|:-----------------------|:--------------|:-----------------|:------------------------|:---------------|:-----------------|:------------------------|:---------------|----------------------------:|--------------------:|
| 2024-01-02     | 2024-03-29   | ok       |                      98 |                              5 |             1 | 2024-03-28 TLN 6.41%    | 2024-03-28 MSTR -24.77% | MSTR:1, RTX:1, F:1, MU:1, TLN:1             | -1.33%          | -0.44%                 | 40.00%        | -2.52%           | -0.18%                  | 40.00%         | -4.13%           | -1.30%                  | 40.00%         |                           0 |                   1 |
| 2024-04-01     | 2024-06-28   | ok       |                      98 |                             57 |            63 | 2024-05-10 NVAX 80.29%  | 2024-05-09 OKLO -54.20% | NEE:18, QCOM:15, AAPL:14, NVDA:14, MRNA:14  | 1.20%           | 0.70%                  | 55.24%        | 2.30%            | 1.15%                   | 56.51%         | 3.43%            | 0.82%                   | 59.37%         |                          38 |                  63 |
| 2024-07-01     | 2024-09-30   | ok       |                      98 |                             59 |            64 | 2024-09-30 MSTR 51.45%  | 2024-07-15 HUT -43.05%  | PLTR:29, TSLA:18, GEV:15, CAVA:11, LMT:11   | 0.75%           | 0.47%                  | 56.25%        | 0.39%            | -0.17%                  | 58.13%         | 1.11%            | -0.32%                  | 60.00%         |                          37 |                  64 |
| 2024-10-01     | 2024-12-31   | ok       |                      98 |                             55 |            64 | 2024-10-23 MSTR 121.47% | 2024-11-20 MSTR -31.10% | PLTR:28, MSTR:27, TSLA:17, AVGO:15, HOOD:13 | 1.62%           | 1.32%                  | 52.19%        | 4.10%            | 3.69%                   | 56.56%         | 10.36%           | 9.35%                   | 62.81%         |                          44 |                  64 |
| 2025-01-02     | 2025-03-31   | ok       |                      98 |                             64 |            60 | 2025-01-03 OKLO 72.07%  | 2025-02-12 BBAI -66.43% | SPOT:16, PLTR:15, OKLO:13, VST:13, AAPL:12  | -2.02%          | -1.22%                 | 37.33%        | -4.31%           | -2.70%                  | 32.00%         | -9.44%           | -5.93%                  | 27.67%         |                          21 |                  60 |
| 2025-04-01     | 2025-06-30   | ok       |                      98 |                             56 |            62 | 2025-05-14 OKLO 74.22%  | 2025-05-16 ACHR -21.95% | PLTR:26, HOOD:22, RBLX:15, GEV:14, COIN:12  | 1.86%           | 0.59%                  | 60.00%        | 5.63%            | 2.99%                   | 74.52%         | 11.57%           | 6.19%                   | 80.65%         |                          50 |                  62 |
| 2025-07-01     | 2025-09-30   | ok       |                      98 |                             54 |            64 | 2025-09-09 IREN 104.31% | 2025-08-04 JOBY -34.38% | IREN:24, APP:18, HOOD:17, NVDA:15, AVGO:15  | 2.62%           | 2.03%                  | 57.50%        | 4.93%            | 3.84%                   | 60.94%         | 9.19%            | 7.11%                   | 64.06%         |                          41 |                  64 |
| 2025-10-01     | 2025-12-31   | ok       |                      98 |                             56 |            64 | 2025-12-15 RKLB 65.67%  | 2025-10-15 SMR -51.41%  | MU:30, AAPL:19, RKLB:16, AVGO:15, AMD:14    | -0.93%          | -1.16%                 | 48.12%        | -0.56%           | -1.12%                  | 48.12%         | -0.57%           | -1.55%                  | 47.81%         |                          29 |                  64 |
| 2026-01-02     | 2026-03-31   | ok       |                      98 |                             48 |            61 | 2026-03-26 MRVL 68.21%  | 2026-01-14 RKLB -28.09% | MU:31, GEV:22, LRCX:16, ASML:15, AMAT:15    | 0.26%           | 0.58%                  | 49.18%        | 0.24%            | 0.59%                   | 48.52%         | 4.17%            | 4.00%                   | 52.79%         |                          44 |                  61 |
| 2026-04-01     | 2026-06-30   | ok       |                      98 |                             34 |            41 | 2026-04-07 INTC 104.40% | 2026-05-27 RKLB -46.29% | INTC:23, MRVL:21, AMD:20, MU:18, QCOM:12    | 8.37%           | 6.75%                  | 72.20%        | 14.15%           | 11.67%                  | 79.02%         | 27.05%           | 23.45%                  | 79.51%         |                          41 |                  41 |
