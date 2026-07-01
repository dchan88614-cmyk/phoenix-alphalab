from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED, calculate_affordability
from src.research.auto_loop import CandidateRule
from src.research.historical_replay import (
    FORWARD_WINDOWS,
    HISTORICAL_BUY_CANDIDATE,
    build_phase1_historical_replay,
    summarize_phase1_replay,
)
from src.trading.trade_simulator import STOP, TARGET_1, TARGET_2, TIME_EXIT


PHASE_1B_FAILED = "PHASE_1B_FAILED"
PHASE_1B_NEEDS_MORE_ITERATION = "PHASE_1B_NEEDS_MORE_ITERATION"
PHASE_1B_EXECUTION_POLICY_PROMISING_NOT_APPROVED = "PHASE_1B_EXECUTION_POLICY_PROMISING_NOT_APPROVED"

POLICIES = [
    {"policy": "baseline_current", "atr_multiple": 1.5, "mode": "intraday"},
    {"policy": "atr_stop_1_5x", "atr_multiple": 1.5, "mode": "intraday"},
    {"policy": "atr_stop_2_0x", "atr_multiple": 2.0, "mode": "intraday"},
    {"policy": "atr_stop_2_5x", "atr_multiple": 2.5, "mode": "intraday"},
    {"policy": "atr_stop_3_0x", "atr_multiple": 3.0, "mode": "intraday"},
    {"policy": "time_exit_20d_no_intraday_stop", "atr_multiple": 0.0, "mode": "time"},
    {"policy": "close_based_stop_1_5x", "atr_multiple": 1.5, "mode": "close_stop"},
    {"policy": "close_based_stop_2_0x", "atr_multiple": 2.0, "mode": "close_stop"},
]


def build_phase1b_execution_diagnostics(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_rounds: int = 100,
    replay_sample_offset: int = 0,
    replay_sample_count: int = 1,
    benchmark_ticker: str = "SPY",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["date", "ticker"]).reset_index(drop=True)

    baseline_decisions, _, baseline_summary = build_phase1_historical_replay(
        frame,
        account_settings,
        rule,
        replay_rounds=replay_rounds,
        benchmark_ticker=benchmark_ticker,
        replay_sample_offset=replay_sample_offset,
    )
    diagnostics = build_trade_diagnostics(baseline_decisions, frame)
    comparison = compare_exit_policies(baseline_decisions, frame, account_settings)
    baseline_trades = simulate_policy_trades(baseline_decisions, frame, account_settings, POLICIES[0])
    attribution = build_ticker_risk_attribution(baseline_trades)
    drawdown = drawdown_attribution(baseline_trades, account_settings.starting_capital)
    robustness = build_sample_robustness(
        frame,
        account_settings,
        rule,
        replay_rounds,
        replay_sample_offset,
        replay_sample_count,
        benchmark_ticker,
    )
    summary = {
        "baseline_phase1a": baseline_summary,
        "phase_1b_status": phase1b_status(comparison, drawdown),
        "best_policy": best_policy_label(comparison),
        "drawdown": drawdown,
        "robustness": robustness,
        "stopped_out_then_20d_positive_count": int(diagnostics["stopped_out_then_20d_positive"].sum()) if not diagnostics.empty else 0,
        "stopped_out_then_20d_positive_rate": (
            float(diagnostics["stopped_out_then_20d_positive"].mean()) if not diagnostics.empty else pd.NA
        ),
    }
    return diagnostics, comparison, attribution, summary


def build_trade_diagnostics(decisions: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
    buys = decisions.loc[decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)].copy()
    if buys.empty:
        return pd.DataFrame()
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    by_ticker = {ticker: group.sort_values("date").reset_index(drop=True) for ticker, group in frame.groupby("ticker")}
    rows = []
    for _, decision in buys.iterrows():
        ticker = decision["ticker"]
        replay_date = pd.Timestamp(decision["replay_date"])
        ticker_data = by_ticker.get(ticker)
        if ticker_data is None:
            continue
        signal = ticker_data.loc[ticker_data["date"].eq(replay_date)]
        future = ticker_data.loc[ticker_data["date"].gt(replay_date)].head(20).copy()
        if signal.empty or future.empty:
            continue
        signal_row = signal.iloc[0]
        entry = future.iloc[0]
        entry_price = _first_valid(entry, ["open", "close"])
        if pd.isna(entry_price) or float(entry_price) <= 0:
            continue
        entry_price = float(entry_price)
        atr = _signal_atr(signal_row, entry_price)
        stop_loss, target_1, target_2 = _risk_levels(entry_price, atr, 1.5)
        future = future.reset_index(drop=True)
        mfe = float(future["high"].max() / entry_price - 1.0)
        mae = float(future["low"].min() / entry_price - 1.0)
        max_favorable_idx = int(future["high"].idxmax()) + 1
        max_adverse_idx = int(future["low"].idxmin()) + 1
        current_exit_reason = decision.get("exit_reason", "")
        stopped = current_exit_reason == STOP
        fwd20 = decision.get("forward_return_20d", pd.NA)
        close_20d = float(signal_row["close"]) * (1.0 + float(fwd20)) if not pd.isna(fwd20) else pd.NA
        rows.append(
            {
                "replay_date": decision["replay_date"],
                "ticker": ticker,
                "reference_price": decision["reference_price"],
                "entry_date": decision.get("entry_date", pd.NA),
                "entry_price": entry_price,
                "entry_gap_pct": entry_price / float(decision["reference_price"]) - 1.0,
                "current_stop_loss": stop_loss,
                "current_target_1": target_1,
                "current_target_2": target_2,
                "current_exit_date": decision.get("exit_date", ""),
                "current_exit_reason": current_exit_reason,
                "current_pnl_dollars": decision.get("pnl_dollars", pd.NA),
                "current_trade_return_pct": decision.get("trade_return_pct", pd.NA),
                "current_account_return_pct": decision.get("account_return_pct", pd.NA),
                **{f"forward_return_{window}d": decision.get(f"forward_return_{window}d", pd.NA) for window in FORWARD_WINDOWS},
                "max_favorable_excursion_20d": mfe,
                "max_adverse_excursion_20d": mae,
                "stopped_out_then_20d_positive": bool(stopped and not pd.isna(fwd20) and float(fwd20) > 0),
                "stopped_out_then_20d_above_target_1": bool(stopped and not pd.isna(close_20d) and float(close_20d) >= target_1),
                "stopped_out_then_20d_above_target_2": bool(stopped and not pd.isna(close_20d) and float(close_20d) >= target_2),
                "recovered_after_stop_within_20d": bool(stopped and _recovered_after_stop(future, entry_price, decision.get("exit_date", ""))),
                "days_to_stop": _first_day_hit(future, "low", stop_loss, "le"),
                "days_to_target_1_if_any": _first_day_hit(future, "high", target_1, "ge"),
                "days_to_target_2_if_any": _first_day_hit(future, "high", target_2, "ge"),
                "days_to_max_favorable_20d": max_favorable_idx,
                "days_to_max_adverse_20d": max_adverse_idx,
            }
        )
    return pd.DataFrame(rows)


def compare_exit_policies(decisions: pd.DataFrame, data: pd.DataFrame, account_settings: AccountSettings) -> pd.DataFrame:
    rows = []
    for policy in POLICIES:
        trades = simulate_policy_trades(decisions, data, account_settings, policy)
        rows.append(policy_summary(trades, policy["policy"], account_settings.starting_capital))
    return pd.DataFrame(rows)


def simulate_policy_trades(
    decisions: pd.DataFrame,
    data: pd.DataFrame,
    account_settings: AccountSettings,
    policy: dict,
) -> pd.DataFrame:
    buys = decisions.loc[decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)].copy()
    columns = [
        "policy",
        "replay_date",
        "ticker",
        "entry_date",
        "exit_date",
        "exit_reason",
        "entry_price",
        "exit_price",
        "stop_loss",
        "target_1",
        "target_2",
        "holding_days",
        "shares",
        "cash_before",
        "cash_after_exit",
        "pnl_dollars",
        "trade_return_pct",
        "account_return_pct",
        "entry_gap_pct",
        "forward_return_20d",
        "status",
    ]
    if buys.empty:
        return pd.DataFrame(columns=columns)
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    by_ticker = {ticker: group.sort_values("date").reset_index(drop=True) for ticker, group in frame.groupby("ticker")}
    cash = float(account_settings.starting_capital)
    open_until = pd.Timestamp.min
    rows = []
    for _, decision in buys.sort_values(["replay_date", "ticker"]).iterrows():
        replay_date = pd.Timestamp(decision["replay_date"])
        if replay_date <= open_until:
            rows.append(_skipped_policy_row(policy["policy"], decision, cash, "SKIPPED_POSITION_OPEN"))
            continue
        ticker_data = by_ticker.get(decision["ticker"])
        if ticker_data is None:
            rows.append(_skipped_policy_row(policy["policy"], decision, cash, "NO_TICKER_DATA"))
            continue
        signal = ticker_data.loc[ticker_data["date"].eq(replay_date)]
        future = ticker_data.loc[ticker_data["date"].gt(replay_date)].head(20).copy()
        if signal.empty or future.empty:
            rows.append(_skipped_policy_row(policy["policy"], decision, cash, "NO_FUTURE_DATA"))
            continue
        trade = _simulate_single_policy_trade(signal.iloc[0], future.reset_index(drop=True), policy)
        if trade is None:
            rows.append(_skipped_policy_row(policy["policy"], decision, cash, "INVALID_ENTRY"))
            continue
        affordability = calculate_affordability(
            pd.Series({"entry_price": trade["entry_price"], "stop_loss": trade["stop_loss"]}),
            cash,
            account_settings,
        )
        if affordability["affordability_status"] != EXECUTED:
            rows.append(_skipped_policy_row(policy["policy"], decision, cash, "NOT_AFFORDABLE"))
            continue
        cash_before = cash
        cash_after_entry = float(affordability["cash_remaining"])
        shares = float(affordability["shares"])
        cash_after_exit = cash_after_entry + shares * float(trade["exit_price"]) - account_settings.commission_per_trade
        pnl = cash_after_exit - cash_before
        cash = cash_after_exit
        open_until = pd.Timestamp(trade["exit_date"])
        rows.append(
            {
                "policy": policy["policy"],
                "replay_date": pd.Timestamp(decision["replay_date"]).strftime("%Y-%m-%d"),
                "ticker": decision["ticker"],
                "entry_date": pd.Timestamp(trade["entry_date"]).strftime("%Y-%m-%d"),
                "exit_date": pd.Timestamp(trade["exit_date"]).strftime("%Y-%m-%d"),
                "exit_reason": trade["exit_reason"],
                "entry_price": trade["entry_price"],
                "exit_price": trade["exit_price"],
                "stop_loss": trade["stop_loss"],
                "target_1": trade["target_1"],
                "target_2": trade["target_2"],
                "holding_days": trade["holding_days"],
                "shares": affordability["shares"],
                "cash_before": cash_before,
                "cash_after_exit": cash_after_exit,
                "pnl_dollars": pnl,
                "trade_return_pct": float(trade["exit_price"]) / float(trade["entry_price"]) - 1.0,
                "account_return_pct": pnl / cash_before if cash_before else pd.NA,
                "entry_gap_pct": float(trade["entry_price"]) / float(decision["reference_price"]) - 1.0,
                "forward_return_20d": decision.get("forward_return_20d", pd.NA),
                "status": EXECUTED,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def policy_summary(trades: pd.DataFrame, policy_name: str, starting_capital: float) -> dict:
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    buy_count = int(len(trades))
    executed_count = int(len(executed))
    wins = executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    losses = executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    stopped = executed.loc[executed["exit_reason"].eq(STOP)].copy() if not executed.empty else pd.DataFrame()
    if executed.empty:
        ending_excluding_best = starting_capital
        top_profit_share = pd.NA
    else:
        ending_excluding_best = starting_capital + float(executed.drop(index=executed["pnl_dollars"].idxmax())["pnl_dollars"].sum())
        ticker_profit = executed.loc[executed["pnl_dollars"] > 0].groupby("ticker")["pnl_dollars"].sum()
        top_profit_share = float(ticker_profit.max() / ticker_profit.sum()) if ticker_profit.sum() > 0 else pd.NA
    return {
        "policy": policy_name,
        "buy_count": buy_count,
        "executed_count": executed_count,
        "win_rate": _positive_rate(executed["pnl_dollars"]) if not executed.empty else pd.NA,
        "trade_simulation_accuracy": _positive_rate(executed["pnl_dollars"]) if not executed.empty else pd.NA,
        "average_win": _mean(executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"]) if not executed.empty else pd.NA,
        "average_loss": _mean(executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"]) if not executed.empty else pd.NA,
        "profit_factor": float(wins / abs(losses)) if losses < 0 else (float("inf") if wins > 0 else 0.0),
        "ending_account_value": float(executed["cash_after_exit"].iloc[-1]) if not executed.empty else starting_capital,
        "max_drawdown": _max_drawdown(executed, starting_capital),
        "worst_trade_account_loss": float(executed["account_return_pct"].min()) if not executed.empty else pd.NA,
        "stop_count": int(executed["exit_reason"].eq(STOP).sum()) if not executed.empty else 0,
        "target_1_count": int(executed["exit_reason"].eq(TARGET_1).sum()) if not executed.empty else 0,
        "target_2_count": int(executed["exit_reason"].eq(TARGET_2).sum()) if not executed.empty else 0,
        "time_exit_count": int(executed["exit_reason"].eq(TIME_EXIT).sum()) if not executed.empty else 0,
        "median_holding_days": _median(executed["holding_days"]) if not executed.empty else pd.NA,
        "average_entry_gap_pct": _mean(executed["entry_gap_pct"]) if not executed.empty else pd.NA,
        "stopped_trades_20d_positive_pct": (
            _positive_rate(stopped["forward_return_20d"]) if not stopped.empty else pd.NA
        ),
        "ending_value_excluding_best_trade": ending_excluding_best,
        "top_ticker_profit_share": top_profit_share,
        "top_ticker_profit_gt_50pct": bool(not pd.isna(top_profit_share) and top_profit_share > 0.50),
    }


def build_ticker_risk_attribution(trades: pd.DataFrame) -> pd.DataFrame:
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    if executed.empty:
        return pd.DataFrame()
    total_profit = executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"].sum()
    total_loss = abs(executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"].sum())
    rows = []
    for ticker, group in executed.groupby("ticker"):
        pnl = group["pnl_dollars"]
        rows.append(
            {
                "ticker": ticker,
                "selection_count": int(len(group)),
                "total_pnl_dollars": float(pnl.sum()),
                "average_pnl_dollars": float(pnl.mean()),
                "win_rate": float((pnl > 0).mean()),
                "worst_trade_pnl_dollars": float(pnl.min()),
                "worst_account_return_pct": float(group["account_return_pct"].min()),
                "contribution_to_total_profit_pct": float(pnl[pnl > 0].sum() / total_profit) if total_profit > 0 else pd.NA,
                "contribution_to_total_loss_pct": float(abs(pnl[pnl < 0].sum()) / total_loss) if total_loss > 0 else pd.NA,
                "max_consecutive_losses": _max_consecutive_losses(group.sort_values("replay_date")["pnl_dollars"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["total_pnl_dollars", "ticker"], ascending=[False, True]).reset_index(drop=True)


def drawdown_attribution(trades: pd.DataFrame, starting_capital: float) -> dict:
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    if executed.empty:
        return {
            "worst_drawdown_start": "",
            "worst_drawdown_end": "",
            "worst_drawdown": 0.0,
            "trades_inside_worst_drawdown": "",
            "ending_value_excluding_best_trade": starting_capital,
            "max_drawdown_excluding_worst_trade": 0.0,
            "remove_best_trade_above_105": False,
            "remove_worst_trade_drawdown_above_minus_35": True,
            "top_ticker_profit_share": pd.NA,
            "top_ticker_loss_share": pd.NA,
            "top_ticker_profit_gt_50pct": False,
            "top_ticker_loss_gt_50pct": False,
        }
    equity = pd.Series([starting_capital, *executed["cash_after_exit"].tolist()])
    running_peak = equity.cummax()
    drawdowns = equity / running_peak - 1.0
    trough_pos = int(drawdowns.idxmin())
    peak_pos = int(equity.iloc[: trough_pos + 1].idxmax())
    start_date = "" if peak_pos == 0 else executed.iloc[peak_pos - 1]["exit_date"]
    end_date = executed.iloc[trough_pos - 1]["exit_date"] if trough_pos > 0 else ""
    inside = executed.iloc[max(0, peak_pos):trough_pos].copy() if trough_pos > peak_pos else pd.DataFrame()
    best_idx = executed["pnl_dollars"].idxmax()
    worst_idx = executed["pnl_dollars"].idxmin()
    without_best = executed.drop(index=best_idx)
    without_worst = executed.drop(index=worst_idx)
    ending_without_best = starting_capital + float(without_best["pnl_dollars"].sum())
    max_dd_without_worst = _max_drawdown_from_pnl(without_worst["pnl_dollars"], starting_capital)
    ticker_profit = executed.loc[executed["pnl_dollars"] > 0].groupby("ticker")["pnl_dollars"].sum()
    ticker_loss = executed.loc[executed["pnl_dollars"] < 0].groupby("ticker")["pnl_dollars"].sum().abs()
    top_profit_share = float(ticker_profit.max() / ticker_profit.sum()) if ticker_profit.sum() > 0 else pd.NA
    top_loss_share = float(ticker_loss.max() / ticker_loss.sum()) if ticker_loss.sum() > 0 else pd.NA
    return {
        "worst_drawdown_start": start_date,
        "worst_drawdown_end": end_date,
        "worst_drawdown": float(drawdowns.min()),
        "trades_inside_worst_drawdown": ", ".join(
            f"{row.replay_date}:{row.ticker}:{row.pnl_dollars:.2f}" for row in inside.itertuples()
        ),
        "ending_value_excluding_best_trade": ending_without_best,
        "max_drawdown_excluding_worst_trade": max_dd_without_worst,
        "remove_best_trade_above_105": bool(ending_without_best > 105.0),
        "remove_worst_trade_drawdown_above_minus_35": bool(max_dd_without_worst > -0.35),
        "top_ticker_profit_share": top_profit_share,
        "top_ticker_loss_share": top_loss_share,
        "top_ticker_profit_gt_50pct": bool(not pd.isna(top_profit_share) and top_profit_share > 0.50),
        "top_ticker_loss_gt_50pct": bool(not pd.isna(top_loss_share) and top_loss_share > 0.50),
    }


def build_sample_robustness(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_rounds: int,
    replay_sample_offset: int,
    replay_sample_count: int,
    benchmark_ticker: str,
) -> pd.DataFrame:
    rows = []
    for sample_index in range(replay_sample_count):
        offset = replay_sample_offset + sample_index
        decisions, _, sample_summary = build_phase1_historical_replay(
            data,
            account_settings,
            rule,
            replay_rounds=replay_rounds,
            benchmark_ticker=benchmark_ticker,
            replay_sample_offset=offset,
        )
        comparison = compare_exit_policies(decisions, data, account_settings)
        baseline = comparison.loc[comparison["policy"].eq("baseline_current")].iloc[0]
        candidates = comparison.loc[comparison["max_drawdown"].gt(-0.35)].copy()
        best = candidates.sort_values(["ending_account_value", "trade_simulation_accuracy"], ascending=[False, False]).head(1)
        best_label = "" if best.empty else str(best.iloc[0]["policy"])
        rows.append(
            {
                "sample_id": offset,
                "replay_rounds": replay_rounds,
                "buy_count": int(sample_summary["buy_count"]),
                "accuracy_20d": sample_summary["accuracy_20d"],
                "baseline_ending_account_value": baseline["ending_account_value"],
                "baseline_max_drawdown": baseline["max_drawdown"],
                "baseline_trade_simulation_accuracy": baseline["trade_simulation_accuracy"],
                "best_alternative_policy": best_label,
                "any_policy_achieved_phase1b_gates": bool(
                    any(policy_passes_gates(row, buy_count=int(sample_summary["buy_count"])) for _, row in comparison.iterrows())
                ),
            }
        )
    return pd.DataFrame(rows)


def phase1b_status(comparison: pd.DataFrame, drawdown: dict) -> str:
    if comparison.empty or not comparison["ending_account_value"].gt(100.0).any():
        return PHASE_1B_FAILED
    for _, row in comparison.iterrows():
        if policy_passes_gates(row, buy_count=int(row["buy_count"])):
            return PHASE_1B_EXECUTION_POLICY_PROMISING_NOT_APPROVED
    return PHASE_1B_NEEDS_MORE_ITERATION


def policy_passes_gates(row: pd.Series, buy_count: int) -> bool:
    return bool(
        float(row["ending_account_value"]) > 120.0
        and float(row["max_drawdown"]) > -0.35
        and not pd.isna(row["trade_simulation_accuracy"])
        and float(row["trade_simulation_accuracy"]) >= 0.50
        and not pd.isna(row["worst_trade_account_loss"])
        and float(row["worst_trade_account_loss"]) > -0.15
        and buy_count >= 20
        and bool(row.get("ending_value_excluding_best_trade", 0.0) > 105.0)
        and not bool(row.get("top_ticker_profit_gt_50pct", False))
    )


def best_policy_label(comparison: pd.DataFrame) -> str:
    if comparison.empty:
        return ""
    candidates = comparison.loc[comparison["max_drawdown"].gt(-0.35)].copy()
    if candidates.empty:
        candidates = comparison.copy()
    return str(candidates.sort_values(["ending_account_value", "trade_simulation_accuracy"], ascending=[False, False]).iloc[0]["policy"])


def write_phase1b_reports(
    diagnostics: pd.DataFrame,
    comparison: pd.DataFrame,
    attribution: pd.DataFrame,
    summary: dict,
    diagnostics_csv_path: str | Path,
    summary_md_path: str | Path,
    comparison_csv_path: str | Path,
    attribution_csv_path: str | Path,
) -> None:
    diagnostics_path = Path(diagnostics_csv_path)
    summary_path = Path(summary_md_path)
    comparison_path = Path(comparison_csv_path)
    attribution_path = Path(attribution_csv_path)
    for path in [diagnostics_path, summary_path, comparison_path, attribution_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
    diagnostics.to_csv(diagnostics_path, index=False)
    comparison.to_csv(comparison_path, index=False)
    attribution.to_csv(attribution_path, index=False)
    summary_path.write_text(_summary_markdown(summary, comparison, attribution), encoding="utf-8")


def _simulate_single_policy_trade(signal: pd.Series, future: pd.DataFrame, policy: dict) -> dict | None:
    entry = future.iloc[0]
    entry_price = _first_valid(entry, ["open", "close"])
    if pd.isna(entry_price) or float(entry_price) <= 0:
        return None
    entry_price = float(entry_price)
    atr = _signal_atr(signal, entry_price)
    stop_loss, target_1, target_2 = _risk_levels(entry_price, atr, float(policy["atr_multiple"]))
    exit_row = future.iloc[-1]
    exit_price = float(exit_row["close"])
    exit_reason = TIME_EXIT
    holding_days = int(len(future))
    if policy["mode"] != "time":
        for day_index, (_, day) in enumerate(future.iterrows(), start=1):
            if policy["mode"] == "close_stop":
                stop_hit = not pd.isna(day["close"]) and float(day["close"]) <= stop_loss
            else:
                stop_hit = not pd.isna(day["low"]) and float(day["low"]) <= stop_loss
            if stop_hit:
                exit_row = day
                exit_price = stop_loss
                exit_reason = STOP
                holding_days = day_index
                break
            if not pd.isna(day["high"]) and float(day["high"]) >= target_2:
                exit_row = day
                exit_price = target_2
                exit_reason = TARGET_2
                holding_days = day_index
                break
            if not pd.isna(day["high"]) and float(day["high"]) >= target_1:
                exit_row = day
                exit_price = target_1
                exit_reason = TARGET_1
                holding_days = day_index
                break
    return {
        "entry_date": entry["date"],
        "exit_date": exit_row["date"],
        "exit_reason": exit_reason,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "holding_days": holding_days,
    }


def _risk_levels(entry_price: float, atr: float, atr_multiple: float) -> tuple[float, float, float]:
    if atr_multiple <= 0:
        return 0.0, float("inf"), float("inf")
    stop_loss = entry_price - atr_multiple * atr
    risk = max(0.0, entry_price - stop_loss)
    return float(stop_loss), float(entry_price + 2.0 * risk), float(entry_price + 4.0 * risk)


def _signal_atr(signal: pd.Series, entry_price: float) -> float:
    atr = signal.get("atr", pd.NA)
    return entry_price * 0.08 / 1.5 if pd.isna(atr) or float(atr) <= 0 else float(atr)


def _first_valid(row: pd.Series, columns: list[str]) -> object:
    for column in columns:
        value = row.get(column, pd.NA)
        if not pd.isna(value):
            return value
    return pd.NA


def _first_day_hit(future: pd.DataFrame, column: str, level: float, direction: str) -> object:
    for index, (_, row) in enumerate(future.iterrows(), start=1):
        value = row.get(column, pd.NA)
        if pd.isna(value):
            continue
        if direction == "le" and float(value) <= level:
            return index
        if direction == "ge" and float(value) >= level:
            return index
    return pd.NA


def _recovered_after_stop(future: pd.DataFrame, entry_price: float, exit_date: object) -> bool:
    if not exit_date:
        return False
    after_stop = future.loc[future["date"].gt(pd.Timestamp(exit_date))]
    return bool(not after_stop.empty and after_stop["close"].gt(entry_price).any())


def _skipped_policy_row(policy_name: str, decision: pd.Series, cash: float, status: str) -> dict:
    return {
        "policy": policy_name,
        "replay_date": pd.Timestamp(decision["replay_date"]).strftime("%Y-%m-%d"),
        "ticker": decision["ticker"],
        "entry_date": "",
        "exit_date": "",
        "exit_reason": "",
        "entry_price": pd.NA,
        "exit_price": pd.NA,
        "stop_loss": pd.NA,
        "target_1": pd.NA,
        "target_2": pd.NA,
        "holding_days": pd.NA,
        "shares": 0,
        "cash_before": cash,
        "cash_after_exit": cash,
        "pnl_dollars": pd.NA,
        "trade_return_pct": pd.NA,
        "account_return_pct": pd.NA,
        "entry_gap_pct": pd.NA,
        "forward_return_20d": decision.get("forward_return_20d", pd.NA),
        "status": status,
    }


def _max_drawdown(executed: pd.DataFrame, starting_capital: float) -> float:
    if executed.empty:
        return 0.0
    equity = pd.Series([starting_capital, *executed["cash_after_exit"].tolist()])
    return float((equity / equity.cummax() - 1.0).min())


def _max_drawdown_from_pnl(pnl: pd.Series, starting_capital: float) -> float:
    equity = starting_capital + pd.to_numeric(pnl, errors="coerce").fillna(0.0).cumsum()
    equity = pd.concat([pd.Series([starting_capital]), equity], ignore_index=True)
    return float((equity / equity.cummax() - 1.0).min())


def _max_consecutive_losses(pnl: pd.Series) -> int:
    longest = 0
    current = 0
    for value in pnl:
        if float(value) < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _positive_rate(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float((clean > 0).mean())


def _mean(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.mean())


def _median(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.median())


def _summary_markdown(summary: dict, comparison: pd.DataFrame, attribution: pd.DataFrame) -> str:
    baseline = summary["baseline_phase1a"]
    drawdown = summary["drawdown"]
    robustness = summary["robustness"]
    lines = [
        "PHOENIX NANO PHASE 1B — EXECUTION RISK AND DRAWDOWN DIAGNOSTICS",
        "",
        "Research/manual-review only. Do not start paper trading or live trading.",
        "",
        "## Baseline Phase 1A Recap",
        "",
        f"- Replay rounds: {baseline['total_replay_rounds']}",
        f"- BUY count: {baseline['buy_count']}",
        f"- NO_TRADE count: {baseline['no_trade_count']}",
        f"- 20d accuracy: {_format_percent(baseline['accuracy_20d'])}",
        f"- Ending account value: {_format_money(baseline['ending_account_value'])}",
        f"- Max drawdown: {_format_percent(baseline['max_drawdown'])}",
        f"- Trade-simulation accuracy: {_format_percent(baseline['trade_simulation_accuracy'])}",
        "",
        "## Core Problem Diagnosis",
        "",
        f"- Stopped-out-then-20d-positive count: {summary['stopped_out_then_20d_positive_count']}",
        f"- Stopped-out-then-20d-positive rate: {_format_percent(summary['stopped_out_then_20d_positive_rate'])}",
        f"- Best diagnostic policy: {summary['best_policy'] or 'none'}",
        f"- Phase 1B status: {summary['phase_1b_status']}",
        "",
        "## Exit Policy Comparison",
        "",
        comparison.to_markdown(index=False) if not comparison.empty else "No policy comparison rows.",
        "",
        "## Drawdown Attribution",
        "",
        f"- Worst drawdown period: {drawdown['worst_drawdown_start']} to {drawdown['worst_drawdown_end']}",
        f"- Worst drawdown: {_format_percent(drawdown['worst_drawdown'])}",
        f"- Trades inside worst drawdown: {drawdown['trades_inside_worst_drawdown'] or 'none'}",
        f"- Ending value excluding best trade: {_format_money(drawdown['ending_value_excluding_best_trade'])}",
        f"- Max drawdown excluding worst trade: {_format_percent(drawdown['max_drawdown_excluding_worst_trade'])}",
        f"- Removing best trade leaves ending value above $105: {drawdown['remove_best_trade_above_105']}",
        f"- Removing worst trade improves max drawdown above -35%: {drawdown['remove_worst_trade_drawdown_above_minus_35']}",
        "",
        "## Ticker Concentration Analysis",
        "",
        f"- Top ticker profit share: {_format_percent(drawdown['top_ticker_profit_share'])}",
        f"- Top ticker loss share: {_format_percent(drawdown['top_ticker_loss_share'])}",
        f"- Any one ticker contributes more than 50% of total profit: {drawdown['top_ticker_profit_gt_50pct']}",
        f"- Any one ticker contributes more than 50% of total loss: {drawdown['top_ticker_loss_gt_50pct']}",
        "",
        attribution.head(20).to_markdown(index=False) if not attribution.empty else "No ticker attribution rows.",
        "",
        "## Sample Robustness",
        "",
        robustness.to_markdown(index=False) if not robustness.empty else "No robustness samples.",
        "",
        "## Next Research Task Recommendation",
        "",
        "Run a drawdown-focused Phase 1C that keeps selection frozen and tests entry timing / stop placement only if GPT approves.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _format_percent(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value) * 100:.2f}%"


def _format_money(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"${float(value):.2f}"
