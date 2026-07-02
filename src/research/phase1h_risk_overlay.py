from __future__ import annotations

from itertools import combinations
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
from src.research.phase1g_redesign_sandbox import (
    BASELINE_POLICY,
    MARKET_SYMBOLS,
    add_redesign_features,
    build_phase1g_preflight,
    ending_excluding_best_trade,
    family_reject_reason,
    forward_return_labels,
    no_trade_row,
    positive_rate,
    rank_family_candidates,
    split_name,
)


PHASE_1H_DATA_BLOCKED = "PHASE_1H_DATA_BLOCKED"
PHASE_1H_NO_OVERLAY_SURVIVED_VALIDATION = "PHASE_1H_NO_OVERLAY_SURVIVED_VALIDATION"
PHASE_1H_HOLDOUT_FAILED = "PHASE_1H_HOLDOUT_FAILED"
PHASE_1H_OVERFILTERED = "PHASE_1H_OVERFILTERED"
PHASE_1H_INSUFFICIENT_SAMPLE_WARNING = "PHASE_1H_INSUFFICIENT_SAMPLE_WARNING"
PHASE_1H_RISK_OVERLAY_PROMISING_FOR_GPT_REVIEW = "PHASE_1H_RISK_OVERLAY_PROMISING_FOR_GPT_REVIEW"

TREND_BASELINE = "candidate35_trend_quality_frozen"
PHASE1H_BASELINES = ["candidate34_frozen_baseline", TREND_BASELINE]


def build_phase1h_risk_overlay_sandbox(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_rounds: int = 100,
    replay_sample_count: int = 30,
    replay_sample_offset: int = 0,
    benchmark_ticker: str = "SPY",
    rejected_metadata: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, dict]:
    frame = add_redesign_features(data)
    preflight = build_phase1g_preflight(frame, rejected_metadata, benchmark_ticker)
    split = deterministic_phase1h_split(replay_sample_count, replay_sample_offset)
    definitions = overlay_definitions_markdown()
    metrics, counterfactuals, drawdown, theme_audit = evaluate_phase1h_samples(
        frame,
        account_settings,
        rule,
        replay_rounds,
        replay_sample_count,
        replay_sample_offset,
        benchmark_ticker,
    )
    metrics["split_name"] = metrics["sample_id"].apply(lambda value: split_name(int(value), split))
    calibration_all = metrics.loc[metrics["split_name"].eq("calibration")].copy()
    calibration_promoted = promote_overlays(calibration_all, max_count=2)
    combined = build_combined_overlay(calibration_all, calibration_promoted)
    if combined:
        combined_metrics, combined_counter, combined_drawdown, combined_theme = evaluate_phase1h_samples(
            frame,
            account_settings,
            rule,
            replay_rounds,
            replay_sample_count,
            replay_sample_offset,
            benchmark_ticker,
            overlay_subset=[combined],
            include_baselines=False,
        )
        combined_metrics["split_name"] = combined_metrics["sample_id"].apply(lambda value: split_name(int(value), split))
        metrics = pd.concat([metrics, combined_metrics], ignore_index=True)
        counterfactuals = pd.concat([counterfactuals, combined_counter], ignore_index=True)
        drawdown = pd.concat([drawdown, combined_drawdown], ignore_index=True)
        theme_audit = pd.concat([theme_audit, combined_theme], ignore_index=True)
        calibration_all = metrics.loc[metrics["split_name"].eq("calibration")].copy()
    validation_names = PHASE1H_BASELINES + calibration_promoted + ([combined["overlay_name"]] if combined else [])
    validation = metrics.loc[metrics["split_name"].eq("validation") & metrics["policy_name"].isin(validation_names)].copy()
    validation_promoted = promote_overlays(validation, max_count=1)
    holdout_names = PHASE1H_BASELINES + validation_promoted
    holdout_matrix = metrics.loc[metrics["split_name"].eq("holdout") & metrics["policy_name"].isin(holdout_names)].copy()
    holdout = build_phase1h_holdout_results(holdout_matrix, counterfactuals, preflight, replay_sample_count)
    comparison = build_phase1h_comparison(metrics, split)
    status = phase1h_status(holdout, preflight, replay_sample_count)
    summary = {
        "phase_1h_status": status,
        "sample_count": replay_sample_count,
        "fallback_used": bool(split["fallback_used"]),
        "calibration_promoted": calibration_promoted,
        "validation_promoted": validation_promoted,
        "combined_overlay": combined["overlay_name"] if combined else "",
        "counterfactual_rows": int(len(counterfactuals)),
        "drawdown_rows": int(len(drawdown)),
        "theme_audit_rows": int(len(theme_audit)),
        "best_holdout_policy": best_policy(holdout),
    }
    summary_md = phase1h_summary_markdown(summary, calibration_all, validation, holdout, comparison, drawdown, theme_audit, counterfactuals)
    return definitions, calibration_all, validation, holdout, comparison, drawdown, theme_audit, counterfactuals, metrics, summary_md, summary


def deterministic_phase1h_split(replay_sample_count: int, replay_sample_offset: int = 0) -> dict:
    ids = list(range(replay_sample_offset, replay_sample_offset + replay_sample_count))
    if replay_sample_count >= 30:
        return {"calibration": ids[:10], "validation": ids[10:20], "holdout": ids[20:30], "fallback_used": False}
    if replay_sample_count >= 20:
        return {"calibration": ids[:7], "validation": ids[7:14], "holdout": ids[14:20], "fallback_used": True}
    third = max(1, replay_sample_count // 3)
    return {"calibration": ids[:third], "validation": ids[third : 2 * third], "holdout": ids[2 * third :], "fallback_used": True}


def overlay_definitions() -> list[dict]:
    overlays = [
        {"overlay_name": "overlay_market_regime_risk_off_skip", "kind": "market_regime", "description": "Skip when SPY/QQQ regime is clearly weak before replay date."},
        {"overlay_name": "overlay_high_volatility_tail_skip", "kind": "volatility_tail", "description": "Skip extreme pre-entry ATR or realized volatility tails."},
    ]
    for loss_threshold in [-0.05, -0.08, -0.10]:
        for cooldown in [3, 5, 8]:
            overlays.append(
                {
                    "overlay_name": f"overlay_theme_loss_cooldown_{int(abs(loss_threshold)*100)}pct_{cooldown}",
                    "kind": "theme_cooldown",
                    "loss_threshold": loss_threshold,
                    "cooldown_decisions": cooldown,
                    "description": "Skip a theme after a prior closed loss in the same theme.",
                }
            )
    for loss_threshold in [-0.05, -0.08, -0.10]:
        for cooldown in [5, 10, 15]:
            overlays.append(
                {
                    "overlay_name": f"overlay_ticker_loss_cooldown_{int(abs(loss_threshold)*100)}pct_{cooldown}",
                    "kind": "ticker_cooldown",
                    "loss_threshold": loss_threshold,
                    "cooldown_decisions": cooldown,
                    "description": "Skip a ticker after a prior closed loss in the same ticker.",
                }
            )
    return overlays


def overlay_definitions_markdown() -> str:
    lines = [
        "# Phase 1H Overlay Definitions",
        "",
        "Research-only. No overlay is approved for daily scan, paper execution, or real-money execution.",
        "",
        "Candidate 35 trend-quality is frozen from Phase 1G. Phase 1H only tests pre-declared risk overlays on top of that frozen sandbox family.",
        "",
    ]
    for overlay in overlay_definitions():
        if overlay["kind"] in {"theme_cooldown", "ticker_cooldown"} and not overlay["overlay_name"].endswith("_5"):
            continue
        lines.extend(
            [
                f"## {overlay['overlay_name']}",
                "",
                f"- Intent: {overlay['description']}",
                "- Allowed inputs: replay-date candidate features, replay-date SPY/QQQ regime features, and prior closed simulated trade outcomes for cooldown overlays.",
                "- Forward returns are not used for overlay decisions.",
                "",
            ]
        )
    lines.extend(
        [
            "## overlay_combined_conservative",
            "",
            "- Intent: Combine at most two independently useful calibration overlays.",
            "- Parameters are frozen before validation and holdout.",
            "",
        ]
    )
    return "\n".join(lines)


def evaluate_phase1h_samples(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_rounds: int,
    replay_sample_count: int,
    replay_sample_offset: int,
    benchmark_ticker: str,
    overlay_subset: list[dict] | None = None,
    include_baselines: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    counter_rows = []
    drawdown_frames = []
    theme_frames = []
    regime_lookup = build_market_regime_lookup(data)
    index_lookup = build_index_feature_lookup(data)
    overlays = overlay_subset if overlay_subset is not None else overlay_definitions()
    outcome_cache: dict[tuple[str, str], dict | None] = {}
    for sample_index in range(replay_sample_count):
        sample_id = replay_sample_offset + sample_index
        replay_dates = sample_replay_dates(data, replay_rounds, benchmark_ticker=benchmark_ticker, replay_sample_offset=sample_id)
        if include_baselines:
            candidate34, _, _ = build_phase1_historical_replay(data, account_settings, rule, replay_rounds, benchmark_ticker, sample_id)
            metric, trades, _ = evaluate_policy(sample_id, replay_rounds, "candidate34_frozen_baseline", candidate34, data, account_settings, pd.DataFrame())
            metric_rows.append(metric)
            drawdown_frames.append(drawdown_attribution(sample_id, "candidate34_frozen_baseline", trades, pd.DataFrame()))
            theme_frames.append(theme_concentration_audit(sample_id, "candidate34_frozen_baseline", trades, None, None))
        base_decisions = build_trend_quality_decisions(data, account_settings, rule, replay_dates, regime_lookup)
        if include_baselines:
            metric, base_trades, _ = evaluate_policy(sample_id, replay_rounds, TREND_BASELINE, base_decisions, data, account_settings, pd.DataFrame())
            metric_rows.append(metric)
            drawdown_frames.append(drawdown_attribution(sample_id, TREND_BASELINE, base_trades, pd.DataFrame()))
            theme_frames.append(theme_concentration_audit(sample_id, TREND_BASELINE, base_trades, None, None))
        for overlay in overlays:
            overlay_decisions, counter = apply_overlay(base_decisions, overlay, data, account_settings, index_lookup, outcome_cache)
            metric, trades, counter = evaluate_policy(sample_id, replay_rounds, overlay["overlay_name"], overlay_decisions, data, account_settings, counter)
            metric_rows.append(metric)
            if not counter.empty:
                counter["sample_id"] = sample_id
                counter_rows.append(counter)
            drawdown_frames.append(drawdown_attribution(sample_id, overlay["overlay_name"], trades, counter))
            theme_frames.append(theme_concentration_audit(sample_id, overlay["overlay_name"], trades, base_decisions, overlay_decisions))
    counters = pd.concat(counter_rows, ignore_index=True) if counter_rows else pd.DataFrame()
    drawdown = pd.concat(drawdown_frames, ignore_index=True) if drawdown_frames else pd.DataFrame()
    themes = pd.concat(theme_frames, ignore_index=True) if theme_frames else pd.DataFrame()
    return pd.DataFrame(metric_rows), counters, drawdown, themes


def build_trend_quality_decisions(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_dates: list[pd.Timestamp],
    regime_lookup: dict,
) -> pd.DataFrame:
    rows = []
    for replay_date in replay_dates:
        latest = data.loc[data["date"].eq(replay_date) & ~data["ticker"].isin(MARKET_SYMBOLS)].copy()
        latest = latest.dropna(subset=["date", "ticker", "close", "atr", "relative_volume_prev20", "return_5d", "return_20d", "distance_to_52w_high_prev", "dollar_volume"])
        if latest.empty:
            rows.append(no_trade_row(replay_date, "NO_ELIGIBLE_DATA", TREND_BASELINE))
            continue
        scored, _ = _score_latest_candidates(latest, rule, account_settings)
        if scored.empty:
            rows.append(no_trade_row(replay_date, "NO_EXECUTABLE_CANDIDATES", TREND_BASELINE))
            continue
        scored = scored.merge(
            latest[["ticker", "close", "sma20", "sma50", "volatility_20d", "atr_pct", "distance_from_20d_high_pct", "gap_pct"]],
            on="ticker",
            how="left",
        )
        scored["regime_label"] = regime_lookup.get(replay_date.strftime("%Y-%m-%d"), {}).get("market_regime_label", "UNKNOWN_MARKET_DATA")
        scored["reject_reason"] = scored.apply(lambda row: family_reject_reason(row, "trend_quality"), axis=1)
        passed = scored.loc[scored["reject_reason"].eq("")].copy()
        if passed.empty:
            rows.append(no_trade_row(replay_date, "NO_TREND_QUALITY_PASS", TREND_BASELINE))
            continue
        chosen = rank_family_candidates(passed, {"kind": "trend_quality"}).iloc[0]
        row = phase1h_buy_decision_row(replay_date, chosen, TREND_BASELINE)
        row.update(forward_return_labels(latest, str(chosen["ticker"])))
        rows.append(row)
    return pd.DataFrame(rows)


def phase1h_buy_decision_row(replay_date: pd.Timestamp, candidate: pd.Series, policy_name: str) -> dict:
    return {
        "replay_date": replay_date.strftime("%Y-%m-%d"),
        "decision": HISTORICAL_BUY_CANDIDATE,
        "ticker": candidate["ticker"],
        "reason": f"{policy_name} research sandbox candidate.",
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
        "volatility_20d": candidate.get("volatility_20d", pd.NA),
        "atr_pct": candidate.get("atr_pct", pd.NA),
        "gap_pct": candidate.get("gap_pct", pd.NA),
        "regime_label": candidate.get("regime_label", pd.NA),
        "policy_name": policy_name,
    }


def apply_overlay(
    base_decisions: pd.DataFrame,
    overlay: dict,
    data: pd.DataFrame,
    account_settings: AccountSettings,
    index_lookup: dict,
    outcome_cache: dict[tuple[str, str], dict | None] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    counters = []
    cooldown_state: dict[str, int] = {}
    pending: list[dict] = []
    completed_decisions = 0
    for _, decision in base_decisions.sort_values("replay_date").iterrows():
        replay_date = pd.Timestamp(decision["replay_date"])
        for outcome in list(pending):
            if pd.Timestamp(outcome["exit_date"]) <= replay_date:
                key = outcome["cooldown_key"]
                if float(outcome["trade_return_pct"]) <= float(overlay.get("loss_threshold", -1.0)):
                    cooldown_state[key] = max(cooldown_state.get(key, 0), completed_decisions + int(overlay.get("cooldown_decisions", 0)))
                pending.remove(outcome)
        skip, reason = overlay_skip_reason(decision, overlay, index_lookup, cooldown_state, completed_decisions)
        if decision.get("decision") == HISTORICAL_BUY_CANDIDATE and skip:
            skipped = no_trade_row(replay_date, reason, overlay["overlay_name"])
            skipped["policy_name"] = overlay["overlay_name"]
            rows.append(skipped)
            counters.append(counterfactual_row(decision, overlay, reason, data, account_settings, outcome_cache))
        else:
            row = decision.to_dict()
            row["policy_name"] = overlay["overlay_name"]
            rows.append(row)
            if decision.get("decision") == HISTORICAL_BUY_CANDIDATE and overlay["kind"] in {"theme_cooldown", "ticker_cooldown", "combined"}:
                outcome = single_trade_outcome(decision, data, account_settings, outcome_cache)
                if outcome:
                    outcome["cooldown_key"] = cooldown_key(decision, overlay)
                    pending.append(outcome)
        completed_decisions += 1
    return pd.DataFrame(rows), pd.DataFrame(counters)


def overlay_skip_reason(decision: pd.Series, overlay: dict, index_lookup: dict, cooldown_state: dict[str, int], completed_decisions: int) -> tuple[bool, str]:
    if decision.get("decision") != HISTORICAL_BUY_CANDIDATE:
        return False, ""
    kind = overlay["kind"]
    if kind == "combined":
        for child in overlay["children"]:
            skip, reason = overlay_skip_reason(decision, child, index_lookup, cooldown_state, completed_decisions)
            if skip:
                return True, f"combined:{reason}"
        return False, ""
    if kind == "market_regime":
        features = index_lookup.get(str(decision["replay_date"]), {})
        weak_spy = bool(features.get("spy_below_50_200", False) and features.get("spy_return_20d", 0.0) < 0)
        weak_qqq = bool(features.get("qqq_below_50_200", False) and features.get("qqq_return_20d", 0.0) < 0)
        high_vol = max(float(features.get("spy_volatility_20d", 0.0)), float(features.get("qqq_volatility_20d", 0.0))) > 0.025
        return (weak_spy and weak_qqq and high_vol, "market_regime_risk_off_skip")
    if kind == "volatility_tail":
        atr = safe_float(decision.get("atr_pct"))
        vol = safe_float(decision.get("volatility_20d"))
        gap = abs(safe_float(decision.get("gap_pct")))
        return (atr > 0.055 or vol > 0.055 or gap > 0.08, "high_volatility_tail_skip")
    if kind in {"theme_cooldown", "ticker_cooldown"}:
        key = cooldown_key(decision, overlay)
        return (cooldown_state.get(key, -1) > completed_decisions, f"{kind}_active")
    return False, ""


def cooldown_key(decision: pd.Series, overlay: dict) -> str:
    if overlay["kind"] == "theme_cooldown":
        return ticker_theme_subtheme(str(decision.get("ticker", "")))[0]
    if overlay["kind"] == "combined":
        return str(decision.get("ticker", ""))
    return str(decision.get("ticker", ""))


def single_trade_outcome(
    decision: pd.Series,
    data: pd.DataFrame,
    account_settings: AccountSettings,
    outcome_cache: dict[tuple[str, str], dict | None] | None = None,
) -> dict | None:
    key = (str(decision.get("replay_date", "")), str(decision.get("ticker", "")))
    if outcome_cache is not None and key in outcome_cache:
        return outcome_cache[key]
    trades = simulate_phase1c_policy_trades(pd.DataFrame([decision.to_dict()]), data, account_settings, BASELINE_POLICY)
    executed = trades.loc[trades["status"].eq(EXECUTED)] if not trades.empty else pd.DataFrame()
    if executed.empty:
        if outcome_cache is not None:
            outcome_cache[key] = None
        return None
    row = executed.iloc[0]
    result = {
        "exit_date": row["exit_date"],
        "trade_return_pct": row["trade_return_pct"],
        "pnl_dollars": row["pnl_dollars"],
    }
    if outcome_cache is not None:
        outcome_cache[key] = result
    return result


def counterfactual_row(
    decision: pd.Series,
    overlay: dict,
    reason: str,
    data: pd.DataFrame,
    account_settings: AccountSettings,
    outcome_cache: dict[tuple[str, str], dict | None] | None = None,
) -> dict:
    outcome = single_trade_outcome(decision, data, account_settings, outcome_cache) or {}
    pnl = safe_float(outcome.get("pnl_dollars"))
    return {
        "replay_date": decision.get("replay_date", ""),
        "overlay_name": overlay["overlay_name"],
        "ticker": decision.get("ticker", ""),
        "theme": ticker_theme_subtheme(str(decision.get("ticker", "")))[0],
        "reference_price": decision.get("reference_price", pd.NA),
        "baseline_candidate35_action": HISTORICAL_BUY_CANDIDATE,
        "overlay_action": HISTORICAL_NO_TRADE,
        "skip_reason": reason,
        "pre_entry_features_used": pre_entry_features(decision),
        "forward_return_20d": decision.get("forward_return_20d", pd.NA),
        "simulated_pnl_if_taken_with_baseline_exit": outcome.get("pnl_dollars", pd.NA),
        "whether_skip_avoided_loss": bool(pnl < 0) if pd.notna(pnl) else pd.NA,
        "whether_skip_missed_win": bool(pnl > 0) if pd.notna(pnl) else pd.NA,
        "whether_skip_missed_large_win": bool(pnl > 5.0) if pd.notna(pnl) else pd.NA,
    }


def evaluate_policy(
    sample_id: int,
    replay_rounds: int,
    policy_name: str,
    decisions: pd.DataFrame,
    data: pd.DataFrame,
    account_settings: AccountSettings,
    counterfactuals: pd.DataFrame,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    trades = simulate_phase1c_policy_trades(decisions, data, account_settings, BASELINE_POLICY)
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    buys = decisions.loc[decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)].copy() if not decisions.empty else pd.DataFrame()
    wins = executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    losses = executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    top_profit_share, top_loss_share = ticker_profit_loss_shares(executed)
    theme_profit_share, theme_loss_share = theme_concentration_shares(executed)
    excluded = counterfactuals.copy() if counterfactuals is not None and not counterfactuals.empty else pd.DataFrame()
    excluded_pnl = pd.to_numeric(excluded.get("simulated_pnl_if_taken_with_baseline_exit", pd.Series(dtype=float)), errors="coerce") if not excluded.empty else pd.Series(dtype=float)
    metric = {
        "sample_id": sample_id,
        "policy_name": policy_name,
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
        "number_of_trades_excluded_by_overlay": int(len(excluded)),
        "excluded_loser_count": int((excluded_pnl < 0).sum()) if not excluded_pnl.empty else 0,
        "excluded_winner_count": int((excluded_pnl > 0).sum()) if not excluded_pnl.empty else 0,
        "excluded_loser_dollars_avoided": float(abs(excluded_pnl[excluded_pnl < 0].sum())) if not excluded_pnl.empty else 0.0,
        "excluded_winner_dollars_missed": float(excluded_pnl[excluded_pnl > 0].sum()) if not excluded_pnl.empty else 0.0,
        "overlay_false_positive_rate": float((excluded_pnl > 0).mean()) if not excluded_pnl.empty else 0.0,
        "overlay_false_negative_rate": float((executed["pnl_dollars"] < 0).mean()) if not executed.empty else 0.0,
        "ending_value_excluding_best_trade": ending_excluding_best_trade(executed, account_settings.starting_capital),
    }
    return metric, executed, excluded


def build_phase1h_comparison(metrics: pd.DataFrame, split: dict) -> pd.DataFrame:
    rows = []
    if metrics.empty:
        return pd.DataFrame()
    for (policy, split_value), group in metrics.groupby(["policy_name", "split_name"]):
        rows.append(aggregate_policy_group(policy, split_value, group, holdout=False))
    return pd.DataFrame(rows)


def build_phase1h_holdout_results(holdout: pd.DataFrame, counterfactuals: pd.DataFrame, preflight: pd.DataFrame, replay_sample_count: int) -> pd.DataFrame:
    if holdout.empty:
        return pd.DataFrame()
    rows = []
    full_sample = replay_sample_count >= 30
    preflight_blocked = has_material_preflight_blocker(preflight)
    for policy, group in holdout.groupby("policy_name"):
        failed = phase1h_failed_gates(group, full_sample, preflight_blocked, counterfactuals, policy)
        row = aggregate_policy_group(policy, "holdout", group, holdout=True)
        row["holdout_gate_pass"] = not failed
        row["failed_gates"] = ";".join(failed)
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate_policy_group(policy: str, split_value: str, group: pd.DataFrame, holdout: bool) -> dict:
    return {
        "policy_name": policy,
        "split_name": split_value,
        "sample_count": int(group["sample_id"].nunique()),
        "total_buy_count": int(group["buy_count"].sum()),
        "median_buy_count": float(group["buy_count"].median()),
        "minimum_buy_count": int(group["buy_count"].min()),
        "median_no_trade_count": float(group["no_trade_count"].median()),
        "median_buy_rate": median(group["buy_rate"]),
        "worst_sample_ending_value": min_or_na(group["ending_account_value"]),
        "median_ending_account_value": median(group["ending_account_value"]),
        "worst_max_drawdown": min_or_na(group["max_drawdown"]),
        "median_simulated_win_rate": median(group["simulated_win_rate"]),
        "median_accuracy_1d": median(group["accuracy_1d"]),
        "median_accuracy_3d": median(group["accuracy_3d"]),
        "median_accuracy_5d": median(group["accuracy_5d"]),
        "median_accuracy_10d": median(group["accuracy_10d"]),
        "median_accuracy_20d": median(group["accuracy_20d"]),
        "median_profit_factor": median(group["profit_factor"]),
        "worst_trade_loss_percent": min_or_na(group["worst_trade_loss_percent"]),
        "max_top_ticker_loss_share": max_or_na(group["top_loss_ticker_contribution_share"]),
        "max_top_theme_loss_share": max_or_na(group["top_loss_theme_contribution_share"]),
        "median_ending_value_excluding_best_trade": median(group["ending_value_excluding_best_trade"]),
        "total_excluded_trades": int(group["number_of_trades_excluded_by_overlay"].sum()),
        "total_excluded_loser_count": int(group["excluded_loser_count"].sum()),
        "total_excluded_winner_count": int(group["excluded_winner_count"].sum()),
        "excluded_loser_dollars_avoided": float(group["excluded_loser_dollars_avoided"].sum()),
        "excluded_winner_dollars_missed": float(group["excluded_winner_dollars_missed"].sum()),
        "median_overlay_false_positive_rate": median(group["overlay_false_positive_rate"]),
        "median_overlay_false_negative_rate": median(group["overlay_false_negative_rate"]),
    }


def phase1h_failed_gates(group: pd.DataFrame, full_sample: bool, preflight_blocked: bool, counterfactuals: pd.DataFrame, policy_name: str) -> list[str]:
    failed = []
    if not full_sample:
        failed.append("full_30_sample_run_not_completed")
    if group["buy_count"].min() < 30:
        failed.append("min_holdout_buy_count_lt_30")
    if median(group["buy_count"]) < 45:
        failed.append("median_holdout_buy_count_lt_45")
    if min_or_na(group["ending_account_value"]) <= 110:
        failed.append("worst_ending_lte_110")
    if median(group["ending_account_value"]) <= 130:
        failed.append("median_ending_lte_130")
    if min_or_na(group["max_drawdown"]) <= -0.35:
        failed.append("worst_drawdown_lte_minus_35")
    if median(group["simulated_win_rate"]) < 0.52:
        failed.append("median_win_rate_lt_52")
    if median(group["accuracy_20d"]) < 0.58:
        failed.append("median_20d_accuracy_lt_58")
    if median(group["profit_factor"]) < 1.30:
        failed.append("median_profit_factor_lt_130")
    if min_or_na(group["worst_trade_loss_percent"]) <= -0.15:
        failed.append("worst_trade_loss_lte_minus_15")
    ticker_loss_share = max_or_na(group["top_loss_ticker_contribution_share"])
    theme_loss_share = max_or_na(group["top_loss_theme_contribution_share"])
    if pd.notna(ticker_loss_share) and ticker_loss_share > 0.35:
        failed.append("top_ticker_loss_share_gt_35")
    if pd.notna(theme_loss_share) and theme_loss_share > 0.45:
        failed.append("top_theme_loss_share_gt_45")
    if median(group["ending_value_excluding_best_trade"]) <= 115:
        failed.append("median_ex_best_lte_115")
    if preflight_blocked:
        failed.append("data_preflight_blocked")
    if policy_name not in PHASE1H_BASELINES:
        policy_counter = counterfactuals.loc[counterfactuals["overlay_name"].eq(policy_name)] if not counterfactuals.empty and "overlay_name" in counterfactuals.columns else pd.DataFrame()
        pnl = pd.to_numeric(policy_counter.get("simulated_pnl_if_taken_with_baseline_exit", pd.Series(dtype=float)), errors="coerce")
        avoided = abs(pnl[pnl < 0].sum()) if not pnl.empty else 0.0
        missed = pnl[pnl > 0].sum() if not pnl.empty else 0.0
        if avoided <= missed:
            failed.append("excluded_winners_missed_gte_losers_avoided")
    return failed


def promote_overlays(metrics: pd.DataFrame, max_count: int) -> list[str]:
    if metrics.empty:
        return []
    overlay_metrics = metrics.loc[~metrics["policy_name"].isin(PHASE1H_BASELINES)].copy()
    if overlay_metrics.empty:
        return []
    comparison = build_phase1h_comparison(overlay_metrics, {})
    comparison["overfilter"] = comparison["minimum_buy_count"] < 30
    ranked = comparison.loc[~comparison["overfilter"]].sort_values(
        ["worst_max_drawdown", "median_ending_account_value", "median_accuracy_20d", "excluded_loser_dollars_avoided"],
        ascending=[False, False, False, False],
    )
    return ranked["policy_name"].head(max_count).tolist()


def build_combined_overlay(calibration: pd.DataFrame, promoted: list[str]) -> dict | None:
    if len(promoted) < 2:
        return None
    children = [overlay for overlay in overlay_definitions() if overlay["overlay_name"] in promoted[:2]]
    if len(children) < 2:
        return None
    return {"overlay_name": "overlay_combined_conservative", "kind": "combined", "children": children, "description": "Combined conservative overlay from the top two calibration overlays."}


def phase1h_status(holdout: pd.DataFrame, preflight: pd.DataFrame, replay_sample_count: int) -> str:
    if has_material_preflight_blocker(preflight):
        return PHASE_1H_DATA_BLOCKED
    if replay_sample_count < 30:
        return PHASE_1H_INSUFFICIENT_SAMPLE_WARNING
    if holdout.empty or not holdout["policy_name"].isin([name for name in holdout["policy_name"] if name not in PHASE1H_BASELINES]).any():
        return PHASE_1H_NO_OVERLAY_SURVIVED_VALIDATION
    overlays = holdout.loc[~holdout["policy_name"].isin(PHASE1H_BASELINES)]
    if overlays.empty:
        return PHASE_1H_NO_OVERLAY_SURVIVED_VALIDATION
    if overlays["minimum_buy_count"].min() < 30 or overlays["median_buy_count"].max() < 45:
        return PHASE_1H_OVERFILTERED
    if overlays["holdout_gate_pass"].any():
        return PHASE_1H_RISK_OVERLAY_PROMISING_FOR_GPT_REVIEW
    return PHASE_1H_HOLDOUT_FAILED


def drawdown_attribution(sample_id: int, policy_name: str, trades: pd.DataFrame, counterfactuals: pd.DataFrame) -> pd.DataFrame:
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    if executed.empty:
        return pd.DataFrame([empty_drawdown_row(sample_id, policy_name)])
    executed["equity"] = 100.0 + executed["pnl_dollars"].cumsum()
    executed["peak"] = executed["equity"].cummax()
    executed["drawdown"] = executed["equity"] / executed["peak"] - 1.0
    worst_idx = executed["drawdown"].idxmin()
    worst = executed.loc[worst_idx]
    start_rows = executed.loc[:worst_idx]
    start = start_rows.loc[start_rows["equity"].eq(start_rows["peak"].max())].tail(1)
    start_date = start["replay_date"].iloc[0] if not start.empty else executed["replay_date"].iloc[0]
    episode = executed.loc[(pd.to_datetime(executed["replay_date"]) >= pd.Timestamp(start_date)) & (pd.to_datetime(executed["replay_date"]) <= pd.Timestamp(worst["replay_date"]))]
    excluded_tickers = set(counterfactuals.get("ticker", pd.Series(dtype=str)).astype(str)) if counterfactuals is not None and not counterfactuals.empty else set()
    return pd.DataFrame(
        [
            {
                "sample_id": sample_id,
                "policy_name": policy_name,
                "drawdown_start_replay_date": start_date,
                "drawdown_end_replay_date": worst["replay_date"],
                "drawdown_depth": float(worst["drawdown"]),
                "number_of_trades_in_drawdown": int(len(episode)),
                "tickers_in_drawdown": ",".join(sorted(set(episode["ticker"].astype(str)))),
                "themes_in_drawdown": ",".join(sorted(set(episode["ticker"].apply(lambda ticker: ticker_theme_subtheme(str(ticker))[0])))),
                "worst_trade_in_drawdown": f"{worst['replay_date']} {worst['ticker']} pnl={float(worst['pnl_dollars']):.2f}",
                "whether_overlay_excluded_worst_trade": bool(str(worst["ticker"]) in excluded_tickers),
                "whether_overlay_reduced_drawdown": pd.NA,
                "whether_overlay_delayed_or_shifted_drawdown": pd.NA,
            }
        ]
    )


def theme_concentration_audit(sample_id: int, policy_name: str, trades: pd.DataFrame, baseline: pd.DataFrame | None, overlay: pd.DataFrame | None) -> pd.DataFrame:
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    if executed.empty:
        return pd.DataFrame()
    executed["theme"] = executed["ticker"].apply(lambda ticker: ticker_theme_subtheme(str(ticker))[0])
    total_losses = abs(executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"].sum())
    total_profits = executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"].sum()
    rows = []
    for theme, group in executed.groupby("theme"):
        losses = abs(group.loc[group["pnl_dollars"] < 0, "pnl_dollars"].sum())
        profits = group.loc[group["pnl_dollars"] > 0, "pnl_dollars"].sum()
        losing = group.loc[group["pnl_dollars"] < 0].copy()
        largest = losing.loc[losing["pnl_dollars"].idxmin()] if not losing.empty else pd.Series(dtype=object)
        rows.append(
            {
                "sample_id": sample_id,
                "policy_name": policy_name,
                "theme": theme,
                "theme_buy_count": int(len(group)),
                "theme_total_pnl": float(group["pnl_dollars"].sum()),
                "theme_loss_share": float(losses / total_losses) if total_losses > 0 else pd.NA,
                "theme_profit_share": float(profits / total_profits) if total_profits > 0 else pd.NA,
                "largest_losing_ticker_in_theme": largest.get("ticker", ""),
                "largest_losing_trade_date": largest.get("replay_date", ""),
                "overlay_effect_on_theme_buy_count": pd.NA,
                "overlay_effect_on_theme_pnl": pd.NA,
            }
        )
    return pd.DataFrame(rows)


def build_index_feature_lookup(data: pd.DataFrame) -> dict:
    frame = data.loc[data["ticker"].isin(["SPY", "QQQ"])].copy()
    if frame.empty:
        return {}
    frame["date"] = pd.to_datetime(frame["date"])
    rows = {}
    for ticker, group in frame.groupby("ticker"):
        group = group.sort_values("date").copy()
        close = pd.to_numeric(group["close"], errors="coerce")
        group["sma50_idx"] = close.rolling(50, min_periods=20).mean()
        group["sma200_idx"] = close.rolling(200, min_periods=50).mean()
        group["ret20_idx"] = close.pct_change(20, fill_method=None)
        group["vol20_idx"] = close.pct_change(fill_method=None).rolling(20, min_periods=10).std()
        prefix = ticker.lower()
        for _, row in group.iterrows():
            key = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
            rows.setdefault(key, {})
            rows[key][f"{prefix}_below_50_200"] = bool(row["close"] < row["sma50_idx"] and row["close"] < row["sma200_idx"])
            rows[key][f"{prefix}_return_20d"] = safe_float(row["ret20_idx"])
            rows[key][f"{prefix}_volatility_20d"] = safe_float(row["vol20_idx"])
    return rows


def has_material_preflight_blocker(preflight: pd.DataFrame) -> bool:
    if preflight.empty:
        return True
    market = preflight.loc[preflight["symbol"].isin(["SPY", "QQQ"])]
    return bool(market.empty or market["bar_count"].min() <= 0 or market["warnings"].astype(str).str.contains("material_blocker").any())


def phase1h_summary_markdown(summary: dict, calibration: pd.DataFrame, validation: pd.DataFrame, holdout: pd.DataFrame, comparison: pd.DataFrame, drawdown: pd.DataFrame, theme_audit: pd.DataFrame, counterfactuals: pd.DataFrame) -> str:
    lines = [
        "PHOENIX NANO PHASE 1H — TREND-QUALITY RISK OVERLAY AND DRAWDOWN COMPRESSION",
        "",
        "Research-only. No overlay is approved for daily scan, paper execution, or real-money execution.",
        "",
        "## Phase 1G Recap",
        "",
        "- Phase 1G ended as PHASE_1G_HOLDOUT_FAILED.",
        "- Candidate 35 trend-quality improved several metrics but failed drawdown, win-rate, and theme concentration gates.",
        "",
        "## Frozen Baseline Reproducibility Check",
        "",
        "- Candidate 34 frozen baseline is re-run without rule changes.",
        "- Candidate 35 trend-quality core rules, ranking, and baseline exit policy are frozen from Phase 1G.",
        "",
        "## Overlay Definitions Summary",
        "",
        "- overlay_market_regime_risk_off_skip",
        "- overlay_high_volatility_tail_skip",
        "- overlay_theme_loss_cooldown parameter grid",
        "- overlay_ticker_loss_cooldown parameter grid",
        "- overlay_combined_conservative when calibration supports it",
        "",
        "## Calibration Results",
        "",
        compact_table(calibration),
        "",
        "## Validation Results",
        "",
        compact_table(validation),
        "",
        "## Holdout Results",
        "",
        holdout.to_markdown(index=False) if not holdout.empty else "No holdout rows.",
        "",
        "## Candidate 34 vs Candidate 35 vs Overlay Comparison",
        "",
        comparison.to_markdown(index=False) if not comparison.empty else "No comparison rows.",
        "",
        "## Drawdown Compression Attribution",
        "",
        drawdown.head(40).to_markdown(index=False) if not drawdown.empty else "No drawdown rows.",
        "",
        "Drawdown changes are interpreted as true risk reduction only when excluded-loss dollars exceed missed-winner dollars and BUY counts remain above gates.",
        "",
        "## Theme Concentration Audit",
        "",
        theme_audit.head(40).to_markdown(index=False) if not theme_audit.empty else "No theme audit rows.",
        "",
        "## Excluded Trade Counterfactual Summary",
        "",
        counterfactual_summary(counterfactuals),
        "",
        "## Improvement Source Assessment",
        "",
        "Any improvement is treated as unapproved unless holdout gates show drawdown compression without overfiltering and without missing more winner dollars than loser dollars avoided.",
        "",
        f"## Final Phase 1H Status: {summary['phase_1h_status']}",
        "",
        "Do not start paper execution or real-money execution.",
        "",
        "## Next Research Task Recommendation",
        "",
        "Ask GPT to decide whether to pause Phoenix Nano, improve data/universe quality, or authorize another narrow research-only overlay iteration.",
        "",
    ]
    return "\n".join(lines)


def write_phase1h_reports(
    definitions_md: str,
    calibration: pd.DataFrame,
    validation: pd.DataFrame,
    holdout: pd.DataFrame,
    comparison: pd.DataFrame,
    drawdown: pd.DataFrame,
    theme_audit: pd.DataFrame,
    counterfactuals: pd.DataFrame,
    summary_md: str,
    definitions_md_path: str | Path,
    calibration_csv_path: str | Path,
    validation_csv_path: str | Path,
    holdout_csv_path: str | Path,
    comparison_csv_path: str | Path,
    drawdown_csv_path: str | Path,
    theme_csv_path: str | Path,
    counterfactual_csv_path: str | Path,
    summary_md_path: str | Path,
) -> None:
    paths = [definitions_md_path, calibration_csv_path, validation_csv_path, holdout_csv_path, comparison_csv_path, drawdown_csv_path, theme_csv_path, counterfactual_csv_path, summary_md_path]
    for path in paths:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(definitions_md_path).write_text(definitions_md, encoding="utf-8")
    calibration.to_csv(calibration_csv_path, index=False)
    validation.to_csv(validation_csv_path, index=False)
    holdout.to_csv(holdout_csv_path, index=False)
    comparison.to_csv(comparison_csv_path, index=False)
    drawdown.to_csv(drawdown_csv_path, index=False)
    theme_audit.to_csv(theme_csv_path, index=False)
    counterfactuals.to_csv(counterfactual_csv_path, index=False)
    Path(summary_md_path).write_text(summary_md, encoding="utf-8")


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


def counterfactual_summary(counterfactuals: pd.DataFrame) -> str:
    if counterfactuals.empty:
        return "- No overlay exclusions."
    pnl = pd.to_numeric(counterfactuals["simulated_pnl_if_taken_with_baseline_exit"], errors="coerce")
    avoided = abs(pnl[pnl < 0].sum())
    missed = pnl[pnl > 0].sum()
    return "\n".join(
        [
            f"- Excluded trade rows: {len(counterfactuals)}",
            f"- Excluded loser dollars avoided: {avoided:.2f}",
            f"- Excluded winner dollars missed: {missed:.2f}",
            f"- Excluded loser count: {(pnl < 0).sum()}",
            f"- Excluded winner count: {(pnl > 0).sum()}",
        ]
    )


def compact_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = ["sample_id", "policy_name", "buy_count", "ending_account_value", "max_drawdown", "simulated_win_rate", "accuracy_20d", "profit_factor", "number_of_trades_excluded_by_overlay"]
    return frame[cols].sort_values(["policy_name", "sample_id"]).head(80).to_markdown(index=False)


def pre_entry_features(decision: pd.Series) -> str:
    fields = ["regime_label", "volatility_20d", "atr_pct", "gap_pct", "return_5d", "return_20d", "distance_to_52w_high_prev", "smoke_score"]
    return ";".join(f"{field}={decision.get(field, pd.NA)}" for field in fields)


def empty_drawdown_row(sample_id: int, policy_name: str) -> dict:
    return {
        "sample_id": sample_id,
        "policy_name": policy_name,
        "drawdown_start_replay_date": "",
        "drawdown_end_replay_date": "",
        "drawdown_depth": pd.NA,
        "number_of_trades_in_drawdown": 0,
        "tickers_in_drawdown": "",
        "themes_in_drawdown": "",
        "worst_trade_in_drawdown": "",
        "whether_overlay_excluded_worst_trade": pd.NA,
        "whether_overlay_reduced_drawdown": pd.NA,
        "whether_overlay_delayed_or_shifted_drawdown": pd.NA,
    }


def best_policy(holdout: pd.DataFrame) -> str:
    if holdout.empty:
        return ""
    ranked = holdout.sort_values(["holdout_gate_pass", "median_ending_account_value", "worst_max_drawdown"], ascending=[False, False, False])
    return str(ranked.iloc[0]["policy_name"])


def safe_float(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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
