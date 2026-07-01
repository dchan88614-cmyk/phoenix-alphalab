# Phoenix Nano Candidate 34 Frozen Rules

Research only. Candidate 34 is not approved for paper trading or live trading.

- Source: `data/reports/auto_research_generations.csv`
- Frozen timestamp UTC: 2026-07-01T22:01:41.786253+00:00

## Candidate Rule

| parameter                      |   value |
|:-------------------------------|--------:|
| candidate_id                   |  34     |
| max_buy_rate                   |   0.3   |
| min_relative_volume_prev20     |   1.5   |
| min_smoke_score                |   0.85  |
| min_rank_gap                   |   0     |
| require_return_5d_positive     |   1     |
| require_return_20d_positive    |   0     |
| distance_to_52w_high_prev_min  |  -0.35  |
| dollar_volume_min              |   2e+07 |
| max_trades_per_ticker_per_year |         |
| max_entry_price                |  50     |

## Account Settings

| parameter             |   value |
|:----------------------|--------:|
| starting_capital      |     100 |
| fractional_shares     |       0 |
| max_position_fraction |       1 |
| min_cash_reserve      |       0 |
| commission_per_trade  |       0 |
| slippage_bps          |      10 |

## Simulator Logic

- Entry reference for daily scan: latest completed EOD close.
- Stop loss: close - 1.5 * ATR, or 8% below close when ATR is unavailable.
- Target 1: entry + 2R.
- Target 2: entry + 4R.
- Expected holding period: up to 20 trading days.
- Affordability: $100 whole-share account after slippage.
- Forward returns and realized trade outcomes are not daily scan inputs.

## Historical Nano Summary

| metric                   | value                            |
|:-------------------------|:---------------------------------|
| candidate_id             | 34                               |
| nano_status              | NANO_RESEARCH_QUALIFIED_NOT_LIVE |
| executed_trade_count     | 27                               |
| ending_equity            | 164.06050369351297               |
| max_drawdown             | -0.3129178555485411              |
| profit_factor            | 1.3075217214151942               |
| win_rate                 | 0.4814814814814814               |
| worst_account_trade_loss | -0.1177980686430113              |
