# Phoenix AlphaLab Regime Diagnostics

Regime tags use only signal-date or prior OHLCV data. No regime gate is applied in this run.

| regime           | bucket   |   trade_count |   avg_realized_excess_return |   realized_win_rate |   stop_hit_rate |   target_1_hit_rate |   target_2_hit_rate |   time_exit_rate |
|:-----------------|:---------|--------------:|-----------------------------:|--------------------:|----------------:|--------------------:|--------------------:|-----------------:|
| spy_above_50dma  | False    |           346 |                 -0.000372279 |            0.427746 |        0.572254 |            0.245665 |           0         |        0.182081  |
| spy_above_50dma  | True     |          2109 |                  0.000755593 |            0.357041 |        0.636321 |            0.286866 |           0.0128023 |        0.0640114 |
| spy_above_200dma | False    |           150 |                 -0.0336171   |            0.22     |        0.78     |            0.22     |           0         |        0         |
| spy_above_200dma | True     |          2305 |                  0.00282312  |            0.376573 |        0.617354 |            0.285033 |           0.0117137 |        0.0859002 |
