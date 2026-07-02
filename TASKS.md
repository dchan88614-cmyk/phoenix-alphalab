# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Current Task: Phoenix Nano Phase 1C — Continuous Account Growth Backtest

Goal:
Backtest whether the simple qualified-stock selector can grow a continuous $100 account over time.

Backtest period:
2024-01-01 to 2026-06-30

Evaluation method:
- Start account at $100 only once.
- Do not reset monthly.
- Run daily historical replay across the full period.
- Use only data available on or before each replay date.
- Select exactly one stock or NO_TRADE each day.
- Only one open position at a time.
- If already holding a position, skip new entries until exit.
- Track account equity over time.
- Track milestone dates when account reaches $150, $200, $300, $500, and $1000.

Selection hard filters:
1. US common stock only; exclude OTC/pink sheet/delisting risk if detectable.
2. Price between $5 and $50.
3. Current account can buy at least 1 whole share after slippage.
4. Dollar volume >= $20,000,000.
5. Past 5 trading days cumulative return between +3% and +15%.
6. At least 3 of past 5 trading days are green.
7. No single day in past 5 trading days gained more than +10%.
8. Relative volume prev20 >= 1.5.
9. ATR / price <= 12%.
10. Distance to 52-week high >= -35%.
11. SPY and QQQ must not be in clear downtrend.
12. If earnings/event data is unavailable, mark event filter UNKNOWN and do not use it as pass.

Ranking:
Rank passed stocks by:
- relative volume strength
- smooth 5-day uptrend quality
- 20-day trend
- relative strength versus SPY/QQQ
- distance to 52-week high
- lower ATR risk

Trade plan:
- Buy using available account cash.
- If shares >= 2: sell 1 share at +15%, move remaining stop to breakeven, sell rest at +30%.
- If shares == 1: sell at +20%.
- Stop loss: -10%.
- Max hold: 20 trading days.
- Only one open position at a time.

Reports:
Create:
- `data/reports/phase1c_continuous_account_trades.csv`
- `data/reports/phase1c_continuous_account_equity_curve.csv`
- `data/reports/phase1c_continuous_account_summary.md`

Summary must include:
- starting account value
- ending account value
- total return
- milestone dates for $150, $200, $300, $500, and $1000
- number of trades
- win rate
- best trade
- worst trade
- max drawdown
- longest flat period
- whether $1000 was reached
- if not, highest account value reached
- what rule blocked most stocks
- what should be adjusted next

Run tests and update `REPORT_TO_GPT.md`.

Do not start paper trading or live trading.
Commit, push, and stop.
