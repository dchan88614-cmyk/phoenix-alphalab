PHOENIX NANO PHASE 1B — EXECUTION RISK AND DRAWDOWN DIAGNOSTICS

Research/manual-review only. Do not start paper trading or live trading.

## Baseline Phase 1A Recap

- Replay rounds: 100
- BUY count: 34
- NO_TRADE count: 66
- 20d accuracy: 58.82%
- Ending account value: $179.61
- Max drawdown: -45.86%
- Trade-simulation accuracy: 41.18%

## Core Problem Diagnosis

- Stopped-out-then-20d-positive count: 7
- Stopped-out-then-20d-positive rate: 20.59%
- Best diagnostic policy: close_based_stop_2_0x
- Phase 1B status: PHASE_1B_EXECUTION_POLICY_PROMISING_NOT_APPROVED

## Exit Policy Comparison

| policy                         |   buy_count |   executed_count |   win_rate |   trade_simulation_accuracy |   average_win |   average_loss |   profit_factor |   ending_account_value |   max_drawdown |   worst_trade_account_loss |   stop_count |   target_1_count |   target_2_count |   time_exit_count |   median_holding_days |   average_entry_gap_pct | stopped_trades_20d_positive_pct   |   ending_value_excluding_best_trade |   top_ticker_profit_share | top_ticker_profit_gt_50pct   |
|:-------------------------------|------------:|-----------------:|-----------:|----------------------------:|--------------:|---------------:|----------------:|-----------------------:|---------------:|---------------------------:|-------------:|-----------------:|-----------------:|------------------:|----------------------:|------------------------:|:----------------------------------|------------------------------------:|--------------------------:|:-----------------------------|
| baseline_current               |          34 |               34 |   0.411765 |                    0.411765 |       24.8419 |       -13.4087 |         1.29687 |                179.612 |      -0.458637 |                  -0.11661  |           20 |               11 |                2 |                 1 |                   4   |              0.0105451  | 0.35                              |                            135.419  |                  0.163582 | False                        |
| atr_stop_1_5x                  |          34 |               34 |   0.411765 |                    0.411765 |       24.8419 |       -13.4087 |         1.29687 |                179.612 |      -0.458637 |                  -0.11661  |           20 |               11 |                2 |                 1 |                   4   |              0.0105451  | 0.35                              |                            135.419  |                  0.163582 | False                        |
| atr_stop_2_0x                  |          34 |               27 |   0.444444 |                    0.444444 |       40.5901 |       -22.8795 |         1.41927 |                243.889 |      -0.5245   |                  -0.129312 |           14 |                8 |                1 |                 4 |                   8   |              0.0105677  | 0.2857142857142857                |                            175.016  |                  0.1414   | False                        |
| atr_stop_2_5x                  |          34 |               25 |   0.52     |                    0.52     |       40.2684 |       -27.4128 |         1.59138 |                294.535 |      -0.364077 |                  -0.163736 |           10 |                8 |                0 |                 7 |                  16   |              0.0114421  | 0.3                               |                            212.743  |                  0.172949 | False                        |
| atr_stop_3_0x                  |          34 |               24 |   0.5      |                    0.5      |       35.1821 |       -28.961  |         1.21481 |                174.653 |      -0.64759  |                  -0.195093 |            9 |                6 |                0 |                 9 |                  14   |              0.0127777  | 0.2222222222222222                |                             86.3403 |                  0.265078 | False                        |
| time_exit_20d_no_intraday_stop |          34 |               19 |   0.578947 |                    0.578947 |       32.6008 |       -28.2333 |         1.5877  |                232.742 |      -0.453535 |                  -0.187906 |            0 |                0 |                0 |                19 |                  20   |              0.00852901 | <NA>                              |                            162.179  |                  0.300995 | False                        |
| close_based_stop_1_5x          |          34 |               30 |   0.433333 |                    0.433333 |       34.9724 |       -18.2487 |         1.46551 |                244.415 |      -0.472134 |                  -0.10111  |           16 |               10 |                2 |                 2 |                   5.5 |              0.00930543 | 0.3125                            |                            170.759  |                  0.19343  | False                        |
| close_based_stop_2_0x          |          34 |               26 |   0.538462 |                    0.538462 |       54.4284 |       -31.5336 |         2.01372 |                483.594 |      -0.314583 |                  -0.137282 |           11 |                9 |                1 |                 5 |                   8   |              0.0134592  | 0.2727272727272727                |                            355.084  |                  0.16865  | False                        |

## Drawdown Attribution

- Worst drawdown period: 2025-05-16 to 2026-03-30
- Worst drawdown: -45.86%
- Trades inside worst drawdown: 2025-06-09:RKLB:-24.85, 2025-06-27:CORZ:-20.60, 2025-07-16:JOBY:38.24, 2025-08-19:INTC:-18.61, 2025-09-05:RIVN:-16.02, 2025-09-23:BBAI:-21.22, 2025-10-10:PATH:-19.08, 2025-10-28:SOFI:-14.29, 2025-11-05:RIVN:24.31, 2025-12-02:INTC:-11.82, 2026-01-08:F:-4.61, 2026-01-27:CORZ:-12.55, 2026-02-04:HPE:-7.93, 2026-03-19:RIVN:-12.55
- Ending value excluding best trade: $135.42
- Max drawdown excluding worst trade: -40.45%
- Removing best trade leaves ending value above $105: True
- Removing worst trade improves max drawdown above -35%: False

## Ticker Concentration Analysis

- Top ticker profit share: 16.36%
- Top ticker loss share: 15.88%
- Any one ticker contributes more than 50% of total profit: False
- Any one ticker contributes more than 50% of total loss: False

| ticker   |   selection_count |   total_pnl_dollars |   average_pnl_dollars |   win_rate |   worst_trade_pnl_dollars |   worst_account_return_pct |   contribution_to_total_profit_pct |   contribution_to_total_loss_pct |   max_consecutive_losses |
|:---------|------------------:|--------------------:|----------------------:|-----------:|--------------------------:|---------------------------:|-----------------------------------:|---------------------------------:|-------------------------:|
| HOOD     |                 2 |            56.8917  |             28.4459   |   1        |                  12.6985  |                  0.114611  |                          0.163582  |                        0         |                        0 |
| ACHR     |                 1 |            41.2685  |             41.2685   |   1        |                  41.2685  |                  0.184394  |                          0.11866   |                        0         |                        0 |
| OKLO     |                 1 |            40.1199  |             40.1199   |   1        |                  40.1199  |                  0.267957  |                          0.115358  |                        0         |                        0 |
| JOBY     |                 1 |            38.2357  |             38.2357   |   1        |                  38.2357  |                  0.174091  |                          0.10994   |                        0         |                        0 |
| HPE      |                 4 |            29.4169  |              7.35423  |   0.5      |                  -7.99746 |                 -0.0543414 |                          0.13037   |                        0.0593798 |                        2 |
| IREN     |                 1 |            26.4344  |             26.4344   |   1        |                  26.4344  |                  0.218943  |                          0.0760075 |                        0         |                        0 |
| PLTR     |                 3 |            23.8944  |              7.96481  |   0.666667 |                  -6.84715 |                 -0.0491987 |                          0.0883921 |                        0.0255324 |                        1 |
| AI       |                 1 |            23.322   |             23.322    |   1        |                  23.322   |                  0.13552   |                          0.0670584 |                        0         |                        0 |
| CCJ      |                 1 |            10.2875  |             10.2875   |   1        |                  10.2875  |                  0.0775091 |                          0.0295799 |                        0         |                        0 |
| SMCI     |                 3 |            -2.54554 |             -0.848514 |   0.333333 |                  -8.28234 |                 -0.087271  |                          0.0311488 |                        0.0498879 |                        2 |
| RIVN     |                 3 |            -4.25915 |             -1.41972  |   0.333333 |                 -16.0249  |                 -0.0803947 |                          0.0699023 |                        0.106536  |                        1 |
| F        |                 2 |           -10.9476  |             -5.47378  |   0        |                  -6.33965 |                 -0.044329  |                          0         |                        0.0408225 |                        2 |
| SOFI     |                 1 |           -14.2869  |            -14.2869   |   0        |                 -14.2869  |                 -0.0781023 |                          0         |                        0.0532748 |                        1 |
| KTOS     |                 1 |           -15.8018  |            -15.8018   |   0        |                 -15.8018  |                 -0.0659486 |                          0         |                        0.0589235 |                        1 |
| NVAX     |                 1 |           -15.9376  |            -15.9376   |   0        |                 -15.9376  |                 -0.11661   |                          0         |                        0.0594298 |                        1 |
| PATH     |                 1 |           -19.083   |            -19.083    |   0        |                 -19.083   |                 -0.0944662 |                          0         |                        0.0711589 |                        1 |
| BBAI     |                 1 |           -21.2192  |            -21.2192   |   0        |                 -21.2192  |                 -0.0950562 |                          0         |                        0.0791246 |                        1 |
| INTC     |                 2 |           -30.4354  |            -15.2177   |   0        |                 -18.6133  |                 -0.0721819 |                          0         |                        0.113491  |                        2 |
| CORZ     |                 2 |           -33.145   |            -16.5725   |   0        |                 -20.5983  |                 -0.0857444 |                          0         |                        0.123595  |                        2 |
| RKLB     |                 2 |           -42.598   |            -21.299    |   0        |                 -24.8451  |                 -0.093729  |                          0         |                        0.158844  |                        2 |

## Sample Robustness

|   sample_id |   replay_rounds |   buy_count |   accuracy_20d |   baseline_ending_account_value |   baseline_max_drawdown |   baseline_trade_simulation_accuracy | best_alternative_policy   | any_policy_achieved_phase1b_gates   |
|------------:|----------------:|------------:|---------------:|--------------------------------:|------------------------:|-------------------------------------:|:--------------------------|:------------------------------------|
|           0 |             100 |          34 |       0.588235 |                        179.612  |               -0.458637 |                             0.411765 | close_based_stop_2_0x     | True                                |
|           1 |             100 |          34 |       0.529412 |                        325.241  |               -0.270413 |                             0.588235 | close_based_stop_2_0x     | True                                |
|           2 |             100 |          36 |       0.583333 |                        287.056  |               -0.347746 |                             0.5      | baseline_current          | True                                |
|           3 |             100 |          38 |       0.526316 |                         60.4946 |               -0.614961 |                             0.289474 |                           | False                               |
|           4 |             100 |          32 |       0.4375   |                         43.1615 |               -0.641373 |                             0.258065 |                           | False                               |

## Next Research Task Recommendation

Run a drawdown-focused Phase 1C that keeps selection frozen and tests entry timing / stop placement only if GPT approves.

