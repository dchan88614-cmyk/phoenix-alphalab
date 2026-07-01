from __future__ import annotations

from pathlib import Path

import pandas as pd


def _format_percent(value: float) -> str:
    if pd.isna(value):
        return ""
    return f"{value:.2%}"


def write_markdown_report(
    report: pd.DataFrame,
    output_path: str | Path,
    tickers: list[str],
    start: str,
    end: str,
    benchmark: str,
    data_source: str,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Phoenix AlphaLab Factor Report",
        "",
        f"- Tickers: {', '.join(tickers)}",
        f"- Date range: {start} to {end}",
        f"- Benchmark: {benchmark}",
        "- Note: forward returns are validation labels and are not used in factor calculation.",
        "",
        "## Research Mode",
        "",
        f"- Data source: {data_source}",
        f"- Benchmark: {benchmark}",
        "- Factor timing: EOD",
        "- Look-ahead limitations: factors may use values known after the factor date close; forward returns are labels only.",
        "- Point-in-time metadata warning: yfinance metadata and market cap are not point-in-time in this MVP.",
        "",
    ]

    if report.empty:
        lines.extend(
            [
                "No factor report rows were produced.",
                "",
                "Common causes: missing price data, too few dates for rolling windows, or filters removed all rows.",
            ]
        )
    else:
        display = report.copy()
        for column in [
            "avg_forward_return",
            "median_forward_return",
            "win_rate",
            "max_drawdown",
            "avg_excess_return",
        ]:
            display[column] = display[column].map(_format_percent)
        lines.append(display.to_markdown(index=False))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
