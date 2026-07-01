from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path

import pandas as pd

from src.backtest.multi_window_smoke_test import DEFAULT_MULTI_WINDOW_SMOKE_WINDOWS, validate_non_overlapping_windows
from src.backtest.smoke_test import build_smoke_test
from src.trading.trade_simulator import STOP, TARGET_1, TARGET_2, TIME_EXIT, simulate_trades


RESEARCH_ONLY_NOT_TRADABLE = "RESEARCH_ONLY_NOT_TRADABLE"
RESEARCH_QUALIFIED_NOT_LIVE = "RESEARCH_QUALIFIED_NOT_LIVE"


@dataclass(frozen=True)
class CandidateRule:
    candidate_id: int
    max_buy_rate: float
    min_relative_volume_prev20: float
    min_smoke_score: float
    min_rank_gap: float
    require_return_5d_positive: bool
    require_return_20d_positive: bool
    distance_to_52w_high_prev_min: float
    dollar_volume_min: float


MAX_BUY_RATES = [1.0, 0.70, 0.50, 0.30, 0.15]
MIN_RELATIVE_VOLUME_PREV20 = [1.0, 1.25, 1.5, 2.0]
MIN_SMOKE_SCORES = [0.70, 0.75, 0.80, 0.85]
MIN_RANK_GAPS = [0.00, 0.03, 0.05, 0.08]
RETURN_5D_REQUIREMENTS = [True, False]
RETURN_20D_REQUIREMENTS = [True, False]
DISTANCE_TO_HIGH_MINIMUMS = [-0.35, -0.25, -0.15]
DOLLAR_VOLUME_MINIMUMS = [10_000_000, 20_000_000, 50_000_000]


def generate_candidate_rules(limit: int = 100) -> list[CandidateRule]:
    raw = list(
        product(
            MAX_BUY_RATES,
            MIN_RELATIVE_VOLUME_PREV20,
            MIN_SMOKE_SCORES,
            MIN_RANK_GAPS,
            RETURN_5D_REQUIREMENTS,
            RETURN_20D_REQUIREMENTS,
            DISTANCE_TO_HIGH_MINIMUMS,
            DOLLAR_VOLUME_MINIMUMS,
        )
    )
    early_diverse: list[tuple] = []
    for index in range(min(40, len(raw))):
        early_diverse.append(
            (
                MAX_BUY_RATES[index % len(MAX_BUY_RATES)],
                MIN_RELATIVE_VOLUME_PREV20[(index // 5) % len(MIN_RELATIVE_VOLUME_PREV20)],
                MIN_SMOKE_SCORES[(index // 3) % len(MIN_SMOKE_SCORES)],
                MIN_RANK_GAPS[(index // 2) % len(MIN_RANK_GAPS)],
                RETURN_5D_REQUIREMENTS[(index // 4) % len(RETURN_5D_REQUIREMENTS)],
                RETURN_20D_REQUIREMENTS[(index // 6) % len(RETURN_20D_REQUIREMENTS)],
                DISTANCE_TO_HIGH_MINIMUMS[index % len(DISTANCE_TO_HIGH_MINIMUMS)],
                DOLLAR_VOLUME_MINIMUMS[(index // 7) % len(DOLLAR_VOLUME_MINIMUMS)],
            )
        )

    ordered: list[tuple] = []
    seen: set[tuple] = set()
    for values in early_diverse + raw:
        if values in seen:
            continue
        ordered.append(values)
        seen.add(values)
        if len(ordered) >= limit:
            break
    return [CandidateRule(index + 1, *values) for index, values in enumerate(ordered)]


def row_passes_candidate(row: pd.Series, candidate: CandidateRule) -> bool:
    """Apply candidate BUY filter using signal-date fields only."""
    if float(row["smoke_score"]) < candidate.min_smoke_score:
        return False
    if float(row.get("rank_gap", 0.0)) < candidate.min_rank_gap:
        return False
    if pd.isna(row["relative_volume_prev20"]) or float(row["relative_volume_prev20"]) < candidate.min_relative_volume_prev20:
        return False
    if candidate.require_return_5d_positive and float(row["return_5d"]) <= 0:
        return False
    if candidate.require_return_20d_positive and float(row["return_20d"]) <= 0:
        return False
    return (
        not pd.isna(row["distance_to_52w_high_prev"])
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
        results.append(
            {
                "window_start": start,
                "window_end": end,
                "smoke_results": add_rank_gap(smoke),
                "path_data": frame,
            }
        )
    return results


def add_rank_gap(smoke_results: pd.DataFrame) -> pd.DataFrame:
    if smoke_results.empty:
        return smoke_results
    frame = smoke_results.copy()
    frame["rank_gap"] = 0.0
    for signal_date, group in frame.groupby("date", sort=False):
        ordered = group.sort_values(["smoke_score", "ticker"], ascending=[False, True])
        top_score = float(ordered.iloc[0]["smoke_score"])
        second_score = float(ordered.iloc[1]["smoke_score"]) if len(ordered) > 1 else 0.0
        frame.loc[frame["date"].eq(signal_date), "rank_gap"] = top_score - second_score
    return frame


def build_candidate_decisions(smoke_results: pd.DataFrame, candidate: CandidateRule) -> pd.DataFrame:
    if smoke_results.empty:
        return pd.DataFrame()
    rank_one = (
        smoke_results.loc[smoke_results["rank"].eq(1)]
        .sort_values(["date", "ticker"])
        .drop_duplicates("date")
        .copy()
    )
    rank_one["eligible_buy"] = rank_one.apply(lambda row: row_passes_candidate(row, candidate), axis=1)
    eligible = rank_one.loc[rank_one["eligible_buy"]].copy()
    rank_one["decision_strength"] = rank_one.apply(_decision_strength, axis=1)
    if eligible.empty:
        rank_one["is_buy"] = False
        return rank_one

    eligible["decision_strength"] = eligible.apply(_decision_strength, axis=1)
    keep_count = min(len(eligible), int(rank_one["date"].nunique() * candidate.max_buy_rate))
    if candidate.max_buy_rate > 0 and keep_count == 0 and not eligible.empty:
        keep_count = 1
    kept_index = (
        eligible.sort_values(["decision_strength", "smoke_score", "rank_gap", "date"], ascending=[False, False, False, True])
        .head(keep_count)
        .index
    )
    rank_one["is_buy"] = rank_one.index.isin(kept_index)
    return rank_one


def _decision_strength(row: pd.Series) -> float:
    smoke_score = _clip(float(row.get("smoke_score", 0.0)), 0.0, 1.0)
    rank_gap = _clip(float(row.get("rank_gap", 0.0)) / 0.20, 0.0, 1.0)
    rel_volume = row.get("relative_volume_prev20", 0.0)
    rel_volume_score = 0.0 if pd.isna(rel_volume) else _clip(float(rel_volume) / 3.0, 0.0, 1.0)
    return float((smoke_score + rank_gap + rel_volume_score) / 3.0)


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def evaluate_candidate(
    candidate: CandidateRule,
    window_smoke_results: list[dict],
    benchmark_ticker: str,
) -> tuple[dict, pd.DataFrame]:
    window_rows: list[dict] = []
    all_trade_frames: list[pd.DataFrame] = []
    total_signal_days = 0
    total_eligible_buy_days = 0
    total_final_buy_days = 0

    for item in window_smoke_results:
        decisions = build_candidate_decisions(item["smoke_results"], candidate)
        signal_days = int(decisions["date"].nunique()) if not decisions.empty else 0
        eligible_buy_days = int(decisions["eligible_buy"].sum()) if not decisions.empty else 0
        final_buy_days = int(decisions["is_buy"].sum()) if not decisions.empty else 0
        total_signal_days += signal_days
        total_eligible_buy_days += eligible_buy_days
        total_final_buy_days += final_buy_days

        buys = decisions.loc[decisions["is_buy"]].copy() if not decisions.empty else pd.DataFrame()
        if not buys.empty:
            buys["candidate_id"] = candidate.candidate_id
            buys["window_start"] = item["window_start"]
            buys["window_end"] = item["window_end"]
        trades = simulate_trades(buys, item["path_data"], benchmark_ticker=benchmark_ticker)
        if not trades.empty:
            all_trade_frames.append(trades)
        window_rows.append(_window_metrics(trades, signal_days, eligible_buy_days, final_buy_days, item["window_start"], item["window_end"]))

    windows = pd.DataFrame(window_rows)
    trades_all = pd.concat(all_trade_frames, ignore_index=True) if all_trade_frames else pd.DataFrame()
    result = asdict(candidate)
    result["signal_days"] = int(total_signal_days)
    result["eligible_buy_days"] = int(total_eligible_buy_days)
    result["final_buy_days"] = int(total_final_buy_days)
    result["buy_count"] = int(len(trades_all))
    result["final_buy_rate"] = float(total_final_buy_days / total_signal_days) if total_signal_days else pd.NA
    result["eligible_buy_rate"] = float(total_eligible_buy_days / total_signal_days) if total_signal_days else pd.NA
    result["valid_windows"] = int(windows["status"].eq("ok").sum()) if not windows.empty else 0
    result["windows_positive_realized_excess"] = int(windows["avg_realized_excess_return"].gt(0).sum()) if not windows.empty else 0
    result["windows_win_rate_ge_52pct"] = int(windows["realized_win_rate"].ge(0.52).sum()) if not windows.empty else 0

    if trades_all.empty:
        result.update(_empty_trade_metrics())
        result["status"] = RESEARCH_ONLY_NOT_TRADABLE
        result["fail_reasons"] = "no_realized_trades"
        result["risk_adjusted_score"] = pd.NA
        result["score"] = pd.NA
        result["window_summary"] = windows
        return result, trades_all

    best = trades_all.loc[trades_all["realized_return"].idxmax()]
    worst = trades_all.loc[trades_all["realized_return"].idxmin()]
    without_best = trades_all.drop(index=best.name)
    without_best_excess = (
        without_best["realized_excess_return"].mean() if not without_best.empty else pd.NA
    )
    exit_rates = trades_all["exit_reason"].value_counts(normalize=True)
    result.update(
        {
            "avg_realized_return": float(trades_all["realized_return"].mean()),
            "avg_realized_excess_return": float(trades_all["realized_excess_return"].mean()),
            "realized_win_rate": float((trades_all["realized_return"] > 0).mean()),
            "median_realized_return": float(trades_all["realized_return"].median()),
            "worst_realized_return": float(worst["realized_return"]),
            "best_realized_return": float(best["realized_return"]),
            "avg_realized_excess_excluding_best_trade": (
                float(without_best_excess) if not pd.isna(without_best_excess) else pd.NA
            ),
            "stop_hit_rate": float(exit_rates.get(STOP, 0.0)),
            "target_1_hit_rate": float(exit_rates.get(TARGET_1, 0.0)),
            "target_2_hit_rate": float(exit_rates.get(TARGET_2, 0.0)),
            "time_exit_rate": float(exit_rates.get(TIME_EXIT, 0.0)),
            "avg_holding_days": float(trades_all["holding_days"].mean()),
            "best_trade": _trade_label(best),
            "worst_trade": _trade_label(worst),
            "window_summary": windows,
        }
    )
    fail_reasons = _gate_fail_reasons(result)
    result["fail_reasons"] = ", ".join(fail_reasons)
    result["status"] = RESEARCH_QUALIFIED_NOT_LIVE if not fail_reasons else RESEARCH_ONLY_NOT_TRADABLE
    result["risk_adjusted_score"] = score_candidate(result)
    result["score"] = result["risk_adjusted_score"] if result["status"] == RESEARCH_QUALIFIED_NOT_LIVE else pd.NA
    return result, trades_all


def _window_metrics(
    trades: pd.DataFrame,
    signal_days: int,
    eligible_buy_days: int,
    final_buy_days: int,
    start: str,
    end: str,
) -> dict:
    base = {
        "window_start": start,
        "window_end": end,
        "signal_days": int(signal_days),
        "eligible_buy_days": int(eligible_buy_days),
        "final_buy_days": int(final_buy_days),
        "final_buy_rate": float(final_buy_days / signal_days) if signal_days else pd.NA,
    }
    if trades.empty:
        return {
            **base,
            "status": "insufficient_data",
            "avg_realized_return": pd.NA,
            "avg_realized_excess_return": pd.NA,
            "realized_win_rate": pd.NA,
            "stop_hit_rate": pd.NA,
            "target_1_hit_rate": pd.NA,
            "target_2_hit_rate": pd.NA,
            "time_exit_rate": pd.NA,
        }
    exit_rates = trades["exit_reason"].value_counts(normalize=True)
    return {
        **base,
        "status": "ok",
        "avg_realized_return": float(trades["realized_return"].mean()),
        "avg_realized_excess_return": float(trades["realized_excess_return"].mean()),
        "realized_win_rate": float((trades["realized_return"] > 0).mean()),
        "stop_hit_rate": float(exit_rates.get(STOP, 0.0)),
        "target_1_hit_rate": float(exit_rates.get(TARGET_1, 0.0)),
        "target_2_hit_rate": float(exit_rates.get(TARGET_2, 0.0)),
        "time_exit_rate": float(exit_rates.get(TIME_EXIT, 0.0)),
    }


def _empty_trade_metrics() -> dict:
    return {
        "avg_realized_return": pd.NA,
        "avg_realized_excess_return": pd.NA,
        "realized_win_rate": pd.NA,
        "median_realized_return": pd.NA,
        "worst_realized_return": pd.NA,
        "best_realized_return": pd.NA,
        "avg_realized_excess_excluding_best_trade": pd.NA,
        "stop_hit_rate": pd.NA,
        "target_1_hit_rate": pd.NA,
        "target_2_hit_rate": pd.NA,
        "time_exit_rate": pd.NA,
        "avg_holding_days": pd.NA,
        "best_trade": "",
        "worst_trade": "",
    }


def _gate_fail_reasons(result: dict) -> list[str]:
    reasons: list[str] = []
    if result["valid_windows"] < 8:
        reasons.append("valid_windows_lt_8")
    if result["buy_count"] < 40:
        reasons.append("final_buy_count_lt_40")
    if pd.isna(result["final_buy_rate"]) or float(result["final_buy_rate"]) > 0.50:
        reasons.append("final_buy_rate_above_50pct")
    if not _gt(result["avg_realized_excess_return"], 0):
        reasons.append("avg_realized_excess_return_not_positive")
    if not _ge(result["realized_win_rate"], 0.52):
        reasons.append("realized_win_rate_lt_52pct")
    if result["windows_positive_realized_excess"] < 6:
        reasons.append("positive_realized_excess_windows_lt_6")
    if not _gt(result["avg_realized_excess_excluding_best_trade"], 0):
        reasons.append("excluding_best_trade_excess_not_positive")
    if not _gt(result["worst_realized_return"], -0.25):
        reasons.append("worst_realized_return_lte_minus_25pct")
    if pd.isna(result["stop_hit_rate"]) or float(result["stop_hit_rate"]) > 0.65:
        reasons.append("stop_hit_rate_above_65pct")
    return reasons


def _gt(value: object, threshold: float) -> bool:
    return not pd.isna(value) and float(value) > threshold


def _ge(value: object, threshold: float) -> bool:
    return not pd.isna(value) and float(value) >= threshold


def score_candidate(result: dict) -> float:
    if pd.isna(result["avg_realized_excess_return"]) or pd.isna(result["realized_win_rate"]):
        return pd.NA
    valid_windows = max(float(result["valid_windows"]), 1.0)
    return (
        float(result["avg_realized_excess_return"]) * 100
        + float(result["realized_win_rate"]) * 20
        + (float(result["windows_positive_realized_excess"]) / valid_windows) * 20
        - abs(float(result["worst_realized_return"])) * 10
        - float(result["stop_hit_rate"]) * 5
    )


def run_auto_research_loop(
    data: pd.DataFrame,
    benchmark_ticker: str,
    horizons: list[int],
    windows: list[tuple[str, str]] | None = None,
    max_candidates: int = 100,
    min_candidates_before_early_stop: int = 50,
    no_improvement_limit: int = 10,
    data_start: str | None = None,
    research_start: str | None = None,
    research_end: str | None = None,
    warmup_limitation: str = "",
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    window_smoke_results = build_window_smoke_results(data, benchmark_ticker, horizons, windows)
    rows: list[dict] = []
    trade_frames: list[pd.DataFrame] = []
    best_score: float | None = None
    no_improvement_count = 0
    stop_reason = ""
    candidates = generate_candidate_rules(max(max_candidates, min_candidates_before_early_stop))

    for candidate in candidates[:max_candidates]:
        evaluated, trades = evaluate_candidate(candidate, window_smoke_results, benchmark_ticker)
        if not trades.empty:
            trade_frames.append(trades)
        window_summary = evaluated.pop("window_summary")
        evaluated["window_summary_json"] = window_summary.to_json(orient="records")
        rows.append(evaluated)
        score = evaluated["risk_adjusted_score"]
        if not pd.isna(score) and (best_score is None or float(score) > best_score):
            best_score = float(score)
            no_improvement_count = 0
        else:
            no_improvement_count += 1
        if len(rows) >= min_candidates_before_early_stop and no_improvement_count >= no_improvement_limit:
            stop_reason = f"{no_improvement_limit}_consecutive_candidates_failed_to_improve_best_score"
            break

    results = pd.DataFrame(rows)
    all_trades = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    passed = int(results["status"].eq(RESEARCH_QUALIFIED_NOT_LIVE).sum()) if not results.empty else 0
    if not stop_reason:
        stop_reason = "completed_candidate_budget"
    summary = {
        "total_candidates_available": int(len(candidates)),
        "total_candidates_tested": int(len(results)),
        "total_candidates_evaluated": int(len(results)),
        "candidates_passed_gate": passed,
        "candidates_failed_gate": int(len(results) - passed),
        "stop_reason": stop_reason,
        "early_stop_reason": stop_reason,
        "data_start": data_start or "",
        "research_start": research_start or "",
        "research_end": research_end or "",
        "warmup_limitation": warmup_limitation,
    }
    return results, summary, all_trades


def write_auto_research_summary(results: pd.DataFrame, summary: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    qualified = results.loc[results["status"].eq(RESEARCH_QUALIFIED_NOT_LIVE)].copy()
    best_qualified = None if qualified.empty else qualified.sort_values("score", ascending=False).iloc[0]
    best_any = None
    if not results.empty:
        best_any = results.sort_values("risk_adjusted_score", ascending=False, na_position="last").iloc[0]

    top_by_excess = results.sort_values("avg_realized_excess_return", ascending=False, na_position="last").head(10).copy()
    top_by_score = results.sort_values("risk_adjusted_score", ascending=False, na_position="last").head(10).copy()
    percent_columns = [
        "eligible_buy_rate",
        "final_buy_rate",
        "avg_realized_return",
        "avg_realized_excess_return",
        "realized_win_rate",
        "median_realized_return",
        "worst_realized_return",
        "best_realized_return",
        "avg_realized_excess_excluding_best_trade",
        "stop_hit_rate",
        "target_1_hit_rate",
        "target_2_hit_rate",
        "time_exit_rate",
    ]
    display_cols = [
        "candidate_id",
        "status",
        "risk_adjusted_score",
        "max_buy_rate",
        "min_relative_volume_prev20",
        "min_smoke_score",
        "min_rank_gap",
        "require_return_5d_positive",
        "require_return_20d_positive",
        "distance_to_52w_high_prev_min",
        "dollar_volume_min",
        "signal_days",
        "eligible_buy_days",
        "final_buy_days",
        "final_buy_rate",
        "avg_realized_excess_return",
        "realized_win_rate",
        "worst_realized_return",
        "stop_hit_rate",
        "target_1_hit_rate",
        "target_2_hit_rate",
        "time_exit_rate",
        "fail_reasons",
    ]
    top_by_excess = _format_display_frame(top_by_excess, percent_columns)
    top_by_score = _format_display_frame(top_by_score, percent_columns)
    common_fail_reasons = _common_fail_reasons(results)

    lines = [
        "# Phoenix AlphaLab Auto Research Loop v0.2",
        "",
        "## Research Mode",
        "",
        "- Offline historical research only.",
        "- New alpha sources: none.",
        "- Trade simulator: historical virtual trades only.",
        "- Live-tradable versions: none.",
        "- Research-qualified means GPT review is required before any paper trading.",
        "",
        "## Summary",
        "",
        f"- Data start: {summary.get('data_start') or 'not reported'}",
        f"- Research start: {summary.get('research_start') or 'not reported'}",
        f"- Research end: {summary.get('research_end') or 'not reported'}",
        f"- Warmup limitation: {summary.get('warmup_limitation') or 'None reported'}",
        f"- Total candidates available: {summary.get('total_candidates_available', len(results))}",
        f"- Total candidates evaluated: {summary.get('total_candidates_evaluated', len(results))}",
        f"- Candidates passed gate: {summary['candidates_passed_gate']}",
        f"- Candidates failed gate: {summary['candidates_failed_gate']}",
        f"- Stop reason: {summary.get('stop_reason') or summary.get('early_stop_reason') or 'None'}",
        f"- BUY rate distribution after active enforcement: {_distribution(results, 'final_buy_rate')}",
        f"- Realized return distribution: {_distribution(results, 'avg_realized_return')}",
        f"- Stop/target/time-exit breakdown: {_exit_breakdown(results)}",
        "",
        (
            "No research-qualified version found. Do not use Phoenix for live trading."
            if best_qualified is None
            else "Research-qualified candidates found. GPT review required before any paper trading."
        ),
        "",
    ]
    if best_any is not None:
        lines.extend(_candidate_lines("Best Candidate Even If Failed", best_any))
    if best_qualified is not None:
        lines.extend(_candidate_lines("Best Research-Qualified Candidate", best_qualified))

    lines.extend(
        [
            "## Top 10 By Realized Excess",
            "",
            top_by_excess[display_cols].to_markdown(index=False),
            "",
            "## Top 10 By Risk-Adjusted Score",
            "",
            top_by_score[display_cols].to_markdown(index=False),
            "",
            "## Worst And Best Realized Trades",
            "",
            f"- Worst realized trade: {_best_or_worst_trade(results, 'worst_trade', 'worst_realized_return', ascending=True)}",
            f"- Best realized trade: {_best_or_worst_trade(results, 'best_trade', 'best_realized_return', ascending=False)}",
            "",
            "## Common Fail Reasons",
            "",
            pd.DataFrame(common_fail_reasons, columns=["fail_reason", "count"]).to_markdown(index=False)
            if common_fail_reasons
            else "No fail reasons recorded.",
            "",
            "## Warning",
            "",
            "Phoenix remains not live-tradable unless a candidate passes all gates and GPT reviews it.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _candidate_lines(title: str, row: pd.Series) -> list[str]:
    return [
        f"## {title}",
        "",
        f"- Candidate ID: {int(row['candidate_id'])}",
        f"- Status: {row['status']}",
        f"- Risk-adjusted score: {_format_number(row['risk_adjusted_score'])}",
        f"- Final BUY days: {int(row['final_buy_days'])}",
        f"- Final BUY rate: {_format_percent(row['final_buy_rate'])}",
        f"- Average realized return: {_format_percent(row['avg_realized_return'])}",
        f"- Average realized excess return: {_format_percent(row['avg_realized_excess_return'])}",
        f"- Realized win rate: {_format_percent(row['realized_win_rate'])}",
        f"- Worst realized return: {_format_percent(row['worst_realized_return'])}",
        f"- Best realized return: {_format_percent(row['best_realized_return'])}",
        f"- Stop hit rate: {_format_percent(row['stop_hit_rate'])}",
        f"- Target 1 hit rate: {_format_percent(row['target_1_hit_rate'])}",
        f"- Target 2 hit rate: {_format_percent(row['target_2_hit_rate'])}",
        f"- Time exit rate: {_format_percent(row['time_exit_rate'])}",
        f"- Fail reasons: {row.get('fail_reasons', '')}",
        "",
    ]


def _trade_label(row: pd.Series) -> str:
    return f"{row['signal_date']} {row['ticker']} {_format_percent(row['realized_return'])} {row['exit_reason']}"


def _format_display_frame(frame: pd.DataFrame, percent_columns: list[str]) -> pd.DataFrame:
    display = frame.copy()
    for column in percent_columns:
        if column in display.columns:
            display[column] = display[column].map(_format_percent)
    return display


def _common_fail_reasons(results: pd.DataFrame) -> list[tuple[str, int]]:
    if results.empty or "fail_reasons" not in results.columns:
        return []
    counter: Counter[str] = Counter()
    for value in results["fail_reasons"].dropna():
        for reason in str(value).split(","):
            clean = reason.strip()
            if clean:
                counter[clean] += 1
    return counter.most_common()


def _distribution(results: pd.DataFrame, column: str) -> str:
    if results.empty or column not in results.columns:
        return "no data"
    values = results[column].dropna().astype(float)
    if values.empty:
        return "no data"
    return f"min {_format_percent(values.min())}, median {_format_percent(values.median())}, max {_format_percent(values.max())}"


def _exit_breakdown(results: pd.DataFrame) -> str:
    if results.empty:
        return "no data"
    return (
        f"stop {_format_percent(results['stop_hit_rate'].dropna().mean())}, "
        f"target1 {_format_percent(results['target_1_hit_rate'].dropna().mean())}, "
        f"target2 {_format_percent(results['target_2_hit_rate'].dropna().mean())}, "
        f"time {_format_percent(results['time_exit_rate'].dropna().mean())}"
    )


def _best_or_worst_trade(results: pd.DataFrame, label_column: str, metric_column: str, ascending: bool) -> str:
    if results.empty or metric_column not in results.columns:
        return ""
    sorted_results = results.sort_values(metric_column, ascending=ascending, na_position="last")
    if sorted_results.empty or pd.isna(sorted_results.iloc[0][metric_column]):
        return ""
    return str(sorted_results.iloc[0][label_column])


def _format_percent(value: object) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        return ""
    return f"{float(value):.2%}"


def _format_number(value: object) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        return ""
    return f"{float(value):.4f}"
