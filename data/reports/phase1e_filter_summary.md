PHOENIX NANO PHASE 1E — CROSS-VALIDATED CONSERVATIVE FILTER VALIDATION

Research-only. This does not change daily scan behavior and does not approve execution.

## Phase 1D Recap

- Phase 1D found promising but unapproved volatility plus smoke-score filter hypotheses.
- Phase 1E calibrates thresholds on calibration samples and validates frozen filters on holdout samples.

## Sample Split Used

- Calibration samples: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- Holdout samples: [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
- Fallback split used: False

## Filters Tested

- Threshold-sweep filters tested: 22
- Baseline, Phase 1D fixed candidate, 20 volatility/smoke threshold combinations, and overlays for selected filters.

## Calibration Results

| filter_name                         |   sample_count |   volatility_20d_max |   smoke_score_min | filter_description                                                         |   median_ending_account_value |   worst_sample_ending_account_value |   median_max_drawdown |   worst_sample_max_drawdown |   median_simulated_win_rate |   worst_sample_simulated_win_rate |   median_buy_count |   minimum_buy_count |   median_20d_average_return |   median_profit_factor |   excluded_loser_count |   excluded_winner_count |   max_top_ticker_profit_share |   max_top_ticker_loss_share | split       | calibration_gate_pass   |
|:------------------------------------|---------------:|---------------------:|------------------:|:---------------------------------------------------------------------------|------------------------------:|------------------------------------:|----------------------:|----------------------------:|----------------------------:|----------------------------------:|-------------------:|--------------------:|----------------------------:|-----------------------:|-----------------------:|------------------------:|------------------------------:|----------------------------:|:------------|:------------------------|
| vol_0.055_smoke_0.900               |             10 |               0.055  |            0.9    | Require volatility_20d <= 0.055 and smoke_score >= 0.900.                  |                       143.845 |                            114.723  |             -0.218384 |                   -0.297105 |                    0.541958 |                          0.333333 |               12   |                  10 |                   0.0573298 |                2.0414  |                    139 |                      82 |                      0.466752 |                    0.518431 | calibration | False                   |
| vol_0.055_smoke_0.940               |             10 |               0.055  |            0.94   | Require volatility_20d <= 0.055 and smoke_score >= 0.940.                  |                       136.92  |                            114.042  |             -0.149529 |                   -0.239761 |                    0.571429 |                          0.333333 |                6.5 |                   4 |                   0.0580718 |                2.49615 |                    169 |                     112 |                      0.698575 |                    1        | calibration | False                   |
| phase1d_volatility_plus_smoke_score |             10 |               0.0697 |            0.8839 | Phase 1D fixed filter: volatility_20d <= 0.0697 and smoke_score >= 0.8839. |                       146.679 |                            113.873  |             -0.266855 |                   -0.347193 |                    0.48913  |                          0.333333 |               18   |                  16 |                   0.0534492 |                1.45662 |                    100 |                      57 |                      0.474206 |                    0.380885 | calibration | False                   |
| vol_0.055_smoke_0.880               |             10 |               0.055  |            0.88   | Require volatility_20d <= 0.055 and smoke_score >= 0.880.                  |                       148.545 |                            113.281  |             -0.195959 |                   -0.339614 |                    0.5      |                          0.333333 |               14   |                  12 |                   0.0536898 |                1.82437 |                    128 |                      76 |                      0.417359 |                    0.422053 | calibration | False                   |
| vol_0.065_smoke_0.900               |             10 |               0.065  |            0.9    | Require volatility_20d <= 0.065 and smoke_score >= 0.900.                  |                       165.425 |                            112.828  |             -0.222448 |                   -0.3067   |                    0.5      |                          0.3125   |               15.5 |                  13 |                   0.056851  |                1.81109 |                    117 |                      66 |                      0.329363 |                    0.273641 | calibration | False                   |
| vol_0.070_smoke_0.880               |             10 |               0.07   |            0.88   | Require volatility_20d <= 0.070 and smoke_score >= 0.880.                  |                       146.679 |                            106.065  |             -0.29235  |                   -0.344188 |                    0.48913  |                          0.315789 |               19   |                  17 |                   0.0492228 |                1.45662 |                     96 |                      55 |                      0.474206 |                    0.381897 | calibration | False                   |
| vol_0.070_smoke_0.900               |             10 |               0.07   |            0.9    | Require volatility_20d <= 0.070 and smoke_score >= 0.900.                  |                       178.465 |                            100.346  |             -0.265674 |                   -0.347193 |                    0.511905 |                          0.3125   |               16.5 |                  14 |                   0.05336   |                1.83421 |                    111 |                      61 |                      0.447742 |                    0.380885 | calibration | False                   |
| vol_0.055_smoke_0.920               |             10 |               0.055  |            0.92   | Require volatility_20d <= 0.055 and smoke_score >= 0.920.                  |                       143.649 |                            100.111  |             -0.17564  |                   -0.269972 |                    0.555556 |                          0.272727 |                9   |                   5 |                   0.0437064 |                2.3116  |                    158 |                     102 |                      0.59228  |                    0.612371 | calibration | False                   |
| vol_0.060_smoke_0.920               |             10 |               0.06   |            0.92   | Require volatility_20d <= 0.060 and smoke_score >= 0.920.                  |                       159.582 |                             99.2946 |             -0.164554 |                   -0.269972 |                    0.569444 |                          0.272727 |               10.5 |                   6 |                   0.0667763 |                2.55871 |                    149 |                      92 |                      0.59228  |                    0.52021  | calibration | False                   |
| vol_0.060_smoke_0.880               |             10 |               0.06   |            0.88   | Require volatility_20d <= 0.060 and smoke_score >= 0.880.                  |                       158.025 |                             96.104  |             -0.229174 |                   -0.352972 |                    0.5      |                          0.333333 |               16   |                  13 |                   0.0659788 |                1.88607 |                    119 |                      66 |                      0.36006  |                    0.301969 | calibration | False                   |

## Selected Holdout Filters

- vol_0.055_smoke_0.900
- vol_0.055_smoke_0.940
- phase1d_volatility_plus_smoke_score

## Holdout Results

| filter_name                                                                |   sample_count |   volatility_20d_max |   smoke_score_min | filter_description                                                                                                     |   median_ending_account_value |   worst_sample_ending_account_value |   median_max_drawdown |   worst_sample_max_drawdown |   median_simulated_win_rate |   worst_sample_simulated_win_rate |   median_buy_count |   minimum_buy_count |   median_20d_average_return |   median_profit_factor |   excluded_loser_count |   excluded_winner_count |   max_top_ticker_profit_share |   max_top_ticker_loss_share | split   | calibration_gate_pass   | phase1e_holdout_gate_pass   | phase1e_status_candidate        |
|:---------------------------------------------------------------------------|---------------:|---------------------:|------------------:|:-----------------------------------------------------------------------------------------------------------------------|------------------------------:|------------------------------------:|----------------------:|----------------------------:|----------------------------:|----------------------------------:|-------------------:|--------------------:|----------------------------:|-----------------------:|-----------------------:|------------------------:|------------------------------:|----------------------------:|:--------|:------------------------|:----------------------------|:--------------------------------|
| vol_0.055_smoke_0.900_theme_cap_3_overlay                                  |             10 |               0.055  |            0.9    | vol_0.055_smoke_0.900 plus at most 3 accepted BUY decisions per deterministic theme per sample.                        |                       127.377 |                            100.796  |             -0.187887 |                   -0.252035 |                    0.449495 |                          0.3      |               11   |                   9 |                   0.0554961 |                1.60398 |                    129 |                      87 |                      0.756645 |                    0.481308 | holdout | False                   | False                       | PHASE_1E_FILTER_NEEDS_MORE_WORK |
| vol_0.055_smoke_0.900                                                      |             10 |               0.055  |            0.9    | Require volatility_20d <= 0.055 and smoke_score >= 0.900.                                                              |                       133.639 |                             99.3563 |             -0.205622 |                   -0.27813  |                    0.461538 |                          0.307692 |               12.5 |                   9 |                   0.0506494 |                1.74075 |                    121 |                      78 |                      0.659438 |                    0.41979  | holdout | False                   | False                       | PHASE_1E_FILTER_NEEDS_MORE_WORK |
| vol_0.055_smoke_0.900_repeated_loser_ticker_cooldown_overlay               |             10 |               0.055  |            0.9    | vol_0.055_smoke_0.900 plus 60 calendar day cooldown after prior accepted losing simulated ticker result.               |                       132.275 |                             99.3563 |             -0.218682 |                   -0.27813  |                    0.430556 |                          0.307692 |               10.5 |                   9 |                   0.0467863 |                1.75265 |                    125 |                      83 |                      0.659438 |                    0.401128 | holdout | False                   | False                       | PHASE_1E_FILTER_NEEDS_MORE_WORK |
| vol_0.055_smoke_0.940                                                      |             10 |               0.055  |            0.94   | Require volatility_20d <= 0.055 and smoke_score >= 0.940.                                                              |                       137.949 |                             97.9992 |             -0.158354 |                   -0.251459 |                    0.5      |                          0.285714 |                6.5 |                   4 |                   0.0469918 |                2.46479 |                    157 |                     104 |                      0.599938 |                    1        | holdout | False                   | False                       | PHASE_1E_FILTER_NEEDS_MORE_WORK |
| vol_0.055_smoke_0.940_repeated_loser_ticker_cooldown_overlay               |             10 |               0.055  |            0.94   | vol_0.055_smoke_0.940 plus 60 calendar day cooldown after prior accepted losing simulated ticker result.               |                       138.28  |                             97.9992 |             -0.158354 |                   -0.204814 |                    0.571429 |                          0.285714 |                6.5 |                   4 |                   0.047685  |                2.56657 |                    159 |                     104 |                      0.599938 |                    1        | holdout | False                   | False                       | PHASE_1E_FILTER_NEEDS_MORE_WORK |
| vol_0.055_smoke_0.940_theme_cap_3_overlay                                  |             10 |               0.055  |            0.94   | vol_0.055_smoke_0.940 plus at most 3 accepted BUY decisions per deterministic theme per sample.                        |                       126.196 |                             97.9992 |             -0.158354 |                   -0.251459 |                    0.5      |                          0.285714 |                6.5 |                   4 |                   0.047685  |                2.46479 |                    157 |                     106 |                      0.756645 |                    1        | holdout | False                   | False                       | PHASE_1E_FILTER_NEEDS_MORE_WORK |
| phase1d_volatility_plus_smoke_score                                        |             10 |               0.0697 |            0.8839 | Phase 1D fixed filter: volatility_20d <= 0.0697 and smoke_score >= 0.8839.                                             |                       131.213 |                             94.4382 |             -0.279917 |                   -0.345422 |                    0.4625   |                          0.3125   |               16.5 |                  15 |                   0.0343919 |                1.3257  |                     89 |                      57 |                      0.444389 |                    0.329883 | holdout | False                   | False                       | PHASE_1E_FILTER_NEEDS_MORE_WORK |
| phase1d_volatility_plus_smoke_score_repeated_loser_ticker_cooldown_overlay |             10 |               0.0697 |            0.8839 | phase1d_volatility_plus_smoke_score plus 60 calendar day cooldown after prior accepted losing simulated ticker result. |                       130.85  |                             94.4382 |             -0.239026 |                   -0.437385 |                    0.48913  |                          0.3125   |               15.5 |                  14 |                   0.0375654 |                1.44661 |                     96 |                      64 |                      0.444389 |                    0.246621 | holdout | False                   | False                       | PHASE_1E_FILTER_NEEDS_MORE_WORK |
| phase1d_volatility_plus_smoke_score_theme_cap_3_overlay                    |             10 |               0.0697 |            0.8839 | phase1d_volatility_plus_smoke_score plus at most 3 accepted BUY decisions per deterministic theme per sample.          |                       119.386 |                             77.2371 |             -0.224176 |                   -0.304991 |                    0.400327 |                          0.307692 |               13   |                  11 |                   0.0502612 |                1.25203 |                    112 |                      73 |                      0.578292 |                    0.389742 | holdout | False                   | False                       | PHASE_1E_FILTER_NEEDS_MORE_WORK |

- `volatility_plus_smoke_score` survived holdout: False

## Overlays

Theme-cap and repeated-loser cooldown overlays were tested only for selected calibration filters. They remain offline diagnostics and are not active policy.

## Excluded Winner vs Loser Summary

- Excluded losers: 6323
- Excluded winners: 3966

## Top Remaining Failure Samples

|   sample_id | filter_name                |   ending_account_value |   max_drawdown |
|------------:|:---------------------------|-----------------------:|---------------:|
|           4 | no_filter_baseline_current |                43.1615 |      -0.641373 |
|          16 | no_filter_baseline_current |                56.6977 |      -0.571967 |
|          10 | no_filter_baseline_current |                57.5263 |      -0.675726 |
|           3 | no_filter_baseline_current |                60.4946 |      -0.614961 |
|           3 | vol_0.075_smoke_0.940      |                66.2222 |      -0.458146 |
|           3 | vol_0.075_smoke_0.900      |                76.0255 |      -0.391675 |
|           3 | vol_0.075_smoke_0.920      |                80.0482 |      -0.319887 |
|          14 | vol_0.075_smoke_0.920      |                80.0798 |      -0.409584 |
|          16 | vol_0.075_smoke_0.920      |                80.6702 |      -0.313666 |
|          10 | vol_0.075_smoke_0.900      |                82.159  |      -0.348252 |

## Top Remaining Failure Tickers/Themes

Top losing themes: UNMAPPED:124, EV / mobility:65, AI / software:57, semiconductor / hardware:52, space / defense / nuclear:47, crypto-adjacent / high beta:40

Top losing tickers: RIVN:29, RKLB:27, F:24, INTC:24, BBAI:23, XPEV:23, HPE:19, CORZ:19

## Final Phase 1E Status: PHASE_1E_FILTER_NEEDS_MORE_WORK

Do not start paper execution or real-money execution.

## Next Research Task Recommendation

Ask GPT to review whether Phase 1E failure patterns justify stopping Nano entry-filter tuning or running one narrower failure-regime analysis.
