from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path

import pandas as pd

from src.backtest.multi_window_smoke_test import DEFAULT_MULTI_WINDOW_SMOKE_WINDOWS, validate_non_overlapping_windows
from src.backtest.smoke_test import build_smoke_test


RESEARCH_ONLY_NOT_TRADABLE = "RESEARCH_ONLY_NOT_TRADABLE"
RESEARCH_QUALIFIED_NOT_LIVE = "RESEARCH_QUALIFIED_NOT_LIVE"


@dataclass(frozen=True)
class CandidateRule:
    candidate_id: int
    smoke_score_threshold: float
    require_return_5d_positive: bool
    require_return_20d_positive: bool
    distance_to_52w_high_prev_min: float
    dollar_volume_min: float
    max_buy_rate: float


def generate_candidate_rules(limit: int = 50) -> list[CandidateRule]:
    candidates: list[CandidateRule] = []
    candidate_id = 1
    for values in product(
        [0.65, 0.70, 0.75, 0.80],
        [True, False],
        [True, False],
        [-0.35, -0.25, -0.15],
        [10_000_000, 20_000_000, 50_000_000],
        [1.0, 0.70, 0.50, 0.30],
    ):
        candidates.append(CandidateRule(candidate_id, *values))
        candidate_id += 1
        if len(candidates) >= limit:
            return candidates
    return candidates


def row_passes_candidate(row: pd.Series, candidate: CandidateRule) -> bool:
    """Apply candidate BUY filter using only signal-date fields, not labels."""
    if float(row["smoke_score"]) < candidate.smoke_score_threshold:
        return False
    if candidate.require_return_5d_positive and float(row["return_5d"]) <= 0:
        return False
    if candidate.require_return_20d_positive and float(row["return_20d"]) <= 0:
        return False
    return (
        not pd.isna(row["relative_volume_prev20"])
        and float(row["distance_to_52w_high_prev"]) >= candidate.distance_to_52w_high_prev_min
        and float(row["dollar_volume"]) >= candidate.dollar_volume_min
    )


def build_window_smoke_results(
    data: pd.DataFrame,
    benchmark_ticker: str,
    horizons: list[int],
    windows: list[tuple[str, str]] | None = None,
) -> list[dict]:
    smoke_windows = windows or DEFAULT_MULTI_WINDOW_SMOKE_WINDOWS
    validate_non_overlapping_windows(smoke_windows)
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    results: list[dict] = []
    for start, end in smoke_windows:
        window_data = frame.loc[frame["date"].between(pd.Timestamp(start), pd.Timestamp(end))].copy()
        smoke = build_smoke_test(
            window_data,
            benchmark_ticker=benchmark_ticker,
            horizons=horizons,
            smoke_days=100_000,
            top_n=5,
        )
        results.append({"window_start": start, "window_end": end, "smoke_results": smoke})
    return results


def _rank_one_decisions(smoke_results: pd.DataFrame, candidate: CandidateRule) -> pd.DataFrame:
    if smoke_results.empty:
        return pd.DataFrame()
    rank_one = (
        smoke_results.loc[smoke_results["rank"].eq(1)]
        .sort_values(["date", "ticker"])
        .drop_duplicates("date")
        .copy()
    )
    rank_one["is_buy"] = rank_one.apply(lambda row: row_passes_candidate(row, candidate), axis=1)
    return rank_one


def _window_metrics(decisions: pd.DataFrame, start: str, end: str) -> dict:
    signal_days = int(decisions["date"].nunique()) if not decisions.empty else 0
    buys = decisions.loc[decisions["is_buy"]].copy() if not decisions.empty else pd.DataFrame()
    if buys.empty:
        return {
            "window_start": start,
            "window_end": end,
            "status": "insufficient_data",
            "signal_days": signal_days,
            "buy_days": 0,
            "buy_rate": 0.0 if signal_days else pd.NA,
            "avg_return_5d": pd.NA,
            "avg_excess_return_5d": pd.NA,
            "avg_return_10d": pd.NA,
            "avg_excess_return_10d": pd.NA,
            "avg_return_20d": pd.NA,
            "avg_excess_return_20d": pd.NA,
            "win_rate_20d": pd.NA,
            "days_outperformed_spy_20d": 0,
            "eligible_days_20d": 0,
            "best_buy": "",
            "worst_buy": "",
            "removing_best_buy_20d_avg_excess_positive": False,
        }

    daily = buys.groupby("date")["excess_return_20d"].mean()
    best = buys.loc[buys["fwd_return_20d"].idxmax()]
    worst = buys.loc[buys["fwd_return_20d"].idxmin()]
    without_best = buys.drop(index=best.name)
    without_best_avg = without_best["excess_return_20d"].mean() if not without_best.empty else pd.NA
    return {
        "window_start": start,
        "window_end": end,
        "status": "ok",
        "signal_days": signal_days,
        "buy_days": int(len(buys)),
        "buy_rate": float(len(buys) / signal_days) if signal_days else pd.NA,
        "avg_return_5d": float(buys["fwd_return_5d"].mean()),
        "avg_excess_return_5d": float(buys["excess_return_5d"].mean()),
        "avg_return_10d": float(buys["fwd_return_10d"].mean()),
        "avg_excess_return_10d": float(buys["excess_return_10d"].mean()),
        "avg_return_20d": float(buys["fwd_return_20d"].mean()),
        "avg_excess_return_20d": float(buys["excess_return_20d"].mean()),
        "win_rate_20d": float((buys["fwd_return_20d"] > 0).mean()),
        "days_outperformed_spy_20d": int((daily > 0).sum()),
        "eligible_days_20d": int(daily.count()),
        "best_buy": _trade_label(best),
        "worst_buy": _trade_label(worst),
        "removing_best_buy_20d_avg_excess_positive": bool(not pd.isna(without_best_avg) and without_best_avg > 0),
    }


def _trade_label(row: pd.Series) -> str:
    return f"{row['date']} {row['ticker']} {_format_percent(row['fwd_return_20d'])}"


def evaluate_candidate(candidate: CandidateRule, window_smoke_results: list[dict]) -> dict:
    window_rows: list[dict] = []
    buy_frames: list[pd.DataFrame] = []
    total_signal_days = 0
    for item in window_smoke_results:
        decisions = _rank_one_decisions(item["smoke_results"], candidate)
        total_signal_days += int(decisions["date"].nunique()) if not decisions.empty else 0
        window_rows.append(_window_metrics(decisions, item["window_start"], item["window_end"]))
        if not decisions.empty:
            buys = decisions.loc[decisions["is_buy"]].copy()
            if not buys.empty:
                buy_frames.append(buys)

    windows = pd.DataFrame(window_rows)
    buys_all = pd.concat(buy_frames, ignore_index=True) if buy_frames else pd.DataFrame()
    result = asdict(candidate)
    result["valid_windows"] = int(windows["status"].eq("ok").sum())
    result["windows_20d_avg_excess_positive"] = int(windows["avg_excess_return_20d"].gt(0).sum())
    outperform_ratio = windows["days_outperformed_spy_20d"] / windows["eligible_days_20d"].replace(0, pd.NA)
    result["windows_20d_outperform_days_above_half"] = int(outperform_ratio.gt(0.5).sum())
    result["total_signal_days"] = int(total_signal_days)
    result["buy_count"] = int(len(buys_all))
    result["overall_buy_rate"] = float(len(buys_all) / total_signal_days) if total_signal_days else pd.NA

    if buys_all.empty:
        result.update(
            {
                "overall_20d_avg_excess": pd.NA,
                "overall_20d_win_rate": pd.NA,
                "best_buy": "",
                "worst_buy": "",
                "worst_20d_return": pd.NA,
                "without_best_20d_avg_excess": pd.NA,
                "status": RESEARCH_ONLY_NOT_TRADABLE,
                "score": pd.NA,
                "fail_reasons": "no_buys",
                "window_summary": windows,
            }
        )
        return result

    best = buys_all.loc[buys_all["fwd_return_20d"].idxmax()]
    worst = buys_all.loc[buys_all["fwd_return_20d"].idxmin()]
    without_best = buys_all.drop(index=best.name)
    without_best_avg = without_best["excess_return_20d"].mean() if not without_best.empty else pd.NA
    result.update(
        {
            "overall_20d_avg_excess": float(buys_all["excess_return_20d"].mean()),
            "overall_20d_win_rate": float((buys_all["fwd_return_20d"] > 0).mean()),
            "best_buy": _trade_label(best),
            "worst_buy": _trade_label(worst),
            "worst_20d_return": float(worst["fwd_return_20d"]),
            "without_best_20d_avg_excess": float(without_best_avg) if not pd.isna(without_best_avg) else pd.NA,
            "window_summary": windows,
        }
    )
    fail_reasons = _gate_fail_reasons(result)
    result["fail_reasons"] = ", ".join(fail_reasons)
    result["status"] = RESEARCH_QUALIFIED_NOT_LIVE if not fail_reasons else RESEARCH_ONLY_NOT_TRADABLE
    result["score"] = score_candidate(result) if result["status"] == RESEARCH_QUALIFIED_NOT_LIVE else pd.NA
    return result


def _gate_fail_reasons(result: dict) -> list[str]:
    reasons: list[str] = []
    if result["valid_windows"] < 8:
        reasons.append("valid_windows_lt_8")
    if result["windows_20d_avg_excess_positive"] < 6:
        reasons.append("positive_20d_excess_windows_lt_6")
    if result["windows_20d_outperform_days_above_half"] < 6:
        reasons.append("outperform_days_windows_lt_6")
    if not _gt(result["overall_20d_avg_excess"], 0):
        reasons.append("overall_20d_avg_excess_not_positive")
    if not _ge(result["overall_20d_win_rate"], 0.52):
        reasons.append("overall_20d_win_rate_lt_52pct")
    if result["buy_count"] < 40:
        reasons.append("buy_count_lt_40")
    if not _gt(result["without_best_20d_avg_excess"], 0):
        reasons.append("without_best_20d_avg_excess_not_positive")
    if not _gt(result["worst_20d_return"], -0.60):
        reasons.append("worst_20d_return_lte_minus_60pct")
    if not pd.isna(result["overall_buy_rate"]) and result["overall_buy_rate"] > result["max_buy_rate"]:
        reasons.append("overall_buy_rate_above_candidate_max")
    return reasons


def _gt(value: object, threshold: float) -> bool:
    return not pd.isna(value) and float(value) > threshold


def _ge(value: object, threshold: float) -> bool:
    return not pd.isna(value) and float(value) >= threshold


def score_candidate(result: dict) -> float:
    return (
        float(result["overall_20d_avg_excess"]) * 100
        + float(result["overall_20d_win_rate"]) * 20
        + (float(result["windows_20d_avg_excess_positive"]) / float(result["valid_windows"])) * 20
        - abs(float(result["worst_20d_return"])) * 10
    )


def run_auto_research_loop(
    data: pd.DataFrame,
    benchmark_ticker: str,
    horizons: list[int],
    windows: list[tuple[str, str]] | None = None,
    max_candidates: int = 50,
    no_improvement_limit: int = 10,
) -> tuple[pd.DataFrame, dict]:
    window_smoke_results = build_window_smoke_results(data, benchmark_ticker, horizons, windows)
    rows: list[dict] = []
    best_score: float | None = None
    no_improvement_count = 0
    early_stop_reason = ""

    for candidate in generate_candidate_rules(max_candidates):
        evaluated = evaluate_candidate(candidate, window_smoke_results)
        window_summary = evaluated.pop("window_summary")
        evaluated["window_summary_json"] = window_summary.to_json(orient="records")
        rows.append(evaluated)
        score = evaluated["score"]
        if not pd.isna(score) and (best_score is None or float(score) > best_score):
            best_score = float(score)
            no_improvement_count = 0
        else:
            no_improvement_count += 1
        if no_improvement_count >= no_improvement_limit:
            early_stop_reason = f"{no_improvement_limit}_consecutive_candidates_failed_to_improve_best_score"
            break

    results = pd.DataFrame(rows)
    passed = int(results["status"].eq(RESEARCH_QUALIFIED_NOT_LIVE).sum()) if not results.empty else 0
    if not early_stop_reason and passed < 3:
        early_stop_reason = "fewer_than_3_candidates_passed_minimum_threshold"
    summary = {
        "total_candidates_tested": int(len(results)),
        "candidates_passed_gate": passed,
        "candidates_failed_gate": int(len(results) - passed),
        "early_stop_reason": early_stop_reason,
    }
    return results, summary


def write_auto_research_summary(results: pd.DataFrame, summary: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    qualified = results.loc[results["status"].eq(RESEARCH_QUALIFIED_NOT_LIVE)].copy()
    best = None
    if not qualified.empty:
        best = qualified.sort_values("score", ascending=False).iloc[0]

    top = results.sort_values("score", ascending=False, na_position="last").head(10).copy()
    display_cols = [
        "candidate_id",
        "status",
        "score",
        "smoke_score_threshold",
        "require_return_5d_positive",
        "require_return_20d_positive",
        "distance_to_52w_high_prev_min",
        "dollar_volume_min",
        "max_buy_rate",
        "buy_count",
        "overall_buy_rate",
        "overall_20d_avg_excess",
        "overall_20d_win_rate",
        "worst_20d_return",
        "fail_reasons",
    ]
    for column in ["overall_buy_rate", "overall_20d_avg_excess", "overall_20d_win_rate", "worst_20d_return"]:
        if column in top.columns:
            top[column] = top[column].map(_format_percent)

    lines = [
        "# Phoenix AlphaLab Auto Research Loop",
        "",
        "## Research Mode",
        "",
        "- Offline historical research only.",
        "- New alpha factors: none.",
        "- Live-tradable versions: none.",
        "- Research-qualified means worth deeper review, not safe to trade.",
        "",
        "## Summary",
        "",
        f"- Total candidates tested: {summary['total_candidates_tested']}",
        f"- Candidates passed gate: {summary['candidates_passed_gate']}",
        f"- Candidates failed gate: {summary['candidates_failed_gate']}",
        f"- Early stop reason: {summary['early_stop_reason'] or 'None'}",
        "",
    ]
    if best is None:
        lines.extend(
            [
                "No research-qualified version found. Do not use Phoenix for live trading.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Best Candidate",
                "",
                f"- Candidate ID: {int(best['candidate_id'])}",
                f"- Status: {best['status']}",
                f"- Score: {best['score']:.4f}",
                f"- smoke_score_threshold: {best['smoke_score_threshold']}",
                f"- require_return_5d_positive: {best['require_return_5d_positive']}",
                f"- require_return_20d_positive: {best['require_return_20d_positive']}",
                f"- distance_to_52w_high_prev_min: {best['distance_to_52w_high_prev_min']}",
                f"- dollar_volume_min: {best['dollar_volume_min']}",
                f"- max_buy_rate: {_format_percent(best['max_buy_rate'])}",
                f"- Valid windows: {int(best['valid_windows'])}",
                f"- Overall 20d avg excess: {_format_percent(best['overall_20d_avg_excess'])}",
                f"- Overall 20d win rate: {_format_percent(best['overall_20d_win_rate'])}",
                f"- Worst 20d return: {_format_percent(best['worst_20d_return'])}",
                "",
                "## Best Candidate Cross-Window Summary",
                "",
                pd.read_json(best["window_summary_json"]).to_markdown(index=False),
                "",
            ]
        )
    lines.extend(
        [
            "## Top 10 Candidates",
            "",
            top[display_cols].to_markdown(index=False),
            "",
            "## Warning",
            "",
            "No version is live-tradable yet.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_percent(value: object) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        return ""
    return f"{float(value):.2%}"
