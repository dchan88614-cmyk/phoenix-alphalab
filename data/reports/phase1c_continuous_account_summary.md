# Phoenix Nano Phase 1C Continuous Account Growth Backtest

Research-only historical backtest. This does not start paper trading or live trading.

## Account Growth

- Period: 2024-01-01 to 2026-06-30
- Starting account value: $100.00
- Ending account value: $92.15
- Total return: -7.85%
- Highest account value reached: $176.25
- $1000 reached: False

## Milestones

- $150: 2024-12-04
- $200: not reached
- $300: not reached
- $500: not reached
- $1000: not reached

## Trades

- Number of trades: 30
- Win rate: 53.33%
- Best trade: 2024-10-22 CORZ TARGET_30 return=28.12%
- Worst trade: 2024-04-26 SOFI STOP return=-10.00%
- Max drawdown: -50.46%
- Longest flat period: 512 calendar days from 2025-02-05 to 2026-07-02

## Bottleneck

- Rule blocked most stocks: price_between_5_and_50 (17345 rows)

## Block Counts

| rule                              |   count |
|:----------------------------------|--------:|
| price_between_5_and_50            |   17345 |
| return_5d_between_3_and_15        |    4776 |
| relative_volume_prev20_min_1_5    |     973 |
| dollar_volume_min                 |     591 |
| green_days_5_min_3                |     455 |
| max_daily_gain_5_lte_10           |     167 |
| distance_to_52w_high_min_minus_35 |      42 |
| spy_qqq_not_clear_downtrend       |      17 |
| atr_pct_lte_12                    |       1 |

## What Should Be Adjusted Next

- Do not start paper or live trading from this report.
- Review the dominant block rule before loosening any threshold.
- If account growth stalls, test one conservative filter adjustment at a time in a separate GPT-approved task.
- Independent vendor data validation remains a separate blocker.
