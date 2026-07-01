# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Autonomous Research Loop v0.
- Kept the smoke ranking factors unchanged.
- Did not add news, SEC, short interest, options, LLM ranking, or external paid data.
- Added `src/research/auto_loop.py`.
- Added candidate BUY / NO_TRADE rule configurations.
- Added multi-window candidate evaluation across the fixed 2024-2026 windows.
- Added minimum research-qualified gates.
- Added deterministic candidate scoring for candidates that pass gates.
- Added early stop after 10 consecutive candidates fail to improve best score.
- Added `--auto-research-loop` CLI flag.
- Added reports:
  - `data/reports/auto_research_generations.csv`
  - `data/reports/auto_research_summary.md`
- Added tests for:
  - BUY count gate failure
  - research-qualified gate pass
  - removing best BUY gate logic
  - CSV/Markdown output writing
  - deterministic scoring
  - no forward-return leakage in BUY decision logic
- Also completed the prerequisite Generation 1 decision engine layer from the previous `TASKS.md` revision, because the remote `TASKS.md` changed while this run was in progress and the auto loop needs decision-rule evaluation support.

## Files Changed

- `README.md`
- `BRAIN.md`
- `REPORT_TO_GPT.md`
- `src/main.py`
- `src/backtest/smoke_test.py`
- `src/decision/__init__.py`
- `src/decision/decision_engine.py`
- `src/research/__init__.py`
- `src/research/auto_loop.py`
- `tests/test_decision_engine.py`
- `tests/test_auto_loop.py`
- `data/reports/smoke_test.csv`
- `data/reports/decision_simulation.csv`
- `data/reports/decision_simulation.md`
- `data/reports/auto_research_generations.csv`
- `data/reports/auto_research_summary.md`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

If using the local virtual environment:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

Expected outputs:

- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/reports/auto_research_generations.csv`
- `data/reports/auto_research_summary.md`
- `data/processed/factor_dataset.csv`

## Output

Latest auto research loop run:

- Total candidates tested: 10
- Candidates passed gate: 0
- Candidates failed gate: 10
- Early stop reason: `10_consecutive_candidates_failed_to_improve_best_score`
- Best candidate: None
- Best candidate status: None
- Research-qualified versions found: 0
- Summary conclusion: `No research-qualified version found. Do not use Phoenix for live trading.`
- Explicit warning included: no version is live-tradable yet.

Top observed candidate pattern:

- Candidate 1 bought 519 times across 544 signal days.
- Overall 20d average excess: 4.60%
- Overall 20d win rate: 56.84%
- Worst 20d return: -63.53%
- Gate failure: `worst_20d_return_lte_minus_60pct`

## Test Results

```bash
.venv/bin/python -m pytest -q
# 28 passed, 1 warning in 0.76s
```

End-to-end auto research loop command completed successfully and wrote both auto research reports.

## Problems

- No candidate passed the minimum research-qualified gate.
- Early stop happened after 10 candidates because no candidate improved a passing best score.
- The first tested candidates were very similar and had extremely high BUY rates around 95.40%.
- Worst BUY 20d return of -63.53% failed the risk gate even though overall 20d excess was positive.
- The first 2024 window still has only 1 eligible signal day due to warmup limits from the 2024-01-01 data start.
- Current watchlist and yfinance metadata are not point-in-time.
- Strict yfinance metadata filtering still rejects some names and has false exclusions such as `U` via keyword matching.
- The run emitted pandas `pct_change` future warnings and the existing macOS LibreSSL warning; neither blocked the run.

## Questions For GPT

- Should the auto loop candidate order be changed so stricter smoke thresholds and lower max BUY rates are tested before early stop?
- Should early stop wait until at least one candidate passes the gate, instead of stopping after 10 initial failures?
- Should the first window be rerun with earlier warmup data before judging the full loop?
- Is the -60% worst BUY gate too strict, or is that exactly the kind of risk filter Phoenix should enforce?

## Next Suggested Tasks

- Review whether early stop logic should be adjusted before running more candidates.
- Add warmup-start support so early windows have enough factor history.
- Improve instrument-type filtering precision before expanding or trusting the watchlist.
- Consider evaluating stop/target path outcomes before tuning BUY filters.
- Do not label any version live-tradable.
