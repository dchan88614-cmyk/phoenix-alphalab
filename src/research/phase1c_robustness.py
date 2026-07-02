from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED, calculate_affordability
from src.research.auto_loop import CandidateRule
from src.research.historical_replay import FORWARD_WINDOWS, HISTORICAL_BUY_CANDIDATE, build_phase1_historical_replay
from src.trading.trade_simulator import STOP, TARGET_1, TARGET_2, TIME_EXIT


PHASE_1C_FAILED = "PHASE_1C_FAILED"
PHASE_1C_NEEDS_ENTRY_RULE_WORK = "PHASE_1C_NEEDS_ENTRY_RULE_WORK"
PHASE_1C_EXECUTION_HYPOTHESIS_NEEDS_REALISM_WORK = "PHASE_1C_EXECUTION_HYPOTHESIS_NEEDS_REALISM_WORK"
PHASE_1C_ROBUSTNESS_PROMISING_NOT_APPROVED = "PHASE_1C_ROBUSTNESS_PROMISING_NOT_APPROVED"

PHASE1C_POLICIES = [
    {"policy": "baseline_current", "atr_multiple": 1.5, "mode": "intraday"},
    {"policy": "atr_stop_2_0x", "atr_multiple": 2.0, "mode": "intraday"},
    {"policy": "atr_stop_2_5x", "atr_multiple": 2.5, "mode": "intraday"},
    {"policy": "time_exit_20d_no_intraday_stop", "atr_multiple": 0.0, "mode": "time"},
    {"policy": "close_based_stop_2_0x", "atr_multiple": 2.0, "mode": "close_stop"},
    {"policy": "close_based_stop_2_0x_with_intraday_breach_flag", "atr_multiple": 2.0, "mode": "close_stop"},
    {"policy": "close_confirmed_stop_2_0x_next_open_exit", "atr_multiple": 2.0, "mode": "close_next_open"},
    {"policy": "hybrid_close_stop_2_0x_intraday_catastrophic_3_0x", "atr_multiple": 2.0, "mode": "hybrid"},
]

THEME_MAP = {
    "RIVN": "EV / mobility",
    "F": "EV / mobility",
    "ACHR": "EV / mobility",
    "JOBY": "EV / mobility",
    "AI": "AI / software",
    "PLTR": "AI / software",
    "PATH": "AI / software",
    "BBAI": "AI / software",
    "SMCI": "semiconductor / hardware",
    "INTC": "semiconductor / hardware",
    "HPE": "semiconductor / hardware",
    "CORZ": "crypto-adjacent / high beta",
    "IREN": "crypto-adjacent / high beta",
    "HOOD": "crypto-adjacent / high beta",
    "RKLB": "space / defense / nuclear",
    "KTOS": "space / defense / nuclear",
    "OKLO": "space / defense / nuclear",
    "CCJ": "space / defense / nuclear",
}


def build_phase1c_robustness_analysis(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_rounds: int = 100,
    replay_sample_count: int = 10,
    replay_sample_offset: int = 0,
    benchmark_ticker: str = "SPY",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["date", "ticker"]).reset_index(drop=True)

    matrix_rows: list[dict] = []
    failure_frames: list[pd.DataFrame] = []
    realism_frames: list[pd.DataFrame] = []
    regime_frames: list[pd.DataFrame] = []

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
        policy_trades: dict[str, pd.DataFrame] = {}
        for policy in PHASE1C_POLICIES:
            trades = simulate_phase1c_policy_trades(decisions, frame, account_settings, policy)
            policy_trades[policy["policy"]] = trades
            summary = policy_matrix_row(sample_id, replay_rounds, decisions, phase1_summary, trades, account_settings)
            matrix_rows.append(summary)
            regime_frames.append(build_regime_attribution(sample_id, trades))
        sample_matrix = pd.DataFrame([row for row in matrix_rows if row["sample_id"] == sample_id])
        failing_sample = sample_failed(sample_matrix, phase1_summary)
        if failing_sample:
            failure_frames.append(build_failure_trades(sample_id, policy_trades["baseline_current"], decisions, frame))
        realism_frames.append(build_close_stop_realism(sample_id, decisions, frame, account_settings, policy_trades))

    matrix = pd.DataFrame(matrix_rows)
    failure_trades = pd.concat(failure_frames, ignore_index=True) if failure_frames else pd.DataFrame()
    close_realism = pd.concat(realism_frames, ignore_index=True) if realism_frames else pd.DataFrame()
    regime = pd.concat(regime_frames, ignore_index=True) if regime_frames else pd.DataFrame()
    summary = summarize_phase1c(matrix, failure_trades, close_realism, regime)
    return matrix, failure_trades, close_realism, regime, summary


def simulate_phase1c_policy_trades(
    decisions: pd.DataFrame,
    data: pd.DataFrame,
    account_settings: AccountSettings,
    policy: dict,
) -> pd.DataFrame:
    buys = decisions.loc[decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)].copy()
    columns = [
        "sample_id",
        "policy",
        "replay_date",
        "ticker",
        "entry_date",
        "entry_price",
        "reference_price",
        "entry_gap_pct",
        "exit_date",
        "exit_price",
        "exit_reason",
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
        "forward_return_20d",
        "decision_strength",
        "smoke_score",
        "intraday_stop_breached",
        "breach_date",
        "breach_low",
        "breach_stop_price",
        "same_day_close",
        "same_day_recovered_above_stop",
        "max_favorable_excursion_20d",
        "max_adverse_excursion_20d",
        "days_to_stop",
        "days_to_max_adverse_20d",
        "theme",
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
            rows.append(_skipped_row(policy["policy"], decision, cash, "SKIPPED_POSITION_OPEN"))
            continue
        ticker_data = by_ticker.get(decision["ticker"])
        if ticker_data is None:
            rows.append(_skipped_row(policy["policy"], decision, cash, "NO_TICKER_DATA"))
            continue
        signal = ticker_data.loc[ticker_data["date"].eq(replay_date)]
        future = ticker_data.loc[ticker_data["date"].gt(replay_date)].head(21).reset_index(drop=True)
        if signal.empty or future.empty:
            rows.append(_skipped_row(policy["policy"], decision, cash, "NO_FUTURE_DATA"))
            continue
        trade = simulate_single_trade(signal.iloc[0], future, policy)
        if trade is None:
            rows.append(_skipped_row(policy["policy"], decision, cash, "INVALID_ENTRY"))
            continue
        affordability = calculate_affordability(
            pd.Series({"entry_price": trade["entry_price"], "stop_loss": trade["stop_loss"]}),
            cash,
            account_settings,
        )
        if affordability["affordability_status"] != EXECUTED:
            rows.append(_skipped_row(policy["policy"], decision, cash, "NOT_AFFORDABLE"))
            continue
        cash_before = cash
        shares = float(affordability["shares"])
        cash_after_entry = float(affordability["cash_remaining"])
        cash_after_exit = cash_after_entry + shares * float(trade["exit_price"]) - account_settings.commission_per_trade
        pnl = cash_after_exit - cash_before
        cash = cash_after_exit
        open_until = pd.Timestamp(trade["exit_date"])
        rows.append(
            {
                "sample_id": pd.NA,
                "policy": policy["policy"],
                "replay_date": replay_date.strftime("%Y-%m-%d"),
                "ticker": decision["ticker"],
                "entry_date": pd.Timestamp(trade["entry_date"]).strftime("%Y-%m-%d"),
                "entry_price": trade["entry_price"],
                "reference_price": decision["reference_price"],
                "entry_gap_pct": float(trade["entry_price"]) / float(decision["reference_price"]) - 1.0,
                "exit_date": pd.Timestamp(trade["exit_date"]).strftime("%Y-%m-%d"),
                "exit_price": trade["exit_price"],
                "exit_reason": trade["exit_reason"],
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
                "forward_return_20d": decision.get("forward_return_20d", pd.NA),
                "decision_strength": decision.get("decision_strength", pd.NA),
                "smoke_score": decision.get("smoke_score", pd.NA),
                "intraday_stop_breached": trade["intraday_stop_breached"],
                "breach_date": trade["breach_date"],
                "breach_low": trade["breach_low"],
                "breach_stop_price": trade["breach_stop_price"],
                "same_day_close": trade["same_day_close"],
                "same_day_recovered_above_stop": trade["same_day_recovered_above_stop"],
                "max_favorable_excursion_20d": trade["max_favorable_excursion_20d"],
                "max_adverse_excursion_20d": trade["max_adverse_excursion_20d"],
                "days_to_stop": trade["days_to_stop"],
                "days_to_max_adverse_20d": trade["days_to_max_adverse_20d"],
                "theme": ticker_theme(str(decision["ticker"])),
                "status": EXECUTED,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def simulate_single_trade(signal: pd.Series, future: pd.DataFrame, policy: dict) -> dict | None:
    entry = future.iloc[0]
    entry_price = first_valid(entry, ["open", "close"])
    if pd.isna(entry_price) or float(entry_price) <= 0:
        return None
    entry_price = float(entry_price)
    atr = signal_atr(signal, entry_price)
    stop_loss, target_1, target_2 = risk_levels(entry_price, atr, float(policy["atr_multiple"]))
    close_stop = stop_loss
    catastrophic_stop = entry_price - 3.0 * atr
    eval_window = future.head(20).copy()
    breach = intraday_breach(eval_window, close_stop)
    mfe = float(eval_window["high"].max() / entry_price - 1.0)
    mae = float(eval_window["low"].min() / entry_price - 1.0)
    days_to_stop = first_day_hit(eval_window, "low", close_stop, "le")
    days_to_max_adverse = int(eval_window["low"].idxmin()) + 1
    exit_row = eval_window.iloc[-1]
    exit_price = float(exit_row["close"])
    exit_reason = TIME_EXIT
    holding_days = int(len(eval_window))
    mode = policy["mode"]

    if mode == "time":
        pass
    elif mode == "close_next_open":
        for day_index, (_, day) in enumerate(eval_window.iterrows(), start=1):
            if float(day["close"]) <= close_stop:
                next_index = day_index
                if next_index < len(future):
                    next_day = future.iloc[next_index]
                    exit_row = next_day
                    exit_price = float(first_valid(next_day, ["open", "close"]))
                    holding_days = day_index + 1
                else:
                    exit_row = day
                    exit_price = float(day["close"])
                    holding_days = day_index
                exit_reason = STOP
                break
            hit = target_hit(day, target_1, target_2)
            if hit:
                exit_row, exit_price, exit_reason, holding_days = day, hit[1], hit[0], day_index
                break
    elif mode == "hybrid":
        for day_index, (_, day) in enumerate(eval_window.iterrows(), start=1):
            if float(day["low"]) <= catastrophic_stop:
                exit_row, exit_price, exit_reason, holding_days = day, catastrophic_stop, STOP, day_index
                break
            if float(day["close"]) <= close_stop:
                exit_row, exit_price, exit_reason, holding_days = day, close_stop, STOP, day_index
                break
            hit = target_hit(day, target_1, target_2)
            if hit:
                exit_row, exit_price, exit_reason, holding_days = day, hit[1], hit[0], day_index
                break
    elif mode == "close_stop":
        for day_index, (_, day) in enumerate(eval_window.iterrows(), start=1):
            if float(day["close"]) <= close_stop:
                exit_row, exit_price, exit_reason, holding_days = day, close_stop, STOP, day_index
                break
            hit = target_hit(day, target_1, target_2)
            if hit:
                exit_row, exit_price, exit_reason, holding_days = day, hit[1], hit[0], day_index
                break
    else:
        for day_index, (_, day) in enumerate(eval_window.iterrows(), start=1):
            if float(day["low"]) <= stop_loss:
                exit_row, exit_price, exit_reason, holding_days = day, stop_loss, STOP, day_index
                break
            hit = target_hit(day, target_1, target_2)
            if hit:
                exit_row, exit_price, exit_reason, holding_days = day, hit[1], hit[0], day_index
                break

    return {
        "entry_date": entry["date"],
        "entry_price": entry_price,
        "exit_date": exit_row["date"],
        "exit_price": float(exit_price),
        "exit_reason": exit_reason,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "holding_days": holding_days,
        "intraday_stop_breached": breach["intraday_stop_breached"],
        "breach_date": breach["breach_date"],
        "breach_low": breach["breach_low"],
        "breach_stop_price": close_stop,
        "same_day_close": breach["same_day_close"],
        "same_day_recovered_above_stop": breach["same_day_recovered_above_stop"],
        "max_favorable_excursion_20d": mfe,
        "max_adverse_excursion_20d": mae,
        "days_to_stop": days_to_stop,
        "days_to_max_adverse_20d": days_to_max_adverse,
    }


def policy_matrix_row(
    sample_id: int,
    replay_rounds: int,
    decisions: pd.DataFrame,
    phase1_summary: dict,
    trades: pd.DataFrame,
    account_settings: AccountSettings,
) -> dict:
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    buy_count = int(phase1_summary["buy_count"])
    no_trade_count = int(phase1_summary["no_trade_count"])
    wins = executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    losses = executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    top_profit_share, top_loss_share = ticker_profit_loss_shares(executed)
    row = {
        "sample_id": sample_id,
        "replay_rounds": replay_rounds,
        "policy": str(trades["policy"].dropna().iloc[0]) if not trades.empty and trades["policy"].notna().any() else "",
        "buy_count": buy_count,
        "no_trade_count": no_trade_count,
        "executed_count": int(len(executed)),
        "trade_simulation_accuracy": positive_rate(executed["pnl_dollars"]) if not executed.empty else pd.NA,
        "accuracy_1d": phase1_summary.get("accuracy_1d", pd.NA),
        "accuracy_3d": phase1_summary.get("accuracy_3d", pd.NA),
        "accuracy_5d": phase1_summary.get("accuracy_5d", pd.NA),
        "accuracy_10d": phase1_summary.get("accuracy_10d", pd.NA),
        "accuracy_20d": phase1_summary.get("accuracy_20d", pd.NA),
        "average_return_20d": phase1_summary.get("avg_forward_return_20d", pd.NA),
        "median_return_20d": phase1_summary.get("median_forward_return_20d", pd.NA),
        "average_win": mean(executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"]) if not executed.empty else pd.NA,
        "average_loss": mean(executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"]) if not executed.empty else pd.NA,
        "profit_factor": float(wins / abs(losses)) if losses < 0 else (float("inf") if wins > 0 else 0.0),
        "ending_account_value": float(executed["cash_after_exit"].iloc[-1]) if not executed.empty else account_settings.starting_capital,
        "max_drawdown": max_drawdown(executed, account_settings.starting_capital),
        "worst_trade_account_loss": float(executed["account_return_pct"].min()) if not executed.empty else pd.NA,
        "ending_value_excluding_best_trade": ending_excluding_best(executed, account_settings.starting_capital),
        "top_ticker_profit_share": top_profit_share,
        "top_ticker_loss_share": top_loss_share,
        "stop_count": int(executed["exit_reason"].eq(STOP).sum()) if not executed.empty else 0,
        "target_1_count": int(executed["exit_reason"].eq(TARGET_1).sum()) if not executed.empty else 0,
        "target_2_count": int(executed["exit_reason"].eq(TARGET_2).sum()) if not executed.empty else 0,
        "time_exit_count": int(executed["exit_reason"].eq(TIME_EXIT).sum()) if not executed.empty else 0,
        "median_holding_days": median(executed["holding_days"]) if not executed.empty else pd.NA,
        "average_entry_gap_pct": mean(executed["entry_gap_pct"]) if not executed.empty else pd.NA,
        "intraday_stop_breach_count": int(executed["intraday_stop_breached"].sum()) if not executed.empty else 0,
        "intraday_stop_breach_rate": float(executed["intraday_stop_breached"].mean()) if not executed.empty else pd.NA,
    }
    row["passes_phase1c_policy_gate"] = passes_phase1c_policy_gate(row)
    return row


def build_failure_trades(sample_id: int, baseline_trades: pd.DataFrame, decisions: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
    losing = baseline_trades.loc[(baseline_trades["status"].eq(EXECUTED)) & (baseline_trades["pnl_dollars"] < 0)].copy()
    if losing.empty:
        return pd.DataFrame()
    merged = losing.merge(
        decisions[["replay_date", "ticker", "decision_strength", "smoke_score"]],
        on=["replay_date", "ticker"],
        how="left",
        suffixes=("", "_decision"),
    )
    merged["sample_id"] = sample_id
    merged["stopped_out_then_20d_positive"] = merged["exit_reason"].eq(STOP) & merged["forward_return_20d"].gt(0)
    merged["failed_checks_at_selection"] = ""
    merged["sector_or_theme"] = merged["ticker"].map(ticker_theme).fillna("")
    return merged[
        [
            "sample_id",
            "replay_date",
            "ticker",
            "entry_date",
            "entry_price",
            "reference_price",
            "entry_gap_pct",
            "exit_date",
            "exit_reason",
            "pnl_dollars",
            "trade_return_pct",
            "account_return_pct",
            "forward_return_20d",
            "max_favorable_excursion_20d",
            "max_adverse_excursion_20d",
            "stopped_out_then_20d_positive",
            "intraday_stop_breached",
            "same_day_recovered_above_stop",
            "days_to_stop",
            "days_to_max_adverse_20d",
            "failed_checks_at_selection",
            "decision_strength",
            "smoke_score",
            "sector_or_theme",
        ]
    ].copy()


def build_close_stop_realism(sample_id: int, decisions: pd.DataFrame, data: pd.DataFrame, account_settings: AccountSettings, policy_trades: dict[str, pd.DataFrame]) -> pd.DataFrame:
    baseline = policy_trades["baseline_current"]
    close_policy = policy_trades["close_based_stop_2_0x"]
    confirmed = policy_trades["close_confirmed_stop_2_0x_next_open_exit"]
    hybrid = policy_trades["hybrid_close_stop_2_0x_intraday_catastrophic_3_0x"]
    keys = ["replay_date", "ticker"]
    merged = baseline.merge(close_policy, on=keys, how="outer", suffixes=("_baseline", "_close"))
    merged = merged.merge(confirmed[keys + ["pnl_dollars"]].rename(columns={"pnl_dollars": "close_confirmed_exit_pnl_dollars"}), on=keys, how="left")
    merged = merged.merge(hybrid[keys + ["pnl_dollars"]].rename(columns={"pnl_dollars": "hybrid_catastrophic_exit_pnl_dollars"}), on=keys, how="left")
    rows = []
    for _, row in merged.iterrows():
        breached = bool(row.get("intraday_stop_breached_close", False))
        differs = row.get("exit_reason_baseline") != row.get("exit_reason_close") or _num(row.get("pnl_dollars_baseline")) != _num(row.get("pnl_dollars_close"))
        if not breached and not differs:
            continue
        warning = "NO_WARNING"
        if breached:
            warning = "INTRADAY_STOP_BREACH_IGNORED_BY_CLOSE_STOP"
        if pd.notna(row.get("entry_gap_pct_close")) and float(row["entry_gap_pct_close"]) < -0.05:
            warning = "GAP_BEYOND_STOP"
        if row.get("exit_reason_close") == STOP and pd.notna(row.get("close_confirmed_exit_pnl_dollars")):
            warning = "CLOSE_STOP_REQUIRES_NEXT_OPEN_SLIPPAGE"
        if breached and _num(row.get("pnl_dollars_close")) > _num(row.get("pnl_dollars_baseline")):
            warning = "POLICY_TOO_OPTIMISTIC_FOR_RESEARCH_GATE"
        rows.append(
            {
                "sample_id": sample_id,
                "replay_date": row["replay_date"],
                "ticker": row["ticker"],
                "policy": "close_based_stop_2_0x",
                "baseline_exit_reason": row.get("exit_reason_baseline", ""),
                "close_based_exit_reason": row.get("exit_reason_close", ""),
                "baseline_pnl_dollars": row.get("pnl_dollars_baseline", pd.NA),
                "close_based_pnl_dollars": row.get("pnl_dollars_close", pd.NA),
                "intraday_low_breached_close_stop": breached,
                "breach_date": row.get("breach_date_close", ""),
                "breach_low": row.get("breach_low_close", pd.NA),
                "breach_stop_price": row.get("breach_stop_price_close", pd.NA),
                "same_day_close": row.get("same_day_close_close", pd.NA),
                "same_day_recovered_above_stop": row.get("same_day_recovered_above_stop_close", pd.NA),
                "next_day_open_after_close_stop": pd.NA,
                "close_confirmed_exit_pnl_dollars": row.get("close_confirmed_exit_pnl_dollars", pd.NA),
                "hybrid_catastrophic_exit_pnl_dollars": row.get("hybrid_catastrophic_exit_pnl_dollars", pd.NA),
                "realism_warning": warning,
            }
        )
    return pd.DataFrame(rows)


def build_regime_attribution(sample_id: int, trades: pd.DataFrame) -> pd.DataFrame:
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    if executed.empty:
        return pd.DataFrame()
    executed["period"] = pd.to_datetime(executed["replay_date"]).dt.to_period("M").astype(str)
    rows = []
    for (period, policy), group in executed.groupby(["period", "policy"]):
        worst = group.loc[group["pnl_dollars"].idxmin()]
        rows.append(
            {
                "sample_id": sample_id,
                "period": period,
                "policy": policy,
                "trade_count": int(len(group)),
                "win_count": int(group["pnl_dollars"].gt(0).sum()),
                "loss_count": int(group["pnl_dollars"].lt(0).sum()),
                "total_pnl_dollars": float(group["pnl_dollars"].sum()),
                "average_pnl_dollars": float(group["pnl_dollars"].mean()),
                "max_drawdown_contribution": max_drawdown_from_pnl(group["pnl_dollars"], 0.0),
                "tickers_in_period": ", ".join(sorted(group["ticker"].unique())),
                "worst_ticker": worst["ticker"],
                "worst_trade_pnl_dollars": float(worst["pnl_dollars"]),
                "average_entry_gap_pct": mean(group["entry_gap_pct"]),
                "average_forward_return_20d": mean(group["forward_return_20d"]),
                "themes_in_period": ", ".join(sorted(set(group["theme"].dropna()))),
            }
        )
    return pd.DataFrame(rows)


def summarize_phase1c(matrix: pd.DataFrame, failure_trades: pd.DataFrame, close_realism: pd.DataFrame, regime: pd.DataFrame) -> dict:
    best_by_median = policy_rank_by_median(matrix)
    realistic = matrix.loc[~matrix["policy"].astype(str).str.contains("close_based_stop_2_0x$|with_intraday_breach_flag", regex=True)].copy()
    best_realistic = policy_rank_by_median(realistic)
    passing_counts = matrix.groupby("policy")["passes_phase1c_policy_gate"].sum().astype(int).to_dict() if not matrix.empty else {}
    worst_samples = (
        matrix.sort_values(["policy", "ending_account_value"]).groupby("policy").head(1)[["policy", "sample_id", "ending_account_value", "max_drawdown"]]
        if not matrix.empty
        else pd.DataFrame()
    )
    status = phase1c_status(matrix, close_realism)
    return {
        "phase_1c_status": status,
        "best_policy_by_median": best_by_median,
        "best_realistic_policy": best_realistic,
        "passing_counts": passing_counts,
        "worst_samples": worst_samples,
        "close_realism_warning_count": int(close_realism["realism_warning"].ne("NO_WARNING").sum()) if not close_realism.empty else 0,
        "intraday_breach_ignored_count": int(close_realism["intraday_low_breached_close_stop"].sum()) if not close_realism.empty else 0,
        "failure_trade_count": int(len(failure_trades)),
        "problem_diagnosis": problem_diagnosis(matrix, failure_trades, close_realism),
    }


def phase1c_status(matrix: pd.DataFrame, close_realism: pd.DataFrame) -> str:
    if matrix.empty:
        return PHASE_1C_FAILED
    medians = matrix.groupby("policy")["ending_account_value"].median()
    if not medians.gt(100.0).any():
        return PHASE_1C_FAILED
    if close_realism_warning_dominates(close_realism):
        return PHASE_1C_EXECUTION_HYPOTHESIS_NEEDS_REALISM_WORK
    if matrix.groupby("policy")["passes_phase1c_policy_gate"].any().any():
        return PHASE_1C_ROBUSTNESS_PROMISING_NOT_APPROVED
    weak_accuracy_samples = matrix.loc[matrix["policy"].eq("baseline_current"), "accuracy_20d"].le(0.50).sum()
    if weak_accuracy_samples >= 2:
        return PHASE_1C_NEEDS_ENTRY_RULE_WORK
    return PHASE_1C_EXECUTION_HYPOTHESIS_NEEDS_REALISM_WORK


def passes_phase1c_policy_gate(row: dict) -> bool:
    return bool(
        float(row["ending_account_value"]) > 120.0
        and float(row["max_drawdown"]) > -0.35
        and not pd.isna(row["trade_simulation_accuracy"])
        and float(row["trade_simulation_accuracy"]) >= 0.50
        and int(row["buy_count"]) >= 20
        and float(row["ending_value_excluding_best_trade"]) > 105.0
        and (pd.isna(row["top_ticker_profit_share"]) or float(row["top_ticker_profit_share"]) <= 0.50)
    )


def write_phase1c_reports(
    matrix: pd.DataFrame,
    failure_trades: pd.DataFrame,
    close_realism: pd.DataFrame,
    regime: pd.DataFrame,
    summary: dict,
    matrix_csv_path: str | Path,
    failure_csv_path: str | Path,
    realism_csv_path: str | Path,
    regime_csv_path: str | Path,
    summary_md_path: str | Path,
) -> None:
    paths = [Path(matrix_csv_path), Path(failure_csv_path), Path(realism_csv_path), Path(regime_csv_path), Path(summary_md_path)]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(matrix_csv_path, index=False)
    failure_trades.to_csv(failure_csv_path, index=False)
    close_realism.to_csv(realism_csv_path, index=False)
    regime.to_csv(regime_csv_path, index=False)
    Path(summary_md_path).write_text(summary_markdown(summary, matrix, failure_trades, close_realism, regime), encoding="utf-8")


def summary_markdown(summary: dict, matrix: pd.DataFrame, failure_trades: pd.DataFrame, close_realism: pd.DataFrame, regime: pd.DataFrame) -> str:
    lines = [
        "PHOENIX NANO PHASE 1C — ROBUSTNESS FAILURE ANALYSIS AND CLOSE-STOP REALISM",
        "",
        "Research/manual-review only. Do not start paper trading or live trading.",
        "",
        "## Phase 1B Recap",
        "",
        "- Phase 1B found close_based_stop_2_0x promising on the baseline sample but not approved.",
        "- Phase 1C keeps ticker/date selections frozen and tests robustness plus stop realism.",
        "",
        "## Policy Robustness Matrix Summary",
        "",
        policy_summary_table(matrix).to_markdown(index=False) if not matrix.empty else "No policy matrix rows.",
        "",
        f"- Best policy by median ending value: {summary['best_policy_by_median'] or 'none'}",
        f"- Best realistic policy after intraday-breach penalties: {summary['best_realistic_policy'] or 'none'}",
        f"- Close-stop realism warnings: {summary['close_realism_warning_count']}",
        f"- Intraday breaches ignored by close-stop candidates: {summary['intraday_breach_ignored_count']}",
        "",
        "## Worst Sample Per Policy",
        "",
        summary["worst_samples"].to_markdown(index=False) if not summary["worst_samples"].empty else "No worst-sample rows.",
        "",
        "## Sample 3 And 4 Failure Explanation",
        "",
        sample_failure_summary(matrix, failure_trades),
        "",
        "## Close-Based Stop Realism Findings",
        "",
        close_realism_summary(close_realism),
        "",
        "## Regime And Theme Attribution",
        "",
        regime_summary(regime),
        "",
        "## Entry Rule vs Execution Rule",
        "",
        summary["problem_diagnosis"],
        "",
        f"## Phase 1C Status: {summary['phase_1c_status']}",
        "",
        "Do not start paper trading or live trading.",
        "",
        "## Next Research Task Recommendation",
        "",
        "Analyze failing samples 3 and 4 at entry-rule level before considering any execution-policy adoption.",
        "",
    ]
    return "\n".join(lines)


def sample_failed(sample_matrix: pd.DataFrame, phase1_summary: dict) -> bool:
    baseline = sample_matrix.loc[sample_matrix["policy"].eq("baseline_current")]
    if baseline.empty:
        return True
    row = baseline.iloc[0]
    return bool(
        float(row["ending_account_value"]) <= 100.0
        or float(row["max_drawdown"]) <= -0.35
        or (not pd.isna(row["trade_simulation_accuracy"]) and float(row["trade_simulation_accuracy"]) < 0.50)
        or (not pd.isna(phase1_summary.get("accuracy_20d")) and float(phase1_summary["accuracy_20d"]) <= 0.50)
    )


def target_hit(day: pd.Series, target_1: float, target_2: float) -> tuple[str, float] | None:
    if not pd.isna(day["high"]) and float(day["high"]) >= target_2:
        return TARGET_2, target_2
    if not pd.isna(day["high"]) and float(day["high"]) >= target_1:
        return TARGET_1, target_1
    return None


def intraday_breach(future: pd.DataFrame, stop_price: float) -> dict:
    for _, day in future.iterrows():
        if float(day["low"]) <= stop_price:
            return {
                "intraday_stop_breached": True,
                "breach_date": pd.Timestamp(day["date"]).strftime("%Y-%m-%d"),
                "breach_low": float(day["low"]),
                "same_day_close": float(day["close"]),
                "same_day_recovered_above_stop": bool(float(day["close"]) > stop_price),
            }
    return {
        "intraday_stop_breached": False,
        "breach_date": "",
        "breach_low": pd.NA,
        "same_day_close": pd.NA,
        "same_day_recovered_above_stop": False,
    }


def first_day_hit(future: pd.DataFrame, column: str, level: float, direction: str) -> object:
    for index, (_, row) in enumerate(future.iterrows(), start=1):
        if direction == "le" and float(row[column]) <= level:
            return index
        if direction == "ge" and float(row[column]) >= level:
            return index
    return pd.NA


def risk_levels(entry_price: float, atr: float, atr_multiple: float) -> tuple[float, float, float]:
    if atr_multiple <= 0:
        return 0.0, float("inf"), float("inf")
    stop = entry_price - atr_multiple * atr
    risk = max(0.0, entry_price - stop)
    return float(stop), float(entry_price + 2.0 * risk), float(entry_price + 4.0 * risk)


def signal_atr(signal: pd.Series, entry_price: float) -> float:
    atr = signal.get("atr", pd.NA)
    return entry_price * 0.08 / 1.5 if pd.isna(atr) or float(atr) <= 0 else float(atr)


def first_valid(row: pd.Series, columns: list[str]) -> object:
    for column in columns:
        value = row.get(column, pd.NA)
        if not pd.isna(value):
            return value
    return pd.NA


def ticker_theme(ticker: str) -> str:
    return THEME_MAP.get(ticker, "")


def _skipped_row(policy: str, decision: pd.Series, cash: float, status: str) -> dict:
    return {
        "sample_id": pd.NA,
        "policy": policy,
        "replay_date": pd.Timestamp(decision["replay_date"]).strftime("%Y-%m-%d"),
        "ticker": decision["ticker"],
        "cash_before": cash,
        "cash_after_exit": cash,
        "pnl_dollars": pd.NA,
        "status": status,
    }


def ticker_profit_loss_shares(executed: pd.DataFrame) -> tuple[object, object]:
    if executed.empty:
        return pd.NA, pd.NA
    profits = executed.loc[executed["pnl_dollars"] > 0].groupby("ticker")["pnl_dollars"].sum()
    losses = executed.loc[executed["pnl_dollars"] < 0].groupby("ticker")["pnl_dollars"].sum().abs()
    profit_share = float(profits.max() / profits.sum()) if profits.sum() > 0 else pd.NA
    loss_share = float(losses.max() / losses.sum()) if losses.sum() > 0 else pd.NA
    return profit_share, loss_share


def max_drawdown(executed: pd.DataFrame, starting_capital: float) -> float:
    if executed.empty:
        return 0.0
    equity = pd.Series([starting_capital, *executed["cash_after_exit"].tolist()])
    return float((equity / equity.cummax() - 1.0).min())


def max_drawdown_from_pnl(pnl: pd.Series, starting_capital: float) -> float:
    equity = starting_capital + pd.to_numeric(pnl, errors="coerce").fillna(0.0).cumsum()
    if starting_capital == 0:
        return float(pd.to_numeric(pnl, errors="coerce").min()) if len(pnl) else 0.0
    equity = pd.concat([pd.Series([starting_capital]), equity], ignore_index=True)
    return float((equity / equity.cummax() - 1.0).min())


def ending_excluding_best(executed: pd.DataFrame, starting_capital: float) -> float:
    if executed.empty:
        return starting_capital
    return float(starting_capital + executed.drop(index=executed["pnl_dollars"].idxmax())["pnl_dollars"].sum())


def policy_rank_by_median(matrix: pd.DataFrame) -> str:
    if matrix.empty:
        return ""
    ranked = matrix.groupby("policy")["ending_account_value"].median().sort_values(ascending=False)
    return str(ranked.index[0]) if len(ranked) else ""


def policy_summary_table(matrix: pd.DataFrame) -> pd.DataFrame:
    if matrix.empty:
        return pd.DataFrame()
    grouped = matrix.groupby("policy").agg(
        samples=("sample_id", "nunique"),
        median_ending_account_value=("ending_account_value", "median"),
        worst_ending_account_value=("ending_account_value", "min"),
        median_max_drawdown=("max_drawdown", "median"),
        worst_max_drawdown=("max_drawdown", "min"),
        median_trade_accuracy=("trade_simulation_accuracy", "median"),
        passing_samples=("passes_phase1c_policy_gate", "sum"),
        intraday_breach_rate=("intraday_stop_breach_rate", "median"),
    )
    return grouped.reset_index().sort_values("median_ending_account_value", ascending=False)


def close_realism_warning_dominates(close_realism: pd.DataFrame) -> bool:
    if close_realism.empty:
        return False
    warnings = close_realism["realism_warning"].ne("NO_WARNING").sum()
    return bool(warnings >= max(3, len(close_realism) * 0.25))


def problem_diagnosis(matrix: pd.DataFrame, failure_trades: pd.DataFrame, close_realism: pd.DataFrame) -> str:
    weak_samples = matrix.loc[matrix["policy"].eq("baseline_current")]
    weak_accuracy = int(weak_samples["accuracy_20d"].le(0.50).sum()) if not weak_samples.empty else 0
    warnings = int(close_realism["realism_warning"].ne("NO_WARNING").sum()) if not close_realism.empty else 0
    if weak_accuracy >= 2:
        return "Current evidence points to entry-rule weakness in multiple deterministic samples, not just exit mechanics."
    if warnings:
        return "Current evidence points to execution-rule realism risk: close-based stops improve results while ignoring intraday stress."
    return "Current evidence is mixed; execution assumptions improve some samples, but robustness is not strong enough for approval."


def sample_failure_summary(matrix: pd.DataFrame, failure_trades: pd.DataFrame) -> str:
    if failure_trades.empty:
        return "No failing-sample losing trades were captured."
    focus = failure_trades.loc[failure_trades["sample_id"].isin([3, 4])]
    if focus.empty:
        focus = failure_trades
    themes = focus["sector_or_theme"].replace("", "unmapped").value_counts().head(5).to_dict()
    tickers = focus["ticker"].value_counts().head(8).to_dict()
    avg_gap = mean(focus["entry_gap_pct"])
    return (
        f"Failing trades concentrated in tickers {tickers}. Theme counts: {themes}. "
        f"Average entry gap among captured failing trades: {format_percent(avg_gap)}."
    )


def close_realism_summary(close_realism: pd.DataFrame) -> str:
    if close_realism.empty:
        return "No close-stop realism exceptions were found."
    warnings = close_realism["realism_warning"].value_counts().to_dict()
    breaches = int(close_realism["intraday_low_breached_close_stop"].sum())
    return f"Close-stop realism rows: {len(close_realism)}. Intraday breaches: {breaches}. Warning mix: {warnings}."


def regime_summary(regime: pd.DataFrame) -> str:
    if regime.empty:
        return "No regime attribution rows were generated."
    worst = regime.sort_values("total_pnl_dollars").head(5)
    return "Worst period-policy rows: " + "; ".join(
        f"{row.sample_id}/{row.period}/{row.policy}/{row.worst_ticker}:{row.total_pnl_dollars:.2f}" for row in worst.itertuples()
    )


def positive_rate(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float((clean > 0).mean())


def mean(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.mean())


def median(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.median())


def _num(value: object) -> float:
    return 0.0 if pd.isna(value) else float(value)


def format_percent(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value) * 100:.2f}%"
