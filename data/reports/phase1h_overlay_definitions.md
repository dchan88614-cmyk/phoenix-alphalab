# Phase 1H Overlay Definitions

Research-only. No overlay is approved for daily scan, paper execution, or real-money execution.

Candidate 35 trend-quality is frozen from Phase 1G. Phase 1H only tests pre-declared risk overlays on top of that frozen sandbox family.

## overlay_market_regime_risk_off_skip

- Intent: Skip when SPY/QQQ regime is clearly weak before replay date.
- Allowed inputs: replay-date candidate features, replay-date SPY/QQQ regime features, and prior closed simulated trade outcomes for cooldown overlays.
- Forward returns are not used for overlay decisions.

## overlay_high_volatility_tail_skip

- Intent: Skip extreme pre-entry ATR or realized volatility tails.
- Allowed inputs: replay-date candidate features, replay-date SPY/QQQ regime features, and prior closed simulated trade outcomes for cooldown overlays.
- Forward returns are not used for overlay decisions.

## overlay_theme_loss_cooldown_5pct_5

- Intent: Skip a theme after a prior closed loss in the same theme.
- Allowed inputs: replay-date candidate features, replay-date SPY/QQQ regime features, and prior closed simulated trade outcomes for cooldown overlays.
- Forward returns are not used for overlay decisions.

## overlay_theme_loss_cooldown_8pct_5

- Intent: Skip a theme after a prior closed loss in the same theme.
- Allowed inputs: replay-date candidate features, replay-date SPY/QQQ regime features, and prior closed simulated trade outcomes for cooldown overlays.
- Forward returns are not used for overlay decisions.

## overlay_theme_loss_cooldown_10pct_5

- Intent: Skip a theme after a prior closed loss in the same theme.
- Allowed inputs: replay-date candidate features, replay-date SPY/QQQ regime features, and prior closed simulated trade outcomes for cooldown overlays.
- Forward returns are not used for overlay decisions.

## overlay_ticker_loss_cooldown_5pct_5

- Intent: Skip a ticker after a prior closed loss in the same ticker.
- Allowed inputs: replay-date candidate features, replay-date SPY/QQQ regime features, and prior closed simulated trade outcomes for cooldown overlays.
- Forward returns are not used for overlay decisions.

## overlay_ticker_loss_cooldown_8pct_5

- Intent: Skip a ticker after a prior closed loss in the same ticker.
- Allowed inputs: replay-date candidate features, replay-date SPY/QQQ regime features, and prior closed simulated trade outcomes for cooldown overlays.
- Forward returns are not used for overlay decisions.

## overlay_ticker_loss_cooldown_10pct_5

- Intent: Skip a ticker after a prior closed loss in the same ticker.
- Allowed inputs: replay-date candidate features, replay-date SPY/QQQ regime features, and prior closed simulated trade outcomes for cooldown overlays.
- Forward returns are not used for overlay decisions.

## overlay_combined_conservative

- Intent: Combine at most two independently useful calibration overlays.
- Parameters are frozen before validation and holdout.
