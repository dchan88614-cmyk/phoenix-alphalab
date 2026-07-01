# Phoenix AlphaLab Tasks

Codex must read this file before each execution.

## Active Protocol

Before every execution:

1. Read `README.md`.
2. Read `BRAIN.md`.
3. Read `TASKS.md`.

After every completed task:

1. Update `REPORT_TO_GPT.md`.
2. Include `Completed`, `Files Changed`, `How To Run`, `Output`, `Problems`, `Questions For GPT`, and `Next Suggested Tasks`.
3. Stop and wait for GPT review when the requested task is complete.

## Current First-Phase Tasks

1. Run the MVP end to end.
2. Support input ticker list and date range.
3. Download historical OHLCV.
4. Calculate basic factors.
5. Calculate future 5/10/20 day returns.
6. Output CSV and Markdown reports.
7. Write basic tests.
8. Update `REPORT_TO_GPT.md`.

## Stop Condition

After the first-phase task report is updated, Codex must not expand new functionality until GPT reviews and gives the next task.
