from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED
from src.backtest.nano_daily_scan import _score_latest_candidates
from src.research.auto_loop import CandidateRule
from src.research.historical_replay import (
    FORWARD_WINDOWS,
    HISTORICAL_BUY_CANDIDATE,
    HISTORICAL_NO_TRADE,
    build_phase1_historical_replay,
    sample_replay_dates,
)
from src.research.phase1c_robustness import max_drawdown, simulate_phase1c_policy_trades, ticker_profit_loss_shares
from src.research.phase1f_failure_audit import build_market_regime_lookup, ticker_theme_subtheme


PHASE_1G_DATA_PREFLIGHT_BLOCKED = "PHASE_1G_DATA_PREFLIGHT_BLOCKED"
PHASE_1G_NO_REDESIGN_SURVIVED_VALIDATION = "PHASE_1G_NO_REDESIGN_SURVIVED_VALIDATION"
PHASE_1G_HOLDOUT_FAILED = "PHASE_1G_HOLDOUT_FAILED"
PHASE_1G_INSUFFICIENT_SAMPLE_WARNING = "PHASE_1G_INSUFFICIENT_SAMPLE_WARNING"
PHASE_1G_REDESIGN_PROMISING_REQUIRES_FULL_SAMPLE = "PHASE_1G_REDESIGN_PROMISING_REQUIRES_FULL_SAMPLE"
PHASE_1G_REDESIGN_PROMISING_FOR_GPT_REVIEW = "PHASE_1G_REDESIGN_PROMISING_FOR_GPT_REVIEW"

BASELINE_POLICY = {"policy": "baseline_current", "atr_multiple": 1.5, "mode": "intraday"}
MARKET_SYMBOLS = {"SPY", "QQQ"}
REQUIRED_FAMILIES = [
    "candidate34_frozen_baseline",
    "candidate35_trend_quality",
    "candidate35_pullback_continuation",
    "candidate35_breakout_confirmation",
    "candidate35_regime_gated_momentum",
    "candidate35_low_volatility_compounder",
]


def build_phase1g_redesign_sandbox(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_rounds: int = 100,
    replay_sample_count: int = 30,
    replay_sample_offset: int = 0,
    benchmark_ticker: str = "SPY",
    rejected_metadata: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, dict]:
    frame = add_redesign_features(data)
    split = deterministic_phase1g_split(replay_sample_count, replay_sample_offset)
    preflight = build_phase1g_preflight(frame, rejected_metadata, benchmark_ticker)
    definitions = candidate_family_definitions_markdown()
    families = candidate35_families()
    all_sample_metrics, rejected = evaluate_families(
        frame,
        account_settings,
        rule,
        families,
        replay_rounds,
        replay_sample_count,
        replay_sample_offset,
        benchmark_ticker,
    )
    all_sample_metrics["split_name"] = all_sample_metrics["sample_id"].apply(lambda value: split_name(int(value), split))
    calibration = all_sample_metrics.loc[all_sample_metrics["split_name"].eq("calibration")].copy()
    calibration_promoted = promote_from_split(calibration, max_count=2, include_baseline=False)
    validation_source = all_sample_metrics.loc[
        all_sample_metrics["split_name"].eq("validation")
        & all_sample_metrics["family_name"].isin(["candidate34_frozen_baseline", *calibration_promoted])
    ].copy()
    validation_promoted = promote_from_split(validation_source, max_count=1, include_baseline=False)
    holdout = all_sample_metrics.loc[
        all_sample_metrics["split_name"].eq("holdout")
        & all_sample_metrics["family_name"].isin(["candidate34_frozen_baseline", *validation_promoted])
    ].copy()
    comparison = build_comparison(all_sample_metrics, split)
    holdout_results = build_holdout_results(holdout, preflight, replay_sample_count)
    status = phase1g_status(holdout_results, preflight, replay_sample_count)
    summary = summarize_phase1g(
        preflight,
        all_sample_metrics,
        calibration,
        validation_source,
        holdout_results,
        comparison,
        rejected,
        split,
        status,
        calibration_promoted,
        validation_promoted,
        replay_sample_count,
    )
    summary_md = phase1g_summary_markdown(summary, preflight, calibration, validation_source, holdout_results, comparison, rejected)
    return preflight, definitions, calibration, validation_source, holdout_results, comparison, rejected, summary_md, summary


def add_redesign_features(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["ticker", "date"]).reset_index(drop=True)
    pieces = []
    for _, group in frame.groupby("ticker"):
        group = group.sort_values("date").copy()
        close = pd.to_numeric(group["close"], errors="coerce")
        high = pd.to_numeric(group["high"], errors="coerce")
        group["sma20"] = close.rolling(20, min_periods=20).mean()
        group["sma50"] = close.rolling(50, min_periods=50).mean()
        group["volatility_20d"] = close.pct_change(fill_method=None).rolling(20, min_periods=20).std()
        group["atr_pct"] = pd.to_numeric(group["atr"], errors="coerce") / close
        group["distance_from_20d_high_pct"] = close / high.rolling(20, min_periods=10).max() - 1.0
        pieces.append(group)
    return pd.concat(pieces, ignore_index=True).sort_values(["date", "ticker"]).reset_index(drop=True)


def deterministic_phase1g_split(replay_sample_count: int, replay_sample_offset: int = 0) -> dict:
    ids = list(range(replay_sample_offset, replay_sample_offset + replay_sample_count))
    if replay_sample_count >= 30:
        return {"calibration": ids[:10], "validation": ids[10:20], "holdout": ids[20:30], "fallback_used": False}
    if replay_sample_count >= 20:
        return {"calibration": ids[:7], "validation": ids[7:14], "holdout": ids[14:20], "fallback_used": True}
    third = max(1, replay_sample_count // 3)
    return {"calibration": ids[:third], "validation": ids[third : 2 * third], "holdout": ids[2 * third :], "fallback_used": True}


def candidate35_families() -> list[dict]:
    return [
        {"family_name": "candidate34_frozen_baseline", "kind": "candidate34"},
        {"family_name": "candidate35_trend_quality", "kind": "trend_quality"},
        {"family_name": "candidate35_pullback_continuation", "kind": "pullback_continuation"},
        {"family_name": "candidate35_breakout_confirmation", "kind": "breakout_confirmation"},
        {"family_name": "candidate35_regime_gated_momentum", "kind": "regime_gated_momentum"},
        {"family_name": "candidate35_low_volatility_compounder", "kind": "low_volatility_compounder"},
    ]


def build_phase1g_preflight(data: pd.DataFrame, rejected_metadata: pd.DataFrame | None, benchmark_ticker: str) -> pd.DataFrame:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    sessions = sorted(frame.loc[frame["ticker"].isin(["SPY", "QQQ"]), "date"].dropna().unique())
    rows = []
    rejected = {}
    if rejected_metadata is not None and not rejected_metadata.empty:
        rejected = dict(zip(rejected_metadata["ticker"], rejected_metadata["reason"]))
    for ticker, group in frame.groupby("ticker"):
        group = group.sort_values("date")
        role = "market_regime_index" if ticker == "QQQ" else ("benchmark" if ticker == benchmark_ticker else "candidate")
        expected = len([date for date in sessions if group["date"].min() <= date <= group["date"].max()]) if sessions else group["date"].nunique()
        volume = pd.to_numeric(group.get("volume", pd.Series(dtype=float)), errors="coerce")
        close = pd.to_numeric(group["close"], errors="coerce")
        warnings = []
        if ticker in rejected:
            warnings.append(f"metadata_rejected:{rejected[ticker]}")
        if ticker in MARKET_SYMBOLS and group.empty:
            warnings.append("missing_market_regime_index")
        rows.append(
            {
                "symbol": ticker,
                "role": role,
                "first_data_date": group["date"].min().strftime("%Y-%m-%d"),
                "last_data_date": group["date"].max().strftime("%Y-%m-%d"),
                "bar_count": int(group["date"].nunique()),
                "missing_session_count": max(0, int(expected - group["date"].nunique())),
                "zero_volume_count": int(volume.fillna(0).eq(0).sum()),
                "abnormal_volume_count": int((volume > volume.median() * 20).sum()) if volume.notna().any() and volume.median() > 0 else 0,
                "split_or_adjustment_anomaly_count": int(close.pct_change(fill_method=None).abs().gt(0.45).sum()),
                "metadata_status": "rejected" if ticker in rejected else "available",
                "warnings": ";".join(warnings),
            }
        )
    for symbol in ["SPY", "QQQ"]:
        if symbol not in set(frame["ticker"]):
            rows.append(
                {
                    "symbol": symbol,
                    "role": "market_regime_index" if symbol == "QQQ" else "benchmark",
                    "first_data_date": "",
                    "last_data_date": "",
                    "bar_count": 0,
                    "missing_session_count": 0,
                    "zero_volume_count": 0,
                    "abnormal_volume_count": 0,
                    "split_or_adjustment_anomaly_count": 0,
                    "metadata_status": "missing",
                    "warnings": "material_blocker_missing_market_data",
                }
            )
    return pd.DataFrame(rows)


def evaluate_families(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    families: list[dict],
    replay_rounds: int,
    replay_sample_count: int,
    replay_sample_offset: int,
    benchmark_ticker: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    rejected_frames = []
    regime_lookup = build_market_regime_lookup(data)
    for sample_index in range(replay_sample_count):
        sample_id = replay_sample_offset + sample_index
        baseline_decisions, _, _ = build_phase1_historical_replay(
            data,
            account_settings,
            rule,
            replay_rounds=replay_rounds,
            benchmark_ticker=benchmark_ticker,
            replay_sample_offset=sample_id,
        )
        baseline_decisions["family_name"] = "candidate34_frozen_baseline"
        baseline_metrics, baseline_rejected = evaluate_decisions_for_family(
            sample_id,
            replay_rounds,
            "candidate34_frozen_baseline",
            baseline_decisions,
            data,
            account_settings,
            pd.DataFrame(),
        )
        metric_rows.append(baseline_metrics)
        if not baseline_rejected.empty:
            rejected_frames.append(baseline_rejected)
        replay_dates = sample_replay_dates(data, replay_rounds, benchmark_ticker=benchmark_ticker, replay_sample_offset=sample_id)
        for family in [item for item in families if item["family_name"] != "candidate34_frozen_baseline"]:
            decisions, rejected = build_candidate35_decisions(
                data,
                account_settings,
                rule,
                replay_dates,
                family,
                regime_lookup,
                benchmark_ticker,
            )
            metrics, rejected_audit = evaluate_decisions_for_family(
                sample_id,
                replay_rounds,
                family["family_name"],
                decisions,
                data,
                account_settings,
                rejected,
            )
            metric_rows.append(metrics)
            if not rejected_audit.empty:
                rejected_audit["sample_id"] = sample_id
                rejected_frames.append(rejected_audit)
    rejected_all = pd.concat(rejected_frames, ignore_index=True) if rejected_frames else pd.DataFrame()
    return pd.DataFrame(metric_rows), rejected_all


def build_candidate35_decisions(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_dates: list[pd.Timestamp],
    family: dict,
    regime_lookup: dict,
    benchmark_ticker: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    decisions = []
    rejected_frames = []
    for replay_date in replay_dates:
        latest = data.loc[data["date"].eq(replay_date) & ~data["ticker"].isin(MARKET_SYMBOLS)].copy()
        latest = latest.dropna(subset=["date", "ticker", "close", "atr", "relative_volume_prev20", "return_5d", "return_20d", "distance_to_52w_high_prev", "dollar_volume"])
        if latest.empty:
            decisions.append(no_trade_row(replay_date, "NO_ELIGIBLE_DATA", family["family_name"]))
            continue
        scored, pre_rejected = _score_latest_candidates(latest, rule, account_settings)
        if scored.empty:
            decisions.append(no_trade_row(replay_date, "NO_EXECUTABLE_CANDIDATES", family["family_name"]))
            continue
        scored = scored.merge(
            latest[["ticker", "close", "sma20", "sma50", "volatility_20d", "atr_pct", "distance_from_20d_high_pct"]],
            on="ticker",
            how="left",
        )
        scored["regime_label"] = regime_lookup.get(replay_date.strftime("%Y-%m-%d"), {}).get("market_regime_label", "UNKNOWN_MARKET_DATA")
        passed, rejected = apply_family_rules(scored, family)
        if not rejected.empty:
            rejected["replay_date"] = replay_date.strftime("%Y-%m-%d")
            rejected["family_name"] = family["family_name"]
            rejected_frames.append(rejected.head(5).copy())
        if passed.empty:
            decisions.append(no_trade_row(replay_date, "NO_CANDIDATE35_RULE_PASS", family["family_name"]))
            continue
        chosen = rank_family_candidates(passed, family).iloc[0]
        row = buy_decision_row(replay_date, chosen, family["family_name"])
        row.update(forward_return_labels(latest, str(chosen["ticker"])))
        decisions.append(row)
    rejected_all = pd.concat(rejected_frames, ignore_index=True) if rejected_frames else pd.DataFrame()
    return pd.DataFrame(decisions), rejected_all


def apply_family_rules(scored: pd.DataFrame, family: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = scored.copy()
    kind = family["kind"]
    reasons = []
    for _, row in frame.iterrows():
        reason = family_reject_reason(row, kind)
        reasons.append(reason)
    frame["reject_reason"] = reasons
    passed = frame.loc[frame["reject_reason"].eq("")].copy()
    rejected = frame.loc[~frame["reject_reason"].eq("")].copy()
    return passed, rejected


def family_reject_reason(row: pd.Series, kind: str) -> str:
    close = _num(row.get("close"))
    sma20 = _num(row.get("sma20"))
    sma50 = _num(row.get("sma50"))
    vol = _num(row.get("volatility_20d"))
    atr_pct = _num(row.get("atr_pct"))
    d52 = _num(row.get("distance_to_52w_high_prev"))
    d20 = _num(row.get("distance_from_20d_high_pct"))
    r5 = _num(row.get("return_5d"))
    r20 = _num(row.get("return_20d"))
    relvol = _num(row.get("relative_volume_prev20"))
    smoke = _num(row.get("smoke_score"))
    regime = str(row.get("regime_label", "UNKNOWN_MARKET_DATA"))
    if kind == "trend_quality":
        if pd.isna(sma20) or pd.isna(sma50) or close < sma20 or sma20 < sma50:
            return "trend_quality_failed_sma_stack"
        if d52 < -0.18 or vol > 0.07 or atr_pct > 0.08:
            return "trend_quality_failed_risk_bounds"
    elif kind == "pullback_continuation":
        if pd.isna(sma50) or close < sma50 or r20 <= 0:
            return "pullback_failed_broader_uptrend"
        if r5 < -0.08 or r5 > 0.18 or vol > 0.075 or atr_pct > 0.08:
            return "pullback_failed_controlled_pullback"
    elif kind == "breakout_confirmation":
        if d20 < -0.05 or r20 <= 0:
            return "breakout_failed_near_high_or_momentum"
        if relvol < 1.5 and r5 < 0.08:
            return "breakout_failed_confirmation"
        if r5 > 0.35 or atr_pct > 0.10:
            return "breakout_failed_extension_risk"
    elif kind == "regime_gated_momentum":
        if regime == "RISK_OFF" and (smoke < 0.94 or vol > 0.055):
            return "regime_risk_off_too_weak"
        if regime in {"MIXED", "UNKNOWN_MARKET_DATA"} and (smoke < 0.90 or vol > 0.07):
            return "regime_mixed_too_weak"
        if r5 <= 0 or r20 <= 0:
            return "regime_failed_positive_momentum"
    elif kind == "low_volatility_compounder":
        if vol > 0.055 or atr_pct > 0.055:
            return "compounder_failed_low_volatility"
        if smoke < 0.88 or r20 <= 0 or d52 < -0.25:
            return "compounder_failed_quality_momentum"
    return ""


def rank_family_candidates(passed: pd.DataFrame, family: dict) -> pd.DataFrame:
    frame = passed.copy()
    kind = family["kind"]
    if kind == "trend_quality":
        frame["family_score"] = frame["smoke_score"] + frame["distance_to_52w_high_prev"] - frame["volatility_20d"].fillna(0)
    elif kind == "pullback_continuation":
        frame["family_score"] = frame["smoke_score"] + frame["return_20d"] - frame["return_5d"].abs()
    elif kind == "breakout_confirmation":
        frame["family_score"] = frame["smoke_score"] + frame["relative_volume_prev20"].rank(pct=True) + frame["return_5d"]
    elif kind == "regime_gated_momentum":
        frame["family_score"] = frame["smoke_score"] + frame["return_5d"] + frame["return_20d"] - frame["volatility_20d"].fillna(0)
    else:
        frame["family_score"] = frame["smoke_score"] - frame["volatility_20d"].fillna(0) - frame["atr_pct"].fillna(0)
    return frame.sort_values(["family_score", "smoke_score", "ticker"], ascending=[False, False, True])


def evaluate_decisions_for_family(
    sample_id: int,
    replay_rounds: int,
    family_name: str,
    decisions: pd.DataFrame,
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rejected: pd.DataFrame,
) -> tuple[dict, pd.DataFrame]:
    trades = simulate_phase1c_policy_trades(decisions, data, account_settings, BASELINE_POLICY)
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    buys = decisions.loc[decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)].copy() if not decisions.empty else pd.DataFrame()
    top_profit_share, top_loss_share = ticker_profit_loss_shares(executed)
    theme_profit_share, theme_loss_share = theme_concentration_shares(executed)
    wins = executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    losses = executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    metrics = {
        "sample_id": sample_id,
        "family_name": family_name,
        "replay_rounds": replay_rounds,
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
        "best_trade": trade_label(executed, best=True),
        "worst_trade": trade_label(executed, best=False),
        "top_profit_ticker_contribution_share": top_profit_share,
        "top_loss_ticker_contribution_share": top_loss_share,
        "top_profit_theme_contribution_share": theme_profit_share,
        "top_loss_theme_contribution_share": theme_loss_share,
        "number_of_rejected_decisions": int(len(rejected)),
        "primary_reject_reasons": reject_reason_summary(rejected),
        "ending_value_excluding_best_trade": ending_excluding_best_trade(executed, account_settings.starting_capital),
    }
    audit = rejected_decision_audit(sample_id, family_name, rejected, data)
    return metrics, audit


def build_comparison(metrics: pd.DataFrame, split: dict) -> pd.DataFrame:
    rows = []
    for (family, split_value), group in metrics.groupby(["family_name", "split_name"]):
        failed = comparison_failed_gates(group)
        rows.append(
            {
                "family_name": family,
                "split_name": split_value,
                "sample_count": int(group["sample_id"].nunique()),
                "total_buy_count": int(group["buy_count"].sum()),
                "median_buy_count_per_sample": float(group["buy_count"].median()),
                "worst_sample_ending_value": float(group["ending_account_value"].min()),
                "median_ending_value": float(group["ending_account_value"].median()),
                "best_sample_ending_value": float(group["ending_account_value"].max()),
                "worst_max_drawdown": float(group["max_drawdown"].min()),
                "median_max_drawdown": float(group["max_drawdown"].median()),
                "median_simulated_win_rate": median(group["simulated_win_rate"]),
                "median_20d_accuracy": median(group["accuracy_20d"]),
                "median_profit_factor": median(group["profit_factor"]),
                "worst_top_ticker_loss_share": max_or_na(group["top_loss_ticker_contribution_share"]),
                "worst_top_theme_loss_share": max_or_na(group["top_loss_theme_contribution_share"]),
                "pass_fail_status": "PASS" if not failed else "FAIL",
                "failed_gates": ";".join(failed),
            }
        )
    return pd.DataFrame(rows)


def build_holdout_results(holdout: pd.DataFrame, preflight: pd.DataFrame, replay_sample_count: int) -> pd.DataFrame:
    if holdout.empty:
        return pd.DataFrame()
    rows = []
    full_sample = replay_sample_count >= 30
    preflight_blocked = has_material_preflight_blocker(preflight)
    for family, group in holdout.groupby("family_name"):
        gates = holdout_failed_gates(group, full_sample, preflight_blocked)
        rows.append(
            {
                "family_name": family,
                "sample_count": int(group["sample_id"].nunique()),
                "median_buy_count": float(group["buy_count"].median()),
                "minimum_buy_count": int(group["buy_count"].min()),
                "worst_holdout_ending_value": float(group["ending_account_value"].min()),
                "median_holdout_ending_value": float(group["ending_account_value"].median()),
                "worst_holdout_max_drawdown": float(group["max_drawdown"].min()),
                "median_holdout_win_rate": median(group["simulated_win_rate"]),
                "median_holdout_20d_accuracy": median(group["accuracy_20d"]),
                "median_holdout_profit_factor": median(group["profit_factor"]),
                "worst_trade_loss_percent": min_or_na(group["worst_trade_loss_percent"]),
                "max_top_ticker_loss_share": max_or_na(group["top_loss_ticker_contribution_share"]),
                "max_top_theme_loss_share": max_or_na(group["top_loss_theme_contribution_share"]),
                "median_ending_value_excluding_best_trade": median(group["ending_value_excluding_best_trade"]),
                "holdout_gate_pass": not gates,
                "failed_gates": ";".join(gates),
            }
        )
    return pd.DataFrame(rows)


def promote_from_split(split_metrics: pd.DataFrame, max_count: int, include_baseline: bool) -> list[str]:
    if split_metrics.empty:
        return []
    comparison = build_comparison(split_metrics, {})
    source = comparison.copy()
    if not include_baseline:
        source = source.loc[~source["family_name"].eq("candidate34_frozen_baseline")].copy()
    ranked = source.sort_values(
        ["pass_fail_status", "worst_sample_ending_value", "median_max_drawdown", "median_simulated_win_rate", "median_ending_value"],
        ascending=[False, False, False, False, False],
    )
    return ranked["family_name"].head(max_count).tolist()


def phase1g_status(holdout_results: pd.DataFrame, preflight: pd.DataFrame, replay_sample_count: int) -> str:
    if has_material_preflight_blocker(preflight):
        return PHASE_1G_DATA_PREFLIGHT_BLOCKED
    if replay_sample_count < 30:
        return PHASE_1G_REDESIGN_PROMISING_REQUIRES_FULL_SAMPLE if not holdout_results.empty and holdout_results["holdout_gate_pass"].any() else PHASE_1G_INSUFFICIENT_SAMPLE_WARNING
    if holdout_results.empty:
        return PHASE_1G_NO_REDESIGN_SURVIVED_VALIDATION
    redesigned = holdout_results.loc[~holdout_results["family_name"].eq("candidate34_frozen_baseline")]
    if redesigned.empty:
        return PHASE_1G_NO_REDESIGN_SURVIVED_VALIDATION
    if redesigned["holdout_gate_pass"].any():
        return PHASE_1G_REDESIGN_PROMISING_FOR_GPT_REVIEW
    return PHASE_1G_HOLDOUT_FAILED


def write_phase1g_reports(
    preflight: pd.DataFrame,
    definitions_md: str,
    calibration: pd.DataFrame,
    validation: pd.DataFrame,
    holdout: pd.DataFrame,
    comparison: pd.DataFrame,
    rejected: pd.DataFrame,
    summary_md: str,
    preflight_csv_path: str | Path,
    definitions_md_path: str | Path,
    calibration_csv_path: str | Path,
    validation_csv_path: str | Path,
    holdout_csv_path: str | Path,
    comparison_csv_path: str | Path,
    rejected_csv_path: str | Path,
    summary_md_path: str | Path,
) -> None:
    for path in [preflight_csv_path, definitions_md_path, calibration_csv_path, validation_csv_path, holdout_csv_path, comparison_csv_path, rejected_csv_path, summary_md_path]:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    preflight.to_csv(preflight_csv_path, index=False)
    Path(definitions_md_path).write_text(definitions_md, encoding="utf-8")
    calibration.to_csv(calibration_csv_path, index=False)
    validation.to_csv(validation_csv_path, index=False)
    holdout.to_csv(holdout_csv_path, index=False)
    comparison.to_csv(comparison_csv_path, index=False)
    rejected.to_csv(rejected_csv_path, index=False)
    Path(summary_md_path).write_text(summary_md, encoding="utf-8")


def candidate_family_definitions_markdown() -> str:
    sections = [
        ("candidate34_frozen_baseline", "Frozen Candidate 34 baseline.", "Existing Candidate 34 rule from auto research output.", "Existing decision_strength then smoke_score ranking.", "NO_TRADE when Candidate 34 has no executable pass.", "Baseline, not a redesign.", "Known broad instability from Phase 1F."),
        ("candidate35_trend_quality", "Prioritizes stable uptrend quality.", "close >= SMA20 >= SMA50, near prior highs, bounded volatility and ATR.", "smoke_score + distance_to_52w_high_prev - volatility_20d.", "NO_TRADE when trend stack or risk bounds fail.", "Adds explicit trend-quality gates absent from Candidate 34.", "May miss early turnarounds and high-beta breakouts."),
        ("candidate35_pullback_continuation", "Controlled pullback inside broader uptrend.", "close above SMA50, positive 20d return, bounded 5d pullback/spike, bounded volatility and ATR.", "smoke_score + return_20d - abs(return_5d).", "NO_TRADE when pullback is too sharp or too extended.", "Avoids chasing short-term spikes.", "May under-trade strong momentum regimes."),
        ("candidate35_breakout_confirmation", "Breakout or momentum confirmation.", "Near 20d high, positive 20d return, relative volume or 5d strength confirmation, blocks extreme extension.", "smoke_score + relative-volume rank + return_5d.", "NO_TRADE when confirmation or extension gates fail.", "Requires confirmation beyond Candidate 34 ranks.", "Can still chase false breakouts."),
        ("candidate35_regime_gated_momentum", "Momentum with SPY/QQQ regime awareness.", "Uses replay-date SPY/QQQ labels; stricter in mixed/risk-off regimes.", "smoke_score + return_5d + return_20d - volatility_20d.", "NO_TRADE more often in weak regimes.", "Adds market-regime gate.", "May over-filter and become regime-dependent."),
        ("candidate35_low_volatility_compounder", "Lower-volatility growth/momentum candidates.", "volatility_20d and ATR pct caps, smoke score, positive 20d return, not far below highs.", "smoke_score - volatility_20d - atr_pct.", "NO_TRADE when low-volatility quality gates fail.", "Intentionally avoids high-beta watchlist names.", "May trade too rarely in speculative universes."),
    ]
    lines = ["# Phase 1G Candidate Family Definitions", "", "Research-only. No family is approved for daily scan, paper execution, or real-money execution.", ""]
    for name, intent, features, formula, no_trade, diff, failure in sections:
        lines.extend(
            [
                f"## {name}",
                "",
                f"- Intent: {intent}",
                f"- Required pre-entry features: {features}",
                f"- Exact rule conditions: {features}",
                f"- Ranking formula: {formula}",
                f"- NO_TRADE behavior: {no_trade}",
                f"- Difference from Candidate 34: {diff}",
                f"- Expected failure mode: {failure}",
                "",
            ]
        )
    return "\n".join(lines)


def buy_decision_row(replay_date: pd.Timestamp, candidate: pd.Series, family_name: str) -> dict:
    return {
        "replay_date": replay_date.strftime("%Y-%m-%d"),
        "decision": HISTORICAL_BUY_CANDIDATE,
        "ticker": candidate["ticker"],
        "reason": f"{family_name} research sandbox candidate.",
        "reference_price": float(candidate["reference_price"]),
        "shares_with_cash": candidate["shares_with_100"],
        "estimated_total_cost": candidate["estimated_total_cost"],
        "estimated_cash_remaining": candidate["estimated_cash_remaining"],
        "smoke_score": candidate["smoke_score"],
        "decision_strength": candidate.get("family_score", candidate["decision_strength"]),
        "relative_volume_prev20": candidate["relative_volume_prev20"],
        "return_5d": candidate["return_5d"],
        "return_20d": candidate["return_20d"],
        "distance_to_52w_high_prev": candidate["distance_to_52w_high_prev"],
        "dollar_volume": candidate["dollar_volume"],
        "family_name": family_name,
    }


def no_trade_row(replay_date: pd.Timestamp, reason: str, family_name: str) -> dict:
    return {
        "replay_date": replay_date.strftime("%Y-%m-%d"),
        "decision": HISTORICAL_NO_TRADE,
        "ticker": "",
        "reason": reason,
        "reference_price": pd.NA,
        "family_name": family_name,
    }


def forward_return_labels(latest: pd.DataFrame, ticker: str) -> dict:
    row = latest.loc[latest["ticker"].eq(ticker)].iloc[0]
    return {f"forward_return_{window}d": row.get(f"fwd_return_{window}d", pd.NA) for window in FORWARD_WINDOWS}


def rejected_decision_audit(sample_id: int, family_name: str, rejected: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
    if rejected.empty:
        return pd.DataFrame()
    rows = []
    for _, row in rejected.iterrows():
        rows.append(
            {
                "sample_id": sample_id,
                "replay_date": row.get("replay_date", ""),
                "family_name": family_name,
                "ticker": row.get("ticker", ""),
                "reference_price": row.get("reference_price", pd.NA),
                "action_if_candidate34": "UNKNOWN_NEAR_MISS",
                "action_if_candidate35": "HISTORICAL_NO_TRADE",
                "reject_reason": row.get("reject_reason", ""),
                "pre_entry_features": pre_entry_feature_string(row),
                "forward_return_20d": pd.NA,
                "simulated_pnl_if_taken_with_baseline_exit": pd.NA,
                "rejection_avoided_a_loss": pd.NA,
                "rejection_missed_a_win": pd.NA,
            }
        )
    return pd.DataFrame(rows)


def comparison_failed_gates(group: pd.DataFrame) -> list[str]:
    failed = []
    if group["buy_count"].min() < 15:
        failed.append("min_buy_count_lt_15")
    if group["ending_account_value"].min() <= 105:
        failed.append("worst_ending_lte_105")
    if group["max_drawdown"].min() <= -0.35:
        failed.append("worst_drawdown_lte_minus_35")
    if median(group["simulated_win_rate"]) < 0.52:
        failed.append("median_win_rate_lt_52")
    if median(group["accuracy_20d"]) < 0.55:
        failed.append("median_20d_accuracy_lt_55")
    return failed


def holdout_failed_gates(group: pd.DataFrame, full_sample: bool, preflight_blocked: bool) -> list[str]:
    failed = comparison_failed_gates(group)
    if not full_sample:
        failed.append("full_30_sample_run_not_completed")
    worst_loss = min_or_na(group["worst_trade_loss_percent"])
    ticker_loss_share = max_or_na(group["top_loss_ticker_contribution_share"])
    theme_loss_share = max_or_na(group["top_loss_theme_contribution_share"])
    ex_best = median(group["ending_value_excluding_best_trade"])
    profit_factor = median(group["profit_factor"])
    if pd.notna(worst_loss) and float(worst_loss) <= -0.15:
        failed.append("worst_trade_loss_lte_minus_15")
    if pd.notna(ticker_loss_share) and float(ticker_loss_share) > 0.40:
        failed.append("top_ticker_loss_share_gt_40")
    if pd.notna(theme_loss_share) and float(theme_loss_share) > 0.50:
        failed.append("top_theme_loss_share_gt_50")
    if pd.notna(ex_best) and float(ex_best) <= 110:
        failed.append("median_ex_best_lte_110")
    if pd.isna(profit_factor) or float(profit_factor) < 1.25:
        failed.append("median_profit_factor_lt_125")
    if preflight_blocked:
        failed.append("data_preflight_blocked")
    return failed


def has_material_preflight_blocker(preflight: pd.DataFrame) -> bool:
    if preflight.empty:
        return True
    market = preflight.loc[preflight["symbol"].isin(["SPY", "QQQ"])]
    return bool(market.empty or market["bar_count"].min() <= 0 or market["warnings"].astype(str).str.contains("material_blocker").any())


def summarize_phase1g(preflight, all_metrics, calibration, validation, holdout, comparison, rejected, split, status, cal_promoted, val_promoted, replay_sample_count) -> dict:
    return {
        "phase_1g_status": status,
        "sample_count": replay_sample_count,
        "fallback_used": bool(split["fallback_used"]),
        "calibration_promoted": cal_promoted,
        "validation_promoted": val_promoted,
        "preflight_blocked": has_material_preflight_blocker(preflight),
        "family_count": len(REQUIRED_FAMILIES),
        "rejected_rows": int(len(rejected)),
        "best_calibration_family": best_family(calibration),
        "best_validation_family": best_family(validation),
        "best_holdout_family": best_family(holdout),
    }


def phase1g_summary_markdown(summary, preflight, calibration, validation, holdout, comparison, rejected) -> str:
    lines = [
        "PHOENIX NANO PHASE 1G — CANDIDATE 35 REDESIGN SANDBOX",
        "",
        "Research-only. No rule is approved for daily scan, paper execution, or real-money execution.",
        "",
        "## Phase 1F Recap",
        "",
        "- Phase 1F concluded Candidate 34 failures were broad and recommended redesign rather than more threshold tuning.",
        "",
        "## Data/Regime Preflight Summary",
        "",
        preflight.to_markdown(index=False) if not preflight.empty else "No preflight rows.",
        "",
        "## Candidate 35 Family Definitions Summary",
        "",
        "\n".join(f"- {name}" for name in REQUIRED_FAMILIES),
        "",
        "## Calibration Results",
        "",
        split_summary(calibration),
        "",
        "## Validation Results",
        "",
        split_summary(validation),
        "",
        "## Holdout Results",
        "",
        holdout.to_markdown(index=False) if not holdout.empty else "No holdout rows.",
        "",
        "## Candidate 34 vs Candidate 35 Comparison",
        "",
        comparison.to_markdown(index=False) if not comparison.empty else "No comparison rows.",
        "",
        "## Rejected Decision Audit Summary",
        "",
        f"- Rejected audit rows: {summary['rejected_rows']}",
        reject_reason_summary(rejected),
        "",
        "## Improvement Assessment",
        "",
        "Any apparent improvement must be read against BUY-count and concentration gates. Families that trade too rarely are treated as over-filtering, not approval.",
        "",
        f"## Final Phase 1G Status: {summary['phase_1g_status']}",
        "",
        "Do not start paper execution or real-money execution.",
        "",
        "## Next Research Task Recommendation",
        "",
        "Ask GPT to review whether the redesign sandbox produced a family worth deeper research, or whether Phoenix Nano should pause until data quality and universe design are upgraded.",
        "",
    ]
    return "\n".join(lines)


def theme_concentration_shares(executed: pd.DataFrame) -> tuple[object, object]:
    if executed.empty:
        return pd.NA, pd.NA
    frame = executed.copy()
    frame["theme"] = frame["ticker"].apply(lambda ticker: ticker_theme_subtheme(str(ticker))[0])
    profits = frame.loc[frame["pnl_dollars"] > 0].groupby("theme")["pnl_dollars"].sum()
    losses = frame.loc[frame["pnl_dollars"] < 0].groupby("theme")["pnl_dollars"].sum().abs()
    return (
        float(profits.max() / profits.sum()) if profits.sum() > 0 else pd.NA,
        float(losses.max() / losses.sum()) if losses.sum() > 0 else pd.NA,
    )


def ending_excluding_best_trade(executed: pd.DataFrame, starting_capital: float) -> float:
    if executed.empty:
        return starting_capital
    return float(starting_capital + executed.drop(index=executed["pnl_dollars"].idxmax())["pnl_dollars"].sum())


def stopped_positive_rate(executed: pd.DataFrame) -> object:
    if executed.empty or "forward_return_20d" not in executed.columns:
        return pd.NA
    stopped = executed["exit_reason"].eq("STOP")
    return float((stopped & pd.to_numeric(executed["forward_return_20d"], errors="coerce").gt(0)).mean())


def trade_label(executed: pd.DataFrame, best: bool) -> str:
    if executed.empty:
        return ""
    idx = executed["pnl_dollars"].idxmax() if best else executed["pnl_dollars"].idxmin()
    row = executed.loc[idx]
    return f"{row['replay_date']} {row['ticker']} pnl={float(row['pnl_dollars']):.2f}"


def reject_reason_summary(rejected: pd.DataFrame) -> str:
    if rejected.empty or "reject_reason" not in rejected.columns:
        return "none"
    return ", ".join(f"{reason}:{count}" for reason, count in rejected["reject_reason"].fillna("").value_counts().head(8).items())


def pre_entry_feature_string(row: pd.Series) -> str:
    fields = ["smoke_score", "volatility_20d", "atr_pct", "return_5d", "return_20d", "relative_volume_prev20", "distance_to_52w_high_prev"]
    return ";".join(f"{field}={row.get(field, pd.NA)}" for field in fields)


def best_family(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    if "ending_account_value" in frame.columns:
        grouped = frame.groupby("family_name")["ending_account_value"].median().sort_values(ascending=False)
        return str(grouped.index[0]) if len(grouped) else ""
    if "median_holdout_ending_value" in frame.columns:
        ranked = frame.sort_values("median_holdout_ending_value", ascending=False)
        return str(ranked.iloc[0]["family_name"]) if len(ranked) else ""
    return ""


def split_summary(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = ["sample_id", "family_name", "buy_count", "ending_account_value", "max_drawdown", "simulated_win_rate", "accuracy_20d", "profit_factor"]
    return frame[cols].sort_values(["family_name", "sample_id"]).to_markdown(index=False)


def split_name(sample_id: int, split: dict) -> str:
    if sample_id in split["calibration"]:
        return "calibration"
    if sample_id in split["validation"]:
        return "validation"
    if sample_id in split["holdout"]:
        return "holdout"
    return "unused"


def positive_rate(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float((clean > 0).mean())


def mean(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.mean())


def median(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.median())


def max_or_na(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.max())


def min_or_na(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.min())


def _num(value: object) -> float:
    try:
        if pd.isna(value):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")
