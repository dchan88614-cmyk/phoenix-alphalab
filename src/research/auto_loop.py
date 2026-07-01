from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import Counter
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


SMOKE_THRESHOLDS = [0.65, 0.70, 0.75, 0.80]
RETURN_5D_REQUIREMENTS = [True, False]
RETURN_20D_REQUIREMENTS = [True, False]
DISTANCE_TO_HIGH_MINIMUMS = [-0.35, -0.25, -0.15]
DOLLAR_VOLUME_MINIMUMS = [10_000_000, 20_000_000, 50_000_000]
MAX_BUY_RATES = [1.0, 0.70, 0.50, 0.30]


def generate_candidate_rules(limit: int = 100) -> list[CandidateRule]:
    raw_combinations = list(
        product(
            SMOKE_THRESHOLDS,
            RETURN_5D_REQUIREMENTS,
            RETURN_20D_REQUIREMENTS,
            DISTANCE_TO_HIGH_MINIMUMS,
            DOLLAR_VOLUME_MINIMUMS,
            MAX_BUY_RATES,
        )
    )
    early_diverse: list[tuple] = []
    for index in range(min(20, len(raw_combinations))):
        early_diverse.append(
            (
                SMOKE_THRESHOLDS[index % len(SMOKE_THRESHOLDS)],
                RETURN_5D_REQUIREMENTS[(index // 4) % len(RETURN_5D_REQUIREMENTS)],
                RETURN_20D_REQUIREMENTS[(index // 2) % len(RETURN_20D_REQUIREMENTS)],
                DISTANCE_TO_HIGH_MINIMUMS[index % len(DISTANCE_TO_HIGH_MINIMUMS)],
                DOLLAR_VOLUME_MINIMUMS[(index // 3) % len(DOLLAR_VOLUME_MINIMUMS)],
                MAX_BUY_RATES[(index // 5) % len(MAX_BUY_RATES)],
            )
        )

    ordered: list[tuple] = []
    seen: set[tuple] = set()
    for values in early_diverse + raw_combinations:
        if values in seen:
            continue
        ordered.append(values)
        seen.add(values)
        if len(ordered) >= limit:
            break

    return [CandidateRule(index + 1, *values) for index, values in enumerate(ordered)]


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
        results.append(
            {
                "window_start": start,
                "window_end": end,
                "smoke_results": smoke,
                "path_data": frame,
            }
        )
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


def add_path_diagnostics(decisions: pd.DataFrame, price_data: pd.DataFrame) -> pd.DataFrame:
    """Attach historical stop/target path diagnostics without changing BUY decisions."""
    if decisions.empty:
        return decisions

    required = {"date", "ticker", "high", "low"}
    if missing := required.difference(price_data.columns):
        diagnosed = decisions.copy()
        diagnosed["stop_loss_hit_20d"] = pd.NA
        diagnosed["target_1_hit_20d"] = pd.NA
        diagnosed["target_2_hit_20d"] = pd.NA
        diagnosed["path_diagnostic_note"] = f"missing_columns:{','.join(sorted(missing))}"
        return diagnosed

    history = price_data.copy()
    history["date"] = pd.to_datetime(history["date"])
    history = history.sort_values(["ticker", "date"])
    by_ticker = {ticker: group for ticker, group in history.groupby("ticker")}

    rows: list[dict] = []
    for _, row in decisions.iterrows():
        record = row.to_dict()
        close = row.get("close", pd.NA)
        atr = row.get("atr", pd.NA)
        if pd.isna(close):
            record.update(
                {
                    "stop_loss_hit_20d": pd.NA,
                    "target_1_hit_20d": pd.NA,
                    "target_2_hit_20d": pd.NA,
                    "path_diagnostic_note": "missing_close",
                }
            )
            rows.append(record)
            continue

        close_value = float(close)
        if pd.isna(atr) or float(atr) <= 0:
            stop_loss = close_value * 0.92
            target_1 = close_value * 1.12
            target_2 = close_value * 1.20
        else:
            atr_value = float(atr)
            stop_loss = close_value - 1.5 * atr_value
            target_1 = close_value + 2.0 * atr_value
            target_2 = close_value + 3.0 * atr_value

        ticker_history = by_ticker.get(row["ticker"])
        if ticker_history is None:
            path = pd.DataFrame()
        else:
            path = ticker_history.loc[ticker_history["date"].gt(pd.Timestamp(row["date"]))].head(20)

        if path.empty:
            record.update(
                {
                    "stop_loss_hit_20d": pd.NA,
                    "target_1_hit_20d": pd.NA,
                    "target_2_hit_20d": pd.NA,
                    "path_diagnostic_note": "no_forward_path",
                }
            )
        else:
            record.update(
                {
                    "stop_loss_hit_20d": bool(path["low"].le(stop_loss).any()),
                    "target_1_hit_20d": bool(path["high"].ge(target_1).any()),
                    "target_2_hit_20d": bool(path["high"].ge(target_2).any()),
                    "path_diagnostic_note": "",
                }
            )
        rows.append(record)
    return pd.DataFrame(rows)


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
            "stop_hit_rate_20d": pd.NA,
            "target_1_hit_rate_20d": pd.NA,
            "target_2_hit_rate_20d": pd.NA,
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
        "stop_hit_rate_20d": _boolean_rate(buys, "stop_loss_hit_20d"),
        "target_1_hit_rate_20d": _boolean_rate(buys, "target_1_hit_20d"),
        "target_2_hit_rate_20d": _boolean_rate(buys, "target_2_hit_20d"),
    }


def _boolean_rate(frame: pd.DataFrame, column: str) -> object:
    if column not in frame.columns:
        return pd.NA
    values = frame[column].dropna()
    return float(values.astype(bool).mean()) if not values.empty else pd.NA


def _trade_label(row: pd.Series) -> str:
    return f"{row['date']} {row['ticker']} {_format_percent(row['fwd_return_20d'])}"


def evaluate_candidate(candidate: CandidateRule, window_smoke_results: list[dict]) -> dict:
    window_rows: list[dict] = []
    buy_frames: list[pd.DataFrame] = []
    total_signal_days = 0
    for item in window_smoke_results:
        decisions = _rank_one_decisions(item["smoke_results"], candidate)
        if "path_data" in item:
            decisions = add_path_diagnostics(decisions, item["path_data"])
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
                "overall_20d_avg_return": pd.NA,
                "overall_20d_win_rate": pd.NA,
                "best_buy": "",
                "worst_buy": "",
                "worst_20d_return": pd.NA,
                "without_best_20d_avg_excess": pd.NA,
                "avg_excess_excluding_best_buy_20d": pd.NA,
                "stop_hit_rate_20d": pd.NA,
                "target_1_hit_rate_20d": pd.NA,
                "target_2_hit_rate_20d": pd.NA,
                "status": RESEARCH_ONLY_NOT_TRADABLE,
                "score": pd.NA,
                "risk_adjusted_score": pd.NA,
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
            "overall_20d_avg_return": float(buys_all["fwd_return_20d"].mean()),
            "overall_20d_avg_excess": float(buys_all["excess_return_20d"].mean()),
            "overall_20d_win_rate": float((buys_all["fwd_return_20d"] > 0).mean()),
            "best_buy": _trade_label(best),
            "worst_buy": _trade_label(worst),
            "worst_20d_return": float(worst["fwd_return_20d"]),
            "without_best_20d_avg_excess": float(without_best_avg) if not pd.isna(without_best_avg) else pd.NA,
            "avg_excess_excluding_best_buy_20d": (
                float(without_best_avg) if not pd.isna(without_best_avg) else pd.NA
            ),
            "stop_hit_rate_20d": _boolean_rate(buys_all, "stop_loss_hit_20d"),
            "target_1_hit_rate_20d": _boolean_rate(buys_all, "target_1_hit_20d"),
            "target_2_hit_rate_20d": _boolean_rate(buys_all, "target_2_hit_20d"),
            "window_summary": windows,
        }
    )
    fail_reasons = _gate_fail_reasons(result)
    result["fail_reasons"] = ", ".join(fail_reasons)
    result["status"] = RESEARCH_QUALIFIED_NOT_LIVE if not fail_reasons else RESEARCH_ONLY_NOT_TRADABLE
    result["risk_adjusted_score"] = score_candidate(result)
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
    max_candidates: int = 100,
    min_candidates_before_early_stop: int = 50,
    no_improvement_limit: int = 10,
    data_start: str | None = None,
    research_start: str | None = None,
    research_end: str | None = None,
    warmup_limitation: str = "",
) -> tuple[pd.DataFrame, dict]:
    window_smoke_results = build_window_smoke_results(data, benchmark_ticker, horizons, windows)
    rows: list[dict] = []
    best_score: float | None = None
    no_improvement_count = 0
    early_stop_reason = ""
    candidates = generate_candidate_rules(max(max_candidates, min_candidates_before_early_stop))

    for candidate in candidates[:max_candidates]:
        evaluated = evaluate_candidate(candidate, window_smoke_results)
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
            early_stop_reason = f"{no_improvement_limit}_consecutive_candidates_failed_to_improve_best_score"
            break

    results = pd.DataFrame(rows)
    passed = int(results["status"].eq(RESEARCH_QUALIFIED_NOT_LIVE).sum()) if not results.empty else 0
    if not early_stop_reason and passed < 3:
        early_stop_reason = "fewer_than_3_candidates_passed_minimum_threshold"
    summary = {
        "total_candidates_available": int(len(candidates)),
        "total_candidates_tested": int(len(results)),
        "total_candidates_evaluated": int(len(results)),
        "candidates_passed_gate": passed,
        "candidates_failed_gate": int(len(results) - passed),
        "early_stop_reason": early_stop_reason,
        "data_start": data_start or "",
        "research_start": research_start or "",
        "research_end": research_end or "",
        "warmup_limitation": warmup_limitation,
    }
    return results, summary


def write_auto_research_summary(results: pd.DataFrame, summary: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    qualified = results.loc[results["status"].eq(RESEARCH_QUALIFIED_NOT_LIVE)].copy()
    best = None
    if not qualified.empty:
        best = qualified.sort_values("score", ascending=False).iloc[0]

    top_by_excess = results.sort_values("overall_20d_avg_excess", ascending=False, na_position="last").head(10).copy()
    top_by_risk_score = results.sort_values("risk_adjusted_score", ascending=False, na_position="last").head(10).copy()
    display_cols = [
        "candidate_id",
        "status",
        "risk_adjusted_score",
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
        "avg_excess_excluding_best_buy_20d",
        "stop_hit_rate_20d",
        "target_1_hit_rate_20d",
        "target_2_hit_rate_20d",
        "fail_reasons",
    ]
    percent_columns = [
        "overall_buy_rate",
        "overall_20d_avg_excess",
        "overall_20d_win_rate",
        "worst_20d_return",
        "avg_excess_excluding_best_buy_20d",
        "stop_hit_rate_20d",
        "target_1_hit_rate_20d",
        "target_2_hit_rate_20d",
    ]
    top_by_excess = _format_display_frame(top_by_excess, percent_columns)
    top_by_risk_score = _format_display_frame(top_by_risk_score, percent_columns)
    buy_rate_summary = _buy_rate_distribution(results)
    common_fail_reasons = _common_fail_reasons(results)
    only_worst_gate = _top_candidates_only_failed_worst_gate(results)

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
        f"- Data start: {summary.get('data_start') or 'not reported'}",
        f"- Research start: {summary.get('research_start') or 'not reported'}",
        f"- Research end: {summary.get('research_end') or 'not reported'}",
        f"- Warmup limitation: {summary.get('warmup_limitation') or 'None reported'}",
        f"- Total candidates available: {summary.get('total_candidates_available', len(results))}",
        f"- Total candidates evaluated: {summary.get('total_candidates_evaluated', summary['total_candidates_tested'])}",
        f"- Candidates passed gate: {summary['candidates_passed_gate']}",
        f"- Candidates failed gate: {summary['candidates_failed_gate']}",
        f"- Early stop reason: {summary['early_stop_reason'] or 'None'}",
        f"- BUY rate distribution: {buy_rate_summary}",
        f"- Top candidates failed only because of -60% worst-trade gate: {'yes' if only_worst_gate else 'no'}",
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
                f"- Risk-adjusted score: {best['risk_adjusted_score']:.4f}",
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
                f"- Stop hit rate diagnostic: {_format_percent(best['stop_hit_rate_20d'])}",
                f"- Target 1 hit rate diagnostic: {_format_percent(best['target_1_hit_rate_20d'])}",
                f"- Target 2 hit rate diagnostic: {_format_percent(best['target_2_hit_rate_20d'])}",
                "",
                "## Best Candidate Cross-Window Summary",
                "",
                pd.read_json(best["window_summary_json"]).to_markdown(index=False),
                "",
            ]
        )
    lines.extend(
        [
            "## Top 10 By 20d Avg Excess",
            "",
            top_by_excess[display_cols].to_markdown(index=False),
            "",
            "## Top 10 By Risk-Adjusted Score",
            "",
            top_by_risk_score[display_cols].to_markdown(index=False),
            "",
            "## Common Fail Reasons",
            "",
            pd.DataFrame(common_fail_reasons, columns=["fail_reason", "count"]).to_markdown(index=False)
            if common_fail_reasons
            else "No fail reasons recorded.",
            "",
            "## Warning",
            "",
            "No version is live-tradable yet.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_display_frame(frame: pd.DataFrame, percent_columns: list[str]) -> pd.DataFrame:
    display = frame.copy()
    for column in percent_columns:
        if column in display.columns:
            display[column] = display[column].map(_format_percent)
    return display


def _buy_rate_distribution(results: pd.DataFrame) -> str:
    if results.empty or "overall_buy_rate" not in results.columns:
        return "no candidates"
    rates = results["overall_buy_rate"].dropna().astype(float)
    if rates.empty:
        return "no BUY-rate data"
    return (
        f"min {_format_percent(rates.min())}, "
        f"median {_format_percent(rates.median())}, "
        f"max {_format_percent(rates.max())}"
    )


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


def _top_candidates_only_failed_worst_gate(results: pd.DataFrame) -> bool:
    if results.empty or "fail_reasons" not in results.columns:
        return False
    top = results.sort_values("overall_20d_avg_excess", ascending=False, na_position="last").head(10)
    return bool(top["fail_reasons"].fillna("").eq("worst_20d_return_lte_minus_60pct").any())


def _format_percent(value: object) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        return ""
    return f"{float(value):.2%}"
