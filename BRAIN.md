# Phoenix AlphaLab Project Charter

`BRAIN.md` is the current project charter from GPT/CIO. Codex must read this file before each execution and must not change project goals, trading scope, or research direction without explicit GPT instruction.

## Roles

- GPT: Chief Investment Officer / Research Brain
- Codex: Quant Engineer / Builder

## Project Goal

Phoenix AlphaLab is a local US common-stock research system for validating whether explainable factors have predictive value for future 5, 10, and 20 trading day returns.

The initial objective is research validation, not live trading. The system should help study high-elasticity opportunities that small accounts may be able to research, while keeping all results reproducible, exportable, and explainable.

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

## Research Constraints

- Factors must use only information known on or before the factor date.
- Forward returns are labels for validation only, never inputs to factors.
- Reports must be reproducible from code and source data.
- If a data source is incomplete or non-point-in-time, the limitation must be disclosed.

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
