# Phoenix AlphaLab Regime Diagnostics

Regime tags use only signal-date or prior OHLCV data. No regime gate is applied in this run.

| regime           | bucket   |   trade_count |   avg_realized_excess_return |   realized_win_rate |   stop_hit_rate |   target_1_hit_rate |   target_2_hit_rate |   time_exit_rate |
|:-----------------|:---------|--------------:|-----------------------------:|--------------------:|----------------:|--------------------:|--------------------:|-----------------:|
| spy_above_50dma  | False    |          2149 |                    0.0056922 |            0.400186 |        0.581201 |            0.312238 |           0         |        0.106561  |
| spy_above_50dma  | True     |          9728 |                    0.015873  |            0.444387 |        0.546155 |            0.35516  |           0.0231291 |        0.0755551 |
| spy_above_200dma | False    |           959 |                    0.016569  |            0.511992 |        0.488008 |            0.419187 |           0         |        0.092805  |
| spy_above_200dma | True     |         10918 |                    0.013808  |            0.429749 |        0.558161 |            0.341088 |           0.0206082 |        0.0801429 |
