from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.backtest.smoke_test import build_smoke_test, summarize_smoke_test


DEFAULT_MULTI_WINDOW_SMOKE_WINDOWS = [
    ("2024-01-02", "2024-03-29"),
    ("2024-04-01", "2024-06-28"),
    ("2024-07-01", "2024-09-30"),
    ("2024-10-01", "2024-12-31"),
    ("2025-01-02", "2025-03-31"),
    ("2025-04-01", "2025-06-30"),
    ("2025-07-01", "2025-09-30"),
    ("2025-10-01", "2025-12-31"),
    ("2026-01-02", "2026-03-31"),
    ("2026-04-01", "2026-06-30"),
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


def validate_non_overlapping_windows(windows: list[tuple[str, str]]) -> None:
    parsed = sorted((pd.Timestamp(start), pd.Timestamp(end)) for start, end in windows)
    for index, (start, end) in enumerate(parsed):
        if start > end:
            raise ValueError(f"Window start is after end: {start.date()} to {end.date()}")
        if index and start <= parsed[index - 1][1]:
            previous_start, previous_end = parsed[index - 1]
            raise ValueError(
                "Multi-window smoke test windows overlap: "
                f"{previous_start.date()} to {previous_end.date()} and {start.date()} to {end.date()}"
            )


def _trade_label(trade: dict | None) -> str:
    if not trade:
        return ""
    return f"{trade['date']} {trade['ticker']} {_format_percent(trade['return'])}"


def _top_selected_label(summary: dict, limit: int = 5) -> str:
    rows = summary.get("top_10_most_selected", [])[:limit]
    return ", ".join(f"{row['ticker']}:{row['selected_count']}" for row in rows)


def build_multi_window_smoke_test(
    data: pd.DataFrame,
    benchmark_ticker: str,
    horizons: list[int],
    universe_ticker_count: int,
    windows: list[tuple[str, str]] | None = None,
    top_n: int = 5,
) -> pd.DataFrame:
    """Run the same smoke ranking rule across non-overlapping date windows."""
    smoke_windows = windows or DEFAULT_MULTI_WINDOW_SMOKE_WINDOWS
    validate_non_overlapping_windows(smoke_windows)

    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    rows: list[dict] = []

    for start, end in smoke_windows:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
        window_data = frame.loc[frame["date"].between(start_ts, end_ts)].copy()
        window_result = build_smoke_test(
            window_data,
            benchmark_ticker=benchmark_ticker,
            horizons=horizons,
            smoke_days=100_000,
            top_n=top_n,
        )
        summary = summarize_smoke_test(window_result, horizons)
        status = "ok" if summary["signal_days"] > 0 else "insufficient_data"
        row: dict = {
            "window_start": start,
            "window_end": end,
            "status": status,
            "universe_ticker_count": int(universe_ticker_count),
            "selected_unique_ticker_count": int(summary["selected_unique_ticker_count"]),
            "signal_days": int(summary["signal_days"]),
            "best_trade": _trade_label(summary.get("best_trade")),
            "worst_trade": _trade_label(summary.get("worst_trade")),
            "top_5_most_selected": _top_selected_label(summary, limit=5),
        }
        for horizon in horizons:
            horizon_summary = summary["horizons"].get(horizon, {})
            row[f"avg_return_{horizon}d"] = horizon_summary.get("avg_return", pd.NA)
            row[f"avg_excess_return_{horizon}d"] = horizon_summary.get("avg_excess_return", pd.NA)
            row[f"win_rate_{horizon}d"] = horizon_summary.get("win_rate", pd.NA)
            if horizon == 20:
                row["days_outperformed_spy_20d"] = horizon_summary.get("days_outperformed_spy", 0)
                row["eligible_days_20d"] = horizon_summary.get("eligible_days", 0)
        rows.append(row)

    return pd.DataFrame(rows)


def write_multi_window_smoke_markdown(
    summary: pd.DataFrame,
    output_path: str | Path,
    benchmark_ticker: str,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    ok = summary.loc[summary["status"].eq("ok")].copy()
    positive_20 = int(ok["avg_excess_return_20d"].gt(0).sum()) if not ok.empty else 0
    beat_half = (
        ok["days_outperformed_spy_20d"].astype(float) / ok["eligible_days_20d"].replace(0, pd.NA).astype(float)
    )
    beat_half_count = int(beat_half.gt(0.5).sum()) if not ok.empty else 0
    best_window = ok.loc[ok["avg_excess_return_20d"].idxmax()] if not ok.empty else None
    worst_window = ok.loc[ok["avg_excess_return_20d"].idxmin()] if not ok.empty else None

    if not ok.empty and positive_20 > len(ok) / 2 and beat_half_count > len(ok) / 2:
        judgment = "Yes, the simple rule shows initial cross-window strength, but it still needs stricter universe and data validation."
    else:
        judgment = "Not enough. The simple rule has not shown broad cross-window strength."

    display = summary.copy()
    for column in display.columns:
        if column.startswith("avg_") or column.startswith("win_rate_"):
            display[column] = display[column].map(_format_percent)

    lines = [
        "# Phoenix AlphaLab Multi-Window Smoke Test",
        "",
        "## Research Mode",
        "",
        "- Factor timing: EOD",
        "- Ranking rule: same Sprint 3 smoke ranking rule, unchanged across windows.",
        "- Benchmark: " + benchmark_ticker,
        "- New alpha factors: none",
        "",
        "## Cross-Window Summary",
        "",
        f"- Windows tested: {len(summary)}",
        f"- Windows with sufficient data: {len(ok)}",
        f"- Windows with 20d avg excess > 0: {positive_20}",
        f"- Windows with 20d days_outperformed_spy above 50%: {beat_half_count}",
        f"- Best window by 20d avg excess: {_window_label(best_window)}",
        f"- Worst window by 20d avg excess: {_window_label(worst_window)}",
        f"- Cross-window judgment: {judgment}",
        "",
        "## Window Results",
        "",
        display.to_markdown(index=False),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _window_label(row: pd.Series | None) -> str:
    if row is None:
        return "None"
    return (
        f"{row['window_start']} to {row['window_end']} "
        f"({_format_percent(row['avg_excess_return_20d'])} 20d avg excess)"
    )
