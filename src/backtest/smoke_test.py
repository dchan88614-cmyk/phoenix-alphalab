from __future__ import annotations

from pathlib import Path

import pandas as pd


SMOKE_RANK_FACTORS = [
    "relative_volume_prev20",
    "return_5d",
    "return_20d",
    "distance_to_52w_high_prev",
    "dollar_volume",
]


def _format_percent(value: float) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        return ""
    return f"{value:.2%}"


def _score_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    scored = frame.copy()
    score_columns: list[str] = []
    for factor in SMOKE_RANK_FACTORS:
        score_column = f"{factor}_score"
        scored[score_column] = scored[factor].rank(method="first", pct=True)
        score_columns.append(score_column)
    scored["smoke_score"] = scored[score_columns].mean(axis=1)
    return scored


def _summarize_returns(results: pd.DataFrame, horizons: list[int]) -> dict[int, dict]:
    metrics: dict[int, dict] = {}
    for horizon in horizons:
        fwd_col = f"fwd_return_{horizon}d"
        excess_col = f"excess_return_{horizon}d"
        metrics[horizon] = {
            "rows": int(len(results)),
            "avg_return": float(results[fwd_col].mean()) if not results.empty else pd.NA,
            "avg_excess_return": float(results[excess_col].mean()) if not results.empty else pd.NA,
            "win_rate": float((results[fwd_col] > 0).mean()) if not results.empty else pd.NA,
        }
    return metrics


def build_smoke_test(
    data: pd.DataFrame,
    benchmark_ticker: str,
    horizons: list[int],
    smoke_days: int = 60,
    top_n: int = 5,
) -> pd.DataFrame:
    """Select simple daily Top N candidates and attach future-return labels.

    Ranking uses only previous-window and same-day EOD factors listed in
    SMOKE_RANK_FACTORS. Forward returns are attached after selection and are
    never included in the ranking score.
    """
    required = ["date", "ticker", *SMOKE_RANK_FACTORS, *[f"fwd_return_{h}d" for h in horizons]]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Smoke test missing required columns: {', '.join(missing)}")

    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])

    benchmark = (
        frame.loc[frame["ticker"].eq(benchmark_ticker), ["date", *[f"fwd_return_{h}d" for h in horizons]]]
        .drop_duplicates("date")
        .rename(columns={f"fwd_return_{h}d": f"benchmark_fwd_return_{h}d" for h in horizons})
    )
    research = frame.loc[~frame["ticker"].eq(benchmark_ticker)].copy()
    research = research.merge(benchmark, on="date", how="left")

    label_columns = [f"fwd_return_{h}d" for h in horizons] + [f"benchmark_fwd_return_{h}d" for h in horizons]
    candidate_columns = ["date", "ticker", *SMOKE_RANK_FACTORS, *label_columns]
    candidates = research[candidate_columns].dropna(subset=SMOKE_RANK_FACTORS + label_columns)
    if candidates.empty:
        return pd.DataFrame()

    eligible_dates = sorted(candidates["date"].drop_duplicates())
    selected_dates = eligible_dates[-int(smoke_days) :]
    candidates = candidates.loc[candidates["date"].isin(selected_dates)]

    rows: list[pd.DataFrame] = []
    for signal_date, group in candidates.groupby("date", sort=True):
        scored = _score_candidates(group)
        picks = scored.sort_values(["smoke_score", "ticker"], ascending=[False, True]).head(top_n).copy()
        picks["rank"] = range(1, len(picks) + 1)
        rows.append(picks)

    if not rows:
        return pd.DataFrame()

    result = pd.concat(rows, ignore_index=True)
    for horizon in horizons:
        result[f"excess_return_{horizon}d"] = (
            result[f"fwd_return_{horizon}d"] - result[f"benchmark_fwd_return_{horizon}d"]
        )

    ordered_columns = [
        "date",
        "rank",
        "ticker",
        "smoke_score",
        *SMOKE_RANK_FACTORS,
        *[f"fwd_return_{h}d" for h in horizons],
        *[f"benchmark_fwd_return_{h}d" for h in horizons],
        *[f"excess_return_{h}d" for h in horizons],
    ]
    result = result[ordered_columns].sort_values(["date", "rank"]).reset_index(drop=True)
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    return result


def summarize_smoke_test(results: pd.DataFrame, horizons: list[int]) -> dict:
    if results.empty:
        return {
            "start_date": None,
            "end_date": None,
            "signal_days": 0,
            "rows": 0,
            "horizons": {},
            "selected_unique_ticker_count": 0,
            "top_10_most_selected": [],
            "best_trade": None,
            "worst_trade": None,
            "best_trade_excluding_most_selected": None,
            "worst_trade_excluding_most_selected": None,
            "excluding_best_single_trade": {},
            "excluding_worst_single_trade": {},
            "excluding_smci": None,
            "worth_continuing": "No data; cannot judge.",
        }

    summary: dict = {
        "start_date": str(results["date"].min()),
        "end_date": str(results["date"].max()),
        "signal_days": int(results["date"].nunique()),
        "rows": int(len(results)),
        "horizons": {},
        "selected_unique_ticker_count": int(results["ticker"].nunique()),
    }
    for horizon in horizons:
        fwd_col = f"fwd_return_{horizon}d"
        bench_col = f"benchmark_fwd_return_{horizon}d"
        excess_col = f"excess_return_{horizon}d"
        daily = results.groupby("date")[[fwd_col, bench_col, excess_col]].mean()
        summary["horizons"][horizon] = {
            "avg_return": float(results[fwd_col].mean()),
            "avg_excess_return": float(results[excess_col].mean()),
            "win_rate": float((results[fwd_col] > 0).mean()),
            "days_outperformed_spy": int((daily[excess_col] > 0).sum()),
            "eligible_days": int(daily[excess_col].count()),
        }

    primary_horizon = 20 if 20 in horizons else max(horizons)
    primary_col = f"fwd_return_{primary_horizon}d"
    best = results.loc[results[primary_col].idxmax()]
    worst = results.loc[results[primary_col].idxmin()]
    top_selected = (
        results["ticker"]
        .value_counts()
        .head(10)
        .rename_axis("ticker")
        .reset_index(name="selected_count")
        .to_dict("records")
    )
    summary["top_10_most_selected"] = top_selected
    summary["best_trade"] = {
        "horizon": primary_horizon,
        "date": best["date"],
        "ticker": best["ticker"],
        "return": float(best[primary_col]),
    }
    summary["worst_trade"] = {
        "horizon": primary_horizon,
        "date": worst["date"],
        "ticker": worst["ticker"],
        "return": float(worst[primary_col]),
    }
    most_selected = top_selected[0]["ticker"] if top_selected else None
    if most_selected:
        without_most_selected = results.loc[~results["ticker"].eq(most_selected)]
        if without_most_selected.empty:
            summary["best_trade_excluding_most_selected"] = None
            summary["worst_trade_excluding_most_selected"] = None
        else:
            best_without = without_most_selected.loc[without_most_selected[primary_col].idxmax()]
            worst_without = without_most_selected.loc[without_most_selected[primary_col].idxmin()]
            summary["best_trade_excluding_most_selected"] = {
                "excluded_ticker": most_selected,
                "horizon": primary_horizon,
                "date": best_without["date"],
                "ticker": best_without["ticker"],
                "return": float(best_without[primary_col]),
            }
            summary["worst_trade_excluding_most_selected"] = {
                "excluded_ticker": most_selected,
                "horizon": primary_horizon,
                "date": worst_without["date"],
                "ticker": worst_without["ticker"],
                "return": float(worst_without[primary_col]),
            }
    summary["excluding_best_single_trade"] = _summarize_returns(results.drop(index=best.name), horizons)
    summary["excluding_worst_single_trade"] = _summarize_returns(results.drop(index=worst.name), horizons)
    if results["ticker"].eq("SMCI").any():
        summary["excluding_smci"] = _summarize_returns(results.loc[~results["ticker"].eq("SMCI")], horizons)
    else:
        summary["excluding_smci"] = None

    positive_excess_horizons = sum(
        1 for horizon in horizons if summary["horizons"][horizon]["avg_excess_return"] > 0
    )
    primary = summary["horizons"][primary_horizon]
    if positive_excess_horizons >= 2 and primary["days_outperformed_spy"] > primary["eligible_days"] / 2:
        summary["worth_continuing"] = "Yes, initial smoke test shows enough relative strength to keep researching."
    else:
        summary["worth_continuing"] = "Not yet. Do not add complexity until the simple smoke test improves."
    return summary


def write_smoke_test_markdown(
    results: pd.DataFrame,
    summary: dict,
    output_path: str | Path,
    benchmark_ticker: str,
    horizons: list[int],
    universe_ticker_count: int,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Phoenix AlphaLab Smoke Test",
        "",
        "## Research Mode",
        "",
        "- Factor timing: EOD",
        "- Ranking rule: simple average percentile score across previous-window factors.",
        "- Ranking factors: " + ", ".join(SMOKE_RANK_FACTORS),
        "- Excluded from ranking: forward returns, market cap, news, SEC data, short interest, AI scores.",
        f"- Benchmark: {benchmark_ticker}",
        f"- Universe ticker count: {universe_ticker_count}",
        f"- Selected unique ticker count: {summary['selected_unique_ticker_count']}",
        "",
    ]
    if universe_ticker_count < 30:
        lines.extend(["WARNING: Universe too small; smoke test is not representative.", ""])

    lines.extend(
        [
            "## Test Range",
            "",
            f"- Start date: {summary['start_date']}",
            f"- End date: {summary['end_date']}",
            f"- Signal days: {summary['signal_days']}",
            f"- Selected rows: {summary['rows']}",
            "",
            "## Summary",
            "",
        ]
    )

    horizon_rows = []
    for horizon in horizons:
        horizon_summary = summary["horizons"].get(horizon, {})
        horizon_rows.append(
            {
                "horizon_days": horizon,
                "avg_return": _format_percent(horizon_summary.get("avg_return", pd.NA)),
                "avg_excess_return": _format_percent(horizon_summary.get("avg_excess_return", pd.NA)),
                "win_rate": _format_percent(horizon_summary.get("win_rate", pd.NA)),
                "days_outperformed_spy": horizon_summary.get("days_outperformed_spy", 0),
                "eligible_days": horizon_summary.get("eligible_days", 0),
            }
        )
    lines.append(pd.DataFrame(horizon_rows).to_markdown(index=False))
    lines.extend(["", "## Top 10 Most Selected Tickers", ""])
    top_selected = summary.get("top_10_most_selected", [])
    if top_selected:
        lines.append(pd.DataFrame(top_selected).to_markdown(index=False))
    else:
        lines.append("No selections were produced.")

    lines.extend(["", "## Best And Worst", ""])

    best = summary.get("best_trade")
    worst = summary.get("worst_trade")
    if best:
        lines.append(
            f"- Best trade ({best['horizon']}d): {best['date']} {best['ticker']} {_format_percent(best['return'])}"
        )
    if worst:
        lines.append(
            f"- Worst trade ({worst['horizon']}d): {worst['date']} {worst['ticker']} {_format_percent(worst['return'])}"
        )
    best_without = summary.get("best_trade_excluding_most_selected")
    worst_without = summary.get("worst_trade_excluding_most_selected")
    if best_without:
        lines.append(
            f"- Best trade excluding most selected ticker ({best_without['excluded_ticker']}, {best_without['horizon']}d): "
            f"{best_without['date']} {best_without['ticker']} {_format_percent(best_without['return'])}"
        )
    if worst_without:
        lines.append(
            f"- Worst trade excluding most selected ticker ({worst_without['excluded_ticker']}, {worst_without['horizon']}d): "
            f"{worst_without['date']} {worst_without['ticker']} {_format_percent(worst_without['return'])}"
        )

    def add_variant_section(title: str, metrics: dict | None) -> None:
        lines.extend(["", f"## {title}", ""])
        if not metrics:
            lines.append("Not applicable.")
            return
        rows = []
        for horizon in horizons:
            horizon_metrics = metrics.get(horizon, {})
            rows.append(
                {
                    "horizon_days": horizon,
                    "rows": horizon_metrics.get("rows", 0),
                    "avg_return": _format_percent(horizon_metrics.get("avg_return", pd.NA)),
                    "avg_excess_return": _format_percent(horizon_metrics.get("avg_excess_return", pd.NA)),
                    "win_rate": _format_percent(horizon_metrics.get("win_rate", pd.NA)),
                }
            )
        lines.append(pd.DataFrame(rows).to_markdown(index=False))

    add_variant_section("Result Excluding Best Single Trade", summary.get("excluding_best_single_trade"))
    add_variant_section("Result Excluding Worst Single Trade", summary.get("excluding_worst_single_trade"))
    add_variant_section("Result Excluding SMCI", summary.get("excluding_smci"))

    lines.extend(["", "## Initial Judgment", "", summary["worth_continuing"], "", "## Daily Top 5", ""])
    if results.empty:
        lines.append("No smoke test rows were produced.")
    else:
        daily = (
            results.sort_values(["date", "rank"])
            .groupby("date")["ticker"]
            .apply(lambda values: ", ".join(values))
            .reset_index(name="top_5")
        )
        lines.append(daily.to_markdown(index=False))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
