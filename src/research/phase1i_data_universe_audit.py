from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED
from src.research.auto_loop import CandidateRule
from src.research.historical_replay import FORWARD_WINDOWS, build_phase1_historical_replay, sample_replay_dates
from src.research.phase1c_robustness import max_drawdown, simulate_phase1c_policy_trades, ticker_profit_loss_shares
from src.research.phase1f_failure_audit import ticker_theme_subtheme
from src.research.phase1g_redesign_sandbox import BASELINE_POLICY, MARKET_SYMBOLS, add_redesign_features, positive_rate
from src.research.phase1h_risk_overlay import (
    TREND_BASELINE,
    build_trend_quality_decisions,
    deterministic_phase1h_split,
    ending_excluding_best_trade,
    theme_concentration_shares,
)


PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH = "PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH"
PHASE_1I_UNIVERSE_BLOCKER_REBUILD_WATCHLIST = "PHASE_1I_UNIVERSE_BLOCKER_REBUILD_WATCHLIST"
PHASE_1I_STRATEGY_BLOCKER_REDESIGN_REQUIRED = "PHASE_1I_STRATEGY_BLOCKER_REDESIGN_REQUIRED"
PHASE_1I_MIXED_BLOCKERS_NEED_REMEDIATION = "PHASE_1I_MIXED_BLOCKERS_NEED_REMEDIATION"
PHASE_1I_CLEAN_UNIVERSE_PROMISING_FOR_GPT_REVIEW = "PHASE_1I_CLEAN_UNIVERSE_PROMISING_FOR_GPT_REVIEW"
PHASE_1I_INSUFFICIENT_SAMPLE_WARNING = "PHASE_1I_INSUFFICIENT_SAMPLE_WARNING"

PHASE1I_VARIANTS = [
    "current_watchlist_full",
    "data_quality_pass_only",
    "metadata_and_price_clean",
    "liquidity_and_price_clean",
    "theme_balanced_clean",
    "conservative_research_universe",
]


def build_phase1i_data_universe_audit(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    watchlist_tickers: list[str],
    universe: pd.DataFrame,
    rejected_metadata: pd.DataFrame,
    requested_start_date: str,
    requested_end_date: str,
    replay_rounds: int = 100,
    replay_sample_count: int = 30,
    replay_sample_offset: int = 0,
    benchmark_ticker: str = "SPY",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, dict]:
    frame = add_redesign_features(data)
    symbols = sorted(set(watchlist_tickers + [benchmark_ticker, "QQQ"]))
    quality = build_symbol_data_quality_audit(frame, symbols, universe, rejected_metadata, requested_start_date, requested_end_date)
    vendor = build_vendor_validation_matrix(frame, symbols)
    incidents = build_data_gap_incident_log(quality, vendor)
    composition = build_universe_composition_audit(quality, frame, watchlist_tickers)
    variants = build_universe_variants(quality, frame, watchlist_tickers)
    matrix = evaluate_universe_variants(frame, account_settings, rule, variants, quality, replay_rounds, replay_sample_count, replay_sample_offset, benchmark_ticker)
    holdout = build_universe_variant_holdout_results(matrix, replay_sample_count)
    attribution = build_strategy_vs_universe_attribution(matrix, variants, quality)
    status = phase1i_status(quality, vendor, incidents, holdout, replay_sample_count)
    summary = {
        "phase_1i_status": status,
        "sample_count": replay_sample_count,
        "quality_counts": quality["data_quality_grade"].value_counts().to_dict() if not quality.empty else {},
        "vendor_status_counts": vendor["validation_status"].value_counts().to_dict() if not vendor.empty else {},
        "incident_count": int(len(incidents)),
        "variant_count": len(variants),
        "best_holdout_variant": best_holdout_variant(holdout),
    }
    summary_md = phase1i_summary_markdown(summary, quality, vendor, incidents, composition, holdout, attribution)
    return quality, vendor, composition, matrix, holdout, incidents, rejected_symbol_audit(quality), attribution, summary_md, summary


def build_symbol_data_quality_audit(
    data: pd.DataFrame,
    symbols: list[str],
    universe: pd.DataFrame,
    rejected_metadata: pd.DataFrame,
    requested_start_date: str,
    requested_end_date: str,
) -> pd.DataFrame:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    meta = universe.set_index("ticker").to_dict("index") if universe is not None and not universe.empty else {}
    rejected = dict(zip(rejected_metadata["ticker"], rejected_metadata["reason"])) if rejected_metadata is not None and not rejected_metadata.empty else {}
    requested_start = pd.Timestamp(requested_start_date)
    requested_end = pd.Timestamp(requested_end_date)
    rows = []
    for ticker in symbols:
        group = frame.loc[frame["ticker"].eq(ticker)].sort_values("date").copy()
        metadata = meta.get(ticker, {})
        rejection_reason = rejected.get(ticker, "")
        has_prices = not group.empty
        ohlcv_missing = int(group[["open", "high", "low", "close", "volume"]].isna().sum().sum()) if has_prices else 0
        total_cells = int(len(group) * 5) if has_prices else 0
        volume = pd.to_numeric(group.get("volume", pd.Series(dtype=float)), errors="coerce") if has_prices else pd.Series(dtype=float)
        close = pd.to_numeric(group.get("close", pd.Series(dtype=float)), errors="coerce") if has_prices else pd.Series(dtype=float)
        dates = pd.to_datetime(group["date"]) if has_prices else pd.Series(dtype="datetime64[ns]")
        duplicate_dates = int(dates.duplicated().sum()) if has_prices else 0
        non_monotonic = bool(not dates.is_monotonic_increasing) if has_prices else False
        gaps = close.pct_change(fill_method=None).abs() if has_prices else pd.Series(dtype=float)
        avg20 = float((close * volume).tail(20).mean()) if has_prices and len(group) >= 1 else pd.NA
        avg60 = float((close * volume).tail(60).mean()) if has_prices and len(group) >= 1 else pd.NA
        metadata_rejected = bool(rejection_reason)
        download_error = not has_prices and not metadata_rejected
        first_date = group["date"].min() if has_prices else pd.NaT
        has_full_lookback = bool(has_prices and first_date <= requested_start + pd.Timedelta(days=7))
        materially_short_lookback = bool(has_prices and first_date > requested_start + pd.Timedelta(days=90))
        has_full_forward = bool(has_prices and group["date"].max() >= requested_end - pd.Timedelta(days=35))
        stale = bool(has_prices and group["date"].max() < requested_end - pd.Timedelta(days=10))
        severe_missing = bool(total_cells and (ohlcv_missing / total_cells) > 0.02)
        split_anomaly = bool(gaps.gt(0.45).any()) if has_prices else False
        abnormal_volume = bool(volume.gt(volume.median() * 20).any()) if has_prices and volume.notna().any() and volume.median() > 0 else False
        zero_count = int(volume.fillna(0).eq(0).sum()) if has_prices else 0
        fail_reasons = []
        warn_reasons = []
        if not has_prices:
            fail_reasons.append("no_ohlcv_downloaded")
        if metadata_rejected and ticker not in {"SPY", "QQQ"}:
            fail_reasons.append(f"metadata_rejected:{rejection_reason}")
        if materially_short_lookback:
            fail_reasons.append("insufficient_factor_lookback")
        elif not has_full_lookback:
            warn_reasons.append("starts_after_requested_start_or_market_holiday")
        if not has_full_forward:
            warn_reasons.append("incomplete_forward_window_near_end")
        if severe_missing:
            fail_reasons.append("severe_missing_ohlcv")
        if stale:
            fail_reasons.append("stale_data")
        if duplicate_dates or non_monotonic:
            fail_reasons.append("date_index_integrity_issue")
        if split_anomaly:
            warn_reasons.append("large_split_or_adjustment_jump")
        if abnormal_volume:
            warn_reasons.append("abnormal_volume_spike")
        if zero_count > max(3, len(group) * 0.02):
            fail_reasons.append("severe_zero_volume")
        if not fail_reasons and not warn_reasons:
            warn_reasons.append("single_retail_vendor_yfinance")
        grade = "FAIL" if fail_reasons else ("WARN" if warn_reasons else "PASS")
        rows.append(
            {
                "ticker": ticker,
                "asset_type": metadata.get("quote_type", "INDEX" if ticker in {"SPY", "QQQ"} else ""),
                "first_available_date": group["date"].min().strftime("%Y-%m-%d") if has_prices else "",
                "last_available_date": group["date"].max().strftime("%Y-%m-%d") if has_prices else "",
                "requested_start_date": requested_start.strftime("%Y-%m-%d"),
                "requested_end_date": requested_end.strftime("%Y-%m-%d"),
                "has_full_lookback_coverage": has_full_lookback,
                "has_full_forward_coverage": has_full_forward,
                "missing_ohlcv_count": ohlcv_missing,
                "missing_ohlcv_pct": float(ohlcv_missing / total_cells) if total_cells else 1.0,
                "zero_volume_count": zero_count,
                "zero_volume_pct": float(zero_count / len(group)) if has_prices and len(group) else 1.0,
                "abnormal_volume_flag": abnormal_volume,
                "stale_data_flag": stale,
                "duplicate_date_count": duplicate_dates,
                "non_monotonic_date_flag": non_monotonic,
                "split_or_adjustment_anomaly_flag": split_anomaly,
                "extreme_gap_count": int(gaps.gt(0.25).sum()) if has_prices else 0,
                "extreme_gap_examples": ",".join(group.loc[gaps.gt(0.25), "date"].dt.strftime("%Y-%m-%d").head(5)) if has_prices else "",
                "metadata_available_flag": bool(metadata),
                "metadata_rejected_flag": metadata_rejected,
                "metadata_rejection_reason": rejection_reason,
                "download_error_flag": download_error,
                "download_error_message": "no_price_data_after_download_or_not_attempted" if not has_prices else "",
                "yfinance_404_flag": bool(ticker == "BITF" and (metadata_rejected or not has_prices)),
                "latest_close": float(close.dropna().iloc[-1]) if has_prices and close.notna().any() else pd.NA,
                "latest_price_under_50_flag": bool(has_prices and close.notna().any() and close.dropna().iloc[-1] < 50),
                "avg_dollar_volume_20d": avg20,
                "avg_dollar_volume_60d": avg60,
                "data_quality_grade": grade,
                "data_quality_reason": ";".join(fail_reasons or warn_reasons),
            }
        )
    return pd.DataFrame(rows)


def build_vendor_validation_matrix(data: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    rows = []
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    for ticker in symbols:
        group = frame.loc[frame["ticker"].eq(ticker)]
        rows.append(
            {
                "ticker": ticker,
                "primary_vendor": "yfinance",
                "secondary_vendor": "",
                "comparison_start_date": group["date"].min().strftime("%Y-%m-%d") if not group.empty else "",
                "comparison_end_date": group["date"].max().strftime("%Y-%m-%d") if not group.empty else "",
                "overlapping_trading_days": 0,
                "close_price_median_abs_diff_pct": pd.NA,
                "close_price_max_abs_diff_pct": pd.NA,
                "volume_median_abs_diff_pct": pd.NA,
                "volume_max_abs_diff_pct": pd.NA,
                "adjusted_price_mismatch_flag": pd.NA,
                "corporate_action_mismatch_flag": pd.NA,
                "validation_status": "NO_SECOND_SOURCE",
                "validation_reason": "No stable secondary OHLCV source is configured without secrets.",
            }
        )
    return pd.DataFrame(rows)


def build_data_gap_incident_log(quality: pd.DataFrame, vendor: pd.DataFrame) -> pd.DataFrame:
    rows = []
    incident_id = 1
    for _, row in quality.iterrows():
        incidents = []
        if bool(row["yfinance_404_flag"]):
            incidents.append(("YFINANCE_404", "HIGH", "Symbol could not be validated or downloaded from yfinance."))
        if bool(row["download_error_flag"]):
            incidents.append(("DOWNLOAD_FAILURE", "HIGH", "No OHLCV data available for replay research."))
        if bool(row["metadata_rejected_flag"]):
            incidents.append(("METADATA_REJECTED", "MEDIUM", str(row["metadata_rejection_reason"])))
        if bool(row["stale_data_flag"]):
            incidents.append(("STALE_DATA", "HIGH", "Latest date is stale relative to requested end."))
        if bool(row["split_or_adjustment_anomaly_flag"]):
            incidents.append(("SPLIT_OR_ADJUSTMENT_ANOMALY", "MEDIUM", "Large single-day adjusted close move."))
        if bool(row["abnormal_volume_flag"]):
            incidents.append(("ABNORMAL_VOLUME", "LOW", "Volume spike above 20x median."))
        for incident_type, severity, effect in incidents:
            rows.append(
                {
                    "incident_id": f"PHASE1I-{incident_id:04d}",
                    "ticker": row["ticker"],
                    "incident_type": incident_type,
                    "first_seen_run_phase": "Phase 1I",
                    "affected_replay_dates": "",
                    "affected_samples": "",
                    "severity": severity,
                    "likely_effect_on_results": effect,
                    "recommended_action": "Validate with a secondary vendor or exclude from research until resolved.",
                }
            )
            incident_id += 1
    return pd.DataFrame(rows)


def build_universe_composition_audit(quality: pd.DataFrame, data: pd.DataFrame, watchlist_tickers: list[str]) -> pd.DataFrame:
    q = quality.loc[quality["ticker"].isin(watchlist_tickers)].copy()
    themes = q["ticker"].apply(lambda ticker: ticker_theme_subtheme(str(ticker))[0])
    theme_counts = themes.value_counts()
    high_risk_themes = {"crypto-adjacent / high beta", "biotech", "EV / mobility", "space / defense / nuclear"}
    frame = data.loc[data["ticker"].isin(watchlist_tickers)].copy()
    latest = frame.sort_values("date").groupby("ticker").tail(1)
    atr = pd.to_numeric(latest.get("atr_pct", pd.Series(dtype=float)), errors="coerce")
    vol = pd.to_numeric(latest.get("volatility_20d", pd.Series(dtype=float)), errors="coerce")
    return pd.DataFrame(
        [
            {
                "total_tickers": int(len(q)),
                "data_quality_pass_count": int(q["data_quality_grade"].eq("PASS").sum()),
                "data_quality_warn_count": int(q["data_quality_grade"].eq("WARN").sum()),
                "data_quality_fail_count": int(q["data_quality_grade"].eq("FAIL").sum()),
                "price_under_50_count": int(q["latest_price_under_50_flag"].sum()),
                "price_under_20_count": int(pd.to_numeric(q["latest_close"], errors="coerce").lt(20).sum()),
                "avg_dollar_volume_pass_count": int(pd.to_numeric(q["avg_dollar_volume_20d"], errors="coerce").gt(1_000_000).sum()),
                "theme_count": int(theme_counts.size),
                "tickers_per_theme": ";".join(f"{theme}:{count}" for theme, count in theme_counts.items()),
                "top_theme_ticker_share": float(theme_counts.max() / len(q)) if len(q) else pd.NA,
                "high_beta_or_speculative_theme_share": float(themes.isin(high_risk_themes).mean()) if len(q) else pd.NA,
                "crypto_adjacent_count": int(themes.eq("crypto-adjacent / high beta").sum()),
                "biotech_count": int(themes.eq("biotech").sum()),
                "EV_mobility_count": int(themes.eq("EV / mobility").sum()),
                "AI_software_count": int(themes.eq("AI / software").sum()),
                "semiconductor_hardware_count": int(themes.eq("semiconductor / hardware").sum()),
                "single_name_theme_count": int((theme_counts == 1).sum()),
                "median_atr_pct": median(atr),
                "median_volatility_20d": median(vol),
                "90th_percentile_atr_pct": quantile(atr, 0.9),
                "90th_percentile_volatility_20d": quantile(vol, 0.9),
                "universe_quality_assessment": universe_quality_assessment(q, themes),
            }
        ]
    )


def build_universe_variants(quality: pd.DataFrame, data: pd.DataFrame, watchlist_tickers: list[str]) -> dict[str, list[str]]:
    q = quality.loc[quality["ticker"].isin(watchlist_tickers)].copy()
    data_tickers = set(data["ticker"].unique())
    current = [ticker for ticker in watchlist_tickers if ticker in data_tickers]
    pass_warn = q.loc[q["data_quality_grade"].isin(["PASS", "WARN"]) & q["ticker"].isin(data_tickers), "ticker"].tolist()
    metadata_price = q.loc[(~q["metadata_rejected_flag"]) & q["ticker"].isin(data_tickers) & pd.to_numeric(q["latest_close"], errors="coerce").le(50), "ticker"].tolist()
    liquidity_price = q.loc[
        q["ticker"].isin(data_tickers)
        & pd.to_numeric(q["avg_dollar_volume_20d"], errors="coerce").ge(1_000_000)
        & pd.to_numeric(q["latest_close"], errors="coerce").le(50),
        "ticker",
    ].tolist()
    balanced = theme_balanced_selection(q.loc[q["ticker"].isin(pass_warn)].copy())
    conservative = sorted(set(pass_warn) & set(metadata_price) & set(liquidity_price) & set(balanced))
    return {
        "current_watchlist_full": sorted(current),
        "data_quality_pass_only": sorted(pass_warn),
        "metadata_and_price_clean": sorted(metadata_price),
        "liquidity_and_price_clean": sorted(liquidity_price),
        "theme_balanced_clean": sorted(balanced),
        "conservative_research_universe": conservative,
    }


def theme_balanced_selection(q: pd.DataFrame, max_per_theme: int = 12) -> list[str]:
    rows = []
    q = q.copy()
    q["theme"] = q["ticker"].apply(lambda ticker: ticker_theme_subtheme(str(ticker))[0])
    q["quality_rank"] = q["data_quality_grade"].map({"PASS": 0, "WARN": 1, "FAIL": 2}).fillna(2)
    q["liquidity_rank"] = pd.to_numeric(q["avg_dollar_volume_20d"], errors="coerce").fillna(0)
    for _, group in q.groupby("theme"):
        selected = group.sort_values(["quality_rank", "liquidity_rank", "ticker"], ascending=[True, False, True]).head(max_per_theme)
        rows.extend(selected["ticker"].tolist())
    return sorted(rows)


def evaluate_universe_variants(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    variants: dict[str, list[str]],
    quality: pd.DataFrame,
    replay_rounds: int,
    replay_sample_count: int,
    replay_sample_offset: int,
    benchmark_ticker: str,
) -> pd.DataFrame:
    rows = []
    split = deterministic_phase1h_split(replay_sample_count, replay_sample_offset)
    for variant, tickers in variants.items():
        variant_data = data.loc[data["ticker"].isin(set(tickers) | {benchmark_ticker, "QQQ"})].copy()
        exclusions = variant_exclusion_counts(quality, tickers, variant)
        for sample_index in range(replay_sample_count):
            sample_id = replay_sample_offset + sample_index
            split_value = split_name_for_sample(sample_id, split)
            candidate34, _, _ = build_phase1_historical_replay(variant_data, account_settings, rule, replay_rounds, benchmark_ticker, sample_id)
            rows.append(evaluate_strategy_row(variant, "candidate34_frozen_baseline", sample_id, split_value, replay_rounds, len(tickers), exclusions, candidate34, variant_data, account_settings))
            replay_dates = sample_replay_dates(variant_data, replay_rounds, benchmark_ticker=benchmark_ticker, replay_sample_offset=sample_id)
            trend_decisions = build_trend_quality_decisions(variant_data, account_settings, rule, replay_dates, {})
            rows.append(evaluate_strategy_row(variant, TREND_BASELINE, sample_id, split_value, replay_rounds, len(tickers), exclusions, trend_decisions, variant_data, account_settings))
    return pd.DataFrame(rows)


def evaluate_strategy_row(variant: str, strategy: str, sample_id: int, split_name: str, replay_rounds: int, universe_size: int, exclusions: dict, decisions: pd.DataFrame, data: pd.DataFrame, account_settings: AccountSettings) -> dict:
    trades = simulate_phase1c_policy_trades(decisions, data, account_settings, BASELINE_POLICY)
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    buys = decisions.loc[decisions["decision"].eq("HISTORICAL_BUY_CANDIDATE")].copy() if not decisions.empty else pd.DataFrame()
    wins = executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    losses = executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    top_profit_share, top_loss_share = ticker_profit_loss_shares(executed)
    theme_profit_share, theme_loss_share = theme_concentration_shares(executed)
    row = {
        "universe_variant": variant,
        "strategy_name": strategy,
        "sample_id": sample_id,
        "split_name": split_name,
        "replay_rounds": replay_rounds,
        "universe_size": universe_size,
        **exclusions,
        "buy_count": int(len(buys)),
        "no_trade_count": int(replay_rounds - len(buys)),
        "buy_rate": float(len(buys) / replay_rounds) if replay_rounds else 0.0,
        "simulated_win_rate": positive_rate(executed["pnl_dollars"]) if not executed.empty else pd.NA,
        **{f"accuracy_{window}d": positive_rate(buys.get(f"forward_return_{window}d", pd.Series(dtype=float))) for window in FORWARD_WINDOWS},
        **{f"average_forward_return_{window}d": mean(buys.get(f"forward_return_{window}d", pd.Series(dtype=float))) for window in FORWARD_WINDOWS},
        **{f"median_forward_return_{window}d": median(buys.get(f"forward_return_{window}d", pd.Series(dtype=float))) for window in FORWARD_WINDOWS},
        "average_win_dollars": mean(executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"]) if not executed.empty else pd.NA,
        "average_loss_dollars": mean(executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"]) if not executed.empty else pd.NA,
        "profit_factor": float(wins / abs(losses)) if losses < 0 else (float("inf") if wins > 0 else 0.0),
        "ending_account_value": float(executed["cash_after_exit"].iloc[-1]) if not executed.empty else account_settings.starting_capital,
        "max_drawdown": max_drawdown(executed, account_settings.starting_capital),
        "worst_trade_loss_percent": float(executed["account_return_pct"].min()) if not executed.empty else pd.NA,
        "stopped_out_but_20d_positive_rate": stopped_positive_rate(executed),
        "top_profit_ticker_contribution_share": top_profit_share,
        "top_loss_ticker_contribution_share": top_loss_share,
        "top_profit_theme_contribution_share": theme_profit_share,
        "top_loss_theme_contribution_share": theme_loss_share,
        "median_ending_value_excluding_best_trade": ending_excluding_best_trade(executed, account_settings.starting_capital),
    }
    row["executed_winner_count"] = int(executed["pnl_dollars"].gt(0).sum()) if not executed.empty else 0
    row["executed_loser_count"] = int(executed["pnl_dollars"].lt(0).sum()) if not executed.empty else 0
    row["winner_dollars"] = float(executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"].sum()) if not executed.empty else 0.0
    row["loser_dollars"] = float(abs(executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"].sum())) if not executed.empty else 0.0
    return row


def build_universe_variant_holdout_results(matrix: pd.DataFrame, replay_sample_count: int) -> pd.DataFrame:
    holdout = matrix.loc[matrix["split_name"].eq("holdout")].copy()
    rows = []
    full_sample = replay_sample_count >= 30
    for (variant, strategy), group in holdout.groupby(["universe_variant", "strategy_name"]):
        failed = holdout_failed_gates(group, full_sample)
        rows.append(
            {
                "universe_variant": variant,
                "strategy_name": strategy,
                "sample_count": int(group["sample_id"].nunique()),
                "median_universe_size": median(group["universe_size"]),
                "minimum_buy_count": int(group["buy_count"].min()),
                "median_buy_count": median(group["buy_count"]),
                "worst_holdout_ending_value": min_or_na(group["ending_account_value"]),
                "median_holdout_ending_value": median(group["ending_account_value"]),
                "worst_holdout_max_drawdown": min_or_na(group["max_drawdown"]),
                "median_holdout_win_rate": median(group["simulated_win_rate"]),
                "median_holdout_20d_accuracy": median(group["accuracy_20d"]),
                "median_holdout_profit_factor": median(group["profit_factor"]),
                "worst_trade_loss_percent": min_or_na(group["worst_trade_loss_percent"]),
                "max_top_ticker_loss_share": max_or_na(group["top_loss_ticker_contribution_share"]),
                "max_top_theme_loss_share": max_or_na(group["top_loss_theme_contribution_share"]),
                "median_ending_value_excluding_best_trade": median(group["median_ending_value_excluding_best_trade"]),
                "holdout_gate_pass": not failed,
                "failed_gates": ";".join(failed),
            }
        )
    return pd.DataFrame(rows)


def build_strategy_vs_universe_attribution(matrix: pd.DataFrame, variants: dict[str, list[str]], quality: pd.DataFrame) -> pd.DataFrame:
    holdout = matrix.loc[matrix["split_name"].eq("holdout")].copy()
    baseline = holdout.loc[holdout["universe_variant"].eq("current_watchlist_full")].groupby("strategy_name").median(numeric_only=True)
    rows = []
    current = set(variants["current_watchlist_full"])
    for (variant, strategy), group in holdout.groupby(["universe_variant", "strategy_name"]):
        if variant == "current_watchlist_full" or strategy not in baseline.index:
            continue
        base = baseline.loc[strategy]
        med = group.median(numeric_only=True)
        removed = sorted(current - set(variants.get(variant, [])))
        removed_q = quality.loc[quality["ticker"].isin(removed)]
        loser_removed = max(0.0, float(base.get("loser_dollars", 0.0) - med.get("loser_dollars", 0.0)))
        winner_removed = max(0.0, float(base.get("winner_dollars", 0.0) - med.get("winner_dollars", 0.0)))
        diagnosis = attribution_diagnosis(med, base, removed_q, loser_removed, winner_removed)
        rows.append(
            {
                "universe_variant": variant,
                "strategy_name": strategy,
                "change_in_universe_size": int(len(variants.get(variant, [])) - len(current)),
                "change_in_buy_count": float(med.get("buy_count", 0) - base.get("buy_count", 0)),
                "change_in_ending_account_value": float(med.get("ending_account_value", 0) - base.get("ending_account_value", 0)),
                "change_in_worst_drawdown": float(med.get("max_drawdown", 0) - base.get("max_drawdown", 0)),
                "change_in_win_rate": float(med.get("simulated_win_rate", 0) - base.get("simulated_win_rate", 0)),
                "change_in_20d_accuracy": float(med.get("accuracy_20d", 0) - base.get("accuracy_20d", 0)),
                "change_in_profit_factor": safe_delta(med.get("profit_factor", 0), base.get("profit_factor", 0)),
                "change_in_top_theme_loss_share": float(med.get("top_loss_theme_contribution_share", 0) - base.get("top_loss_theme_contribution_share", 0)),
                "bad_data_removed_count": int(removed_q["data_quality_grade"].eq("FAIL").sum()),
                "high_risk_theme_removed_count": int(removed_q["ticker"].apply(lambda ticker: ticker_theme_subtheme(str(ticker))[0]).isin({"crypto-adjacent / high beta", "biotech", "EV / mobility"}).sum()),
                "winners_removed_count": pd.NA,
                "losers_removed_count": pd.NA,
                "winner_dollars_removed": winner_removed,
                "loser_dollars_removed": loser_removed,
                "net_counterfactual_effect": loser_removed - winner_removed,
                "diagnosis": diagnosis,
            }
        )
    return pd.DataFrame(rows)


def phase1i_status(quality: pd.DataFrame, vendor: pd.DataFrame, incidents: pd.DataFrame, holdout: pd.DataFrame, replay_sample_count: int) -> str:
    if replay_sample_count < 30:
        return PHASE_1I_INSUFFICIENT_SAMPLE_WARNING
    fail_rate = float(quality["data_quality_grade"].eq("FAIL").mean()) if not quality.empty else 1.0
    high_incidents = int(incidents["severity"].isin(["HIGH", "BLOCKER"]).sum()) if not incidents.empty else 0
    vendor_single_source = bool(vendor["validation_status"].eq("NO_SECOND_SOURCE").mean() > 0.8) if not vendor.empty else True
    if fail_rate > 0.10 or high_incidents >= 3:
        if clean_universe_materially_improves(holdout):
            return PHASE_1I_MIXED_BLOCKERS_NEED_REMEDIATION
        return PHASE_1I_DATA_BLOCKER_PAUSE_RESEARCH
    if clean_universe_promising(holdout):
        return PHASE_1I_CLEAN_UNIVERSE_PROMISING_FOR_GPT_REVIEW
    if clean_universe_materially_improves(holdout):
        return PHASE_1I_UNIVERSE_BLOCKER_REBUILD_WATCHLIST
    if vendor_single_source:
        return PHASE_1I_MIXED_BLOCKERS_NEED_REMEDIATION
    return PHASE_1I_STRATEGY_BLOCKER_REDESIGN_REQUIRED


def phase1i_summary_markdown(summary: dict, quality: pd.DataFrame, vendor: pd.DataFrame, incidents: pd.DataFrame, composition: pd.DataFrame, holdout: pd.DataFrame, attribution: pd.DataFrame) -> str:
    lines = [
        "PHOENIX NANO PHASE 1I — DATA QUALITY, VENDOR VALIDATION, AND UNIVERSE DESIGN AUDIT",
        "",
        "Research-only. No rule, universe, or data source is approved for daily scan, paper execution, or real-money execution.",
        "",
        "## Phase 1H Recap",
        "",
        "- Phase 1H ended as PHASE_1H_HOLDOUT_FAILED.",
        "- Candidate 35 trend-quality and the best overlay still failed drawdown, win-rate, concentration, and counterfactual gates.",
        "",
        "## Data Quality PASS / WARN / FAIL Counts",
        "",
        str(summary["quality_counts"]),
        "",
        "## Vendor Validation Coverage",
        "",
        str(summary["vendor_status_counts"]),
        "",
        "If most rows are NO_SECOND_SOURCE, Phoenix Nano remains dependent on a single retail-grade data source and is not execution-grade.",
        "",
        "## Data Gap Incidents",
        "",
        incidents.head(40).to_markdown(index=False) if not incidents.empty else "No incidents logged.",
        "",
        "## Universe Composition Findings",
        "",
        composition.to_markdown(index=False) if not composition.empty else "No composition rows.",
        "",
        "## Universe Variant Holdout Results",
        "",
        holdout.to_markdown(index=False) if not holdout.empty else "No holdout rows.",
        "",
        "## Candidate 34 vs Candidate 35 Across Universe Variants",
        "",
        "See phase1i_universe_variant_backtest_matrix.csv and phase1i_universe_variant_holdout_results.csv.",
        "",
        "## Strategy-vs-Universe Attribution",
        "",
        attribution.to_markdown(index=False) if not attribution.empty else "No attribution rows.",
        "",
        f"## Final Phase 1I Status: {summary['phase_1i_status']}",
        "",
        "Do not start paper execution or real-money execution.",
        "",
        "## Next Research Task Recommendation",
        "",
        "Ask GPT whether to pause Phoenix Nano until data/vendor coverage and universe construction are remediated.",
        "",
    ]
    return "\n".join(lines)


def write_phase1i_reports(quality, vendor, composition, matrix, holdout, incidents, rejected, attribution, summary_md, paths: dict[str, str | Path]) -> None:
    for path in paths.values():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    quality.to_csv(paths["quality"], index=False)
    vendor.to_csv(paths["vendor"], index=False)
    composition.to_csv(paths["composition"], index=False)
    matrix.to_csv(paths["matrix"], index=False)
    holdout.to_csv(paths["holdout"], index=False)
    incidents.to_csv(paths["incidents"], index=False)
    rejected.to_csv(paths["rejected"], index=False)
    attribution.to_csv(paths["attribution"], index=False)
    Path(paths["summary"]).write_text(summary_md, encoding="utf-8")


def rejected_symbol_audit(quality: pd.DataFrame) -> pd.DataFrame:
    return quality.loc[quality["metadata_rejected_flag"] | quality["download_error_flag"] | quality["data_quality_grade"].eq("FAIL")].copy()


def holdout_failed_gates(group: pd.DataFrame, full_sample: bool) -> list[str]:
    failed = []
    if not full_sample:
        failed.append("full_30_sample_run_not_completed")
    if group["buy_count"].min() < 30:
        failed.append("min_buy_count_lt_30")
    worst_ending = min_or_na(group["ending_account_value"])
    median_ending = median(group["ending_account_value"])
    worst_drawdown = min_or_na(group["max_drawdown"])
    median_win_rate = median(group["simulated_win_rate"])
    median_accuracy_20d = median(group["accuracy_20d"])
    median_profit_factor = median(group["profit_factor"])
    worst_trade_loss = min_or_na(group["worst_trade_loss_percent"])
    median_ex_best = median(group["median_ending_value_excluding_best_trade"])
    if pd.isna(worst_ending) or worst_ending <= 110:
        failed.append("worst_ending_lte_110")
    if pd.isna(median_ending) or median_ending <= 130:
        failed.append("median_ending_lte_130")
    if pd.isna(worst_drawdown) or worst_drawdown <= -0.35:
        failed.append("worst_drawdown_lte_minus_35")
    if pd.isna(median_win_rate) or median_win_rate < 0.52:
        failed.append("median_win_rate_lt_52")
    if pd.isna(median_accuracy_20d) or median_accuracy_20d < 0.58:
        failed.append("median_20d_accuracy_lt_58")
    if pd.isna(median_profit_factor) or median_profit_factor < 1.30:
        failed.append("median_profit_factor_lt_130")
    if pd.isna(worst_trade_loss) or worst_trade_loss <= -0.15:
        failed.append("worst_trade_loss_lte_minus_15")
    ticker_share = max_or_na(group["top_loss_ticker_contribution_share"])
    theme_share = max_or_na(group["top_loss_theme_contribution_share"])
    if pd.notna(ticker_share) and ticker_share > 0.35:
        failed.append("top_ticker_loss_share_gt_35")
    if pd.notna(theme_share) and theme_share > 0.45:
        failed.append("top_theme_loss_share_gt_45")
    if pd.isna(median_ex_best) or median_ex_best <= 115:
        failed.append("median_ex_best_lte_115")
    return failed


def clean_universe_promising(holdout: pd.DataFrame) -> bool:
    if holdout.empty:
        return False
    clean = holdout.loc[
        holdout["strategy_name"].eq(TREND_BASELINE)
        & ~holdout["universe_variant"].eq("current_watchlist_full")
        & holdout["holdout_gate_pass"].eq(True)
    ]
    return not clean.empty


def clean_universe_materially_improves(holdout: pd.DataFrame) -> bool:
    if holdout.empty:
        return False
    base = holdout.loc[holdout["universe_variant"].eq("current_watchlist_full") & holdout["strategy_name"].eq(TREND_BASELINE)]
    clean = holdout.loc[~holdout["universe_variant"].eq("current_watchlist_full") & holdout["strategy_name"].eq(TREND_BASELINE)]
    if base.empty or clean.empty:
        return False
    base_row = base.iloc[0]
    return bool(
        clean["worst_holdout_max_drawdown"].max() > float(base_row["worst_holdout_max_drawdown"]) + 0.05
        or clean["median_holdout_ending_value"].max() > float(base_row["median_holdout_ending_value"]) * 1.15
    )


def variant_exclusion_counts(quality: pd.DataFrame, tickers: list[str], variant: str) -> dict:
    selected = set(tickers)
    watch = quality.loc[~quality["ticker"].isin(["SPY", "QQQ"])].copy()
    excluded = watch.loc[~watch["ticker"].isin(selected)].copy()
    return {
        "data_fail_excluded_count": int(excluded["data_quality_grade"].eq("FAIL").sum()),
        "metadata_excluded_count": int(excluded["metadata_rejected_flag"].sum()),
        "liquidity_excluded_count": int(pd.to_numeric(excluded["avg_dollar_volume_20d"], errors="coerce").lt(1_000_000).sum()),
        "theme_balance_excluded_count": int(len(excluded)) if "theme_balanced" in variant or "conservative" in variant else 0,
    }


def universe_quality_assessment(q: pd.DataFrame, themes: pd.Series) -> str:
    fail_rate = float(q["data_quality_grade"].eq("FAIL").mean()) if len(q) else 1.0
    top_theme_share = float(themes.value_counts().max() / len(q)) if len(q) else 1.0
    if fail_rate > 0.10:
        return "DATA_QUALITY_BLOCKER"
    if top_theme_share > 0.25:
        return "THEME_CONCENTRATION_WARNING"
    return "USABLE_FOR_RESEARCH_WITH_VENDOR_LIMITATIONS"


def attribution_diagnosis(med: pd.Series, base: pd.Series, removed_q: pd.DataFrame, loser_removed: float, winner_removed: float) -> str:
    if int(removed_q["data_quality_grade"].eq("FAIL").sum()) > 0 and loser_removed > winner_removed:
        return "DATA_BLOCKER"
    if float(med.get("ending_account_value", 0)) > float(base.get("ending_account_value", 0)) and loser_removed > winner_removed:
        return "UNIVERSE_BLOCKER"
    if float(med.get("ending_account_value", 0)) <= float(base.get("ending_account_value", 0)):
        return "STRATEGY_BLOCKER"
    return "MIXED"


def stopped_positive_rate(executed: pd.DataFrame) -> object:
    if executed.empty or "forward_return_20d" not in executed.columns:
        return pd.NA
    stopped = executed["exit_reason"].eq("STOP")
    return float((stopped & pd.to_numeric(executed["forward_return_20d"], errors="coerce").gt(0)).mean())


def split_name_for_sample(sample_id: int, split: dict) -> str:
    if sample_id in split["calibration"]:
        return "calibration"
    if sample_id in split["validation"]:
        return "validation"
    if sample_id in split["holdout"]:
        return "holdout"
    return "unused"


def best_holdout_variant(holdout: pd.DataFrame) -> str:
    if holdout.empty:
        return ""
    trend = holdout.loc[holdout["strategy_name"].eq(TREND_BASELINE)].copy()
    if trend.empty:
        return ""
    row = trend.sort_values(["holdout_gate_pass", "median_holdout_ending_value", "worst_holdout_max_drawdown"], ascending=[False, False, False]).iloc[0]
    return str(row["universe_variant"])


def mean(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.mean())


def median(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.median())


def quantile(series: pd.Series, value: float) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.quantile(value))


def max_or_na(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.max())


def min_or_na(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.min())


def safe_delta(left: object, right: object) -> float:
    left_num = pd.to_numeric(pd.Series([left]), errors="coerce").iloc[0]
    right_num = pd.to_numeric(pd.Series([right]), errors="coerce").iloc[0]
    if pd.isna(left_num) or pd.isna(right_num):
        return 0.0
    if left_num == float("inf") and right_num == float("inf"):
        return 0.0
    if left_num == float("inf"):
        return 999.0
    if right_num == float("inf"):
        return -999.0
    return float(left_num - right_num)
