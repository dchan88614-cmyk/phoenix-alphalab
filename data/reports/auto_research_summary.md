# Phoenix AlphaLab Auto Research Loop v0.3

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
- BUY rate distribution after active enforcement: min 6.95%, median 29.47%, max 90.23%
- Realized return distribution: min -6.64%, median 0.38%, max 4.00%
- Robustness excluding MSTR: min -6.91%, median -0.01%, max 3.37%
- Robustness excluding most selected ticker: min -8.48%, median -0.12%, max 4.18%
- Equal-ticker-weighted excess distribution: min -6.44%, median -0.18%, max 5.06%
- Stop/target/time-exit breakdown: stop 66.30%, target1 25.89%, target2 0.55%, time 7.27%

Research-qualified candidates found. GPT review required before any paper trading.

## Best Candidate Even If Failed

- Candidate ID: 39
- Status: NANO_RESEARCH_ONLY_NOT_TRADABLE
- Risk-adjusted score: 20.8461
- Final BUY days: 42
- Final BUY rate: 6.95%
- Average realized return: 4.00%
- Average realized excess return: 3.37%
- Realized win rate: 45.45%
- Worst realized return: -13.84%
- Best realized return: 37.76%
- Stop hit rate: 54.55%
- Target 1 hit rate: 40.91%
- Target 2 hit rate: 0.00%
- Time exit rate: 4.55%
- Top 1 ticker trade share: 9.09%
- Top 3 ticker trade share: 27.27%
- Excluding MSTR avg realized excess: 3.37%
- Excluding most selected avg realized excess: 1.58%
- Equal-ticker-weighted avg realized excess: 3.28%
- Fail reasons: executed_trade_count_lt_20

## Best Research-Qualified Candidate

- Candidate ID: 34
- Status: NANO_RESEARCH_QUALIFIED_NOT_LIVE
- Risk-adjusted score: 13.1217
- Final BUY days: 178
- Final BUY rate: 29.47%
- Average realized return: 0.46%
- Average realized excess return: -0.07%
- Realized win rate: 39.39%
- Worst realized return: -16.60%
- Best realized return: 37.76%
- Stop hit rate: 60.61%
- Target 1 hit rate: 28.79%
- Target 2 hit rate: 0.00%
- Time exit rate: 10.61%
- Top 1 ticker trade share: 13.64%
- Top 3 ticker trade share: 34.85%
- Excluding MSTR avg realized excess: 0.08%
- Excluding most selected avg realized excess: -0.63%
- Equal-ticker-weighted avg realized excess: -0.84%
- Fail reasons: 

## Top 10 By Realized Excess

|   candidate_id | status                          |   risk_adjusted_score |   max_buy_rate |   min_relative_volume_prev20 |   min_smoke_score |   min_rank_gap | require_return_5d_positive   | require_return_20d_positive   |   distance_to_52w_high_prev_min |   dollar_volume_min |   max_trades_per_ticker_per_year |   signal_days |   eligible_buy_days |   final_buy_days | final_buy_rate   | avg_realized_excess_return   | realized_win_rate   | worst_realized_return   | stop_hit_rate   | target_1_hit_rate   | target_2_hit_rate   | time_exit_rate   | top1_ticker_trade_share   | top3_ticker_trade_share   | excluding_mstr_avg_realized_excess_return   | excluding_most_selected_avg_realized_excess_return   | equal_ticker_weighted_avg_realized_excess_return   | fail_reasons                                                                                                                         |
|---------------:|:--------------------------------|----------------------:|---------------:|-----------------------------:|------------------:|---------------:|:-----------------------------|:------------------------------|--------------------------------:|--------------------:|---------------------------------:|--------------:|--------------------:|-----------------:|:-----------------|:-----------------------------|:--------------------|:------------------------|:----------------|:--------------------|:--------------------|:-----------------|:--------------------------|:--------------------------|:--------------------------------------------|:-----------------------------------------------------|:---------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------|
|             39 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               20.8461 |           0.3  |                          2   |              0.7  |           0.08 | False                        | True                          |                           -0.15 |            50000000 |                              nan |           604 |                  42 |               42 | 6.95%            | 3.37%                        | 45.45%              | -13.84%                 | 54.55%          | 40.91%              | 0.00%               | 4.55%            | 9.09%                     | 27.27%                    | 3.37%                                       | 1.58%                                                | 3.28%                                              | executed_trade_count_lt_20                                                                                                           |
|             40 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               20.0118 |           0.15 |                          2   |              0.75 |           0.08 | False                        | True                          |                           -0.35 |            50000000 |                              nan |           604 |                  43 |               43 | 7.12%            | 3.03%                        | 43.48%              | -13.84%                 | 56.52%          | 39.13%              | 0.00%               | 4.35%            | 8.70%                     | 26.09%                    | 3.03%                                       | 1.30%                                                | 2.85%                                              | executed_trade_count_lt_20, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital                               |
|             31 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               17.8935 |           1    |                          1.5 |              0.8  |           0.08 | False                        | False                         |                           -0.35 |            20000000 |                                5 |           604 |                  66 |               66 | 10.93%           | 2.74%                        | 46.15%              | -13.84%                 | 53.85%          | 34.62%              | 0.00%               | 11.54%           | 19.23%                    | 42.31%                    | 3.22%                                       | 2.09%                                                | 0.32%                                              | executed_trade_count_lt_20, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital                               |
|             32 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               17.8935 |           0.7  |                          1.5 |              0.8  |           0.08 | False                        | False                         |                           -0.25 |            20000000 |                                5 |           604 |                  66 |               66 | 10.93%           | 2.74%                        | 46.15%              | -13.84%                 | 53.85%          | 34.62%              | 0.00%               | 11.54%           | 19.23%                    | 42.31%                    | 3.22%                                       | 2.09%                                                | 0.32%                                              | executed_trade_count_lt_20, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital                               |
|             24 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               20.2706 |           0.3  |                          1   |              0.85 |           0.08 | False                        | False                         |                           -0.15 |            10000000 |                               10 |           604 |                  78 |               78 | 12.91%           | 2.73%                        | 50.00%              | -13.84%                 | 50.00%          | 30.00%              | 0.00%               | 20.00%           | 30.00%                    | 50.00%                    | 2.73%                                       | 0.91%                                                | 3.09%                                              | executed_trade_count_lt_20, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital                               |
|             23 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               19.3333 |           0.5  |                          1   |              0.85 |           0.08 | False                        | False                         |                           -0.25 |            10000000 |                               10 |           604 |                  81 |               81 | 13.41%           | 2.38%                        | 47.62%              | -13.84%                 | 52.38%          | 28.57%              | 0.00%               | 19.05%           | 28.57%                    | 47.62%                    | 2.38%                                       | 0.55%                                                | 2.51%                                              | executed_trade_count_lt_20, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital                               |
|             44 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               13.5769 |           1    |                          1   |              0.7  |           0    | True                         | True                          |                           -0.35 |            10000000 |                              nan |           604 |                 545 |              545 | 90.23%           | 1.83%                        | 42.36%              | -18.92%                 | 56.65%          | 33.99%              | 2.46%               | 6.90%            | 10.84%                    | 29.06%                    | 1.65%                                       | 1.51%                                                | -0.46%                                             | max_drawdown_lte_minus_35pct, win_rate_lt_45pct                                                                                      |
|             49 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               13.5769 |           1    |                          1   |              0.7  |           0    | True                         | True                          |                           -0.35 |            10000000 |                               20 |           604 |                 545 |              545 | 90.23%           | 1.83%                        | 42.36%              | -18.92%                 | 56.65%          | 33.99%              | 2.46%               | 6.90%            | 10.84%                    | 29.06%                    | 1.65%                                       | 1.51%                                                | -0.46%                                             | max_drawdown_lte_minus_35pct, win_rate_lt_45pct                                                                                      |
|             25 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               15.1884 |           0.15 |                          1   |              0.7  |           0    | True                         | True                          |                           -0.35 |            10000000 |                                5 |           604 |                 545 |               87 | 14.40%           | 1.65%                        | 40.00%              | -14.65%                 | 60.00%          | 35.00%              | 0.00%               | 5.00%            | 15.00%                    | 35.00%                    | 1.65%                                       | 0.58%                                                | 0.74%                                              | executed_trade_count_lt_20, max_drawdown_lte_minus_35pct, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital |
|             35 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               13.8947 |           0.15 |                          1.5 |              0.85 |           0.03 | True                         | False                         |                           -0.25 |            20000000 |                              nan |           604 |                 215 |               87 | 14.40%           | 1.47%                        | 40.00%              | -14.65%                 | 60.00%          | 32.00%              | 0.00%               | 8.00%            | 12.00%                    | 28.00%                    | 1.92%                                       | 0.62%                                                | -0.43%                                             | max_drawdown_lte_minus_35pct, win_rate_lt_45pct                                                                                      |

## Top 10 By Risk-Adjusted Score

|   candidate_id | status                          |   risk_adjusted_score |   max_buy_rate |   min_relative_volume_prev20 |   min_smoke_score |   min_rank_gap | require_return_5d_positive   | require_return_20d_positive   |   distance_to_52w_high_prev_min |   dollar_volume_min |   max_trades_per_ticker_per_year |   signal_days |   eligible_buy_days |   final_buy_days | final_buy_rate   | avg_realized_excess_return   | realized_win_rate   | worst_realized_return   | stop_hit_rate   | target_1_hit_rate   | target_2_hit_rate   | time_exit_rate   | top1_ticker_trade_share   | top3_ticker_trade_share   | excluding_mstr_avg_realized_excess_return   | excluding_most_selected_avg_realized_excess_return   | equal_ticker_weighted_avg_realized_excess_return   | fail_reasons                                                                                                                         |
|---------------:|:--------------------------------|----------------------:|---------------:|-----------------------------:|------------------:|---------------:|:-----------------------------|:------------------------------|--------------------------------:|--------------------:|---------------------------------:|--------------:|--------------------:|-----------------:|:-----------------|:-----------------------------|:--------------------|:------------------------|:----------------|:--------------------|:--------------------|:-----------------|:--------------------------|:--------------------------|:--------------------------------------------|:-----------------------------------------------------|:---------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------|
|             39 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               20.8461 |           0.3  |                          2   |              0.7  |           0.08 | False                        | True                          |                           -0.15 |            50000000 |                              nan |           604 |                  42 |               42 | 6.95%            | 3.37%                        | 45.45%              | -13.84%                 | 54.55%          | 40.91%              | 0.00%               | 4.55%            | 9.09%                     | 27.27%                    | 3.37%                                       | 1.58%                                                | 3.28%                                              | executed_trade_count_lt_20                                                                                                           |
|             24 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               20.2706 |           0.3  |                          1   |              0.85 |           0.08 | False                        | False                         |                           -0.15 |            10000000 |                               10 |           604 |                  78 |               78 | 12.91%           | 2.73%                        | 50.00%              | -13.84%                 | 50.00%          | 30.00%              | 0.00%               | 20.00%           | 30.00%                    | 50.00%                    | 2.73%                                       | 0.91%                                                | 3.09%                                              | executed_trade_count_lt_20, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital                               |
|             40 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               20.0118 |           0.15 |                          2   |              0.75 |           0.08 | False                        | True                          |                           -0.35 |            50000000 |                              nan |           604 |                  43 |               43 | 7.12%            | 3.03%                        | 43.48%              | -13.84%                 | 56.52%          | 39.13%              | 0.00%               | 4.35%            | 8.70%                     | 26.09%                    | 3.03%                                       | 1.30%                                                | 2.85%                                              | executed_trade_count_lt_20, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital                               |
|             23 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               19.3333 |           0.5  |                          1   |              0.85 |           0.08 | False                        | False                         |                           -0.25 |            10000000 |                               10 |           604 |                  81 |               81 | 13.41%           | 2.38%                        | 47.62%              | -13.84%                 | 52.38%          | 28.57%              | 0.00%               | 19.05%           | 28.57%                    | 47.62%                    | 2.38%                                       | 0.55%                                                | 2.51%                                              | executed_trade_count_lt_20, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital                               |
|             32 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               17.8935 |           0.7  |                          1.5 |              0.8  |           0.08 | False                        | False                         |                           -0.25 |            20000000 |                                5 |           604 |                  66 |               66 | 10.93%           | 2.74%                        | 46.15%              | -13.84%                 | 53.85%          | 34.62%              | 0.00%               | 11.54%           | 19.23%                    | 42.31%                    | 3.22%                                       | 2.09%                                                | 0.32%                                              | executed_trade_count_lt_20, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital                               |
|             31 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               17.8935 |           1    |                          1.5 |              0.8  |           0.08 | False                        | False                         |                           -0.35 |            20000000 |                                5 |           604 |                  66 |               66 | 10.93%           | 2.74%                        | 46.15%              | -13.84%                 | 53.85%          | 34.62%              | 0.00%               | 11.54%           | 19.23%                    | 42.31%                    | 3.22%                                       | 2.09%                                                | 0.32%                                              | executed_trade_count_lt_20, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital                               |
|             19 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               15.7928 |           0.3  |                          2   |              0.8  |           0.03 | True                         | False                         |                           -0.35 |            50000000 |                               10 |           604 |                 148 |              140 | 23.18%           | 0.75%                        | 41.67%              | -14.80%                 | 58.33%          | 30.56%              | 0.00%               | 11.11%           | 16.67%                    | 41.67%                    | 0.75%                                       | 0.50%                                                | 2.38%                                              | executed_trade_count_lt_20, win_rate_lt_45pct                                                                                        |
|             25 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               15.1884 |           0.15 |                          1   |              0.7  |           0    | True                         | True                          |                           -0.35 |            10000000 |                                5 |           604 |                 545 |               87 | 14.40%           | 1.65%                        | 40.00%              | -14.65%                 | 60.00%          | 35.00%              | 0.00%               | 5.00%            | 15.00%                    | 35.00%                    | 1.65%                                       | 0.58%                                                | 0.74%                                              | executed_trade_count_lt_20, max_drawdown_lte_minus_35pct, win_rate_lt_45pct, ending_equity_excluding_best_trade_lte_starting_capital |
|             35 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               13.8947 |           0.15 |                          1.5 |              0.85 |           0.03 | True                         | False                         |                           -0.25 |            20000000 |                              nan |           604 |                 215 |               87 | 14.40%           | 1.47%                        | 40.00%              | -14.65%                 | 60.00%          | 32.00%              | 0.00%               | 8.00%            | 12.00%                    | 28.00%                    | 1.92%                                       | 0.62%                                                | -0.43%                                             | max_drawdown_lte_minus_35pct, win_rate_lt_45pct                                                                                      |
|             49 | NANO_RESEARCH_ONLY_NOT_TRADABLE |               13.5769 |           1    |                          1   |              0.7  |           0    | True                         | True                          |                           -0.35 |            10000000 |                               20 |           604 |                 545 |              545 | 90.23%           | 1.83%                        | 42.36%              | -18.92%                 | 56.65%          | 33.99%              | 2.46%               | 6.90%            | 10.84%                    | 29.06%                    | 1.65%                                       | 1.51%                                                | -0.46%                                             | max_drawdown_lte_minus_35pct, win_rate_lt_45pct                                                                                      |

## Worst And Best Realized Trades

- Worst realized trade: 2024-12-30 BBAI -18.92% STOP
- Best realized trade: 2025-01-24 OKLO 37.76% TARGET_1

## Common Fail Reasons

| fail_reason                                             |   count |
|:--------------------------------------------------------|--------:|
| win_rate_lt_45pct                                       |      47 |
| ending_equity_excluding_best_trade_lte_starting_capital |      42 |
| profit_factor_lte_1_15                                  |      32 |
| ending_equity_lte_120                                   |      29 |
| executed_trade_count_lt_20                              |      26 |
| max_drawdown_lte_minus_35pct                            |      17 |
| top_ticker_profit_share_above_50pct                     |      14 |
| traded_ticker_count_lt_5                                |       4 |

## Warning

Phoenix remains not live-tradable unless a candidate passes all gates and GPT reviews it.
