# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Auto Research Loop v0.3 — Concentration Risk + Robustness Before Gate Tuning

The previous run completed correctly and materially improved Phoenix:

- v0.2 added a historical virtual trade simulator.
- Trades now use EOD signal date, next trading day entry, stop loss, Target 1, Target 2, and max 20-trading-day exits.
- Candidate evaluation now uses realized simulated trades instead of only 20d forward-return labels.
- Active max BUY rate enforcement now reduces trades before simulation.
- 50 candidates were evaluated.
- 0 candidates passed the v0.2 research-qualified gate.
- Best candidate: candidate 35.
- Candidate 35 final BUY rate: 14.40%.
- Candidate 35 average realized return: 3.58%.
- Candidate 35 average realized excess return: 3.12%.
- Candidate 35 realized win rate: 51.72%, just below the 52% gate.
- Candidate 35 worst realized return: -14.65%.
- Candidate 35 stop hit rate: 47.13%.
- Overall v0.2 common fail reason: `realized_win_rate_lt_52pct` for all 50 candidates.
- Worst realized trade and best realized trade were both MSTR, showing likely concentration risk.

This is real progress: the simulator reduced the prior -63.53% tail observation to materially smaller realized trade losses under defined exits. But Phoenix is still not research-qualified and not tradable.

Do not loosen the research gate yet.
Do not tune the win-rate threshold just to make a candidate pass.
Do not add new alpha sources yet.
Do not add news, SEC, short interest, options, LLM ranking, paid data, or external APIs.
Do not output live trade recommendations.
Do not label anything live-tradable.

## Goal

Before changing gates or optimizing exits, determine whether v0.2 performance is robust or mostly caused by concentration in a few high-volatility tickers such as MSTR.

The output should answer:

1. Is the best candidate still positive after excluding MSTR?
2. Is the best candidate still positive after excluding its most selected ticker?
3. Is the best candidate still positive after applying a per-ticker trade cap?
4. Which tickers and themes dominate trades, winners, losers, stop hits, and target hits?
5. Is the 51.72% win rate problem caused by broad weakness, a few bad tickers, or exit design?
6. Should the next iteration focus on ticker concentration, market regime filters, or exit logic?

## Part 1: Add Concentration Diagnostics

Create or update:

`src/research/concentration.py`

For each candidate and for the best candidate specifically, compute ticker-level diagnostics from `trade_simulation_trades.csv` or directly from in-memory simulated trades.

Required metrics by ticker:

- ticker
- trade_count
- trade_share
- avg_realized_return
- avg_realized_excess_return
- median_realized_return
- realized_win_rate
- worst_realized_return
- best_realized_return
- stop_hit_rate
- target_1_hit_rate
- target_2_hit_rate
- time_exit_rate
- avg_holding_days
- total_contribution_to_realized_return
- total_contribution_to_realized_excess_return

Also compute:

- Top 10 tickers by trade_count.
- Top 10 tickers by positive contribution.
- Top 10 tickers by negative contribution.
- Tickers responsible for the worst 10 trades.
- Tickers responsible for the best 10 trades.
- Percent of all trades from the top 1 ticker.
- Percent of all trades from the top 3 tickers.
- Percent of all realized excess return from the top 1 ticker.
- Percent of all realized excess return from the top 3 tickers.

## Part 2: Robustness Variants

For every candidate, evaluate these variants without changing the original candidate decisions:

1. Base simulated trades.
2. Excluding MSTR.
3. Excluding the most selected ticker for that candidate.
4. Excluding the top 3 most selected tickers for that candidate.
5. Per-ticker cap: max 10 trades per ticker per full research period.
6. Per-ticker cap: max 5 trades per ticker per calendar year.
7. Equal-ticker-weighted summary, where each ticker contributes equally regardless of trade count.

For each variant, compute:

- remaining_trade_count
- avg_realized_return
- avg_realized_excess_return
- realized_win_rate
- median_realized_return
- worst_realized_return
- best_realized_return
- stop_hit_rate
- target_1_hit_rate
- target_2_hit_rate
- time_exit_rate
- avg_holding_days
- avg_realized_excess_excluding_best_trade
- valid_windows
- windows_positive_realized_excess
- windows_win_rate_ge_52pct

Important:

- Do not use realized returns to choose trades for per-ticker caps.
- Per-ticker caps must keep earliest eligible trades or highest decision-strength trades using only signal-date information.
- Do not use future returns, simulated returns, or exit outcomes to choose which trades survive.

## Part 3: Optional Active Per-Ticker Cap Candidate Parameter

Add candidate parameter for v0.3 search:

- `max_trades_per_ticker_per_year`: none, 20, 10, 5

This parameter must be active before simulation.

Implementation rule:

- Apply the cap after candidate filters and active max BUY rate enforcement.
- Use only signal-date-safe decision strength to choose which ticker trades remain if the cap is exceeded.
- Do not use future returns or realized returns.

## Part 4: Market Regime Diagnostics Only

Add diagnostics, not gates yet.

For each trade, tag the signal date market regime using only information available on or before the signal date:

- SPY above/below 50-day moving average.
- SPY above/below 200-day moving average.
- QQQ above/below 50-day moving average.
- QQQ above/below 200-day moving average.
- VIX proxy unavailable unless already in data; do not add new data source.

For each regime bucket, report:

- trade_count
- avg_realized_excess_return
- realized_win_rate
- stop_hit_rate
- target_1_hit_rate
- target_2_hit_rate
- time_exit_rate

Do not add a regime gate in this task unless diagnostics clearly show catastrophic underperformance in a regime. If a regime gate is proposed, report it as a next task only.

## Part 5: Research-Qualified Gate v0.3

Keep the v0.2 base gate unchanged for the base candidate:

1. At least 8 windows have sufficient data.
2. Final BUY count >= 40 across all windows.
3. Final overall BUY rate <= 50%.
4. Overall average realized excess return > 0.
5. Overall realized win rate >= 52%.
6. At least 6 valid windows have positive realized excess return.
7. Removing the single best trade still leaves average realized excess return > 0.
8. Worst realized return must be greater than -25%.
9. Stop hit rate must be <= 65%.

Add robustness requirements for any candidate to be called `RESEARCH_QUALIFIED_NOT_LIVE`:

10. Excluding MSTR must leave average realized excess return > 0.
11. Excluding the most selected ticker must leave average realized excess return > 0.
12. Top 1 ticker trade share must be <= 25%.
13. Top 3 ticker trade share must be <= 50%.
14. Equal-ticker-weighted average realized excess return must be > 0.

If it fails any gate, label:

`RESEARCH_ONLY_NOT_TRADABLE`

Nothing may be labeled live-tradable.

## Part 6: Outputs

Create or update:

`data/reports/trade_simulation_trades.csv`
`data/reports/auto_research_generations.csv`
`data/reports/auto_research_summary.md`
`data/reports/concentration_report.csv`
`data/reports/concentration_report.md`
`data/reports/robustness_report.csv`
`data/reports/regime_diagnostics.csv`
`data/reports/regime_diagnostics.md`

The summary must include:

- total candidates evaluated
- candidates passed v0.3 gate
- candidates failed v0.3 gate
- best candidate even if failed
- best candidate if qualified
- base BUY rate distribution
- realized return distribution
- robustness summary excluding MSTR
- robustness summary excluding most selected ticker
- top 1 and top 3 ticker concentration for best candidate
- equal-ticker-weighted performance for best candidate
- top positive and negative ticker contributors
- worst realized trade
- best realized trade
- stop/target/time-exit breakdown
- market regime diagnostics summary
- common fail reasons
- explicit statement that Phoenix remains not live-tradable unless a candidate passes all gates and GPT reviews it

If zero candidates pass gate, say:

`No research-qualified version found. Do not use Phoenix for live trading.`

If candidates pass, say:

`Research-qualified candidates found. GPT review required before any paper trading.`

## Part 7: CLI

Keep:

```bash
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

This command should now also generate concentration, robustness, and regime diagnostic outputs.

## Part 8: Tests

Add tests for:

1. Concentration report computes ticker trade share correctly.
2. Excluding MSTR removes only MSTR trades.
3. Excluding most selected ticker identifies the correct ticker without using returns.
4. Per-ticker cap keeps trades using signal-date-safe decision strength only.
5. Per-ticker cap does not use realized returns, forward returns, or exit outcomes.
6. Equal-ticker-weighted performance gives each ticker equal weight.
7. Robustness gates fail a candidate if MSTR removal destroys positive excess.
8. Robustness gates fail a candidate if top 1 ticker share exceeds 25%.
9. Regime diagnostics use only signal-date or prior data.
10. Reports are written.

## Part 9: Update REPORT_TO_GPT.md

When done, update `REPORT_TO_GPT.md` with:

- Completed
- Files Changed
- How To Run
- Output
- Test Results
- Trade Simulation Summary
- Concentration Summary
- Robustness Summary
- Regime Diagnostics Summary
- Whether any candidate became `RESEARCH_QUALIFIED_NOT_LIVE`
- Best candidate if any
- Worst realized trade
- Best realized trade
- Problems
- Questions For GPT
- Next Suggested Tasks

## Decision Guidance For GPT

After this task, GPT should decide one of three paths:

1. If performance collapses after excluding MSTR or the top ticker, focus on concentration controls and universe quality.
2. If performance remains positive but win rate stays below 52%, focus on exit design and stop/target calibration.
3. If performance is regime-dependent, add a market regime gate in the next task.

## Stop Condition

Commit, push, and stop.
Do not start paper trading.
Do not start live trade generation.
Do not label anything live-tradable.
