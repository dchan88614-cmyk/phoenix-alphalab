# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PUBLIC
- defaultBranch: main

## Completed

- Executed the latest `TASKS.md`: Auto Research Loop v0.1 - Fix Coverage Before Judging.
- Removed premature early stop before 50 evaluated candidates.
- Set the auto research loop default candidate cap to 100.
- Reordered candidate generation so the first 20 candidates are diversified across:
  - `smoke_score_threshold`
  - `max_buy_rate`
  - `distance_to_52w_high_prev_min`
  - `dollar_volume_min`
  - `require_return_5d_positive`
  - `require_return_20d_positive`
- Added diagnostic-only 20-trading-day path columns:
  - `stop_hit_rate_20d`
  - `target_1_hit_rate_20d`
  - `target_2_hit_rate_20d`
- Added 300-calendar-day warmup download support while keeping `--start` as `research_start`.
- Updated auto research summary reporting with total candidates, stop reason, BUY rate distribution, top candidates even if failed, common fail reasons, and worst-trade gate diagnostics.
- Kept alpha factors unchanged.
- Did not add news, SEC, short interest, options, LLM ranking, or external paid data.
- Did not label any version live-tradable.

## Files Changed

- `src/main.py`
- `src/research/auto_loop.py`
- `tests/test_auto_loop.py`
- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/reports/auto_research_generations.csv`
- `data/reports/auto_research_summary.md`
- `REPORT_TO_GPT.md`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

Local virtual environment:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

## Output

Latest auto research loop run:

- Data start requested: 2023-03-07
- Research start: 2024-01-01
- Research end: 2026-06-30
- Warmup limitation: earliest available data in the run was 2023-04-03.
- Total candidates available: 100
- Total candidates evaluated: 50
- Candidates passed gate: 0
- Candidates failed gate: 50
- Stop reason: `10_consecutive_candidates_failed_to_improve_best_score`
- BUY rate distribution: min 90.07%, median 93.87%, max 99.50%

Top candidate even if failed:

- Candidate ID: 12
- Status: `RESEARCH_ONLY_NOT_TRADABLE`
- Overall 20d avg excess: 5.77%
- Avg excess excluding best BUY: 5.57%
- Worst 20d return: -63.53%
- BUY count: 550
- BUY rate: 91.06%
- Fail reasons: `worst_20d_return_lte_minus_60pct`, `overall_buy_rate_above_candidate_max`

Worst gate analysis:

- Candidates failed only because of `worst_20d_return_lte_minus_60pct`: 12
- Top candidates include cases where the -60% worst-trade gate is the only failure.
- Best 20d avg excess after excluding best BUY: 5.57%

Stop/target diagnostic summary across evaluated candidates:

- Mean stop hit rate: 61.91%
- Mean target 1 hit rate: 63.20%
- Mean target 2 hit rate: 48.34%
- These diagnostics are not used in BUY / NO_TRADE decisions.

Phoenix remains not tradable:

- No candidate passed the research gate.
- BUY rates remain too broad.
- Worst 20d return remains below the -60% risk gate.
- All outputs remain offline historical research only.

Generated files:

- `data/reports/auto_research_generations.csv`
- `data/reports/auto_research_summary.md`
- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`
- `data/processed/factor_dataset.csv`

## Test Results

```bash
.venv/bin/python -m pytest -q
# 34 passed, 1 warning in 0.73s
```

End-to-end command completed successfully:

```bash
.venv/bin/python -m src.main --watchlist config/watchlists/us_liquid_growth_100.txt --start 2024-01-01 --end 2026-06-30 --auto-research-loop
```

## Problems

- No candidate passed the gate.
- Candidate BUY rates remain high even after diversified ordering.
- The same worst 20d return of -63.53% still blocks otherwise positive candidates.
- Warmup improved the setup, but yfinance only returned data starting 2023-04-03 for this run instead of the requested 2023-03-07.
- yfinance metadata filtering still rejects some watchlist names and may have false exclusions such as `U` via keyword matching.
- The run emitted existing pandas `pct_change` future warnings and the macOS LibreSSL warning; neither blocked execution.

## Questions For GPT

- Should the next iteration focus on reducing BUY rate before changing any research gate?
- Should the -60% worst-trade gate remain hard, or should stop/target diagnostics be promoted into a separate future simulation layer first?
- Should metadata filtering be improved before the next research-loop run so the intended universe is less distorted?

## Next Suggested Tasks

- Do not add new alpha sources yet.
- Tighten candidate rules to reduce BUY rate without using forward returns.
- Investigate whether stop/target logic should become a separate simulation after diagnostics are reviewed.
- Improve watchlist metadata filtering precision.
- Keep Phoenix labeled research-only and not live-tradable.
