from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.trading.trade_simulator import STOP, TARGET_1, TARGET_2, TIME_EXIT


VARIANT_BASE = "base"
VARIANT_EX_MSTR = "excluding_mstr"
VARIANT_EX_MOST_SELECTED = "excluding_most_selected_ticker"
VARIANT_EX_TOP3_SELECTED = "excluding_top3_selected_tickers"
VARIANT_CAP10_FULL = "per_ticker_cap_10_full_period"
VARIANT_CAP5_YEAR = "per_ticker_cap_5_per_year"
VARIANT_EQUAL_TICKER = "equal_ticker_weighted"


def build_concentration_report(trades: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if trades.empty:
        return pd.DataFrame(), {}
    frame = _prepare_trades(trades)
    candidate_totals = frame.groupby("candidate_id").size().to_dict()
    grouped = frame.groupby(["candidate_id", "ticker"], dropna=False)
    rows = []
    for (candidate_id, ticker), group in grouped:
        rows.append(
            {
                "candidate_id": candidate_id,
                "ticker": ticker,
                "trade_count": int(len(group)),
                "trade_share": float(len(group) / candidate_totals.get(candidate_id, len(group))),
                **_trade_metrics(group),
                "total_contribution_to_realized_return": float(group["realized_return"].sum()),
                "total_contribution_to_realized_excess_return": float(group["realized_excess_return"].sum()),
            }
        )
    report = pd.DataFrame(rows)
    summary = concentration_summary(frame)
    return report.sort_values(["candidate_id", "trade_count"], ascending=[True, False]), summary


def concentration_summary(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {}
    frame = _prepare_trades(trades)
    counts = frame["ticker"].value_counts()
    excess_by_ticker = frame.groupby("ticker")["realized_excess_return"].sum().sort_values(ascending=False)
    total_excess_abs = abs(float(excess_by_ticker.sum()))
    return {
        "top_10_by_trade_count": counts.head(10).to_dict(),
        "top_10_positive_contributors": excess_by_ticker.head(10).to_dict(),
        "top_10_negative_contributors": excess_by_ticker.sort_values().head(10).to_dict(),
        "worst_10_trade_tickers": frame.sort_values("realized_return").head(10)["ticker"].value_counts().to_dict(),
        "best_10_trade_tickers": frame.sort_values("realized_return", ascending=False).head(10)["ticker"].value_counts().to_dict(),
        "top1_trade_share": float(counts.iloc[0] / len(frame)) if not counts.empty else pd.NA,
        "top3_trade_share": float(counts.head(3).sum() / len(frame)) if not counts.empty else pd.NA,
        "top1_excess_share": _contribution_share(excess_by_ticker.head(1).sum(), total_excess_abs),
        "top3_excess_share": _contribution_share(excess_by_ticker.head(3).sum(), total_excess_abs),
        "most_selected_ticker": counts.index[0] if not counts.empty else "",
    }


def build_robustness_report(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows = []
    for candidate_id, group in _prepare_trades(trades).groupby("candidate_id"):
        variants = robustness_variants(group)
        for variant_name, variant_trades in variants.items():
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "variant": variant_name,
                    **variant_metrics(variant_trades, equal_ticker_weighted=variant_name == VARIANT_EQUAL_TICKER),
                }
            )
    return pd.DataFrame(rows)


def robustness_variants(trades: pd.DataFrame) -> dict[str, pd.DataFrame]:
    frame = _prepare_trades(trades)
    most_selected = frame["ticker"].value_counts().index[0] if not frame.empty else ""
    top3 = frame["ticker"].value_counts().head(3).index.tolist()
    return {
        VARIANT_BASE: frame,
        VARIANT_EX_MSTR: frame.loc[~frame["ticker"].eq("MSTR")].copy(),
        VARIANT_EX_MOST_SELECTED: frame.loc[~frame["ticker"].eq(most_selected)].copy(),
        VARIANT_EX_TOP3_SELECTED: frame.loc[~frame["ticker"].isin(top3)].copy(),
        VARIANT_CAP10_FULL: apply_per_ticker_cap(frame, max_trades=10),
        VARIANT_CAP5_YEAR: apply_per_ticker_cap(frame, max_trades=5, per_year=True),
        VARIANT_EQUAL_TICKER: frame,
    }


def variant_metrics(trades: pd.DataFrame, equal_ticker_weighted: bool = False) -> dict:
    if trades.empty:
        return {
            "remaining_trade_count": 0,
            "avg_realized_return": pd.NA,
            "avg_realized_excess_return": pd.NA,
            "realized_win_rate": pd.NA,
            "median_realized_return": pd.NA,
            "worst_realized_return": pd.NA,
            "best_realized_return": pd.NA,
            "stop_hit_rate": pd.NA,
            "target_1_hit_rate": pd.NA,
            "target_2_hit_rate": pd.NA,
            "time_exit_rate": pd.NA,
            "avg_holding_days": pd.NA,
            "avg_realized_excess_excluding_best_trade": pd.NA,
            "valid_windows": 0,
            "windows_positive_realized_excess": 0,
            "windows_win_rate_ge_52pct": 0,
        }
    frame = _prepare_trades(trades)
    if equal_ticker_weighted:
        metrics = _equal_ticker_metrics(frame)
    else:
        metrics = _trade_metrics(frame)
    best = frame.loc[frame["realized_return"].idxmax()]
    without_best = frame.drop(index=best.name)
    windowed = _window_metrics(frame)
    return {
        "remaining_trade_count": int(len(frame)),
        **metrics,
        "avg_realized_excess_excluding_best_trade": (
            float(without_best["realized_excess_return"].mean()) if not without_best.empty else pd.NA
        ),
        **windowed,
    }


def apply_per_ticker_cap(trades: pd.DataFrame, max_trades: int, per_year: bool = False) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    frame = _prepare_trades(trades)
    frame["signal_year"] = pd.to_datetime(frame["signal_date"]).dt.year
    group_cols = ["ticker", "signal_year"] if per_year else ["ticker"]
    capped = (
        frame.sort_values(["decision_strength", "signal_date", "ticker"], ascending=[False, True, True])
        .groupby(group_cols, group_keys=False)
        .head(max_trades)
        .sort_values(["signal_date", "ticker"])
        .copy()
    )
    return capped.drop(columns=["signal_year"], errors="ignore")


def excluding_mstr(trades: pd.DataFrame) -> pd.DataFrame:
    return _prepare_trades(trades).loc[lambda frame: ~frame["ticker"].eq("MSTR")].copy()


def excluding_most_selected_ticker(trades: pd.DataFrame) -> pd.DataFrame:
    frame = _prepare_trades(trades)
    if frame.empty:
        return frame
    most_selected = frame["ticker"].value_counts().index[0]
    return frame.loc[~frame["ticker"].eq(most_selected)].copy()


def equal_ticker_weighted_metrics(trades: pd.DataFrame) -> dict:
    return _equal_ticker_metrics(_prepare_trades(trades))


def robustness_gate_fail_reasons(result: dict) -> list[str]:
    reasons = []
    if not _gt(result.get("excluding_mstr_avg_realized_excess_return"), 0):
        reasons.append("excluding_mstr_excess_not_positive")
    if not _gt(result.get("excluding_most_selected_avg_realized_excess_return"), 0):
        reasons.append("excluding_most_selected_excess_not_positive")
    if pd.isna(result.get("top1_ticker_trade_share")) or float(result["top1_ticker_trade_share"]) > 0.25:
        reasons.append("top1_ticker_trade_share_above_25pct")
    if pd.isna(result.get("top3_ticker_trade_share")) or float(result["top3_ticker_trade_share"]) > 0.50:
        reasons.append("top3_ticker_trade_share_above_50pct")
    if not _gt(result.get("equal_ticker_weighted_avg_realized_excess_return"), 0):
        reasons.append("equal_ticker_weighted_excess_not_positive")
    return reasons


def build_regime_diagnostics(trades: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    regimes = _build_regime_table(data)
    frame = _prepare_trades(trades)
    frame["signal_date"] = pd.to_datetime(frame["signal_date"])
    merged = frame.merge(regimes, left_on="signal_date", right_on="date", how="left")
    regime_cols = [col for col in ["spy_above_50dma", "spy_above_200dma", "qqq_above_50dma", "qqq_above_200dma"] if col in merged]
    rows = []
    for col in regime_cols:
        for value, group in merged.groupby(col, dropna=False):
            rows.append({"regime": col, "bucket": str(value), **_regime_metrics(group)})
    return pd.DataFrame(rows)


def write_concentration_markdown(report: pd.DataFrame, summary: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    top_count = report.sort_values("trade_count", ascending=False).head(10) if not report.empty else pd.DataFrame()
    positive = report.sort_values("total_contribution_to_realized_excess_return", ascending=False).head(10) if not report.empty else pd.DataFrame()
    negative = report.sort_values("total_contribution_to_realized_excess_return").head(10) if not report.empty else pd.DataFrame()
    lines = [
        "# Phoenix AlphaLab Concentration Report",
        "",
        "Offline historical research only. Not live-tradable.",
        "",
        f"- Top 1 ticker trade share: {_format_percent(summary.get('top1_trade_share'))}",
        f"- Top 3 ticker trade share: {_format_percent(summary.get('top3_trade_share'))}",
        f"- Top 1 realized excess contribution share: {_format_percent(summary.get('top1_excess_share'))}",
        f"- Top 3 realized excess contribution share: {_format_percent(summary.get('top3_excess_share'))}",
        f"- Most selected ticker: {summary.get('most_selected_ticker', '')}",
        "",
        "## Top 10 By Trade Count",
        "",
        top_count.to_markdown(index=False) if not top_count.empty else "No trades.",
        "",
        "## Top 10 Positive Contributors",
        "",
        positive.to_markdown(index=False) if not positive.empty else "No trades.",
        "",
        "## Top 10 Negative Contributors",
        "",
        negative.to_markdown(index=False) if not negative.empty else "No trades.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_regime_markdown(report: pd.DataFrame, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phoenix AlphaLab Regime Diagnostics",
        "",
        "Regime tags use only signal-date or prior OHLCV data. No regime gate is applied in this run.",
        "",
        report.to_markdown(index=False) if not report.empty else "No regime diagnostics available.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _prepare_trades(trades: pd.DataFrame) -> pd.DataFrame:
    frame = trades.copy()
    if "decision_strength" not in frame.columns:
        frame["decision_strength"] = 0.0
    frame["decision_strength"] = frame["decision_strength"].fillna(0.0)
    return frame


def _trade_metrics(frame: pd.DataFrame) -> dict:
    exit_rates = frame["exit_reason"].value_counts(normalize=True)
    return {
        "avg_realized_return": float(frame["realized_return"].mean()),
        "avg_realized_excess_return": float(frame["realized_excess_return"].mean()),
        "median_realized_return": float(frame["realized_return"].median()),
        "realized_win_rate": float((frame["realized_return"] > 0).mean()),
        "worst_realized_return": float(frame["realized_return"].min()),
        "best_realized_return": float(frame["realized_return"].max()),
        "stop_hit_rate": float(exit_rates.get(STOP, 0.0)),
        "target_1_hit_rate": float(exit_rates.get(TARGET_1, 0.0)),
        "target_2_hit_rate": float(exit_rates.get(TARGET_2, 0.0)),
        "time_exit_rate": float(exit_rates.get(TIME_EXIT, 0.0)),
        "avg_holding_days": float(frame["holding_days"].mean()),
    }


def _equal_ticker_metrics(frame: pd.DataFrame) -> dict:
    per_ticker = frame.groupby("ticker").agg(
        avg_realized_return=("realized_return", "mean"),
        avg_realized_excess_return=("realized_excess_return", "mean"),
        median_realized_return=("realized_return", "median"),
        realized_win_rate=("realized_return", lambda series: float((series > 0).mean())),
        worst_realized_return=("realized_return", "min"),
        best_realized_return=("realized_return", "max"),
        avg_holding_days=("holding_days", "mean"),
    )
    return {
        "avg_realized_return": float(per_ticker["avg_realized_return"].mean()),
        "avg_realized_excess_return": float(per_ticker["avg_realized_excess_return"].mean()),
        "median_realized_return": float(per_ticker["median_realized_return"].mean()),
        "realized_win_rate": float(per_ticker["realized_win_rate"].mean()),
        "worst_realized_return": float(per_ticker["worst_realized_return"].min()),
        "best_realized_return": float(per_ticker["best_realized_return"].max()),
        "stop_hit_rate": float(frame.groupby("ticker")["exit_reason"].apply(lambda s: (s == STOP).mean()).mean()),
        "target_1_hit_rate": float(frame.groupby("ticker")["exit_reason"].apply(lambda s: (s == TARGET_1).mean()).mean()),
        "target_2_hit_rate": float(frame.groupby("ticker")["exit_reason"].apply(lambda s: (s == TARGET_2).mean()).mean()),
        "time_exit_rate": float(frame.groupby("ticker")["exit_reason"].apply(lambda s: (s == TIME_EXIT).mean()).mean()),
        "avg_holding_days": float(per_ticker["avg_holding_days"].mean()),
    }


def _window_metrics(frame: pd.DataFrame) -> dict:
    grouped = frame.groupby(["window_start", "window_end"])
    rows = grouped.agg(
        avg_realized_excess_return=("realized_excess_return", "mean"),
        realized_win_rate=("realized_return", lambda series: float((series > 0).mean())),
    )
    return {
        "valid_windows": int(len(rows)),
        "windows_positive_realized_excess": int(rows["avg_realized_excess_return"].gt(0).sum()),
        "windows_win_rate_ge_52pct": int(rows["realized_win_rate"].ge(0.52).sum()),
    }


def _build_regime_table(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    rows = []
    for ticker, prefix in [("SPY", "spy"), ("QQQ", "qqq")]:
        subset = frame.loc[frame["ticker"].eq(ticker), ["date", "close"]].dropna().sort_values("date").copy()
        if subset.empty:
            continue
        subset[f"{prefix}_above_50dma"] = subset["close"] > subset["close"].rolling(50, min_periods=50).mean()
        subset[f"{prefix}_above_200dma"] = subset["close"] > subset["close"].rolling(200, min_periods=200).mean()
        rows.append(subset.drop(columns=["close"]))
    if not rows:
        return pd.DataFrame(columns=["date"])
    regime = rows[0]
    for item in rows[1:]:
        regime = regime.merge(item, on="date", how="outer")
    return regime.sort_values("date")


def _regime_metrics(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {}
    exit_rates = frame["exit_reason"].value_counts(normalize=True)
    return {
        "trade_count": int(len(frame)),
        "avg_realized_excess_return": float(frame["realized_excess_return"].mean()),
        "realized_win_rate": float((frame["realized_return"] > 0).mean()),
        "stop_hit_rate": float(exit_rates.get(STOP, 0.0)),
        "target_1_hit_rate": float(exit_rates.get(TARGET_1, 0.0)),
        "target_2_hit_rate": float(exit_rates.get(TARGET_2, 0.0)),
        "time_exit_rate": float(exit_rates.get(TIME_EXIT, 0.0)),
    }


def _contribution_share(value: float, denominator: float) -> object:
    if denominator == 0:
        return pd.NA
    return float(value / denominator)


def _gt(value: object, threshold: float) -> bool:
    return not pd.isna(value) and float(value) > threshold


def _format_percent(value: object) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        return ""
    return f"{float(value):.2%}"
