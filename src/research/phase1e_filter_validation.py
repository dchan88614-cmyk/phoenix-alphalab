from __future__ import annotations

from itertools import product
from pathlib import Path
import warnings

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.research.auto_loop import CandidateRule
from src.research.historical_replay import HISTORICAL_BUY_CANDIDATE, build_phase1_historical_replay
from src.research.phase1c_robustness import simulate_phase1c_policy_trades
from src.research.phase1d_entry_rules import (
    BASELINE_POLICY,
    apply_candidate_filter,
    build_entry_rule_diagnostics,
    diagnostic_columns,
    excluded_decision_audit,
    theme_failure_summary,
)


PHASE_1E_FAILED = "PHASE_1E_FAILED"
PHASE_1E_FILTER_OVERFIT_NOT_APPROVED = "PHASE_1E_FILTER_OVERFIT_NOT_APPROVED"
PHASE_1E_FILTER_NEEDS_MORE_WORK = "PHASE_1E_FILTER_NEEDS_MORE_WORK"
PHASE_1E_FILTER_ROBUSTNESS_IMPROVED_REQUIRES_GPT_REVIEW = "PHASE_1E_FILTER_ROBUSTNESS_IMPROVED_REQUIRES_GPT_REVIEW"

VOLATILITY_GRID = [0.055, 0.060, 0.065, 0.070, 0.075]
SMOKE_GRID = [0.880, 0.900, 0.920, 0.940]


def build_phase1e_filter_validation(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_rounds: int = 100,
    replay_sample_count: int = 20,
    replay_sample_offset: int = 0,
    benchmark_ticker: str = "SPY",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, dict]:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["date", "ticker"]).reset_index(drop=True)

    diagnostics_frames: list[pd.DataFrame] = []
    decision_frames: list[pd.DataFrame] = []
    phase1_summaries: dict[int, dict] = {}
    for sample_index in range(replay_sample_count):
        sample_id = replay_sample_offset + sample_index
        decisions, _, phase1_summary = build_phase1_historical_replay(
            frame,
            account_settings,
            rule,
            replay_rounds=replay_rounds,
            benchmark_ticker=benchmark_ticker,
            replay_sample_offset=sample_id,
        )
        decisions["sample_id"] = sample_id
        baseline_trades = simulate_phase1c_policy_trades(decisions, frame, account_settings, BASELINE_POLICY)
        diagnostics_frames.append(build_entry_rule_diagnostics(sample_id, decisions, baseline_trades, frame, rule))
        decision_frames.append(decisions)
        phase1_summaries[sample_id] = phase1_summary

    diagnostics = pd.concat(diagnostics_frames, ignore_index=True) if diagnostics_frames else pd.DataFrame()
    decisions_all = pd.concat(decision_frames, ignore_index=True) if decision_frames else pd.DataFrame()
    split = deterministic_sample_split(replay_sample_count, replay_sample_offset)
    filters = phase1e_filter_family()
    threshold_sweep, excluded_all = build_filter_backtest_matrix(
        diagnostics,
        decisions_all,
        frame,
        account_settings,
        filters,
        replay_rounds,
        phase1_summaries,
    )
    threshold_sweep["split"] = threshold_sweep["sample_id"].apply(lambda value: split_label(int(value), split))
    calibration_summary = summarize_filter_set(threshold_sweep.loc[threshold_sweep["split"].eq("calibration")], split_name="calibration")
    selected = select_holdout_filters(calibration_summary)
    overlay_filters = build_overlay_filters(selected)
    validation_filters = [item for item in filters if item["filter_name"] in set(selected["filter_name"])] + overlay_filters
    validation_matrix, validation_excluded = build_filter_backtest_matrix(
        diagnostics.loc[diagnostics["sample_id"].isin(split["holdout"])],
        decisions_all.loc[decisions_all["sample_id"].isin(split["holdout"])],
        frame,
        account_settings,
        validation_filters,
        replay_rounds,
        phase1_summaries,
    )
    validation_matrix["split"] = "holdout"
    validation_summary = summarize_filter_set(validation_matrix, split_name="holdout")
    holdout_results = validation_summary.copy()
    holdout_results["phase1e_holdout_gate_pass"] = holdout_results.apply(holdout_gate_pass, axis=1)
    holdout_results["phase1e_status_candidate"] = holdout_results["phase1e_holdout_gate_pass"].map(
        {True: PHASE_1E_FILTER_ROBUSTNESS_IMPROVED_REQUIRES_GPT_REVIEW, False: PHASE_1E_FILTER_NEEDS_MORE_WORK}
    )
    excluded_sources = [frame for frame in [excluded_all, validation_excluded] if not frame.empty]
    excluded = (
        concat_frames(excluded_sources)
        if excluded_sources
        else excluded_decision_audit(pd.DataFrame(), {"filter_name": "", "filter_description": ""})
    )
    summary = summarize_phase1e(diagnostics, threshold_sweep, calibration_summary, holdout_results, excluded, split, selected, validation_filters, replay_sample_count)
    summary_md = phase1e_summary_markdown(summary, calibration_summary, holdout_results, threshold_sweep, excluded)
    return threshold_sweep, validation_matrix, holdout_results, excluded, summary_md, summary


def deterministic_sample_split(replay_sample_count: int, replay_sample_offset: int = 0) -> dict:
    sample_ids = list(range(replay_sample_offset, replay_sample_offset + replay_sample_count))
    if replay_sample_count >= 20:
        return {"calibration": sample_ids[:10], "holdout": sample_ids[10:20], "fallback_used": False}
    if replay_sample_count >= 10:
        return {"calibration": sample_ids[:5], "holdout": sample_ids[5:10], "fallback_used": True}
    midpoint = max(1, replay_sample_count // 2)
    return {"calibration": sample_ids[:midpoint], "holdout": sample_ids[midpoint:], "fallback_used": True}


def phase1e_filter_family() -> list[dict]:
    filters = [
        {"filter_name": "no_filter_baseline_current", "filter_description": "Candidate 34 unchanged with baseline_current exits.", "kind": "no_filter"},
        {
            "filter_name": "phase1d_volatility_plus_smoke_score",
            "filter_description": "Phase 1D fixed filter: volatility_20d <= 0.0697 and smoke_score >= 0.8839.",
            "kind": "vol_smoke",
            "volatility_20d_max": 0.0697,
            "smoke_score_min": 0.8839,
        },
    ]
    for vol, smoke in product(VOLATILITY_GRID, SMOKE_GRID):
        filters.append(
            {
                "filter_name": f"vol_{vol:.3f}_smoke_{smoke:.3f}",
                "filter_description": f"Require volatility_20d <= {vol:.3f} and smoke_score >= {smoke:.3f}.",
                "kind": "vol_smoke",
                "volatility_20d_max": vol,
                "smoke_score_min": smoke,
            }
        )
    return filters


def apply_phase1e_filter(sample_diag: pd.DataFrame, filter_def: dict) -> pd.DataFrame:
    if sample_diag.empty:
        return sample_diag.copy()
    kind = filter_def.get("kind")
    if kind == "no_filter":
        return sample_diag.iloc[0:0].copy()
    if kind == "vol_smoke":
        vol = pd.to_numeric(sample_diag["volatility_20d"], errors="coerce")
        smoke = pd.to_numeric(sample_diag["smoke_score"], errors="coerce")
        mask = vol.gt(float(filter_def["volatility_20d_max"])) | smoke.lt(float(filter_def["smoke_score_min"])) | vol.isna() | smoke.isna()
        excluded = sample_diag.loc[mask].copy()
    elif kind == "theme_cap_overlay":
        base_excluded = apply_phase1e_filter(sample_diag, filter_def["base_filter"])
        accepted = sample_diag.loc[~sample_diag.index.isin(base_excluded.index)].copy()
        overlay_excluded = apply_candidate_filter(accepted, {"filter_name": filter_def["filter_name"], "filter_description": filter_def["filter_description"], "kind": "theme_cap", "cap": 3})
        excluded = pd.concat([base_excluded, overlay_excluded], ignore_index=False)
    elif kind == "ticker_cooldown_overlay":
        base_excluded = apply_phase1e_filter(sample_diag, filter_def["base_filter"])
        accepted = sample_diag.loc[~sample_diag.index.isin(base_excluded.index)].copy()
        cooldown_indices = []
        cooldown_until: dict[str, pd.Timestamp] = {}
        for index, row in accepted.sort_values(["replay_date", "ticker"]).iterrows():
            replay_date = pd.Timestamp(row["replay_date"])
            ticker = str(row["ticker"])
            if ticker in cooldown_until and replay_date <= cooldown_until[ticker]:
                cooldown_indices.append(index)
                continue
            if not bool(row.get("winner_baseline_simulation", False)):
                cooldown_until[ticker] = replay_date + pd.Timedelta(days=60)
        overlay_excluded = accepted.loc[cooldown_indices].copy()
        excluded = pd.concat([base_excluded, overlay_excluded], ignore_index=False)
    else:
        raise ValueError(f"Unsupported Phase 1E filter kind: {kind}")
    if not excluded.empty:
        excluded["reason_excluded"] = filter_def["filter_description"]
    return excluded


def build_phase1e_matrix(
    diagnostics: pd.DataFrame,
    decisions: pd.DataFrame,
    data: pd.DataFrame,
    account_settings: AccountSettings,
    filters: list[dict],
    replay_rounds: int,
    phase1_summaries: dict[int, dict],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    excluded_frames = []
    for sample_id in sorted(diagnostics["sample_id"].dropna().unique()):
        sample_diag = diagnostics.loc[diagnostics["sample_id"].eq(sample_id)].sort_values(["replay_date", "ticker"]).copy()
        sample_decisions = decisions.loc[decisions["sample_id"].eq(sample_id)].copy()
        for filter_def in filters:
            excluded = apply_phase1e_filter(sample_diag, filter_def)
            audit = excluded_decision_audit(ensure_phase1d_audit_columns(excluded), filter_def)
            if not audit.empty:
                audit["stage"] = filter_def.get("stage", "")
                audit["volatility_20d_max"] = filter_def.get("volatility_20d_max", pd.NA)
                audit["smoke_score_min"] = filter_def.get("smoke_score_min", pd.NA)
            excluded_frames.append(audit)
            filtered = sample_decisions.loc[
                ~(
                    sample_decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)
                    & sample_decisions["replay_date"].isin(excluded["replay_date"])
                    & sample_decisions["ticker"].isin(excluded["ticker"])
                )
            ].copy()
            trades = simulate_phase1c_policy_trades(filtered, data, account_settings, BASELINE_POLICY)
            from src.research.phase1d_entry_rules import filter_matrix_row

            row = filter_matrix_row(
                int(sample_id),
                filter_def,
                replay_rounds,
                int(len(sample_diag)),
                sample_diag,
                excluded,
                trades,
                account_settings,
                phase1_summaries.get(int(sample_id), {}),
            )
            row["volatility_20d_max"] = filter_def.get("volatility_20d_max", pd.NA)
            row["smoke_score_min"] = filter_def.get("smoke_score_min", pd.NA)
            row["filter_kind"] = filter_def.get("kind", "")
            rows.append(row)
    matrix = pd.DataFrame(rows)
    non_empty = [frame for frame in excluded_frames if not frame.empty]
    excluded = concat_frames(non_empty) if non_empty else excluded_decision_audit(pd.DataFrame(), {"filter_name": "", "filter_description": ""})
    return matrix, excluded


def build_filter_backtest_matrix(*args, **kwargs):
    return build_phase1e_matrix(*args, **kwargs)


def summarize_filter_set(matrix: pd.DataFrame, split_name: str) -> pd.DataFrame:
    if matrix.empty:
        return pd.DataFrame()
    grouped = matrix.groupby("filter_name").agg(
        sample_count=("sample_id", "nunique"),
        volatility_20d_max=("volatility_20d_max", "first"),
        smoke_score_min=("smoke_score_min", "first"),
        filter_description=("filter_description", "first"),
        median_ending_account_value=("ending_account_value", "median"),
        worst_sample_ending_account_value=("ending_account_value", "min"),
        median_max_drawdown=("max_drawdown", "median"),
        worst_sample_max_drawdown=("max_drawdown", "min"),
        median_simulated_win_rate=("trade_simulation_accuracy", "median"),
        worst_sample_simulated_win_rate=("trade_simulation_accuracy", "min"),
        median_buy_count=("filtered_buy_count", "median"),
        minimum_buy_count=("filtered_buy_count", "min"),
        median_20d_average_return=("average_return_20d", "median"),
        median_profit_factor=("profit_factor", "median"),
        excluded_loser_count=("excluded_loser_count", "sum"),
        excluded_winner_count=("excluded_winner_count", "sum"),
        max_top_ticker_profit_share=("top_ticker_profit_share", "max"),
        max_top_ticker_loss_share=("top_ticker_loss_share", "max"),
    ).reset_index()
    grouped["split"] = split_name
    grouped["calibration_gate_pass"] = grouped.apply(calibration_gate_pass, axis=1)
    return grouped


def calibration_gate_pass(row: pd.Series) -> bool:
    return bool(
        float(row["median_ending_account_value"]) > 120.0
        and float(row["worst_sample_ending_account_value"]) > 100.0
        and float(row["median_max_drawdown"]) > -0.35
        and float(row["worst_sample_max_drawdown"]) > -0.45
        and pd.notna(row["median_simulated_win_rate"])
        and float(row["median_simulated_win_rate"]) >= 0.50
        and int(row["minimum_buy_count"]) >= 15
        and int(row["excluded_loser_count"]) > int(row["excluded_winner_count"])
        and float(row["median_20d_average_return"]) > 0
        and float(row["median_profit_factor"]) > 1.2
    )


def holdout_gate_pass(row: pd.Series) -> bool:
    return bool(
        float(row["median_ending_account_value"]) > 120.0
        and float(row["worst_sample_ending_account_value"]) > 100.0
        and float(row["median_max_drawdown"]) > -0.35
        and float(row["worst_sample_max_drawdown"]) > -0.45
        and pd.notna(row["median_simulated_win_rate"])
        and float(row["median_simulated_win_rate"]) >= 0.50
        and int(row["minimum_buy_count"]) >= 15
        and float(row["median_20d_average_return"]) > 0
        and float(row["median_profit_factor"]) > 1.2
        and (pd.isna(row["max_top_ticker_profit_share"]) or float(row["max_top_ticker_profit_share"]) <= 0.50)
        and (pd.isna(row["max_top_ticker_loss_share"]) or float(row["max_top_ticker_loss_share"]) <= 0.50)
        and int(row["excluded_loser_count"]) > int(row["excluded_winner_count"])
    )


def select_holdout_filters(calibration_summary: pd.DataFrame) -> pd.DataFrame:
    if calibration_summary.empty:
        return pd.DataFrame()
    eligible = calibration_summary.loc[calibration_summary["calibration_gate_pass"]].copy()
    source = eligible if not eligible.empty else calibration_summary.copy()
    source["selection_status"] = "CALIBRATION_PASSED" if not eligible.empty else "CALIBRATION_NOT_PASSED_DIAGNOSTIC_ONLY"
    return source.sort_values(
        [
            "worst_sample_ending_account_value",
            "worst_sample_max_drawdown",
            "median_simulated_win_rate",
            "median_ending_account_value",
            "excluded_winner_count",
        ],
        ascending=[False, False, False, False, True],
    ).head(3)


def build_overlay_filters(selected: pd.DataFrame) -> list[dict]:
    overlays = []
    for row in selected.itertuples():
        base = {
            "filter_name": row.filter_name,
            "filter_description": row.filter_description,
            "kind": "no_filter" if row.filter_name == "no_filter_baseline_current" else "vol_smoke",
            "volatility_20d_max": row.volatility_20d_max,
            "smoke_score_min": row.smoke_score_min,
        }
        overlays.append(
            {
                "filter_name": f"{row.filter_name}_theme_cap_3_overlay",
                "filter_description": f"{row.filter_name} plus at most 3 accepted BUY decisions per deterministic theme per sample.",
                "kind": "theme_cap_overlay",
                "base_filter": base,
                "volatility_20d_max": row.volatility_20d_max,
                "smoke_score_min": row.smoke_score_min,
            }
        )
        overlays.append(
            {
                "filter_name": f"{row.filter_name}_repeated_loser_ticker_cooldown_overlay",
                "filter_description": f"{row.filter_name} plus 60 calendar day cooldown after prior accepted losing simulated ticker result.",
                "kind": "ticker_cooldown_overlay",
                "base_filter": base,
                "volatility_20d_max": row.volatility_20d_max,
                "smoke_score_min": row.smoke_score_min,
            }
        )
    return overlays


def split_label(sample_id: int, split: dict) -> str:
    if sample_id in split["calibration"]:
        return "calibration"
    if sample_id in split["holdout"]:
        return "holdout"
    return "unused"


def ensure_phase1d_audit_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    result = frame.copy()
    for column in diagnostic_columns():
        if column not in result.columns:
            result[column] = pd.NA
    return result


def phase1e_status(holdout_results: pd.DataFrame, selected: pd.DataFrame) -> str:
    if holdout_results.empty:
        return PHASE_1E_FAILED
    if holdout_results["phase1e_holdout_gate_pass"].any():
        return PHASE_1E_FILTER_ROBUSTNESS_IMPROVED_REQUIRES_GPT_REVIEW
    if selected.empty or not bool(selected["calibration_gate_pass"].any()):
        return PHASE_1E_FILTER_NEEDS_MORE_WORK
    return PHASE_1E_FILTER_OVERFIT_NOT_APPROVED


def summarize_phase1e(
    diagnostics: pd.DataFrame,
    threshold_sweep: pd.DataFrame,
    calibration_summary: pd.DataFrame,
    holdout_results: pd.DataFrame,
    excluded: pd.DataFrame,
    split: dict,
    selected: pd.DataFrame,
    validation_filters: list[dict],
    replay_sample_count: int,
) -> dict:
    best_cal = _best_row(calibration_summary, "worst_sample_ending_account_value")
    best_holdout = _best_row(holdout_results, "worst_sample_ending_account_value")
    fixed = holdout_results.loc[holdout_results["filter_name"].eq("phase1d_volatility_plus_smoke_score")]
    status = phase1e_status(holdout_results, selected)
    failure_matrix = threshold_sweep.loc[threshold_sweep["ending_account_value"].lt(100.0)].copy()
    top_failures = (
        failure_matrix.sort_values("ending_account_value").head(10)[["sample_id", "filter_name", "ending_account_value", "max_drawdown"]]
        if not failure_matrix.empty
        else pd.DataFrame()
    )
    return {
        "phase_1e_status": status,
        "sample_count": int(diagnostics["sample_id"].nunique()) if not diagnostics.empty else 0,
        "fallback_used": bool(split["fallback_used"] or replay_sample_count < 20),
        "calibration_samples": split["calibration"],
        "holdout_samples": split["holdout"],
        "filters_tested": int(threshold_sweep["filter_name"].nunique()) if not threshold_sweep.empty else 0,
        "selected_holdout_filters": selected["filter_name"].tolist() if not selected.empty else [],
        "validation_filters": [item["filter_name"] for item in validation_filters],
        "best_calibration_filter": best_cal,
        "best_holdout_filter": best_holdout,
        "volatility_plus_smoke_score_survived": bool(not fixed.empty and bool(fixed.iloc[0].get("phase1e_holdout_gate_pass", False))),
        "excluded_loser_count": int(excluded["would_have_been_winner_baseline_simulation"].eq(False).sum()) if not excluded.empty else 0,
        "excluded_winner_count": int(excluded["would_have_been_winner_baseline_simulation"].eq(True).sum()) if not excluded.empty else 0,
        "top_remaining_failure_samples": top_failures,
        "theme_failure_summary": theme_failure_summary(diagnostics),
    }


def write_phase1e_reports(
    threshold_sweep: pd.DataFrame,
    validation_matrix: pd.DataFrame,
    holdout_results: pd.DataFrame,
    excluded: pd.DataFrame,
    summary_md: str,
    threshold_sweep_csv_path: str | Path,
    validation_matrix_csv_path: str | Path,
    holdout_results_csv_path: str | Path,
    excluded_csv_path: str | Path,
    summary_md_path: str | Path,
) -> None:
    paths = [Path(threshold_sweep_csv_path), Path(validation_matrix_csv_path), Path(holdout_results_csv_path), Path(excluded_csv_path), Path(summary_md_path)]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    threshold_sweep.to_csv(threshold_sweep_csv_path, index=False)
    validation_matrix.to_csv(validation_matrix_csv_path, index=False)
    holdout_results.to_csv(holdout_results_csv_path, index=False)
    excluded.to_csv(excluded_csv_path, index=False)
    Path(summary_md_path).write_text(summary_md, encoding="utf-8")


def phase1e_summary_markdown(
    summary: dict,
    calibration_summary: pd.DataFrame,
    holdout_results: pd.DataFrame,
    threshold_sweep: pd.DataFrame,
    excluded: pd.DataFrame,
) -> str:
    lines = [
        "PHOENIX NANO PHASE 1E — CROSS-VALIDATED CONSERVATIVE FILTER VALIDATION",
        "",
        "Research-only. This does not change daily scan behavior and does not approve execution.",
        "",
        "## Phase 1D Recap",
        "",
        "- Phase 1D found promising but unapproved volatility plus smoke-score filter hypotheses.",
        "- Phase 1E calibrates thresholds on calibration samples and validates frozen filters on holdout samples.",
        "",
        "## Sample Split Used",
        "",
        f"- Calibration samples: {summary['calibration_samples']}",
        f"- Holdout samples: {summary['holdout_samples']}",
        f"- Fallback split used: {summary['fallback_used']}",
        "",
        "## Filters Tested",
        "",
        f"- Threshold-sweep filters tested: {summary['filters_tested']}",
        "- Baseline, Phase 1D fixed candidate, 20 volatility/smoke threshold combinations, and overlays for selected filters.",
        "",
        "## Calibration Results",
        "",
        calibration_summary.sort_values("worst_sample_ending_account_value", ascending=False).head(10).to_markdown(index=False) if not calibration_summary.empty else "No calibration rows.",
        "",
        "## Selected Holdout Filters",
        "",
        "\n".join(f"- {name}" for name in summary["selected_holdout_filters"]) or "- none",
        "",
        "## Holdout Results",
        "",
        holdout_results.sort_values("worst_sample_ending_account_value", ascending=False).to_markdown(index=False) if not holdout_results.empty else "No holdout rows.",
        "",
        f"- `volatility_plus_smoke_score` survived holdout: {summary['volatility_plus_smoke_score_survived']}",
        "",
        "## Overlays",
        "",
        "Theme-cap and repeated-loser cooldown overlays were tested only for selected calibration filters. They remain offline diagnostics and are not active policy.",
        "",
        "## Excluded Winner vs Loser Summary",
        "",
        f"- Excluded losers: {summary['excluded_loser_count']}",
        f"- Excluded winners: {summary['excluded_winner_count']}",
        "",
        "## Top Remaining Failure Samples",
        "",
        summary["top_remaining_failure_samples"].to_markdown(index=False) if not summary["top_remaining_failure_samples"].empty else "No remaining failure rows.",
        "",
        "## Top Remaining Failure Tickers/Themes",
        "",
        summary["theme_failure_summary"],
        "",
        f"## Final Phase 1E Status: {summary['phase_1e_status']}",
        "",
        "Do not start paper execution or real-money execution.",
        "",
        "## Next Research Task Recommendation",
        "",
        "Ask GPT to review whether Phase 1E failure patterns justify stopping Nano entry-filter tuning or running one narrower failure-regime analysis.",
        "",
    ]
    return "\n".join(lines)


def _best_row(frame: pd.DataFrame, column: str) -> dict:
    if frame.empty:
        return {}
    row = frame.sort_values(column, ascending=False).iloc[0]
    return row.to_dict()


def concat_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning, message="The behavior of DataFrame concatenation.*")
        return pd.concat(frames, ignore_index=True)
