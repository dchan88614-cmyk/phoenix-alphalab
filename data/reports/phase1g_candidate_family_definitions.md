# Phase 1G Candidate Family Definitions

Research-only. No family is approved for daily scan, paper execution, or real-money execution.

## candidate34_frozen_baseline

- Intent: Frozen Candidate 34 baseline.
- Required pre-entry features: Existing Candidate 34 rule from auto research output.
- Exact rule conditions: Existing Candidate 34 rule from auto research output.
- Ranking formula: Existing decision_strength then smoke_score ranking.
- NO_TRADE behavior: NO_TRADE when Candidate 34 has no executable pass.
- Difference from Candidate 34: Baseline, not a redesign.
- Expected failure mode: Known broad instability from Phase 1F.

## candidate35_trend_quality

- Intent: Prioritizes stable uptrend quality.
- Required pre-entry features: close >= SMA20 >= SMA50, near prior highs, bounded volatility and ATR.
- Exact rule conditions: close >= SMA20 >= SMA50, near prior highs, bounded volatility and ATR.
- Ranking formula: smoke_score + distance_to_52w_high_prev - volatility_20d.
- NO_TRADE behavior: NO_TRADE when trend stack or risk bounds fail.
- Difference from Candidate 34: Adds explicit trend-quality gates absent from Candidate 34.
- Expected failure mode: May miss early turnarounds and high-beta breakouts.

## candidate35_pullback_continuation

- Intent: Controlled pullback inside broader uptrend.
- Required pre-entry features: close above SMA50, positive 20d return, bounded 5d pullback/spike, bounded volatility and ATR.
- Exact rule conditions: close above SMA50, positive 20d return, bounded 5d pullback/spike, bounded volatility and ATR.
- Ranking formula: smoke_score + return_20d - abs(return_5d).
- NO_TRADE behavior: NO_TRADE when pullback is too sharp or too extended.
- Difference from Candidate 34: Avoids chasing short-term spikes.
- Expected failure mode: May under-trade strong momentum regimes.

## candidate35_breakout_confirmation

- Intent: Breakout or momentum confirmation.
- Required pre-entry features: Near 20d high, positive 20d return, relative volume or 5d strength confirmation, blocks extreme extension.
- Exact rule conditions: Near 20d high, positive 20d return, relative volume or 5d strength confirmation, blocks extreme extension.
- Ranking formula: smoke_score + relative-volume rank + return_5d.
- NO_TRADE behavior: NO_TRADE when confirmation or extension gates fail.
- Difference from Candidate 34: Requires confirmation beyond Candidate 34 ranks.
- Expected failure mode: Can still chase false breakouts.

## candidate35_regime_gated_momentum

- Intent: Momentum with SPY/QQQ regime awareness.
- Required pre-entry features: Uses replay-date SPY/QQQ labels; stricter in mixed/risk-off regimes.
- Exact rule conditions: Uses replay-date SPY/QQQ labels; stricter in mixed/risk-off regimes.
- Ranking formula: smoke_score + return_5d + return_20d - volatility_20d.
- NO_TRADE behavior: NO_TRADE more often in weak regimes.
- Difference from Candidate 34: Adds market-regime gate.
- Expected failure mode: May over-filter and become regime-dependent.

## candidate35_low_volatility_compounder

- Intent: Lower-volatility growth/momentum candidates.
- Required pre-entry features: volatility_20d and ATR pct caps, smoke score, positive 20d return, not far below highs.
- Exact rule conditions: volatility_20d and ATR pct caps, smoke score, positive 20d return, not far below highs.
- Ranking formula: smoke_score - volatility_20d - atr_pct.
- NO_TRADE behavior: NO_TRADE when low-volatility quality gates fail.
- Difference from Candidate 34: Intentionally avoids high-beta watchlist names.
- Expected failure mode: May trade too rarely in speculative universes.
