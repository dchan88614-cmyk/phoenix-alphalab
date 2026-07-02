PHOENIX NANO PHASE 1C — ROBUSTNESS FAILURE ANALYSIS AND CLOSE-STOP REALISM

Research/manual-review only. Do not start paper trading or live trading.

## Phase 1B Recap

- Phase 1B found close_based_stop_2_0x promising on the baseline sample but not approved.
- Phase 1C keeps ticker/date selections frozen and tests robustness plus stop realism.

## Policy Robustness Matrix Summary

| policy                                            |   samples |   median_ending_account_value |   worst_ending_account_value |   median_max_drawdown |   worst_max_drawdown |   median_trade_accuracy |   passing_samples |   intraday_breach_rate |
|:--------------------------------------------------|----------:|------------------------------:|-----------------------------:|----------------------:|---------------------:|------------------------:|------------------:|-----------------------:|
| baseline_current                                  |        10 |                       185.825 |                      43.1615 |             -0.372696 |            -0.641373 |                0.426471 |                 2 |               0.637218 |
| close_based_stop_2_0x                             |        10 |                       175.099 |                      41.1902 |             -0.423737 |            -0.670633 |                0.519231 |                 3 |               0.538462 |
| close_based_stop_2_0x_with_intraday_breach_flag   |        10 |                       175.099 |                      41.1902 |             -0.423737 |            -0.670633 |                0.519231 |                 3 |               0.538462 |
| hybrid_close_stop_2_0x_intraday_catastrophic_3_0x |        10 |                       154.153 |                      30.52   |             -0.489492 |            -0.710487 |                0.519231 |                 2 |               0.538462 |
| close_confirmed_stop_2_0x_next_open_exit          |        10 |                       144.079 |                      35.4391 |             -0.581754 |            -0.715912 |                0.49     |                 1 |               0.562609 |
| atr_stop_2_5x                                     |        10 |                       131.422 |                      34.3749 |             -0.518063 |            -0.689888 |                0.49913  |                 2 |               0.395652 |
| atr_stop_2_0x                                     |        10 |                       118.772 |                      34.1119 |             -0.485822 |            -0.702679 |                0.407407 |                 1 |               0.566239 |
| time_exit_20d_no_intraday_stop                    |        10 |                       101.638 |                      15.1645 |             -0.667325 |            -0.848355 |                0.472136 |                 0 |               0        |

- Best policy by median ending value: baseline_current
- Best realistic policy after intraday-breach penalties: baseline_current
- Close-stop realism warnings: 234
- Intraday breaches ignored by close-stop candidates: 223

## Worst Sample Per Policy

| policy                                            |   sample_id |   ending_account_value |   max_drawdown |
|:--------------------------------------------------|------------:|-----------------------:|---------------:|
| atr_stop_2_0x                                     |           4 |                34.1119 |      -0.702679 |
| atr_stop_2_5x                                     |           4 |                34.3749 |      -0.689888 |
| baseline_current                                  |           4 |                43.1615 |      -0.641373 |
| close_based_stop_2_0x                             |           3 |                41.1902 |      -0.603784 |
| close_based_stop_2_0x_with_intraday_breach_flag   |           3 |                41.1902 |      -0.603784 |
| close_confirmed_stop_2_0x_next_open_exit          |           3 |                35.4391 |      -0.715912 |
| hybrid_close_stop_2_0x_intraday_catastrophic_3_0x |           3 |                30.52   |      -0.710487 |
| time_exit_20d_no_intraday_stop                    |           4 |                15.1645 |      -0.848355 |

## Sample 3 And 4 Failure Explanation

Failing trades concentrated in tickers {'SMR': 6, 'BBAI': 4, 'F': 4, 'INTC': 3, 'CCJ': 3, 'AFRM': 2, 'HPE': 2, 'HOOD': 2}. Theme counts: {'unmapped': 22, 'EV / mobility': 8, 'space / defense / nuclear': 5, 'crypto-adjacent / high beta': 5, 'AI / software': 5}. Average entry gap among captured failing trades: 0.50%.

## Close-Based Stop Realism Findings

Close-stop realism rows: 340. Intraday breaches: 223. Warning mix: {'NO_WARNING': 106, 'CLOSE_STOP_REQUIRES_NEXT_OPEN_SLIPPAGE': 84, 'POLICY_TOO_OPTIMISTIC_FOR_RESEARCH_GATE': 83, 'INTRADAY_STOP_BREACH_IGNORED_BY_CLOSE_STOP': 56, 'GAP_BEYOND_STOP': 11}.

## Regime And Theme Attribution

Worst period-policy rows: 1/2025-10/time_exit_20d_no_intraday_stop/BBAI:-142.60; 0/2025-06/hybrid_close_stop_2_0x_intraday_catastrophic_3_0x/CORZ:-122.20; 0/2025-06/close_based_stop_2_0x/RKLB:-113.04; 0/2025-06/close_based_stop_2_0x_with_intraday_breach_flag/RKLB:-113.04; 6/2025-06/hybrid_close_stop_2_0x_intraday_catastrophic_3_0x/CORZ:-110.25

## Entry Rule vs Execution Rule

Current evidence points to entry-rule weakness in multiple deterministic samples, not just exit mechanics.

## Phase 1C Status: PHASE_1C_EXECUTION_HYPOTHESIS_NEEDS_REALISM_WORK

Do not start paper trading or live trading.

## Next Research Task Recommendation

Analyze failing samples 3 and 4 at entry-rule level before considering any execution-policy adoption.
