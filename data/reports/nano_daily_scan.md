PHOENIX NANO DAILY SCAN
Action: NO_TRADE_MANUAL_REVIEW
Status: RESEARCH_ONLY_NOT_TRADABLE

This is not active paper trading or live trading. It is only a research-derived manual verification candidate.

Ticker: 
Latest data date: 2026-06-30
Reference price: 
Shares with $100: 0
Estimated total cost: $0.00
Estimated cash remaining: $100.00
Stop loss: 
Target 1: 
Target 2: 
Max dollar risk: $0.00
Expected holding period: 
Reason: NO_CANDIDATE_PASSED_RULES

## Rule

- Factor timing: EOD
- Uses only latest-date-safe factors; forward returns and realized trade outcomes are not ranking inputs.
- Account: $100, whole shares only.
- Candidate rule: Candidate 34 Nano with max_entry_price $50.00.
- Executable universe count: 27
- Rejected not affordable count: 56
- Rejected above max entry price count: 70
- Stale data: False
- Data source: yfinance
- Scan timestamp UTC: 2026-07-01T19:57:03.828548+00:00

## Closest Executable Near-Misses

| ticker   |   reference_price |   shares_with_100 |   estimated_total_cost |   estimated_cash_remaining |   smoke_score |   relative_volume_prev20 |   return_5d |   return_20d |   distance_to_52w_high_prev |   dollar_volume | failed_checks                                                                                                    |
|:---------|------------------:|------------------:|-----------------------:|---------------------------:|--------------:|-------------------------:|------------:|-------------:|----------------------------:|----------------:|:-----------------------------------------------------------------------------------------------------------------|
| RIVN     |             17.35 |                 5 |                86.8368 |                   13.1632  |      0.792593 |                 0.967683 |  0.165212   |    0.0235988 |                   -0.235346 |     5.44334e+08 | smoke_score_below_min, relative_volume_prev20_below_min                                                          |
| SDGR     |             16.25 |                 6 |                97.5975 |                    2.4025  |      0.711111 |                 1.84336  |  0.0804521  |    0.028481  |                   -0.315789 |     4.42292e+07 | smoke_score_below_min                                                                                            |
| PATH     |             10.87 |                 9 |                97.9278 |                    2.07217 |      0.681481 |                 1.28981  |  0.0698819  |   -0.170229  |                   -0.452117 |     7.03786e+08 | smoke_score_below_min, rank_gap_below_min, relative_volume_prev20_below_min, distance_to_52w_high_prev_below_min |
| S        |             16.97 |                 5 |                84.9348 |                   15.0652  |      0.674074 |                 0.996414 |  0.121613   |   -0.0471645 |                   -0.207009 |     1.20102e+08 | smoke_score_below_min, rank_gap_below_min, relative_volume_prev20_below_min                                      |
| F        |             13.9  |                 7 |                97.3973 |                    2.6027  |      0.666667 |                 1.03225  | -0.00714288 |   -0.164161  |                   -0.218223 |     8.24391e+08 | smoke_score_below_min, rank_gap_below_min, relative_volume_prev20_below_min, return_5d_not_positive              |

## Rejected Before Nano Ranking

These names were not eligible for Nano ranking because they failed account executability filters before ranking.

| ticker   |   reference_price |   shares_with_100 |   estimated_total_cost | max_entry_price_pass   | affordability_pass   | rejection_reason                                   |
|:---------|------------------:|------------------:|-----------------------:|:-----------------------|:---------------------|:---------------------------------------------------|
| ASML     |           1989.44 |                 0 |                      0 | False                  | False                | not_affordable, above_candidate_34_max_entry_price |
| GEV      |           1174.86 |                 0 |                      0 | False                  | False                | not_affordable, above_candidate_34_max_entry_price |
| MU       |           1154.29 |                 0 |                      0 | False                  | False                | not_affordable, above_candidate_34_max_entry_price |
| AMAT     |            723    |                 0 |                      0 | False                  | False                | not_affordable, above_candidate_34_max_entry_price |
| PWR      |            720.04 |                 0 |                      0 | False                  | False                | not_affordable, above_candidate_34_max_entry_price |
| AMD      |            580.91 |                 0 |                      0 | False                  | False                | not_affordable, above_candidate_34_max_entry_price |
| APP      |            515.23 |                 0 |                      0 | False                  | False                | not_affordable, above_candidate_34_max_entry_price |
| LMT      |            509.46 |                 0 |                      0 | False                  | False                | not_affordable, above_candidate_34_max_entry_price |
| NOC      |            509.31 |                 0 |                      0 | False                  | False                | not_affordable, above_candidate_34_max_entry_price |
| TER      |            483.84 |                 0 |                      0 | False                  | False                | not_affordable, above_candidate_34_max_entry_price |
