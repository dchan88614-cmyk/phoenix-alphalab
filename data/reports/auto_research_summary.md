# Phoenix AlphaLab Auto Research Loop v0.2

## Research Mode

- Offline historical research only.
- New alpha sources: none.
- Trade simulator: historical virtual trades only.
- Live-tradable versions: none.
- Research-qualified means GPT review is required before any paper trading.

## Summary

- Data start: 2023-03-07
- Research start: 2024-01-01
- Research end: 2026-06-30
- Warmup limitation: Requested warmup from 2023-03-07, earliest available data is 2023-04-03.
- Total candidates available: 100
- Total candidates evaluated: 50
- Candidates passed gate: 0
- Candidates failed gate: 50
- Stop reason: 10_consecutive_candidates_failed_to_improve_best_score
- BUY rate distribution after active enforcement: min 6.95%, median 29.47%, max 91.72%
- Realized return distribution: min 1.26%, median 1.92%, max 3.58%
- Stop/target/time-exit breakdown: stop 54.04%, target1 34.58%, target2 1.86%, time 9.52%

No research-qualified version found. Do not use Phoenix for live trading.

## Best Candidate Even If Failed

- Candidate ID: 35
- Status: RESEARCH_ONLY_NOT_TRADABLE
- Risk-adjusted score: 23.6449
- Final BUY days: 87
- Final BUY rate: 14.40%
- Average realized return: 3.58%
- Average realized excess return: 3.12%
- Realized win rate: 51.72%
- Worst realized return: -14.65%
- Best realized return: 37.76%
- Stop hit rate: 47.13%
- Target 1 hit rate: 39.08%
- Target 2 hit rate: 2.30%
- Time exit rate: 11.49%
- Fail reasons: realized_win_rate_lt_52pct

## Top 10 By Realized Excess

|   candidate_id | status                     |   risk_adjusted_score |   max_buy_rate |   min_relative_volume_prev20 |   min_smoke_score |   min_rank_gap | require_return_5d_positive   | require_return_20d_positive   |   distance_to_52w_high_prev_min |   dollar_volume_min |   signal_days |   eligible_buy_days |   final_buy_days | final_buy_rate   | avg_realized_excess_return   | realized_win_rate   | worst_realized_return   | stop_hit_rate   | target_1_hit_rate   | target_2_hit_rate   | time_exit_rate   | fail_reasons               |
|---------------:|:---------------------------|----------------------:|---------------:|-----------------------------:|------------------:|---------------:|:-----------------------------|:------------------------------|--------------------------------:|--------------------:|--------------:|--------------------:|-----------------:|:-----------------|:-----------------------------|:--------------------|:------------------------|:----------------|:--------------------|:--------------------|:-----------------|:---------------------------|
|             35 | RESEARCH_ONLY_NOT_TRADABLE |               23.6449 |           0.15 |                         1.5  |              0.85 |           0.03 | True                         | False                         |                           -0.25 |            20000000 |           604 |                 215 |               87 | 14.40%           | 3.12%                        | 51.72%              | -14.65%                 | 47.13%          | 39.08%              | 2.30%               | 11.49%           | realized_win_rate_lt_52pct |
|             10 | RESEARCH_ONLY_NOT_TRADABLE |               23.0813 |           0.15 |                         1.25 |              0.85 |           0    | True                         | False                         |                           -0.35 |            20000000 |           604 |                 434 |               87 | 14.40%           | 2.85%                        | 50.57%              | -14.65%                 | 48.28%          | 37.93%              | 2.30%               | 11.49%           | realized_win_rate_lt_52pct |
|             25 | RESEARCH_ONLY_NOT_TRADABLE |               23.0109 |           0.15 |                         1    |              0.7  |           0    | True                         | True                          |                           -0.35 |            10000000 |           604 |                 545 |               87 | 14.40%           | 2.78%                        | 50.57%              | -14.65%                 | 48.28%          | 37.93%              | 2.30%               | 11.49%           | realized_win_rate_lt_52pct |
|             20 | RESEARCH_ONLY_NOT_TRADABLE |               22.199  |           0.15 |                         2    |              0.8  |           0.03 | True                         | False                         |                           -0.25 |            50000000 |           604 |                 148 |               84 | 13.91%           | 2.40%                        | 48.81%              | -14.65%                 | 50.00%          | 36.90%              | 1.19%               | 11.90%           | realized_win_rate_lt_52pct |
|             22 | RESEARCH_ONLY_NOT_TRADABLE |               21.7602 |           0.7  |                         1    |              0.85 |           0.05 | False                        | False                         |                           -0.35 |            10000000 |           604 |                 205 |              205 | 33.94%           | 2.39%                        | 48.29%              | -17.27%                 | 51.22%          | 37.56%              | 2.93%               | 8.29%            | realized_win_rate_lt_52pct |
|             27 | RESEARCH_ONLY_NOT_TRADABLE |               21.1935 |           0.7  |                         1.25 |              0.7  |           0.03 | True                         | True                          |                           -0.15 |            10000000 |           604 |                 264 |              264 | 43.71%           | 2.33%                        | 46.21%              | -17.27%                 | 53.03%          | 37.50%              | 3.03%               | 6.44%            | realized_win_rate_lt_52pct |
|             12 | RESEARCH_ONLY_NOT_TRADABLE |               21.3569 |           0.7  |                         1.5  |              0.85 |           0.03 | True                         | False                         |                           -0.15 |            20000000 |           604 |                 208 |              208 | 34.44%           | 2.23%                        | 46.63%              | -15.78%                 | 52.40%          | 37.02%              | 2.40%               | 8.17%            | realized_win_rate_lt_52pct |
|             21 | RESEARCH_ONLY_NOT_TRADABLE |               21.383  |           1    |                         1    |              0.8  |           0.05 | False                        | False                         |                           -0.15 |            50000000 |           604 |                 204 |              204 | 33.77%           | 2.20%                        | 47.55%              | -17.27%                 | 51.96%          | 36.76%              | 2.94%               | 8.33%            | realized_win_rate_lt_52pct |
|             11 | RESEARCH_ONLY_NOT_TRADABLE |               21.4001 |           1    |                         1.5  |              0.85 |           0.03 | True                         | False                         |                           -0.25 |            20000000 |           604 |                 215 |              215 | 35.60%           | 2.19%                        | 46.98%              | -15.78%                 | 52.09%          | 36.74%              | 2.33%               | 8.84%            | realized_win_rate_lt_52pct |
|             39 | RESEARCH_ONLY_NOT_TRADABLE |               21.6249 |           0.3  |                         2    |              0.7  |           0.08 | False                        | True                          |                           -0.15 |            50000000 |           604 |                  42 |               42 | 6.95%            | 2.18%                        | 50.00%              | -13.84%                 | 50.00%          | 35.71%              | 0.00%               | 14.29%           | realized_win_rate_lt_52pct |

## Top 10 By Risk-Adjusted Score

|   candidate_id | status                     |   risk_adjusted_score |   max_buy_rate |   min_relative_volume_prev20 |   min_smoke_score |   min_rank_gap | require_return_5d_positive   | require_return_20d_positive   |   distance_to_52w_high_prev_min |   dollar_volume_min |   signal_days |   eligible_buy_days |   final_buy_days | final_buy_rate   | avg_realized_excess_return   | realized_win_rate   | worst_realized_return   | stop_hit_rate   | target_1_hit_rate   | target_2_hit_rate   | time_exit_rate   | fail_reasons               |
|---------------:|:---------------------------|----------------------:|---------------:|-----------------------------:|------------------:|---------------:|:-----------------------------|:------------------------------|--------------------------------:|--------------------:|--------------:|--------------------:|-----------------:|:-----------------|:-----------------------------|:--------------------|:------------------------|:----------------|:--------------------|:--------------------|:-----------------|:---------------------------|
|             35 | RESEARCH_ONLY_NOT_TRADABLE |               23.6449 |           0.15 |                         1.5  |              0.85 |           0.03 | True                         | False                         |                           -0.25 |            20000000 |           604 |                 215 |               87 | 14.40%           | 3.12%                        | 51.72%              | -14.65%                 | 47.13%          | 39.08%              | 2.30%               | 11.49%           | realized_win_rate_lt_52pct |
|             10 | RESEARCH_ONLY_NOT_TRADABLE |               23.0813 |           0.15 |                         1.25 |              0.85 |           0    | True                         | False                         |                           -0.35 |            20000000 |           604 |                 434 |               87 | 14.40%           | 2.85%                        | 50.57%              | -14.65%                 | 48.28%          | 37.93%              | 2.30%               | 11.49%           | realized_win_rate_lt_52pct |
|             25 | RESEARCH_ONLY_NOT_TRADABLE |               23.0109 |           0.15 |                         1    |              0.7  |           0    | True                         | True                          |                           -0.35 |            10000000 |           604 |                 545 |               87 | 14.40%           | 2.78%                        | 50.57%              | -14.65%                 | 48.28%          | 37.93%              | 2.30%               | 11.49%           | realized_win_rate_lt_52pct |
|             28 | RESEARCH_ONLY_NOT_TRADABLE |               22.9854 |           0.5  |                         1.25 |              0.75 |           0.03 | True                         | True                          |                           -0.35 |            10000000 |           604 |                 274 |              271 | 44.87%           | 2.14%                        | 46.13%              | -17.27%                 | 53.14%          | 37.27%              | 2.58%               | 7.01%            | realized_win_rate_lt_52pct |
|              3 | RESEARCH_ONLY_NOT_TRADABLE |               22.7558 |           0.5  |                         1    |              0.7  |           0.03 | True                         | True                          |                           -0.15 |            10000000 |           604 |                 297 |              278 | 46.03%           | 2.03%                        | 45.68%              | -17.27%                 | 53.60%          | 37.05%              | 2.16%               | 7.19%            | realized_win_rate_lt_52pct |
|             20 | RESEARCH_ONLY_NOT_TRADABLE |               22.199  |           0.15 |                         2    |              0.8  |           0.03 | True                         | False                         |                           -0.25 |            50000000 |           604 |                 148 |               84 | 13.91%           | 2.40%                        | 48.81%              | -14.65%                 | 50.00%          | 36.90%              | 1.19%               | 11.90%           | realized_win_rate_lt_52pct |
|             22 | RESEARCH_ONLY_NOT_TRADABLE |               21.7602 |           0.7  |                         1    |              0.85 |           0.05 | False                        | False                         |                           -0.35 |            10000000 |           604 |                 205 |              205 | 33.94%           | 2.39%                        | 48.29%              | -17.27%                 | 51.22%          | 37.56%              | 2.93%               | 8.29%            | realized_win_rate_lt_52pct |
|             39 | RESEARCH_ONLY_NOT_TRADABLE |               21.6249 |           0.3  |                         2    |              0.7  |           0.08 | False                        | True                          |                           -0.15 |            50000000 |           604 |                  42 |               42 | 6.95%            | 2.18%                        | 50.00%              | -13.84%                 | 50.00%          | 35.71%              | 0.00%               | 14.29%           | realized_win_rate_lt_52pct |
|             11 | RESEARCH_ONLY_NOT_TRADABLE |               21.4001 |           1    |                         1.5  |              0.85 |           0.03 | True                         | False                         |                           -0.25 |            20000000 |           604 |                 215 |              215 | 35.60%           | 2.19%                        | 46.98%              | -15.78%                 | 52.09%          | 36.74%              | 2.33%               | 8.84%            | realized_win_rate_lt_52pct |
|             21 | RESEARCH_ONLY_NOT_TRADABLE |               21.383  |           1    |                         1    |              0.8  |           0.05 | False                        | False                         |                           -0.15 |            50000000 |           604 |                 204 |              204 | 33.77%           | 2.20%                        | 47.55%              | -17.27%                 | 51.96%          | 36.76%              | 2.94%               | 8.33%            | realized_win_rate_lt_52pct |

## Worst And Best Realized Trades

- Worst realized trade: 2024-03-28 MSTR -19.95% STOP
- Best realized trade: 2024-10-24 MSTR 44.38% TARGET_2

## Common Fail Reasons

| fail_reason                           |   count |
|:--------------------------------------|--------:|
| realized_win_rate_lt_52pct            |      50 |
| final_buy_rate_above_50pct            |      13 |
| positive_realized_excess_windows_lt_6 |       2 |

## Warning

Phoenix remains not live-tradable unless a candidate passes all gates and GPT reviews it.
