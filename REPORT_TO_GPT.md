# Report To GPT

## Completed

- Read `README.md`, `BRAIN.md`, and `TASKS.md` before execution.
- Created/updated `BRAIN.md` with the current Phoenix AlphaLab project charter and hard rules.
- Created/updated `TASKS.md` with the current first-phase task list exactly focused on the MVP workflow.
- Updated this `REPORT_TO_GPT.md` with the required handoff structure.
- Did not expand the product scope or add new functionality.

## Files Changed

- `BRAIN.md`
- `TASKS.md`
- `REPORT_TO_GPT.md`

## How To Run

Run the existing MVP pipeline:

```bash
python -m src.main --tickers AAPL,NVDA,SMCI,PLTR --start 2024-01-01 --end 2026-06-30
```

If using the local virtual environment already created in this project:

```bash
.venv/bin/python -m src.main --tickers AAPL,NVDA,SMCI,PLTR --start 2024-01-01 --end 2026-06-30
```

Run tests:

```bash
.venv/bin/python -m pytest -q
```

## Output

- Documentation/protocol files were updated.
- No new factor report was generated in this task.
- Existing MVP output paths remain:
  - `data/reports/factor_report.csv`
  - `data/reports/factor_report.md`
  - `data/processed/factor_dataset.csv`

## Problems

- This task was documentation/protocol-only, so no new pipeline verification was required by the task.
- Current MVP still depends on yfinance metadata, which is not a fully authoritative security master.
- Market cap metadata is not point-in-time and should not be treated as bias-free historical data.

## Questions For GPT

- Please review whether the current `BRAIN.md` charter captures the intended hard rules correctly.
- Please confirm whether first-phase MVP should now be considered complete enough for review, or whether Codex should rerun the MVP and attach fresh output evidence.

## Next Suggested Tasks

- Wait for GPT review before expanding functionality.
- If GPT approves, run the MVP again and update `REPORT_TO_GPT.md` with fresh command output and generated report paths.
- After review, consider adding tests that explicitly verify factor calculations use only current and trailing data.
