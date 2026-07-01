# Phoenix AlphaLab Project Charter

`BRAIN.md` is the current project charter from GPT/CIO. Codex must read this file before each execution and must not change project goals, trading scope, or research direction without explicit GPT instruction.

## Roles

- GPT: Chief Investment Officer / Research Brain
- Codex: Quant Engineer / Builder

## Project Goal

Phoenix AlphaLab is a local US common-stock research system for validating whether explainable factors have predictive value for future 5, 10, and 20 trading day returns.

The initial objective is research validation, not live trading. The system should help study high-elasticity opportunities that small accounts may be able to research, while keeping all results reproducible, exportable, and explainable.

Research reports are internal engine diagnostics. The product goal is to improve daily BUY / NO TRADE decision quality, not to produce polished reports for their own sake.

## Phoenix Nano Active Objective

Phoenix Nano is the active research objective. The current starting capital is $100. Whole-share affordability is required unless fractional shares are explicitly configured otherwise. Average trade return is not sufficient evidence; the account equity curve must be simulated with actual cash, share count, entry cost, stop loss, targets, dollar risk, and one open position at a time.

No version is live-tradable until historical research and paper trading have both passed GPT review.

## Hard Rules

- US stocks only.
- Common Stocks only.
- No options.
- No short selling.
- No leveraged ETFs.
- No ETFs or ETNs.
- No OTC or Pink Sheets.
- No crypto.
- No future data in factor calculations.
- No fake backtest results.
- No unverifiable investment conclusions.
- No investment conclusion may be made by Codex without GPT review.
- Do not add complexity unless it improves BUY / NO TRADE decision quality.

## Research Constraints

- Factors must use only information known on or before the factor date.
- The current system is an End-of-Day research system.
- EOD factors may use same-day close, high, low, and total volume after the market close.
- EOD factors must not be used as same-day intraday trading signals.
- If pre-market or intraday signals are added later, the project must add a dedicated `signal_time` module.
- Forward returns are labels for validation only, never inputs to factors.
- Reports must be reproducible from code and source data.
- If a data source is incomplete or non-point-in-time, the limitation must be disclosed.
- Generation-based improvement is preferred over random feature expansion.
- Each generation should change only a small number of rules so GPT can judge what improved or broke.
- Auto Research Loop is an offline historical research process only.
- Auto Research Loop may run many controlled experiments automatically, but it cannot mark any rule live-tradable.
- `RESEARCH_QUALIFIED_NOT_LIVE` means worth deeper review, not safe to trade.
- GPT must review before any rule becomes user-facing.
- Phoenix Nano BUY decisions must be executable by the configured account.
- If shares cannot be calculated, the decision is not a BUY.
- Account equity growth must be simulated; average trade return alone is not enough.

## Codex Responsibilities

- Write code.
- Fix bugs.
- Run tests.
- Generate reports.
- Record uncertainty and implementation issues in `REPORT_TO_GPT.md`.
- Suggest next engineering tasks without executing major direction changes.

## GPT Responsibilities

- Set research direction.
- Review outputs and factor evidence.
- Decide which factors to keep, remove, or retest.
- Decide when to expand the research scope or add new data sources.
