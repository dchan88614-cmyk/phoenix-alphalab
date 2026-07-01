from __future__ import annotations

import numpy as np
import pandas as pd


DEFAULT_FACTORS = [
    "relative_volume_eod",
    "relative_volume_prev20",
    "volume_change_20d",
    "return_5d",
    "return_10d",
    "return_20d",
    "distance_to_52w_high_eod",
    "distance_to_52w_high_prev",
    "atr_pct",
    "gap_pct",
    "dollar_volume",
]


def _max_drawdown(return_series: pd.Series) -> float:
    clean = return_series.dropna()
    if clean.empty:
        return np.nan
    equity = (1.0 + clean).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min())


def _assign_quantiles(series: pd.Series, quantiles: int) -> pd.Series:
    clean_count = int(series.notna().sum())
    if clean_count < 2:
        return pd.Series(index=series.index, data=np.nan)

    effective_quantiles = min(quantiles, clean_count)
    ranked = series.rank(method="first")
    try:
        return pd.qcut(ranked, q=effective_quantiles, labels=False, duplicates="drop") + 1
    except ValueError:
        return pd.Series(index=series.index, data=np.nan)


def build_factor_report(
    data: pd.DataFrame,
    factors: list[str],
    horizons: list[int],
    benchmark_ticker: str,
    quantiles: int,
) -> pd.DataFrame:
    """Group each factor into quantiles and summarize forward returns."""
    rows: list[dict] = []
    benchmark = (
        data.loc[data["ticker"].eq(benchmark_ticker), ["date", *[f"fwd_return_{h}d" for h in horizons]]]
        .drop_duplicates("date")
        .rename(columns={f"fwd_return_{h}d": f"benchmark_fwd_return_{h}d" for h in horizons})
    )
    research_data = data.loc[~data["ticker"].eq(benchmark_ticker)].copy()
    research_data = research_data.merge(benchmark, on="date", how="left")

    for factor in factors:
        if factor not in research_data.columns:
            continue

        factor_frame = research_data[["date", "ticker", factor, *[f"fwd_return_{h}d" for h in horizons], *[f"benchmark_fwd_return_{h}d" for h in horizons]]].dropna(subset=[factor])
        if factor_frame.empty:
            continue

        factor_frame["factor_quantile"] = factor_frame.groupby("date")[factor].transform(
            lambda series: _assign_quantiles(series, quantiles)
        )
        factor_frame = factor_frame.dropna(subset=["factor_quantile"])

        for horizon in horizons:
            fwd_col = f"fwd_return_{horizon}d"
            bench_col = f"benchmark_fwd_return_{horizon}d"
            valid = factor_frame.dropna(subset=[fwd_col])
            if valid.empty:
                continue

            for quantile, group in valid.groupby("factor_quantile"):
                returns = group[fwd_col]
                excess = group[fwd_col] - group[bench_col]
                rows.append(
                    {
                        "factor": factor,
                        "quantile": int(quantile),
                        "horizon_days": horizon,
                        "observations": int(returns.count()),
                        "avg_forward_return": float(returns.mean()),
                        "median_forward_return": float(returns.median()),
                        "win_rate": float((returns > 0).mean()),
                        "max_drawdown": _max_drawdown(returns.sort_index()),
                        "avg_excess_return": float(excess.mean()) if excess.notna().any() else np.nan,
                    }
                )

    return pd.DataFrame(rows).sort_values(["factor", "horizon_days", "quantile"])
