from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


BUY = "BUY"
NO_TRADE = "NO_TRADE"
DECISION_REASON_BUY = "Top ranked EOD candidate with positive 5d/20d momentum and elevated relative volume."
DECISION_REASON_NO_TRADE = "Top ranked EOD candidate failed one or more baseline BUY filters."


@dataclass(frozen=True)
class DecisionRecord:
    date: str
    action: str
    ticker: str
    entry_price: float
    entry_low: float
    entry_high: float
    stop_loss: float
    target_1: float
    target_2: float
    expected_holding_days: int
    confidence: int
    reason: str
    smoke_score: float
    rank: int


def _is_present(value: object) -> bool:
    return not pd.isna(value)


def _confidence(smoke_score: float) -> int:
    return int(min(95, max(50, round(float(smoke_score) * 100))))


def _build_price_levels(row: pd.Series) -> dict[str, float]:
    close = float(row["close"])
    atr = row.get("atr")
    if _is_present(atr):
        stop_loss = close - 1.5 * float(atr)
    else:
        stop_loss = close * 0.92
    risk = close - stop_loss
    return {
        "entry_price": close,
        "entry_low": close * 0.995,
        "entry_high": close * 1.005,
        "stop_loss": stop_loss,
        "target_1": close + 2 * risk,
        "target_2": close + 4 * risk,
    }


def _passes_buy_rule(row: pd.Series) -> bool:
    return (
        float(row["smoke_score"]) >= 0.70
        and _is_present(row["relative_volume_prev20"])
        and float(row["return_5d"]) > 0
        and float(row["return_20d"]) > 0
        and float(row["distance_to_52w_high_prev"]) >= -0.25
        and float(row["dollar_volume"]) >= 20_000_000
    )


def build_decision_record(row: pd.Series) -> DecisionRecord:
    """Convert one rank-1 smoke candidate into a BUY or NO_TRADE record."""
    price_levels = _build_price_levels(row)
    is_buy = _passes_buy_rule(row)
    return DecisionRecord(
        date=str(row["date"]),
        action=BUY if is_buy else NO_TRADE,
        ticker=str(row["ticker"]),
        expected_holding_days=20,
        confidence=_confidence(float(row["smoke_score"])),
        reason=DECISION_REASON_BUY if is_buy else DECISION_REASON_NO_TRADE,
        smoke_score=float(row["smoke_score"]),
        rank=int(row["rank"]),
        **price_levels,
    )


def build_decision_simulation(smoke_results: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    """Build one decision per signal date from rank-1 smoke candidates.

    Forward returns remain labels for reporting only. They are copied after
    BUY/NO_TRADE is decided and are not read by build_decision_record().
    """
    required = [
        "date",
        "ticker",
        "rank",
        "close",
        "smoke_score",
        "relative_volume_prev20",
        "return_5d",
        "return_20d",
        "distance_to_52w_high_prev",
        "dollar_volume",
    ]
    missing = [column for column in required if column not in smoke_results.columns]
    if missing:
        raise ValueError(f"Decision simulation missing required columns: {', '.join(missing)}")

    if smoke_results.empty:
        return pd.DataFrame()

    rank_one = (
        smoke_results.loc[smoke_results["rank"].eq(1)]
        .sort_values(["date", "ticker"])
        .drop_duplicates("date")
        .copy()
    )
    records: list[dict] = []
    label_columns = [
        *[f"fwd_return_{horizon}d" for horizon in horizons],
        *[f"excess_return_{horizon}d" for horizon in horizons],
    ]
    for _, row in rank_one.iterrows():
        record = asdict(build_decision_record(row))
        for column in label_columns:
            if column in row:
                record[column] = row[column]
        records.append(record)

    return pd.DataFrame(records)


def _format_percent(value: float) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        return ""
    return f"{value:.2%}"


def _decision_metrics(frame: pd.DataFrame, horizons: list[int]) -> dict[int, dict]:
    metrics: dict[int, dict] = {}
    for horizon in horizons:
        fwd_col = f"fwd_return_{horizon}d"
        excess_col = f"excess_return_{horizon}d"
        metrics[horizon] = {
            "rows": int(len(frame)),
            "avg_forward_return": float(frame[fwd_col].mean()) if not frame.empty else pd.NA,
            "avg_excess_return": float(frame[excess_col].mean()) if not frame.empty else pd.NA,
            "win_rate": float((frame[fwd_col] > 0).mean()) if not frame.empty else pd.NA,
        }
    return metrics


def summarize_decision_simulation(decisions: pd.DataFrame, smoke_results: pd.DataFrame, horizons: list[int]) -> dict:
    total_days = int(decisions["date"].nunique()) if not decisions.empty else 0
    buys = decisions.loc[decisions["action"].eq(BUY)].copy() if not decisions.empty else pd.DataFrame()
    rank_one = smoke_results.loc[smoke_results["rank"].eq(1)].copy()
    buy_days = int(len(buys))
    no_trade_days = int(total_days - buy_days)

    primary_horizon = 20 if 20 in horizons else max(horizons)
    primary_col = f"fwd_return_{primary_horizon}d"
    best_buy = None
    worst_buy = None
    if not buys.empty:
        best = buys.loc[buys[primary_col].idxmax()]
        worst = buys.loc[buys[primary_col].idxmin()]
        best_buy = {
            "date": best["date"],
            "ticker": best["ticker"],
            "return": float(best[primary_col]),
            "horizon": primary_horizon,
        }
        worst_buy = {
            "date": worst["date"],
            "ticker": worst["ticker"],
            "return": float(worst[primary_col]),
            "horizon": primary_horizon,
        }

    buy_metrics = _decision_metrics(buys, horizons)
    rank_one_metrics = _decision_metrics(rank_one, horizons)
    buy_primary = buy_metrics[primary_horizon]["avg_excess_return"]
    rank_one_primary = rank_one_metrics[primary_horizon]["avg_excess_return"]
    if pd.isna(buy_primary) or pd.isna(rank_one_primary):
        comparison = "Insufficient BUY data to compare against always buying smoke rank 1."
    elif buy_primary > rank_one_primary:
        comparison = "BUY filtering improved performance versus always buying smoke rank 1."
    elif buy_primary < rank_one_primary:
        comparison = "BUY filtering hurt performance versus always buying smoke rank 1."
    else:
        comparison = "BUY filtering matched always buying smoke rank 1."

    return {
        "total_signal_days": total_days,
        "buy_days": buy_days,
        "no_trade_days": no_trade_days,
        "buy_rate": float(buy_days / total_days) if total_days else pd.NA,
        "buy_metrics": buy_metrics,
        "rank_one_metrics": rank_one_metrics,
        "best_buy": best_buy,
        "worst_buy": worst_buy,
        "comparison": comparison,
    }


def write_decision_simulation_markdown(
    decisions: pd.DataFrame,
    summary: dict,
    output_path: str | Path,
    horizons: list[int],
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    metric_rows = []
    for horizon in horizons:
        buy = summary["buy_metrics"].get(horizon, {})
        rank_one = summary["rank_one_metrics"].get(horizon, {})
        metric_rows.append(
            {
                "horizon_days": horizon,
                "buy_avg_forward_return": _format_percent(buy.get("avg_forward_return", pd.NA)),
                "buy_avg_excess_return": _format_percent(buy.get("avg_excess_return", pd.NA)),
                "buy_win_rate": _format_percent(buy.get("win_rate", pd.NA)),
                "rank1_avg_forward_return": _format_percent(rank_one.get("avg_forward_return", pd.NA)),
                "rank1_avg_excess_return": _format_percent(rank_one.get("avg_excess_return", pd.NA)),
                "rank1_win_rate": _format_percent(rank_one.get("win_rate", pd.NA)),
            }
        )

    best_buy = summary.get("best_buy")
    worst_buy = summary.get("worst_buy")
    lines = [
        "# Phoenix AlphaLab Decision Simulation",
        "",
        "## Research Mode",
        "",
        "- Factor timing: EOD",
        "- Entry proxy: same-day close",
        "- Decision rule: Generation 1 baseline BUY / NO_TRADE rule",
        "- New alpha factors: none",
        "",
        "## Summary",
        "",
        f"- Total signal days: {summary['total_signal_days']}",
        f"- BUY days: {summary['buy_days']}",
        f"- NO_TRADE days: {summary['no_trade_days']}",
        f"- BUY rate: {_format_percent(summary['buy_rate'])}",
        f"- Best BUY: {_trade_label(best_buy)}",
        f"- Worst BUY: {_trade_label(worst_buy)}",
        f"- Comparison: {summary['comparison']}",
        "",
        "## BUY vs Always Buy Smoke Rank 1",
        "",
        pd.DataFrame(metric_rows).to_markdown(index=False),
        "",
        "## Decisions",
        "",
    ]
    if decisions.empty:
        lines.append("No decision rows were produced.")
    else:
        display_columns = [
            "date",
            "action",
            "ticker",
            "entry_price",
            "entry_low",
            "entry_high",
            "stop_loss",
            "target_1",
            "target_2",
            "confidence",
            "reason",
        ]
        lines.append(decisions[display_columns].to_markdown(index=False))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _trade_label(trade: dict | None) -> str:
    if not trade:
        return "None"
    return f"{trade['date']} {trade['ticker']} {_format_percent(trade['return'])} ({trade['horizon']}d)"
