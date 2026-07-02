from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED
from src.research.auto_loop import CandidateRule
from src.research.historical_replay import FORWARD_WINDOWS, HISTORICAL_BUY_CANDIDATE, build_phase1_historical_replay
from src.research.phase1c_robustness import (
    THEME_MAP,
    max_drawdown,
    policy_matrix_row,
    simulate_phase1c_policy_trades,
    ticker_profit_loss_shares,
)


PHASE_1D_FAILED = "PHASE_1D_FAILED"
PHASE_1D_ENTRY_FILTER_NEEDS_MORE_WORK = "PHASE_1D_ENTRY_FILTER_NEEDS_MORE_WORK"
PHASE_1D_FILTER_HYPOTHESIS_PROMISING_NOT_APPROVED = "PHASE_1D_FILTER_HYPOTHESIS_PROMISING_NOT_APPROVED"
PHASE_1D_ROBUSTNESS_IMPROVED_BUT_REQUIRES_GPT_REVIEW = "PHASE_1D_ROBUSTNESS_IMPROVED_BUT_REQUIRES_GPT_REVIEW"

BASELINE_POLICY = {"policy": "baseline_current", "atr_multiple": 1.5, "mode": "intraday"}

ATTRIBUTION_FEATURES = [
    "atr_pct",
    "volatility_20d",
    "entry_gap_pct",
    "decision_strength",
    "smoke_score",
    "relative_volume_prev20",
    "distance_from_20d_high_pct",
    "distance_from_52w_high_pct",
    "return_1d_prior",
    "return_5d_prior",
    "return_10d_prior",
    "return_20d_prior",
    "max_single_day_loss_20d",
    "near_max_entry_price_pct",
]


def build_phase1d_entry_rule_analysis(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_rounds: int = 100,
    replay_sample_count: int = 10,
    replay_sample_offset: int = 0,
    benchmark_ticker: str = "SPY",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, dict]:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["date", "ticker"]).reset_index(drop=True)

    diagnostics_frames: list[pd.DataFrame] = []
    decision_frames: list[pd.DataFrame] = []
    phase1_summaries: dict[int, dict] = {}

    for sample_index in range(replay_sample_count):
        sample_id = replay_sample_offset + sample_index
        decisions, _, phase1_summary = build_phase1_historical_replay(
            frame,
            account_settings,
            rule,
            replay_rounds=replay_rounds,
            benchmark_ticker=benchmark_ticker,
            replay_sample_offset=sample_id,
        )
        decisions["sample_id"] = sample_id
        baseline_trades = simulate_phase1c_policy_trades(decisions, frame, account_settings, BASELINE_POLICY)
        diagnostics_frames.append(build_entry_rule_diagnostics(sample_id, decisions, baseline_trades, frame, rule))
        decision_frames.append(decisions)
        phase1_summaries[sample_id] = phase1_summary

    diagnostics = pd.concat(diagnostics_frames, ignore_index=True) if diagnostics_frames else pd.DataFrame()
    decisions_all = pd.concat(decision_frames, ignore_index=True) if decision_frames else pd.DataFrame()
    attribution = build_loser_feature_attribution(diagnostics)
    filters = candidate_filters_from_diagnostics(diagnostics, rule)
    matrix, excluded = build_filter_backtest_matrix(
        diagnostics,
        decisions_all,
        frame,
        account_settings,
        filters,
        replay_rounds,
        phase1_summaries,
    )
    summary = summarize_phase1d(diagnostics, attribution, matrix, excluded, filters)
    candidate_filter_md = candidate_filter_markdown(filters, diagnostics, matrix, excluded)
    return diagnostics, attribution, matrix, excluded, candidate_filter_md, summary


def build_entry_rule_diagnostics(
    sample_id: int,
    decisions: pd.DataFrame,
    baseline_trades: pd.DataFrame,
    data: pd.DataFrame,
    rule: CandidateRule,
) -> pd.DataFrame:
    buys = decisions.loc[decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)].copy()
    if buys.empty:
        return pd.DataFrame(columns=diagnostic_columns())
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    by_ticker = {ticker: group.sort_values("date").reset_index(drop=True) for ticker, group in frame.groupby("ticker")}
    trades = baseline_trades.set_index(["replay_date", "ticker"]) if not baseline_trades.empty else pd.DataFrame()
    rows = []
    for _, decision in buys.sort_values(["replay_date", "ticker"]).iterrows():
        replay_date = pd.Timestamp(decision["replay_date"])
        ticker = str(decision["ticker"])
        history = by_ticker.get(ticker, pd.DataFrame())
        history = history.loc[history["date"].le(replay_date)].copy() if not history.empty else history
        signal = history.tail(1).iloc[0] if not history.empty else pd.Series(dtype=object)
        trade = _trade_for_decision(trades, decision)
        entry_price = _num(trade.get("entry_price", decision.get("reference_price")))
        reference_price = _num(decision.get("reference_price"))
        atr = _num(signal.get("atr"))
        stop_loss = _num(trade.get("stop_loss", entry_price - 1.5 * atr if pd.notna(atr) else pd.NA))
        target_1 = _num(trade.get("target_1", pd.NA))
        target_2 = _num(trade.get("target_2", pd.NA))
        max_entry = _num(getattr(rule, "max_entry_price", pd.NA))
        row = {
            "sample_id": sample_id,
            "replay_date": replay_date.strftime("%Y-%m-%d"),
            "ticker": ticker,
            "entry_date": _date_string(trade.get("entry_date", "")),
            "reference_price": reference_price,
            "entry_price": entry_price,
            "entry_gap_pct": entry_price / reference_price - 1.0 if pd.notna(entry_price) and pd.notna(reference_price) and reference_price else pd.NA,
            "shares_with_100": decision.get("shares_with_cash", pd.NA),
            "estimated_total_cost": decision.get("estimated_total_cost", pd.NA),
            "estimated_cash_remaining": decision.get("estimated_cash_remaining", pd.NA),
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "stop_distance_pct": stop_loss / entry_price - 1.0 if pd.notna(stop_loss) and pd.notna(entry_price) and entry_price else pd.NA,
            "target_1_distance_pct": target_1 / entry_price - 1.0 if pd.notna(target_1) and pd.notna(entry_price) and entry_price else pd.NA,
            "target_2_distance_pct": target_2 / entry_price - 1.0 if pd.notna(target_2) and pd.notna(entry_price) and entry_price else pd.NA,
            "max_dollar_risk": (entry_price - stop_loss) * _num(decision.get("shares_with_cash", 0)) if pd.notna(entry_price) and pd.notna(stop_loss) else pd.NA,
            "decision_strength": decision.get("decision_strength", pd.NA),
            "smoke_score": decision.get("smoke_score", pd.NA),
            "failed_checks_at_selection": decision.get("failed_checks", ""),
            "sector_or_theme": THEME_MAP.get(ticker, ""),
            "latest_volume": signal.get("volume", pd.NA),
            "dollar_volume": decision.get("dollar_volume", signal.get("dollar_volume", pd.NA)),
            "relative_volume_prev20": decision.get("relative_volume_prev20", signal.get("relative_volume_prev20", pd.NA)),
            "atr_14": atr,
            "atr_pct": atr / _num(signal.get("close")) if pd.notna(atr) and pd.notna(_num(signal.get("close"))) and _num(signal.get("close")) else pd.NA,
            "close_vs_sma20_pct": close_vs_sma(history, 20),
            "close_vs_sma50_pct": close_vs_sma(history, 50),
            "distance_from_20d_high_pct": distance_from_high(history, 20),
            "distance_from_52w_high_pct": decision.get("distance_to_52w_high_prev", distance_from_high(history, 252)),
            "return_1d_prior": trailing_return(history, 1),
            "return_5d_prior": decision.get("return_5d", trailing_return(history, 5)),
            "return_10d_prior": trailing_return(history, 10),
            "return_20d_prior": decision.get("return_20d", trailing_return(history, 20)),
            "volatility_20d": volatility_20d(history),
            "max_single_day_loss_20d": max_single_day_loss_20d(history),
            "near_max_entry_price_pct": entry_price / max_entry if pd.notna(entry_price) and pd.notna(max_entry) and max_entry else pd.NA,
        }
        for window in FORWARD_WINDOWS:
            row[f"forward_return_{window}d"] = decision.get(f"forward_return_{window}d", pd.NA)
        row.update(
            {
                "baseline_exit_reason": trade.get("exit_reason", ""),
                "baseline_pnl_dollars": trade.get("pnl_dollars", pd.NA),
                "baseline_trade_return_pct": trade.get("trade_return_pct", pd.NA),
                "baseline_account_return_pct": trade.get("account_return_pct", pd.NA),
                "stopped_out_then_20d_positive": bool(trade.get("exit_reason", "") == "STOP" and _gt_zero(decision.get("forward_return_20d"))),
                "intraday_stop_breached": bool(trade.get("intraday_stop_breached", False)),
                "winner_20d": _gt_zero(decision.get("forward_return_20d")),
                "winner_baseline_simulation": _gt_zero(trade.get("pnl_dollars")),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows, columns=diagnostic_columns())


def build_loser_feature_attribution(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if diagnostics.empty:
        return pd.DataFrame()
    sample_ids: list[object] = ["ALL", *sorted(diagnostics["sample_id"].dropna().unique())]
    for sample_id in sample_ids:
        subset = diagnostics if sample_id == "ALL" else diagnostics.loc[diagnostics["sample_id"].eq(sample_id)]
        winners = subset.loc[subset["winner_baseline_simulation"].astype(bool)]
        losers = subset.loc[~subset["winner_baseline_simulation"].astype(bool)]
        for feature in ATTRIBUTION_FEATURES:
            winner_values = pd.to_numeric(winners.get(feature, pd.Series(dtype=float)), errors="coerce").dropna()
            loser_values = pd.to_numeric(losers.get(feature, pd.Series(dtype=float)), errors="coerce").dropna()
            missing_rate = float(pd.to_numeric(subset.get(feature, pd.Series(dtype=float)), errors="coerce").isna().mean()) if len(subset) else 0.0
            winner_mean = _mean(winner_values)
            loser_mean = _mean(loser_values)
            winner_median = _median(winner_values)
            loser_median = _median(loser_values)
            pooled_std = pd.to_numeric(subset.get(feature, pd.Series(dtype=float)), errors="coerce").std()
            separation = (
                abs(float(loser_mean) - float(winner_mean)) / float(pooled_std)
                if pd.notna(loser_mean) and pd.notna(winner_mean) and pd.notna(pooled_std) and float(pooled_std) > 0
                else 0.0
            )
            rows.append(
                {
                    "feature_name": feature,
                    "sample_id": sample_id,
                    "winner_count": int(len(winner_values)),
                    "loser_count": int(len(loser_values)),
                    "winner_mean": winner_mean,
                    "loser_mean": loser_mean,
                    "winner_median": winner_median,
                    "loser_median": loser_median,
                    "loser_minus_winner_mean": _diff(loser_mean, winner_mean),
                    "loser_minus_winner_median": _diff(loser_median, winner_median),
                    "simple_separation_score": separation,
                    "missing_rate": missing_rate,
                    "notes": attribution_note(feature, loser_mean, winner_mean),
                }
            )
    return pd.DataFrame(rows)


def candidate_filters_from_diagnostics(diagnostics: pd.DataFrame, rule: CandidateRule) -> list[dict]:
    losers = diagnostics.loc[~diagnostics["winner_baseline_simulation"].astype(bool)] if not diagnostics.empty else pd.DataFrame()

    def q(column: str, quantile: float, default: float) -> float:
        if column == "entry_gap_pct_abs":
            source = pd.to_numeric(losers.get("entry_gap_pct", pd.Series(dtype=float)), errors="coerce").abs().dropna()
        else:
            source = pd.to_numeric(losers.get(column, pd.Series(dtype=float)), errors="coerce").dropna()
        if source.empty:
            if column == "entry_gap_pct_abs":
                source = pd.to_numeric(diagnostics.get("entry_gap_pct", pd.Series(dtype=float)), errors="coerce").abs().dropna()
            else:
                source = pd.to_numeric(diagnostics.get(column, pd.Series(dtype=float)), errors="coerce").dropna()
        return float(source.quantile(quantile)) if not source.empty else default

    max_entry_price = float(getattr(rule, "max_entry_price", 50.0) or 50.0)
    filters = [
        _filter("high_atr_pct", f"Exclude atr_pct above {q('atr_pct', 0.75, 0.08):.4f}", "atr_pct", "le", q("atr_pct", 0.75, 0.08)),
        _filter("high_volatility_20d", f"Exclude volatility_20d above {q('volatility_20d', 0.75, 0.06):.4f}", "volatility_20d", "le", q("volatility_20d", 0.75, 0.06)),
        _filter("extreme_entry_gap_pct", f"Exclude absolute entry_gap_pct above {q('entry_gap_pct_abs', 0.75, 0.04):.4f}", "entry_gap_pct", "abs_le", q("entry_gap_pct_abs", 0.75, 0.04)),
        _filter("minimum_decision_strength", f"Require decision_strength >= {max(float(getattr(rule, 'min_rank_gap', 0.0)), q('decision_strength', 0.25, 0.02)):.4f}", "decision_strength", "ge", q("decision_strength", 0.25, 0.02)),
        _filter("minimum_smoke_score", f"Require smoke_score >= {max(float(getattr(rule, 'min_smoke_score', 0.0)), q('smoke_score', 0.25, 0.5)):.4f}", "smoke_score", "ge", max(float(getattr(rule, "min_smoke_score", 0.0)), q("smoke_score", 0.25, 0.5))),
        _filter("low_relative_volume_prev20", f"Require relative_volume_prev20 >= {max(float(getattr(rule, 'min_relative_volume_prev20', 0.0)), q('relative_volume_prev20', 0.25, 1.0)):.4f}", "relative_volume_prev20", "ge", max(float(getattr(rule, "min_relative_volume_prev20", 0.0)), q("relative_volume_prev20", 0.25, 1.0))),
        _filter("weak_distance_from_high", f"Require distance_from_52w_high_pct >= {q('distance_from_52w_high_pct', 0.25, -0.35):.4f}", "distance_from_52w_high_pct", "ge", q("distance_from_52w_high_pct", 0.25, -0.35)),
        _filter("extreme_short_term_runup", f"Exclude return_5d_prior above {q('return_5d_prior', 0.75, 0.20):.4f}", "return_5d_prior", "le", q("return_5d_prior", 0.75, 0.20)),
        {"filter_name": "theme_concentration_cap", "filter_description": "Within each sample, allow at most 3 entries per deterministic local theme.", "kind": "theme_cap", "cap": 3},
        {"filter_name": "repeated_loser_ticker_cooldown", "filter_description": "Within each sample, skip a ticker after its prior baseline losing BUY.", "kind": "ticker_cooldown"},
    ]
    filters.extend(
        [
            {"filter_name": "atr_plus_decision_strength", "filter_description": "Combination: high_atr_pct plus minimum_decision_strength.", "kind": "combo", "members": ["high_atr_pct", "minimum_decision_strength"]},
            {"filter_name": "volatility_plus_smoke_score", "filter_description": "Combination: high_volatility_20d plus minimum_smoke_score.", "kind": "combo", "members": ["high_volatility_20d", "minimum_smoke_score"]},
            {"filter_name": "risk_stack_filter", "filter_description": "Combination: high_atr_pct, high_volatility_20d, and extreme_entry_gap_pct.", "kind": "combo", "members": ["high_atr_pct", "high_volatility_20d", "extreme_entry_gap_pct"]},
        ]
    )
    return filters


def build_filter_backtest_matrix(
    diagnostics: pd.DataFrame,
    decisions: pd.DataFrame,
    data: pd.DataFrame,
    account_settings: AccountSettings,
    filters: list[dict],
    replay_rounds: int,
    phase1_summaries: dict[int, dict],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    excluded_frames = []
    sample_ids = sorted(diagnostics["sample_id"].dropna().unique()) if not diagnostics.empty else []
    for sample_id in sample_ids:
        sample_diag = diagnostics.loc[diagnostics["sample_id"].eq(sample_id)].sort_values(["replay_date", "ticker"]).copy()
        sample_decisions = decisions.loc[decisions["sample_id"].eq(sample_id)].copy()
        original_buy_count = int(len(sample_diag))
        for filter_def in filters:
            excluded = apply_candidate_filter(sample_diag, filter_def, filters)
            excluded_frames.append(excluded_decision_audit(excluded, filter_def))
            filtered_decisions = sample_decisions.loc[
                ~(
                    sample_decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)
                    & sample_decisions["replay_date"].isin(excluded["replay_date"])
                    & sample_decisions["ticker"].isin(excluded["ticker"])
                )
            ].copy()
            filtered_trades = simulate_phase1c_policy_trades(filtered_decisions, data, account_settings, BASELINE_POLICY)
            row = filter_matrix_row(
                sample_id,
                filter_def,
                replay_rounds,
                original_buy_count,
                sample_diag,
                excluded,
                filtered_trades,
                account_settings,
                phase1_summaries.get(sample_id, {}),
            )
            rows.append(row)
    matrix = pd.DataFrame(rows)
    non_empty_excluded = [frame for frame in excluded_frames if not frame.empty]
    excluded = (
        pd.concat(non_empty_excluded, ignore_index=True)
        if non_empty_excluded
        else excluded_decision_audit(pd.DataFrame(), {"filter_name": "", "filter_description": ""})
    )
    return matrix, excluded


def apply_candidate_filter(sample_diag: pd.DataFrame, filter_def: dict, all_filters: list[dict] | None = None) -> pd.DataFrame:
    if sample_diag.empty:
        return sample_diag.copy()
    kind = filter_def.get("kind", "threshold")
    if kind == "combo":
        mask = pd.Series(False, index=sample_diag.index)
        filters_by_name = {item["filter_name"]: item for item in (all_filters or [])}
        for member in filter_def["members"]:
            member_filter = filters_by_name[member]
            mask = mask | _threshold_excluded(sample_diag, member_filter)
        excluded = sample_diag.loc[mask].copy()
    elif kind == "theme_cap":
        counts: dict[str, int] = {}
        indices = []
        for index, row in sample_diag.iterrows():
            theme = str(row.get("sector_or_theme", "")) or "UNMAPPED"
            counts[theme] = counts.get(theme, 0) + 1
            if counts[theme] > int(filter_def["cap"]):
                indices.append(index)
        excluded = sample_diag.loc[indices].copy()
    elif kind == "ticker_cooldown":
        lost: set[str] = set()
        indices = []
        for index, row in sample_diag.iterrows():
            ticker = str(row["ticker"])
            if ticker in lost:
                indices.append(index)
            if not bool(row.get("winner_baseline_simulation", False)):
                lost.add(ticker)
        excluded = sample_diag.loc[indices].copy()
    else:
        excluded = sample_diag.loc[_threshold_excluded(sample_diag, filter_def)].copy()
    if not excluded.empty:
        excluded["reason_excluded"] = filter_def["filter_description"]
    return excluded


def filter_matrix_row(
    sample_id: int,
    filter_def: dict,
    replay_rounds: int,
    original_buy_count: int,
    sample_diag: pd.DataFrame,
    excluded: pd.DataFrame,
    trades: pd.DataFrame,
    account_settings: AccountSettings,
    phase1_summary: dict,
) -> dict:
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    filtered_buy_count = original_buy_count - int(len(excluded))
    summary_like = {
        **phase1_summary,
        "buy_count": filtered_buy_count,
        "no_trade_count": replay_rounds - filtered_buy_count,
    }
    base = policy_matrix_row(sample_id, replay_rounds, pd.DataFrame(), summary_like, trades, account_settings)
    top_profit_share, top_loss_share = ticker_profit_loss_shares(executed)
    row = {
        "sample_id": sample_id,
        "filter_name": filter_def["filter_name"],
        "filter_description": filter_def["filter_description"],
        "replay_rounds": replay_rounds,
        "original_buy_count": original_buy_count,
        "filtered_buy_count": filtered_buy_count,
        "excluded_decision_count": int(len(excluded)),
        "excluded_loser_count": int((~excluded.get("winner_baseline_simulation", pd.Series(dtype=bool)).astype(bool)).sum()) if not excluded.empty else 0,
        "excluded_winner_count": int(excluded.get("winner_baseline_simulation", pd.Series(dtype=bool)).astype(bool).sum()) if not excluded.empty else 0,
        "excluded_stopped_out_then_20d_positive_count": int(excluded.get("stopped_out_then_20d_positive", pd.Series(dtype=bool)).astype(bool).sum()) if not excluded.empty else 0,
        "no_trade_count_after_filter": replay_rounds - filtered_buy_count,
        "trade_simulation_accuracy": base["trade_simulation_accuracy"],
        "accuracy_1d": _positive_rate(sample_diag.loc[~sample_diag.index.isin(excluded.index), "forward_return_1d"]),
        "accuracy_3d": _positive_rate(sample_diag.loc[~sample_diag.index.isin(excluded.index), "forward_return_3d"]),
        "accuracy_5d": _positive_rate(sample_diag.loc[~sample_diag.index.isin(excluded.index), "forward_return_5d"]),
        "accuracy_10d": _positive_rate(sample_diag.loc[~sample_diag.index.isin(excluded.index), "forward_return_10d"]),
        "accuracy_20d": _positive_rate(sample_diag.loc[~sample_diag.index.isin(excluded.index), "forward_return_20d"]),
        "average_return_20d": _mean(sample_diag.loc[~sample_diag.index.isin(excluded.index), "forward_return_20d"]),
        "median_return_20d": _median(sample_diag.loc[~sample_diag.index.isin(excluded.index), "forward_return_20d"]),
        "average_win": base["average_win"],
        "average_loss": base["average_loss"],
        "profit_factor": base["profit_factor"],
        "ending_account_value": base["ending_account_value"],
        "max_drawdown": max_drawdown(executed, account_settings.starting_capital),
        "worst_trade_account_loss": base["worst_trade_account_loss"],
        "ending_value_excluding_best_decision": base["ending_value_excluding_best_trade"],
        "top_ticker_profit_share": top_profit_share,
        "top_ticker_loss_share": top_loss_share,
    }
    row["passes_phase1d_diagnostic_gate"] = passes_phase1d_diagnostic_gate(row)
    return row


def excluded_decision_audit(excluded: pd.DataFrame, filter_def: dict) -> pd.DataFrame:
    columns = [
        "sample_id",
        "filter_name",
        "replay_date",
        "ticker",
        "entry_date",
        "entry_price",
        "reference_price",
        "sector_or_theme",
        "reason_excluded",
        "decision_strength",
        "smoke_score",
        "atr_pct",
        "volatility_20d",
        "entry_gap_pct",
        "relative_volume_prev20",
        "baseline_exit_reason",
        "baseline_pnl_dollars",
        "forward_return_20d",
        "stopped_out_then_20d_positive",
        "would_have_been_winner_baseline_simulation",
        "would_have_been_winner_20d",
    ]
    if excluded.empty:
        return pd.DataFrame(columns=columns)
    audit = excluded.copy()
    audit["filter_name"] = filter_def["filter_name"]
    audit["would_have_been_winner_baseline_simulation"] = audit["winner_baseline_simulation"]
    audit["would_have_been_winner_20d"] = audit["winner_20d"]
    return audit.rename(columns={"sector_or_theme": "sector_or_theme"})[columns].copy()


def passes_phase1d_diagnostic_gate(row: dict) -> bool:
    return bool(
        float(row["ending_account_value"]) > 120.0
        and int(row["filtered_buy_count"]) >= 15
        and float(row["max_drawdown"]) > -0.35
        and not pd.isna(row["trade_simulation_accuracy"])
        and float(row["trade_simulation_accuracy"]) >= 0.50
        and float(row["ending_value_excluding_best_decision"]) > 105.0
        and (pd.isna(row["top_ticker_profit_share"]) or float(row["top_ticker_profit_share"]) <= 0.50)
        and int(row["excluded_loser_count"]) > int(row["excluded_winner_count"])
        and not pd.isna(row["average_return_20d"])
        and float(row["average_return_20d"]) > 0
    )


def phase1d_status(matrix: pd.DataFrame) -> str:
    if matrix.empty:
        return PHASE_1D_FAILED
    grouped = matrix.groupby("filter_name").agg(
        median_ending=("ending_account_value", "median"),
        worst_ending=("ending_account_value", "min"),
        median_dd=("max_drawdown", "median"),
        worst_dd=("max_drawdown", "min"),
        median_accuracy=("trade_simulation_accuracy", "median"),
        min_buy_count=("filtered_buy_count", "min"),
        median_ex_best=("ending_value_excluding_best_decision", "median"),
        max_top_profit_share=("top_ticker_profit_share", "max"),
        all_pass=("passes_phase1d_diagnostic_gate", "all"),
    )
    if grouped["all_pass"].any():
        return PHASE_1D_ROBUSTNESS_IMPROVED_BUT_REQUIRES_GPT_REVIEW
    if grouped["median_ending"].gt(120.0).any() and grouped["median_dd"].gt(-0.45).any():
        return PHASE_1D_FILTER_HYPOTHESIS_PROMISING_NOT_APPROVED
    if grouped["median_ending"].gt(100.0).any():
        return PHASE_1D_ENTRY_FILTER_NEEDS_MORE_WORK
    return PHASE_1D_FAILED


def summarize_phase1d(
    diagnostics: pd.DataFrame,
    attribution: pd.DataFrame,
    matrix: pd.DataFrame,
    excluded: pd.DataFrame,
    filters: list[dict],
) -> dict:
    best_median = _best_filter(matrix, "median", "ending_account_value")
    worst_sample = matrix.groupby("filter_name")["ending_account_value"].min().sort_values(ascending=False) if not matrix.empty else pd.Series(dtype=float)
    drawdown = matrix.groupby("filter_name")["max_drawdown"].median().sort_values(ascending=False) if not matrix.empty else pd.Series(dtype=float)
    return {
        "phase_1d_status": phase1d_status(matrix),
        "sample_count": int(diagnostics["sample_id"].nunique()) if not diagnostics.empty else 0,
        "buy_decision_count": int(len(diagnostics)),
        "filters_tested": [item["filter_name"] for item in filters],
        "best_filter_by_median_ending": best_median,
        "best_filter_by_worst_sample_ending": str(worst_sample.index[0]) if len(worst_sample) else "",
        "best_filter_by_drawdown_reduction": str(drawdown.index[0]) if len(drawdown) else "",
        "top_suspicious_signals": top_suspicious_signals(attribution),
        "excluded_winner_heavy_filters": excluded_winner_heavy_filters(matrix),
        "theme_failure_summary": theme_failure_summary(diagnostics),
        "status_gate_failures": gate_failure_summary(matrix),
        "excluded_decision_count": int(len(excluded)),
    }


def write_phase1d_reports(
    diagnostics: pd.DataFrame,
    attribution: pd.DataFrame,
    matrix: pd.DataFrame,
    excluded: pd.DataFrame,
    candidate_filter_md: str,
    summary: dict,
    diagnostics_csv_path: str | Path,
    attribution_csv_path: str | Path,
    matrix_csv_path: str | Path,
    excluded_csv_path: str | Path,
    candidate_filter_md_path: str | Path,
    summary_md_path: str | Path,
) -> None:
    paths = [
        Path(diagnostics_csv_path),
        Path(attribution_csv_path),
        Path(matrix_csv_path),
        Path(excluded_csv_path),
        Path(candidate_filter_md_path),
        Path(summary_md_path),
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    diagnostics.to_csv(diagnostics_csv_path, index=False)
    attribution.to_csv(attribution_csv_path, index=False)
    matrix.to_csv(matrix_csv_path, index=False)
    excluded.to_csv(excluded_csv_path, index=False)
    Path(candidate_filter_md_path).write_text(candidate_filter_md, encoding="utf-8")
    Path(summary_md_path).write_text(phase1d_summary_markdown(summary, diagnostics, attribution, matrix, excluded), encoding="utf-8")


def phase1d_summary_markdown(
    summary: dict,
    diagnostics: pd.DataFrame,
    attribution: pd.DataFrame,
    matrix: pd.DataFrame,
    excluded: pd.DataFrame,
) -> str:
    lines = [
        "PHOENIX NANO PHASE 1D — ENTRY-RULE FAILURE DIAGNOSTICS",
        "",
        "Research/manual-review only. This does not change daily scan behavior and does not approve any trading.",
        "",
        "## Phase 1C Recap",
        "",
        "- Phase 1C found exit-policy tuning was not robust enough across deterministic samples.",
        "- Phase 1D tests whether pre-entry features can identify losing BUY candidates before entry.",
        "",
        "## Scope",
        "",
        f"- Total samples analyzed: {summary['sample_count']}",
        f"- BUY decisions analyzed: {summary['buy_decision_count']}",
        f"- Excluded decision audit rows: {summary['excluded_decision_count']}",
        "",
        "## Winner vs Loser Feature Findings",
        "",
        attribution_table(attribution),
        "",
        "## Top 5 Suspicious Loser Signals",
        "",
        "\n".join(f"- {item}" for item in summary["top_suspicious_signals"]) or "- none",
        "",
        "## Filters Tested",
        "",
        "\n".join(f"- {name}" for name in summary["filters_tested"]),
        "",
        f"- Best filter by median ending account value: {summary['best_filter_by_median_ending'] or 'none'}",
        f"- Best filter by worst-sample ending account value: {summary['best_filter_by_worst_sample_ending'] or 'none'}",
        f"- Best filter by drawdown reduction: {summary['best_filter_by_drawdown_reduction'] or 'none'}",
        "",
        "## Filters That Excluded Too Many Winners",
        "",
        "\n".join(f"- {item}" for item in summary["excluded_winner_heavy_filters"]) or "- none",
        "",
        "## Theme And Ticker Failure Concentration",
        "",
        summary["theme_failure_summary"],
        "",
        "## Fixability Assessment",
        "",
        "Conservative filters are offline hypotheses only. Failures look fixable only if a filter improves worst-sample ending value and drawdown without removing too many winners.",
        "",
        "## Gate Failures",
        "",
        summary["status_gate_failures"],
        "",
        f"## Phase 1D Status: {summary['phase_1d_status']}",
        "",
        "Do not start paper trading or live trading.",
        "",
        "## Next Research Task Recommendation",
        "",
        "Ask GPT to review the top suspicious pre-entry signals and select one narrow Phase 1E entry-filter experiment, without loosening Candidate 34.",
        "",
    ]
    return "\n".join(lines)


def candidate_filter_markdown(filters: list[dict], diagnostics: pd.DataFrame, matrix: pd.DataFrame, excluded: pd.DataFrame) -> str:
    lines = [
        "# Phase 1D Candidate Entry Filters",
        "",
        "Offline diagnostics only. These filters use replay-date or entry-date information only and do not change daily scan behavior.",
        "",
    ]
    for item in filters:
        lines.append(f"## {item['filter_name']}")
        lines.append("")
        lines.append(item["filter_description"])
        lines.append("")
    return "\n".join(lines)


def diagnostic_columns() -> list[str]:
    return [
        "sample_id", "replay_date", "ticker", "entry_date", "reference_price", "entry_price", "entry_gap_pct",
        "shares_with_100", "estimated_total_cost", "estimated_cash_remaining", "stop_loss", "target_1", "target_2",
        "stop_distance_pct", "target_1_distance_pct", "target_2_distance_pct", "max_dollar_risk",
        "decision_strength", "smoke_score", "failed_checks_at_selection", "sector_or_theme", "latest_volume",
        "dollar_volume", "relative_volume_prev20", "atr_14", "atr_pct", "close_vs_sma20_pct", "close_vs_sma50_pct",
        "distance_from_20d_high_pct", "distance_from_52w_high_pct", "return_1d_prior", "return_5d_prior",
        "return_10d_prior", "return_20d_prior", "volatility_20d", "max_single_day_loss_20d", "near_max_entry_price_pct",
        "forward_return_1d", "forward_return_3d", "forward_return_5d", "forward_return_10d", "forward_return_20d",
        "baseline_exit_reason", "baseline_pnl_dollars", "baseline_trade_return_pct", "baseline_account_return_pct",
        "stopped_out_then_20d_positive", "intraday_stop_breached", "winner_20d", "winner_baseline_simulation",
    ]


def _filter(name: str, description: str, column: str, operator: str, threshold: float) -> dict:
    return {"filter_name": name, "filter_description": description, "kind": "threshold", "column": column, "operator": operator, "threshold": threshold}


def _threshold_excluded(frame: pd.DataFrame, filter_def: dict) -> pd.Series:
    values = pd.to_numeric(frame[filter_def["column"]], errors="coerce")
    threshold = float(filter_def["threshold"])
    operator = filter_def["operator"]
    if operator == "le":
        return values.gt(threshold)
    if operator == "ge":
        return values.lt(threshold) | values.isna()
    if operator == "abs_le":
        return values.abs().gt(threshold)
    raise ValueError(f"Unsupported filter operator: {operator}")


def _trade_for_decision(trades: pd.DataFrame, decision: pd.Series) -> pd.Series:
    if trades.empty:
        return pd.Series(dtype=object)
    key = (pd.Timestamp(decision["replay_date"]).strftime("%Y-%m-%d"), decision["ticker"])
    if key in trades.index:
        found = trades.loc[key]
        return found.iloc[0] if isinstance(found, pd.DataFrame) else found
    return pd.Series(dtype=object)


def close_vs_sma(history: pd.DataFrame, window: int) -> object:
    if history.empty or len(history) < window:
        return pd.NA
    close = pd.to_numeric(history["close"], errors="coerce")
    sma = close.tail(window).mean()
    return float(close.iloc[-1] / sma - 1.0) if sma else pd.NA


def distance_from_high(history: pd.DataFrame, window: int) -> object:
    if history.empty or len(history) < min(window, 2):
        return pd.NA
    close = _num(history.iloc[-1].get("close"))
    high = pd.to_numeric(history["high"], errors="coerce").tail(window).max()
    return float(close / high - 1.0) if pd.notna(close) and pd.notna(high) and high else pd.NA


def trailing_return(history: pd.DataFrame, window: int) -> object:
    if history.empty or len(history) <= window:
        return pd.NA
    close = pd.to_numeric(history["close"], errors="coerce")
    prior = close.iloc[-window - 1]
    return float(close.iloc[-1] / prior - 1.0) if prior else pd.NA


def volatility_20d(history: pd.DataFrame) -> object:
    if history.empty or len(history) < 21:
        return pd.NA
    returns = pd.to_numeric(history["close"], errors="coerce").pct_change(fill_method=None).tail(20)
    return float(returns.std()) if returns.notna().any() else pd.NA


def max_single_day_loss_20d(history: pd.DataFrame) -> object:
    if history.empty or len(history) < 21:
        return pd.NA
    returns = pd.to_numeric(history["close"], errors="coerce").pct_change(fill_method=None).tail(20)
    return float(returns.min()) if returns.notna().any() else pd.NA


def attribution_note(feature: str, loser_mean: object, winner_mean: object) -> str:
    if pd.isna(loser_mean) or pd.isna(winner_mean):
        return "insufficient_data"
    direction = "higher_for_losers" if float(loser_mean) > float(winner_mean) else "lower_for_losers"
    return f"{feature}_{direction}"


def top_suspicious_signals(attribution: pd.DataFrame) -> list[str]:
    if attribution.empty:
        return []
    top = attribution.loc[attribution["sample_id"].eq("ALL")].sort_values("simple_separation_score", ascending=False).head(5)
    return [
        f"{row.feature_name}: loser_mean={_fmt(row.loser_mean)}, winner_mean={_fmt(row.winner_mean)}, separation={_fmt(row.simple_separation_score)}"
        for row in top.itertuples()
    ]


def attribution_table(attribution: pd.DataFrame) -> str:
    if attribution.empty:
        return "No attribution rows."
    cols = ["feature_name", "winner_count", "loser_count", "winner_mean", "loser_mean", "simple_separation_score", "missing_rate", "notes"]
    return attribution.loc[attribution["sample_id"].eq("ALL"), cols].sort_values("simple_separation_score", ascending=False).head(10).to_markdown(index=False)


def excluded_winner_heavy_filters(matrix: pd.DataFrame) -> list[str]:
    if matrix.empty:
        return []
    grouped = matrix.groupby("filter_name")[["excluded_winner_count", "excluded_loser_count"]].sum()
    heavy = grouped.loc[grouped["excluded_winner_count"] >= grouped["excluded_loser_count"]]
    return [f"{name}: winners={int(row.excluded_winner_count)}, losers={int(row.excluded_loser_count)}" for name, row in heavy.iterrows()]


def theme_failure_summary(diagnostics: pd.DataFrame) -> str:
    if diagnostics.empty:
        return "No diagnostics rows."
    losers = diagnostics.loc[~diagnostics["winner_baseline_simulation"].astype(bool)]
    theme_counts = losers["sector_or_theme"].replace("", "UNMAPPED").value_counts().head(8)
    ticker_counts = losers["ticker"].value_counts().head(8)
    return (
        "Top losing themes: "
        + (", ".join(f"{idx}:{val}" for idx, val in theme_counts.items()) or "none")
        + "\n\nTop losing tickers: "
        + (", ".join(f"{idx}:{val}" for idx, val in ticker_counts.items()) or "none")
    )


def gate_failure_summary(matrix: pd.DataFrame) -> str:
    if matrix.empty:
        return "No filter matrix rows."
    best = matrix.groupby("filter_name").agg(
        median_ending=("ending_account_value", "median"),
        worst_ending=("ending_account_value", "min"),
        median_drawdown=("max_drawdown", "median"),
        worst_drawdown=("max_drawdown", "min"),
        min_buy_count=("filtered_buy_count", "min"),
        median_accuracy=("trade_simulation_accuracy", "median"),
        median_ex_best=("ending_value_excluding_best_decision", "median"),
        max_profit_share=("top_ticker_profit_share", "max"),
    )
    lines = []
    for name, row in best.sort_values("median_ending", ascending=False).head(5).iterrows():
        failed = []
        if row.median_ending <= 120:
            failed.append("median ending <= $120")
        if row.worst_ending <= 100:
            failed.append("worst ending <= $100")
        if row.median_drawdown <= -0.35:
            failed.append("median drawdown <= -35%")
        if row.worst_drawdown <= -0.45:
            failed.append("worst drawdown <= -45%")
        if row.min_buy_count < 15:
            failed.append("sample buy count < 15")
        if pd.isna(row.median_accuracy) or row.median_accuracy < 0.50:
            failed.append("median simulation accuracy < 50%")
        if row.median_ex_best <= 105:
            failed.append("median ending excluding best <= $105")
        if pd.notna(row.max_profit_share) and row.max_profit_share > 0.50:
            failed.append("top ticker profit share > 50%")
        lines.append(f"- {name}: {', '.join(failed) if failed else 'all core gates passed'}")
    return "\n".join(lines)


def _best_filter(matrix: pd.DataFrame, agg: str, column: str) -> str:
    if matrix.empty:
        return ""
    ranked = getattr(matrix.groupby("filter_name")[column], agg)().sort_values(ascending=False)
    return str(ranked.index[0]) if len(ranked) else ""


def _num(value: object) -> object:
    try:
        if pd.isna(value):
            return pd.NA
        return float(value)
    except (TypeError, ValueError):
        return pd.NA


def _gt_zero(value: object) -> bool:
    numeric = _num(value)
    return bool(pd.notna(numeric) and float(numeric) > 0)


def _date_string(value: object) -> str:
    if value is None or value == "" or pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _mean(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.mean())


def _median(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.median())


def _positive_rate(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float((clean > 0).mean())


def _diff(left: object, right: object) -> object:
    return pd.NA if pd.isna(left) or pd.isna(right) else float(left) - float(right)


def _fmt(value: object) -> str:
    return "" if pd.isna(value) else f"{float(value):.4f}"
