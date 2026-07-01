from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED, calculate_affordability
from src.backtest.nano_daily_scan import _score_latest_candidates
from src.backtest.smoke_test import SMOKE_RANK_FACTORS
from src.research.auto_loop import CandidateRule
from src.trading.trade_simulator import simulate_trades


HISTORICAL_BUY_CANDIDATE = "HISTORICAL_BUY_CANDIDATE"
HISTORICAL_NO_TRADE = "HISTORICAL_NO_TRADE"
PHASE_1A_FAILED = "PHASE_1A_FAILED"
PHASE_1A_NEEDS_MORE_ITERATION = "PHASE_1A_NEEDS_MORE_ITERATION"
PHASE_1A_PROMISING_NOT_READY = "PHASE_1A_PROMISING_NOT_READY"
FORWARD_WINDOWS = [1, 3, 5, 10, 20]


def build_phase1_historical_replay(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_rounds: int = 100,
    benchmark_ticker: str = "SPY",
    replay_sample_offset: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    required = {"date", "ticker", "open", "high", "low", "close", "atr", *SMOKE_RANK_FACTORS}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Historical replay missing required columns: {', '.join(sorted(missing))}")

    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["date", "ticker"]).reset_index(drop=True)

    replay_dates = sample_replay_dates(
        frame,
        replay_rounds,
        benchmark_ticker=benchmark_ticker,
        replay_sample_offset=replay_sample_offset,
    )
    decisions: list[dict] = []
    near_miss_frames: list[pd.DataFrame] = []
    cash = float(account_settings.starting_capital)
    open_until = pd.Timestamp.min

    for replay_date in replay_dates:
        if replay_date <= open_until:
            decisions.append(_no_trade_row(replay_date, "POSITION_OPEN", cash))
            continue

        latest = _latest_replay_slice(frame, replay_date, benchmark_ticker)
        replay_account = AccountSettings(
            starting_capital=cash,
            fractional_shares=account_settings.fractional_shares,
            max_position_fraction=account_settings.max_position_fraction,
            min_cash_reserve=account_settings.min_cash_reserve,
            commission_per_trade=account_settings.commission_per_trade,
            slippage_bps=account_settings.slippage_bps,
        )
        scored, rejected = _score_latest_candidates(latest, rule, replay_account)
        if not scored.empty:
            near = scored.head(5).copy()
            near["replay_date"] = replay_date.strftime("%Y-%m-%d")
            near["row_type"] = "EXECUTABLE_NEAR_MISS"
            near_miss_frames.append(near)
        if not rejected.empty:
            rejected_sample = rejected.head(10).copy()
            rejected_sample["replay_date"] = replay_date.strftime("%Y-%m-%d")
            rejected_sample["row_type"] = "REJECTED_BEFORE_NANO_RANKING"
            near_miss_frames.append(rejected_sample)

        passed = scored.loc[scored["all_rule_checks_passed"]].copy() if not scored.empty else pd.DataFrame()
        if passed.empty:
            decisions.append(_no_trade_row(replay_date, "NO_CANDIDATE_PASSED_RULES", cash, scored, rejected))
            continue

        candidate = passed.sort_values(["decision_strength", "smoke_score", "ticker"], ascending=[False, False, True]).iloc[0]
        signal_row = _signal_row_for_trade(latest, candidate, rule)
        trade = simulate_trades(pd.DataFrame([signal_row]), frame, benchmark_ticker=benchmark_ticker)
        decision = _buy_decision_row(replay_date, candidate, latest, cash, scored, rejected)
        decision.update(_forward_return_labels(latest, candidate["ticker"]))

        if trade.empty:
            decision.update(_unexecuted_trade_fields(cash, "NO_FUTURE_TRADE_DATA"))
            decisions.append(decision)
            continue

        trade_row = trade.iloc[0]
        affordability = calculate_affordability(trade_row, cash, account_settings)
        if affordability["affordability_status"] != EXECUTED:
            decision.update(_unexecuted_trade_fields(cash, "ENTRY_NOT_AFFORDABLE"))
            decisions.append(decision)
            continue

        cash_before = cash
        cash_after_entry = float(affordability["cash_remaining"])
        shares = float(affordability["shares"])
        exit_value = shares * float(trade_row["exit_price"])
        cash_after_exit = cash_after_entry + exit_value - account_settings.commission_per_trade
        pnl = cash_after_exit - cash_before
        cash = cash_after_exit
        open_until = pd.Timestamp(trade_row["exit_date"])
        decision.update(
            {
                "trade_simulation_status": EXECUTED,
                "entry_date": trade_row["entry_date"],
                "exit_date": trade_row["exit_date"],
                "exit_reason": trade_row["exit_reason"],
                "entry_price": float(trade_row["entry_price"]),
                "exit_price": float(trade_row["exit_price"]),
                "shares": affordability["shares"],
                "cash_before": cash_before,
                "cash_after_exit": cash_after_exit,
                "pnl_dollars": pnl,
                "trade_return_pct": float(trade_row["realized_return"]),
                "account_return_pct": pnl / cash_before if cash_before else pd.NA,
            }
        )
        decisions.append(decision)

    decisions_frame = pd.DataFrame(decisions)
    near_misses = pd.concat(near_miss_frames, ignore_index=True) if near_miss_frames else pd.DataFrame()
    summary = summarize_phase1_replay(decisions_frame, account_settings)
    return decisions_frame, near_misses, summary


def sample_replay_dates(
    data: pd.DataFrame,
    replay_rounds: int,
    benchmark_ticker: str = "SPY",
    replay_sample_offset: int = 0,
) -> list[pd.Timestamp]:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    required_signal_columns = ["close", "atr", *SMOKE_RANK_FACTORS]
    forward_20 = "fwd_return_20d"
    research = frame.loc[~frame["ticker"].eq(benchmark_ticker)].dropna(subset=required_signal_columns).copy()
    if forward_20 in research.columns:
        research = research.loc[research[forward_20].notna()].copy()
    dates = sorted(pd.Timestamp(date).normalize() for date in research["date"].dropna().unique())
    if len(dates) < replay_rounds:
        raise ValueError(f"Only {len(dates)} eligible replay dates available for {replay_rounds} rounds.")
    if replay_rounds <= 0:
        raise ValueError("replay_rounds must be positive.")
    if replay_rounds == 1:
        return [dates[-1]]
    positions = [
        min(len(dates) - 1, round(index * (len(dates) - 1) / (replay_rounds - 1)) + max(0, replay_sample_offset))
        for index in range(replay_rounds)
    ]
    sampled = [dates[position] for position in positions]
    deduped: list[pd.Timestamp] = []
    used: set[pd.Timestamp] = set()
    for position in positions:
        cursor = position
        while cursor < len(dates) and dates[cursor] in used:
            cursor += 1
        if cursor >= len(dates):
            cursor = position
            while cursor >= 0 and dates[cursor] in used:
                cursor -= 1
        value = dates[cursor]
        used.add(value)
        deduped.append(value)
    return deduped if len(deduped) == replay_rounds else sampled


def summarize_phase1_replay(decisions: pd.DataFrame, account_settings: AccountSettings) -> dict:
    total_rounds = int(len(decisions))
    buys = decisions.loc[decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)].copy() if not decisions.empty else pd.DataFrame()
    executed = buys.loc[buys["trade_simulation_status"].eq(EXECUTED)].copy() if not buys.empty else pd.DataFrame()
    buy_count = int(len(buys))
    no_trade_count = int(total_rounds - buy_count)
    summary = {
        "total_replay_rounds": total_rounds,
        "buy_count": buy_count,
        "no_trade_count": no_trade_count,
        "buy_rate": float(buy_count / total_rounds) if total_rounds else 0.0,
    }
    for window in FORWARD_WINDOWS:
        column = f"forward_return_{window}d"
        summary[f"accuracy_{window}d"] = _positive_rate(buys[column]) if column in buys.columns else pd.NA
        summary[f"avg_forward_return_{window}d"] = _mean(buys[column]) if column in buys.columns else pd.NA
        summary[f"median_forward_return_{window}d"] = _median(buys[column]) if column in buys.columns else pd.NA

    summary["trade_simulation_accuracy"] = _positive_rate(executed["pnl_dollars"]) if not executed.empty else pd.NA
    summary["average_win_size"] = _mean(executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"]) if not executed.empty else pd.NA
    summary["average_loss_size"] = _mean(executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"]) if not executed.empty else pd.NA
    wins = executed.loc[executed["pnl_dollars"] > 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    losses = executed.loc[executed["pnl_dollars"] < 0, "pnl_dollars"].sum() if not executed.empty else 0.0
    summary["profit_factor"] = float(wins / abs(losses)) if losses < 0 else (float("inf") if wins > 0 else 0.0)
    summary["ending_account_value"] = (
        float(executed["cash_after_exit"].iloc[-1]) if not executed.empty else float(account_settings.starting_capital)
    )
    summary["max_drawdown"] = _max_drawdown(executed, account_settings.starting_capital)
    summary["worst_trade_account_loss"] = (
        float(executed["account_return_pct"].min()) if not executed.empty else pd.NA
    )
    summary["best_pick"] = _pick_label(buys.loc[buys["forward_return_20d"].idxmax()]) if buy_count and buys["forward_return_20d"].notna().any() else ""
    summary["worst_pick"] = _pick_label(buys.loc[buys["forward_return_20d"].idxmin()]) if buy_count and buys["forward_return_20d"].notna().any() else ""
    summary["top_selected_tickers"] = (
        ", ".join(f"{ticker}:{count}" for ticker, count in buys["ticker"].value_counts().head(10).items())
        if buy_count
        else ""
    )
    summary["phase_1a_status"] = _phase_status(summary)
    return summary


def write_phase1_historical_replay_reports(
    decisions: pd.DataFrame,
    near_misses: pd.DataFrame,
    summary: dict,
    decisions_csv_path: str | Path,
    summary_md_path: str | Path,
    near_misses_csv_path: str | Path,
) -> None:
    decisions_path = Path(decisions_csv_path)
    summary_path = Path(summary_md_path)
    near_misses_path = Path(near_misses_csv_path)
    decisions_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    near_misses_path.parent.mkdir(parents=True, exist_ok=True)
    decisions.to_csv(decisions_path, index=False)
    near_misses.to_csv(near_misses_path, index=False)
    summary_path.write_text(_summary_markdown(summary, decisions), encoding="utf-8")


def _latest_replay_slice(frame: pd.DataFrame, replay_date: pd.Timestamp, benchmark_ticker: str) -> pd.DataFrame:
    latest = frame.loc[(frame["date"].eq(replay_date)) & (~frame["ticker"].eq(benchmark_ticker))].copy()
    return latest.dropna(subset=["date", "ticker", "close", *SMOKE_RANK_FACTORS])


def _signal_row_for_trade(latest: pd.DataFrame, candidate: pd.Series, rule: CandidateRule) -> dict:
    source = latest.loc[latest["ticker"].eq(candidate["ticker"])].iloc[0].to_dict()
    source.update(
        {
            "candidate_id": rule.candidate_id,
            "decision_strength": candidate["decision_strength"],
            "window_start": "",
            "window_end": "",
        }
    )
    return source


def _buy_decision_row(
    replay_date: pd.Timestamp,
    candidate: pd.Series,
    latest: pd.DataFrame,
    cash: float,
    scored: pd.DataFrame,
    rejected: pd.DataFrame,
) -> dict:
    return {
        "replay_date": replay_date.strftime("%Y-%m-%d"),
        "decision": HISTORICAL_BUY_CANDIDATE,
        "ticker": candidate["ticker"],
        "reason": "Candidate 34 Nano rule passed with replay-date $100 whole-share affordability.",
        "reference_price": float(candidate["reference_price"]),
        "shares_with_cash": candidate["shares_with_100"],
        "estimated_total_cost": candidate["estimated_total_cost"],
        "estimated_cash_remaining": candidate["estimated_cash_remaining"],
        "cash_before_decision": cash,
        "smoke_score": candidate["smoke_score"],
        "decision_strength": candidate["decision_strength"],
        "relative_volume_prev20": candidate["relative_volume_prev20"],
        "return_5d": candidate["return_5d"],
        "return_20d": candidate["return_20d"],
        "distance_to_52w_high_prev": candidate["distance_to_52w_high_prev"],
        "dollar_volume": candidate["dollar_volume"],
        "executable_universe_count": int(len(scored)),
        "rejected_before_ranking_count": int(len(rejected)),
    }


def _no_trade_row(
    replay_date: pd.Timestamp,
    reason: str,
    cash: float,
    scored: pd.DataFrame | None = None,
    rejected: pd.DataFrame | None = None,
) -> dict:
    scored = scored if scored is not None else pd.DataFrame()
    rejected = rejected if rejected is not None else pd.DataFrame()
    return {
        "replay_date": replay_date.strftime("%Y-%m-%d"),
        "decision": HISTORICAL_NO_TRADE,
        "ticker": "",
        "reason": reason,
        "reference_price": pd.NA,
        "shares_with_cash": 0,
        "estimated_total_cost": 0.0,
        "estimated_cash_remaining": cash,
        "cash_before_decision": cash,
        "smoke_score": pd.NA,
        "decision_strength": pd.NA,
        "relative_volume_prev20": pd.NA,
        "return_5d": pd.NA,
        "return_20d": pd.NA,
        "distance_to_52w_high_prev": pd.NA,
        "dollar_volume": pd.NA,
        "executable_universe_count": int(len(scored)),
        "rejected_before_ranking_count": int(len(rejected)),
        **{f"forward_return_{window}d": pd.NA for window in FORWARD_WINDOWS},
        **_unexecuted_trade_fields(cash, ""),
    }


def _forward_return_labels(latest: pd.DataFrame, ticker: str) -> dict:
    row = latest.loc[latest["ticker"].eq(ticker)].iloc[0]
    labels = {}
    for window in FORWARD_WINDOWS:
        source = f"fwd_return_{window}d"
        labels[f"forward_return_{window}d"] = row[source] if source in row.index else pd.NA
    return labels


def _unexecuted_trade_fields(cash: float, status: str) -> dict:
    return {
        "trade_simulation_status": status,
        "entry_date": "",
        "exit_date": "",
        "exit_reason": "",
        "entry_price": pd.NA,
        "exit_price": pd.NA,
        "shares": 0,
        "cash_before": cash,
        "cash_after_exit": cash,
        "pnl_dollars": pd.NA,
        "trade_return_pct": pd.NA,
        "account_return_pct": pd.NA,
    }


def _summary_markdown(summary: dict, decisions: pd.DataFrame) -> str:
    lines = [
        "PHOENIX NANO PHASE 1A — 100 HISTORICAL REPLAY ROUNDS",
        "",
        "Research/manual-review only. This does not start paper trading or live trading.",
        "",
        "## Summary",
        "",
        f"- Phase 1A status: {summary['phase_1a_status']}",
        f"- Total replay rounds: {summary['total_replay_rounds']}",
        f"- BUY count: {summary['buy_count']}",
        f"- NO_TRADE count: {summary['no_trade_count']}",
        f"- BUY rate: {_format_percent(summary['buy_rate'])}",
        f"- Ending account value: {_format_money(summary['ending_account_value'])}",
        f"- Max drawdown: {_format_percent(summary['max_drawdown'])}",
        f"- Profit factor: {_format_number(summary['profit_factor'])}",
        "",
        "## Accuracy",
        "",
    ]
    for window in FORWARD_WINDOWS:
        lines.append(f"- {window}d accuracy: {_format_percent(summary[f'accuracy_{window}d'])}")
        lines.append(f"- {window}d average forward return: {_format_percent(summary[f'avg_forward_return_{window}d'])}")
        lines.append(f"- {window}d median forward return: {_format_percent(summary[f'median_forward_return_{window}d'])}")
    lines.extend(
        [
            f"- Trade-simulation accuracy: {_format_percent(summary['trade_simulation_accuracy'])}",
            f"- Average win size: {_format_money(summary['average_win_size'])}",
            f"- Average loss size: {_format_money(summary['average_loss_size'])}",
            f"- Worst trade account loss: {_format_percent(summary['worst_trade_account_loss'])}",
            "",
            "## Picks",
            "",
            f"- Best pick: {summary['best_pick'] or 'none'}",
            f"- Worst pick: {summary['worst_pick'] or 'none'}",
            f"- Top selected tickers: {summary['top_selected_tickers'] or 'none'}",
            "",
            "## Decision Counts",
            "",
            decisions["decision"].value_counts().rename_axis("decision").reset_index(name="count").to_markdown(index=False)
            if not decisions.empty
            else "No decisions.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _phase_status(summary: dict) -> str:
    ending = float(summary.get("ending_account_value", 0.0))
    accuracy_20d = summary.get("accuracy_20d", pd.NA)
    drawdown = float(summary.get("max_drawdown", 0.0))
    trade_accuracy = summary.get("trade_simulation_accuracy", pd.NA)
    buy_count = int(summary.get("buy_count", 0))
    if ending <= 100.0 or (not pd.isna(accuracy_20d) and float(accuracy_20d) <= 0.45):
        return PHASE_1A_FAILED
    if ending > 120.0 and drawdown > -0.35 and not pd.isna(trade_accuracy) and float(trade_accuracy) >= 0.50 and buy_count >= 20:
        return PHASE_1A_PROMISING_NOT_READY
    return PHASE_1A_NEEDS_MORE_ITERATION


def _max_drawdown(executed: pd.DataFrame, starting_capital: float) -> float:
    if executed.empty:
        return 0.0
    equity = pd.Series([starting_capital, *executed["cash_after_exit"].tolist()])
    return float((equity / equity.cummax() - 1.0).min())


def _positive_rate(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float((clean > 0).mean())


def _mean(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.mean())


def _median(series: pd.Series) -> object:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return pd.NA if clean.empty else float(clean.median())


def _pick_label(row: pd.Series) -> str:
    return f"{row['replay_date']} {row['ticker']} 20d={_format_percent(row['forward_return_20d'])}"


def _format_percent(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value) * 100:.2f}%"


def _format_money(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"${float(value):.2f}"


def _format_number(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    if value == float("inf"):
        return "inf"
    return f"{float(value):.4f}"
