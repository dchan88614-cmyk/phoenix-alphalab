from __future__ import annotations

from collections import Counter
from pathlib import Path
from math import floor

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.backtest.smoke_test import SMOKE_RANK_FACTORS


MILESTONES = [150, 200, 300, 500, 1000]
NO_TRADE = "NO_TRADE"
BUY = "BUY"
POSITION_OPEN = "POSITION_OPEN"


def build_phase1c_continuous_account_backtest(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    start: str,
    end: str,
    benchmark_ticker: str = "SPY",
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    required = {"date", "ticker", "open", "high", "low", "close", "atr", *SMOKE_RANK_FACTORS}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Phase 1C continuous account missing required columns: {', '.join(sorted(missing))}")

    frame = _prepare_features(data)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    replay_dates = sorted(
        pd.Timestamp(value)
        for value in frame.loc[
            frame["date"].between(start_ts, end_ts) & ~frame["ticker"].isin([benchmark_ticker, "QQQ"]), "date"
        ].dropna().unique()
    )
    by_ticker = {ticker: group.sort_values("date").reset_index(drop=True) for ticker, group in frame.groupby("ticker")}

    cash = float(account_settings.starting_capital)
    open_until = pd.Timestamp.min
    trades: list[dict] = []
    equity_rows: list[dict] = [
        _equity_row("", "START", "", account_settings.starting_capital, cash, "", "", 0, "")
    ]
    block_counter: Counter[str] = Counter()

    for replay_date in replay_dates:
        if replay_date <= open_until:
            continue

        latest_all = frame.loc[frame["date"].eq(replay_date)].copy()
        latest = _latest_candidates(frame, replay_date, benchmark_ticker)
        candidates, rejected = _filter_candidates(latest, latest_all, cash, account_settings)
        block_counter.update(rejected["primary_block_reason"].dropna().astype(str).tolist() if not rejected.empty else [])
        if candidates.empty:
            equity_rows.append(_equity_row(replay_date, NO_TRADE, "", cash, cash, "", "", 0, _top_block_reason(rejected)))
            continue

        ranked = _rank_candidates(candidates)
        selected = ranked.iloc[0]
        trade, events = _simulate_trade(selected, by_ticker.get(str(selected["ticker"])), replay_date, cash, account_settings)
        if trade is None:
            equity_rows.append(_equity_row(replay_date, NO_TRADE, "", cash, cash, "", "", 0, "NO_FUTURE_ENTRY_DATA"))
            continue

        trades.append(trade)
        cash = float(trade["cash_after_exit"])
        open_until = pd.Timestamp(trade["exit_date"])
        equity_rows.extend(events)

    trades_frame = pd.DataFrame(trades)
    equity = pd.DataFrame(equity_rows)
    summary = summarize_phase1c_continuous_account(trades_frame, equity, account_settings, block_counter, start, end)
    return trades_frame, equity, summary


def write_phase1c_continuous_account_reports(
    trades: pd.DataFrame,
    equity: pd.DataFrame,
    summary: dict,
    trades_csv_path: str | Path,
    equity_csv_path: str | Path,
    summary_md_path: str | Path,
) -> None:
    trades_path = Path(trades_csv_path)
    equity_path = Path(equity_csv_path)
    summary_path = Path(summary_md_path)
    trades_path.parent.mkdir(parents=True, exist_ok=True)
    equity_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    trades.to_csv(trades_path, index=False)
    equity.to_csv(equity_path, index=False)
    summary_path.write_text(_summary_markdown(summary), encoding="utf-8")


def summarize_phase1c_continuous_account(
    trades: pd.DataFrame,
    equity: pd.DataFrame,
    account_settings: AccountSettings,
    block_counter: Counter[str],
    start: str,
    end: str,
) -> dict:
    equity_values = pd.to_numeric(equity["equity"], errors="coerce").dropna() if not equity.empty else pd.Series(dtype=float)
    ending = float(equity_values.iloc[-1]) if not equity_values.empty else float(account_settings.starting_capital)
    high = float(equity_values.max()) if not equity_values.empty else float(account_settings.starting_capital)
    milestones = {}
    for level in MILESTONES:
        hit = equity.loc[pd.to_numeric(equity["equity"], errors="coerce").ge(level)] if not equity.empty else pd.DataFrame()
        milestones[level] = "" if hit.empty else str(hit.iloc[0]["date"])
    executed = trades.loc[trades["status"].eq("EXECUTED")].copy() if not trades.empty else pd.DataFrame()
    best = _trade_label(executed.loc[executed["trade_return_pct"].idxmax()]) if not executed.empty else ""
    worst = _trade_label(executed.loc[executed["trade_return_pct"].idxmin()]) if not executed.empty else ""
    return {
        "period_start": start,
        "period_end": end,
        "starting_account_value": float(account_settings.starting_capital),
        "ending_account_value": ending,
        "total_return": ending / float(account_settings.starting_capital) - 1.0,
        "milestone_dates": milestones,
        "trade_count": int(len(executed)),
        "win_rate": pd.NA if executed.empty else float((executed["pnl_dollars"] > 0).mean()),
        "best_trade": best,
        "worst_trade": worst,
        "max_drawdown": _max_drawdown(equity_values),
        "longest_flat_period": _longest_flat_period(equity),
        "reached_1000": bool(milestones[1000]),
        "highest_account_value": high,
        "top_block_rule": block_counter.most_common(1)[0][0] if block_counter else "",
        "top_block_rule_count": block_counter.most_common(1)[0][1] if block_counter else 0,
        "block_counts": dict(block_counter.most_common(12)),
    }


def _prepare_features(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["ticker", "date"]).reset_index(drop=True)
    grouped = frame.groupby("ticker", group_keys=False)
    frame["daily_return"] = grouped["close"].pct_change()
    frame["green_day"] = frame["close"].gt(frame["open"]).astype(int)
    frame["green_days_5"] = grouped["green_day"].transform(lambda s: s.rolling(5, min_periods=5).sum())
    frame["max_daily_gain_5"] = grouped["daily_return"].transform(lambda s: s.rolling(5, min_periods=5).max())
    frame["atr_pct"] = frame["atr"] / frame["close"]
    return frame


def _latest_candidates(frame: pd.DataFrame, replay_date: pd.Timestamp, benchmark_ticker: str) -> pd.DataFrame:
    latest = frame.loc[frame["date"].eq(replay_date) & ~frame["ticker"].isin([benchmark_ticker, "QQQ"])].copy()
    return latest.dropna(subset=["date", "ticker", "close", *SMOKE_RANK_FACTORS])


def _filter_candidates(latest: pd.DataFrame, latest_all: pd.DataFrame, cash: float, settings: AccountSettings) -> tuple[pd.DataFrame, pd.DataFrame]:
    if latest.empty:
        return pd.DataFrame(), pd.DataFrame()
    spy_qqq_down = _market_downtrend(latest_all)
    market_return_20d = _market_return_20d(latest_all)
    rows = []
    for _, row in latest.iterrows():
        reasons = []
        price = float(row["close"])
        adjusted_entry = price * (1.0 + settings.slippage_bps / 10_000.0)
        shares = floor(cash / adjusted_entry)
        checks = {
            "price_between_5_and_50": 5.0 <= price <= 50.0,
            "whole_share_affordable": shares >= 1,
            "dollar_volume_min": float(row["dollar_volume"]) >= 20_000_000,
            "return_5d_between_3_and_15": 0.03 <= float(row["return_5d"]) <= 0.15,
            "green_days_5_min_3": float(row.get("green_days_5", 0)) >= 3,
            "max_daily_gain_5_lte_10": float(row.get("max_daily_gain_5", 1.0)) <= 0.10,
            "relative_volume_prev20_min_1_5": float(row["relative_volume_prev20"]) >= 1.5,
            "atr_pct_lte_12": float(row.get("atr_pct", 1.0)) <= 0.12,
            "distance_to_52w_high_min_minus_35": float(row["distance_to_52w_high_prev"]) >= -0.35,
            "spy_qqq_not_clear_downtrend": not spy_qqq_down,
        }
        for name, passed in checks.items():
            if not passed:
                reasons.append(name)
        enriched = row.to_dict()
        enriched.update(
            {
                "event_filter_status": "UNKNOWN",
                "market_return_20d": market_return_20d,
                "relative_strength_vs_market": float(row["return_20d"]) - market_return_20d,
                "shares": shares,
                "adjusted_entry_price": adjusted_entry,
                "estimated_total_cost": shares * adjusted_entry,
                "all_hard_filters_passed": len(reasons) == 0,
                "failed_filters": ";".join(reasons),
                "primary_block_reason": reasons[0] if reasons else "",
            }
        )
        rows.append(enriched)
    checked = pd.DataFrame(rows)
    return checked.loc[checked["all_hard_filters_passed"]].copy(), checked.loc[~checked["all_hard_filters_passed"]].copy()


def _market_downtrend(latest_all: pd.DataFrame) -> bool:
    market = latest_all.loc[latest_all["ticker"].isin(["SPY", "QQQ"])].copy()
    if market.empty:
        return False
    downtrend_flags = []
    for _, row in market.iterrows():
        close = row.get("close", pd.NA)
        ret20 = row.get("return_20d", pd.NA)
        if pd.isna(close) or pd.isna(ret20):
            downtrend_flags.append(False)
        else:
            downtrend_flags.append(float(ret20) < -0.03)
    return bool(any(downtrend_flags))


def _market_return_20d(latest_all: pd.DataFrame) -> float:
    market = latest_all.loc[latest_all["ticker"].isin(["SPY", "QQQ"]), "return_20d"]
    values = pd.to_numeric(market, errors="coerce").dropna()
    return 0.0 if values.empty else float(values.mean())


def _rank_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    frame = candidates.copy()
    frame["smooth_uptrend_quality"] = frame["green_days_5"] / 5.0 - frame["max_daily_gain_5"].clip(lower=0.0)
    frame["relative_strength_proxy"] = frame["relative_strength_vs_market"]
    score_specs = [
        ("relative_volume_prev20", True),
        ("smooth_uptrend_quality", True),
        ("return_20d", True),
        ("relative_strength_proxy", True),
        ("distance_to_52w_high_prev", True),
        ("atr_pct", False),
    ]
    score_cols = []
    for column, ascending_good in score_specs:
        score_col = f"{column}_rank_score"
        frame[score_col] = frame[column].rank(method="first", pct=True, ascending=ascending_good)
        score_cols.append(score_col)
    frame["selection_score"] = frame[score_cols].mean(axis=1)
    return frame.sort_values(["selection_score", "relative_volume_prev20", "ticker"], ascending=[False, False, True]).reset_index(drop=True)


def _simulate_trade(
    selected: pd.Series,
    ticker_data: pd.DataFrame | None,
    replay_date: pd.Timestamp,
    cash: float,
    settings: AccountSettings,
) -> tuple[dict | None, list[dict]]:
    if ticker_data is None or ticker_data.empty:
        return None, []
    future = ticker_data.loc[ticker_data["date"].gt(replay_date)].head(21).reset_index(drop=True)
    if future.empty:
        return None, []
    entry = future.iloc[0]
    entry_price = float(entry["open"] if not pd.isna(entry["open"]) else entry["close"])
    adjusted_entry = entry_price * (1.0 + settings.slippage_bps / 10_000.0)
    shares = floor(cash / adjusted_entry)
    if shares < 1:
        return None, []
    cash_after_entry = cash - shares * adjusted_entry
    remaining = shares
    stop = adjusted_entry * 0.90
    target_1 = adjusted_entry * (1.15 if shares >= 2 else 1.20)
    target_2 = adjusted_entry * 1.30
    partial_exit_date = ""
    partial_exit_price = pd.NA
    partial_exit_shares = 0
    exit_reason = "OPEN_AT_DATA_END"
    exit_date = pd.Timestamp(entry["date"])
    exit_price = float(entry["close"])
    events = [
        _equity_row(pd.Timestamp(entry["date"]), "ENTRY", selected["ticker"], cash_after_entry + shares * exit_price, cash_after_entry, selected["ticker"], "", shares, "entered next session open")
    ]

    for day_index, (_, day) in enumerate(future.iterrows(), start=1):
        low = float(day["low"])
        high = float(day["high"])
        close = float(day["close"])
        exit_date = pd.Timestamp(day["date"])
        exit_price = close

        if low <= stop:
            cash_after_entry += remaining * stop
            exit_price = stop
            exit_reason = "STOP"
            remaining = 0
            break
        if shares == 1 and high >= target_1:
            cash_after_entry += remaining * target_1
            exit_price = target_1
            exit_reason = "TARGET_20"
            remaining = 0
            break
        if shares >= 2 and partial_exit_shares == 0 and high >= target_1:
            partial_exit_shares = 1
            partial_exit_price = target_1
            partial_exit_date = exit_date.strftime("%Y-%m-%d")
            cash_after_entry += target_1
            remaining -= 1
            stop = adjusted_entry
            events.append(_equity_row(exit_date, "PARTIAL_EXIT", selected["ticker"], cash_after_entry + remaining * close, cash_after_entry, selected["ticker"], "TARGET_15", remaining, "sold one share and moved stop to breakeven"))
        if shares >= 2 and remaining > 0 and high >= target_2:
            cash_after_entry += remaining * target_2
            exit_price = target_2
            exit_reason = "TARGET_30"
            remaining = 0
            break
        if day_index >= 20:
            cash_after_entry += remaining * close
            exit_reason = "TIME_EXIT"
            remaining = 0
            break

    if remaining > 0:
        cash_after_entry += remaining * exit_price
    cash_after_exit = cash_after_entry
    pnl = cash_after_exit - cash
    events.append(_equity_row(exit_date, "EXIT", selected["ticker"], cash_after_exit, cash_after_exit, selected["ticker"], exit_reason, 0, "final exit or data-end mark"))
    trade = {
        "signal_date": replay_date.strftime("%Y-%m-%d"),
        "ticker": selected["ticker"],
        "entry_date": pd.Timestamp(entry["date"]).strftime("%Y-%m-%d"),
        "entry_price": entry_price,
        "adjusted_entry_price": adjusted_entry,
        "shares": shares,
        "cash_before": cash,
        "cash_after_entry": cash - shares * adjusted_entry,
        "partial_exit_date": partial_exit_date,
        "partial_exit_price": partial_exit_price,
        "partial_exit_shares": partial_exit_shares,
        "exit_date": exit_date.strftime("%Y-%m-%d"),
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "cash_after_exit": cash_after_exit,
        "pnl_dollars": pnl,
        "trade_return_pct": pnl / (shares * adjusted_entry) if shares else pd.NA,
        "account_return_pct": pnl / cash if cash else pd.NA,
        "selection_score": selected["selection_score"],
        "relative_volume_prev20": selected["relative_volume_prev20"],
        "return_5d": selected["return_5d"],
        "return_20d": selected["return_20d"],
        "green_days_5": selected["green_days_5"],
        "max_daily_gain_5": selected["max_daily_gain_5"],
        "atr_pct": selected["atr_pct"],
        "distance_to_52w_high_prev": selected["distance_to_52w_high_prev"],
        "event_filter_status": "UNKNOWN",
        "status": "EXECUTED",
    }
    return trade, events


def _equity_row(date, event, ticker, equity, cash, position_ticker, exit_reason, open_shares, note) -> dict:
    date_value = "" if date == "" else pd.Timestamp(date).strftime("%Y-%m-%d")
    return {
        "date": date_value,
        "event": event,
        "ticker": ticker,
        "equity": float(equity),
        "cash": float(cash),
        "position_ticker": position_ticker,
        "exit_reason": exit_reason,
        "open_shares": open_shares,
        "note": note,
    }


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    return float((equity / equity.cummax() - 1.0).min())


def _longest_flat_period(equity: pd.DataFrame) -> str:
    if equity.empty or "date" not in equity.columns:
        return ""
    rows = equity.loc[equity["date"].astype(str).ne("")].copy()
    if rows.empty:
        return ""
    rows["date"] = pd.to_datetime(rows["date"])
    rows["equity"] = pd.to_numeric(rows["equity"], errors="coerce")
    high = -float("inf")
    high_date = rows.iloc[0]["date"]
    longest = 0
    longest_label = ""
    for _, row in rows.iterrows():
        if row["equity"] > high:
            high = row["equity"]
            high_date = row["date"]
        days = int((row["date"] - high_date).days)
        if days > longest:
            longest = days
            longest_label = f"{longest} calendar days from {high_date.strftime('%Y-%m-%d')} to {row['date'].strftime('%Y-%m-%d')}"
    return longest_label or "0 calendar days"


def _trade_label(row: pd.Series) -> str:
    return f"{row['signal_date']} {row['ticker']} {row['exit_reason']} return={_format_percent(row['trade_return_pct'])}"


def _top_block_reason(rejected: pd.DataFrame) -> str:
    if rejected.empty:
        return "NO_ELIGIBLE_DATA"
    counts = rejected["primary_block_reason"].value_counts()
    return str(counts.index[0]) if not counts.empty else "NO_ELIGIBLE_DATA"


def _summary_markdown(summary: dict) -> str:
    milestones = summary["milestone_dates"]
    lines = [
        "# Phoenix Nano Phase 1C Continuous Account Growth Backtest",
        "",
        "Research-only historical backtest. This does not start paper trading or live trading.",
        "",
        "## Account Growth",
        "",
        f"- Period: {summary['period_start']} to {summary['period_end']}",
        f"- Starting account value: {_format_money(summary['starting_account_value'])}",
        f"- Ending account value: {_format_money(summary['ending_account_value'])}",
        f"- Total return: {_format_percent(summary['total_return'])}",
        f"- Highest account value reached: {_format_money(summary['highest_account_value'])}",
        f"- $1000 reached: {summary['reached_1000']}",
        "",
        "## Milestones",
        "",
        *[f"- ${level}: {milestones[level] or 'not reached'}" for level in MILESTONES],
        "",
        "## Trades",
        "",
        f"- Number of trades: {summary['trade_count']}",
        f"- Win rate: {_format_percent(summary['win_rate'])}",
        f"- Best trade: {summary['best_trade'] or 'none'}",
        f"- Worst trade: {summary['worst_trade'] or 'none'}",
        f"- Max drawdown: {_format_percent(summary['max_drawdown'])}",
        f"- Longest flat period: {summary['longest_flat_period']}",
        "",
        "## Bottleneck",
        "",
        f"- Rule blocked most stocks: {summary['top_block_rule'] or 'none'} ({summary['top_block_rule_count']} rows)",
        "",
        "## Block Counts",
        "",
    ]
    if summary["block_counts"]:
        lines.append(pd.DataFrame([{"rule": k, "count": v} for k, v in summary["block_counts"].items()]).to_markdown(index=False))
    else:
        lines.append("No blocked-stock rows were counted.")
    lines.extend(
        [
            "",
            "## What Should Be Adjusted Next",
            "",
            "- Do not start paper or live trading from this report.",
            "- Review the dominant block rule before loosening any threshold.",
            "- If account growth stalls, test one conservative filter adjustment at a time in a separate GPT-approved task.",
            "- Independent vendor data validation remains a separate blocker.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_money(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"${float(value):.2f}"


def _format_percent(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value) * 100:.2f}%"
