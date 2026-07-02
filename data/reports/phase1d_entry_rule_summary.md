PHOENIX NANO PHASE 1D — ENTRY-RULE FAILURE DIAGNOSTICS

Research/manual-review only. This does not change daily scan behavior and does not approve any trading.

## Phase 1C Recap

- Phase 1C found exit-policy tuning was not robust enough across deterministic samples.
- Phase 1D tests whether pre-entry features can identify losing BUY candidates before entry.

## Scope

- Total samples analyzed: 10
- BUY decisions analyzed: 344
- Excluded decision audit rows: 1345

## Winner vs Loser Feature Findings

| feature_name               |   winner_count |   loser_count |   winner_mean |   loser_mean |   simple_separation_score |   missing_rate | notes                                        |
|:---------------------------|---------------:|--------------:|--------------:|-------------:|--------------------------:|---------------:|:---------------------------------------------|
| distance_from_52w_high_pct |            146 |           198 |    -0.044649  |   -0.0752878 |                  0.239548 |     0          | distance_from_52w_high_pct_lower_for_losers  |
| decision_strength          |            146 |           198 |     0.707558  |    0.678832  |                  0.234421 |     0          | decision_strength_lower_for_losers           |
| near_max_entry_price_pct   |            146 |           197 |     0.527141  |    0.473722  |                  0.199483 |     0.00290698 | near_max_entry_price_pct_lower_for_losers    |
| smoke_score                |            146 |           198 |     0.929296  |    0.921007  |                  0.193019 |     0          | smoke_score_lower_for_losers                 |
| return_10d_prior           |            146 |           191 |     0.293451  |    0.333748  |                  0.138716 |     0.0203488  | return_10d_prior_higher_for_losers           |
| relative_volume_prev20     |            146 |           198 |     3.34102   |    2.94341   |                  0.137711 |     0          | relative_volume_prev20_lower_for_losers      |
| distance_from_20d_high_pct |            146 |           198 |    -0.0492907 |   -0.0432216 |                  0.131973 |     0          | distance_from_20d_high_pct_higher_for_losers |
| max_single_day_loss_20d    |            140 |           188 |    -0.0663382 |   -0.0619181 |                  0.128804 |     0.0465116  | max_single_day_loss_20d_higher_for_losers    |
| return_5d_prior            |            146 |           198 |     0.222821  |    0.243299  |                  0.102338 |     0          | return_5d_prior_higher_for_losers            |
| return_20d_prior           |            146 |           198 |     0.415323  |    0.442924  |                  0.064694 |     0          | return_20d_prior_higher_for_losers           |

## Top 5 Suspicious Loser Signals

- distance_from_52w_high_pct: loser_mean=-0.0753, winner_mean=-0.0446, separation=0.2395
- decision_strength: loser_mean=0.6788, winner_mean=0.7076, separation=0.2344
- near_max_entry_price_pct: loser_mean=0.4737, winner_mean=0.5271, separation=0.1995
- smoke_score: loser_mean=0.9210, winner_mean=0.9293, separation=0.1930
- return_10d_prior: loser_mean=0.3337, winner_mean=0.2935, separation=0.1387

## Filters Tested

- high_atr_pct
- high_volatility_20d
- extreme_entry_gap_pct
- minimum_decision_strength
- minimum_smoke_score
- low_relative_volume_prev20
- weak_distance_from_high
- extreme_short_term_runup
- theme_concentration_cap
- repeated_loser_ticker_cooldown
- atr_plus_decision_strength
- volatility_plus_smoke_score
- risk_stack_filter

- Best filter by median ending account value: weak_distance_from_high
- Best filter by worst-sample ending account value: volatility_plus_smoke_score
- Best filter by drawdown reduction: volatility_plus_smoke_score

## Filters That Excluded Too Many Winners

- none

## Theme And Ticker Failure Concentration

Top losing themes: UNMAPPED:62, EV / mobility:33, semiconductor / hardware:27, space / defense / nuclear:27, AI / software:26, crypto-adjacent / high beta:23

Top losing tickers: RIVN:15, RKLB:14, F:12, XPEV:12, INTC:11, IREN:10, HPE:10, CORZ:10

## Fixability Assessment

Conservative filters are offline hypotheses only. Failures look fixable only if a filter improves worst-sample ending value and drawdown without removing too many winners.

## Gate Failures

- weak_distance_from_high: worst ending <= $100, worst drawdown <= -45%, median simulation accuracy < 50%
- minimum_smoke_score: worst ending <= $100, worst drawdown <= -45%, median simulation accuracy < 50%
- minimum_decision_strength: worst ending <= $100, worst drawdown <= -45%, median simulation accuracy < 50%
- high_volatility_20d: worst ending <= $100, median drawdown <= -35%, worst drawdown <= -45%, median simulation accuracy < 50%
- extreme_short_term_runup: worst ending <= $100, worst drawdown <= -45%, median simulation accuracy < 50%

## Phase 1D Status: PHASE_1D_FILTER_HYPOTHESIS_PROMISING_NOT_APPROVED

Do not start paper trading or live trading.

## Next Research Task Recommendation

Ask GPT to review the top suspicious pre-entry signals and select one narrow Phase 1E entry-filter experiment, without loosening Candidate 34.
