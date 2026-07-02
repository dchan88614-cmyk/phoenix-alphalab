# Phase 1D Candidate Entry Filters

Offline diagnostics only. These filters use replay-date or entry-date information only and do not change daily scan behavior.

## high_atr_pct

Exclude atr_pct above 0.0691

## high_volatility_20d

Exclude volatility_20d above 0.0697

## extreme_entry_gap_pct

Exclude absolute entry_gap_pct above 0.0362

## minimum_decision_strength

Require decision_strength >= 0.5863

## minimum_smoke_score

Require smoke_score >= 0.8839

## low_relative_volume_prev20

Require relative_volume_prev20 >= 1.8162

## weak_distance_from_high

Require distance_from_52w_high_pct >= -0.1624

## extreme_short_term_runup

Exclude return_5d_prior above 0.3309

## theme_concentration_cap

Within each sample, allow at most 3 entries per deterministic local theme.

## repeated_loser_ticker_cooldown

Within each sample, skip a ticker after its prior baseline losing BUY.

## atr_plus_decision_strength

Combination: high_atr_pct plus minimum_decision_strength.

## volatility_plus_smoke_score

Combination: high_volatility_20d plus minimum_smoke_score.

## risk_stack_filter

Combination: high_atr_pct, high_volatility_20d, and extreme_entry_gap_pct.
