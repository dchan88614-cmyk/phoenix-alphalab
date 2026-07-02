from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings
from src.backtest.nano_daily_scan import _score_latest_candidates
from src.backtest.smoke_test import SMOKE_RANK_FACTORS
from src.research.auto_loop import CandidateRule
from src.research.historical_replay import HISTORICAL_BUY_CANDIDATE, HISTORICAL_NO_TRADE


FORWARD_WINDOWS = [1, 3, 5, 10, 20]


def build_phase1b_last_month_replay(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_start: str,
    replay_end: str,
    benchmark_ticker: str = "SPY",
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    required = {"date", "ticker", "open", "high", "low", "close", "atr", *SMOKE_RANK_FACTORS}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Phase 1B last-month replay missing required columns: {', '.join(sorted(missing))}")

    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["ticker", "date"]).reset_index(drop=True)
    start = pd.Timestamp(replay_start)
    end = pd.Timestamp(replay_end)
    replay_dates = sorted(
        pd.Timestamp(value)
        for value in frame.loc[
            frame["date"].between(start, end) & ~frame["ticker"].eq(benchmark_ticker), "date"
        ].dropna().unique()
    )

    decisions: list[dict] = []
    near_misses: list[dict] = []
    for replay_date in replay_dates:
        latest = _latest_slice(frame, replay_date, benchmark_ticker)
        scored, rejected = _score_latest_candidates(latest, rule, account_settings)
        passed = scored.loc[scored["all_rule_checks_passed"]].copy() if not scored.empty else pd.DataFrame()

        if passed.empty:
            decisions.append(_no_trade_row(replay_date, scored, rejected))
            closest = scored.head(5).copy() if not scored.empty else pd.DataFrame()
            for _, candidate in closest.iterrows():
                near_misses.append(_candidate_row(replay_date, candidate, "EXECUTABLE_NEAR_MISS", frame))
            continue

        best = passed.sort_values(["decision_strength", "smoke_score", "ticker"], ascending=[False, False, True]).iloc[0]
        decisions.append(_candidate_row(replay_date, best, HISTORICAL_BUY_CANDIDATE, frame))

    decisions_frame = pd.DataFrame(decisions)
    near_misses_frame = pd.DataFrame(near_misses)
    summary = summarize_phase1b_last_month(decisions_frame, near_misses_frame, replay_start, replay_end)
    return decisions_frame, near_misses_frame, summary


def write_phase1b_last_month_reports(
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
    summary_path.write_text(_summary_markdown(summary, decisions, near_misses), encoding="utf-8")


def summarize_phase1b_last_month(decisions: pd.DataFrame, near_misses: pd.DataFrame, replay_start: str, replay_end: str) -> dict:
    buys = decisions.loc[decisions["decision"].eq(HISTORICAL_BUY_CANDIDATE)].copy() if not decisions.empty else pd.DataFrame()
    summary = {
        "replay_start": replay_start,
        "replay_end": replay_end,
        "total_trading_days": int(len(decisions)),
        "buy_count": int(len(buys)),
        "no_trade_count": int(len(decisions) - len(buys)),
        "best_pick": _best_worst_label(buys, best=True),
        "worst_pick": _best_worst_label(buys, best=False),
        "top_repeated_tickers": _top_counts(buys["ticker"]) if not buys.empty else "",
        "near_misses_later_performed_well": _near_miss_labels(near_misses, best=True),
        "near_misses_failed_badly": _near_miss_labels(near_misses, best=False),
    }
    for window in FORWARD_WINDOWS:
        return_col = f"return_{window}d"
        complete_col = f"data_complete_{window}d"
        complete_buys = buys.loc[buys[complete_col].eq(True)] if complete_col in buys.columns else pd.DataFrame()
        returns = pd.to_numeric(complete_buys[return_col], errors="coerce").dropna() if return_col in complete_buys.columns else pd.Series(dtype=float)
        summary[f"accuracy_{window}d"] = pd.NA if returns.empty else float((returns > 0).mean())
        summary[f"avg_return_{window}d"] = pd.NA if returns.empty else float(returns.mean())
        summary[f"median_return_{window}d"] = pd.NA if returns.empty else float(returns.median())
    return summary


def _latest_slice(frame: pd.DataFrame, replay_date: pd.Timestamp, benchmark_ticker: str) -> pd.DataFrame:
    latest = frame.loc[frame["date"].eq(replay_date) & ~frame["ticker"].eq(benchmark_ticker)].copy()
    return latest.dropna(subset=["date", "ticker", "close", *SMOKE_RANK_FACTORS])


def _candidate_row(replay_date: pd.Timestamp, candidate: pd.Series, decision: str, frame: pd.DataFrame) -> dict:
    row = {
        "replay_date": replay_date.strftime("%Y-%m-%d"),
        "decision": decision,
        "ticker": candidate["ticker"],
        "reason": (
            "Candidate 34 Nano rule passed with replay-date $100 whole-share affordability."
            if decision == HISTORICAL_BUY_CANDIDATE
            else "Closest executable near-miss after Candidate 34 checks failed."
        ),
        "reference_price": float(candidate["reference_price"]),
        "shares_with_cash": candidate["shares_with_100"],
        "estimated_total_cost": candidate["estimated_total_cost"],
        "estimated_cash_remaining": candidate["estimated_cash_remaining"],
        "smoke_score": candidate["smoke_score"],
        "decision_strength": candidate["decision_strength"],
        "relative_volume_prev20": candidate["relative_volume_prev20"],
        "return_5d_signal": candidate["return_5d"],
        "return_20d_signal": candidate["return_20d"],
        "distance_to_52w_high_prev": candidate["distance_to_52w_high_prev"],
        "dollar_volume": candidate["dollar_volume"],
        "all_rule_checks_passed": bool(candidate["all_rule_checks_passed"]),
        "failed_checks": candidate.get("failed_checks", ""),
    }
    row.update(_future_verification(frame, str(candidate["ticker"]), replay_date, float(candidate["reference_price"])))
    return row


def _no_trade_row(replay_date: pd.Timestamp, scored: pd.DataFrame, rejected: pd.DataFrame) -> dict:
    return {
        "replay_date": replay_date.strftime("%Y-%m-%d"),
        "decision": HISTORICAL_NO_TRADE,
        "ticker": "",
        "reason": "NO_CANDIDATE_PASSED_RULES",
        "reference_price": pd.NA,
        "shares_with_cash": 0,
        "estimated_total_cost": 0.0,
        "estimated_cash_remaining": 100.0,
        "smoke_score": pd.NA,
        "decision_strength": pd.NA,
        "relative_volume_prev20": pd.NA,
        "return_5d_signal": pd.NA,
        "return_20d_signal": pd.NA,
        "distance_to_52w_high_prev": pd.NA,
        "dollar_volume": pd.NA,
        "all_rule_checks_passed": False,
        "failed_checks": "",
        "executable_near_miss_count": int(min(5, len(scored))),
        "rejected_before_ranking_count": int(len(rejected)),
        **{f"return_{window}d": pd.NA for window in FORWARD_WINDOWS},
        **{f"data_complete_{window}d": False for window in FORWARD_WINDOWS},
        "max_favorable_move_20d": pd.NA,
        "max_adverse_move_20d": pd.NA,
        "data_complete_mfe_mae_20d": False,
    }


def _future_verification(frame: pd.DataFrame, ticker: str, replay_date: pd.Timestamp, reference_price: float) -> dict:
    ticker_rows = frame.loc[frame["ticker"].eq(ticker)].sort_values("date").reset_index(drop=True)
    future = ticker_rows.loc[ticker_rows["date"].gt(replay_date)].copy()
    output: dict[str, object] = {}
    for window in FORWARD_WINDOWS:
        complete = len(future) >= window
        output[f"data_complete_{window}d"] = bool(complete)
        output[f"return_{window}d"] = (
            float(future.iloc[window - 1]["close"] / reference_price - 1.0) if complete else pd.NA
        )
    complete_20 = len(future) >= 20
    output["data_complete_mfe_mae_20d"] = bool(complete_20)
    window_rows = future.head(20)
    if window_rows.empty:
        output["max_favorable_move_20d"] = pd.NA
        output["max_adverse_move_20d"] = pd.NA
    else:
        output["max_favorable_move_20d"] = float(window_rows["high"].max() / reference_price - 1.0)
        output["max_adverse_move_20d"] = float(window_rows["low"].min() / reference_price - 1.0)
    return output


def _summary_markdown(summary: dict, decisions: pd.DataFrame, near_misses: pd.DataFrame) -> str:
    lines = [
        "# Phoenix Nano Phase 1B Last Month Daily Replay Validation",
        "",
        "Research-only historical replay. This does not start Phase 2, Phase 3, paper execution, or live execution.",
        "",
        "## Replay Range",
        "",
        f"- Date range: {summary['replay_start']} to {summary['replay_end']}",
        f"- Total trading days tested: {summary['total_trading_days']}",
        f"- BUY candidate count: {summary['buy_count']}",
        f"- NO_TRADE count: {summary['no_trade_count']}",
        "",
        "## Daily Decisions",
        "",
    ]
    if decisions.empty:
        lines.append("No replay decisions were generated.")
    else:
        display = decisions[["replay_date", "decision", "ticker", "reason"]].copy()
        lines.append(display.to_markdown(index=False))
    lines.extend(["", "## BUY Candidate Accuracy", ""])
    for window in FORWARD_WINDOWS:
        lines.append(f"- {window}d accuracy: {_format_percent(summary[f'accuracy_{window}d'])}")
        lines.append(f"- {window}d average return: {_format_percent(summary[f'avg_return_{window}d'])}")
        lines.append(f"- {window}d median return: {_format_percent(summary[f'median_return_{window}d'])}")
    lines.extend(
        [
            "",
            "## Best And Worst",
            "",
            f"- Best selected stock: {summary['best_pick'] or 'none'}",
            f"- Worst selected stock: {summary['worst_pick'] or 'none'}",
            f"- Most repeated selected tickers: {summary['top_repeated_tickers'] or 'none'}",
            "",
            "## Near Miss Lessons",
            "",
            f"- Near-misses that later performed well: {summary['near_misses_later_performed_well'] or 'none'}",
            f"- Near-misses that failed badly: {summary['near_misses_failed_badly'] or 'none'}",
            "",
            "## Short Conclusion",
            "",
            _short_conclusion(summary, near_misses),
            "",
        ]
    )
    return "\n".join(lines)


def _short_conclusion(summary: dict, near_misses: pd.DataFrame) -> str:
    if summary["buy_count"] == 0:
        return "The month produced no full Candidate 34 Nano BUY candidates; the immediate lesson is to review whether standards are too restrictive or data quality blocks are suppressing valid setups."
    acc = summary.get("accuracy_20d", pd.NA)
    if pd.isna(acc):
        return "The month produced BUY candidates, but 20d verification is incomplete, so this replay cannot yet judge full 20-trading-day follow-through."
    if float(acc) > 0.5:
        return "The completed BUY candidates had positive 20d accuracy above 50%, but this is still historical research and needs broader validation."
    return "The completed BUY candidates did not exceed a 50% positive 20d accuracy bar, so the month argues for caution before any further strategy expansion."


def _best_worst_label(frame: pd.DataFrame, best: bool) -> str:
    if frame.empty or "return_20d" not in frame.columns:
        return ""
    complete = frame.loc[frame["data_complete_20d"].eq(True)].copy()
    if complete.empty:
        return ""
    index = complete["return_20d"].idxmax() if best else complete["return_20d"].idxmin()
    row = complete.loc[index]
    return f"{row['replay_date']} {row['ticker']} 20d={_format_percent(row['return_20d'])}"


def _near_miss_labels(frame: pd.DataFrame, best: bool) -> str:
    if frame.empty or "return_20d" not in frame.columns:
        return ""
    complete = frame.loc[frame["data_complete_20d"].eq(True)].copy()
    complete = complete.loc[complete["return_20d"].gt(0)] if best else complete.loc[complete["return_20d"].lt(0)]
    if complete.empty:
        return ""
    ordered = complete.sort_values("return_20d", ascending=not best).head(5)
    return ", ".join(f"{row.replay_date} {row.ticker} 20d={_format_percent(row.return_20d)}" for row in ordered.itertuples())


def _top_counts(series: pd.Series) -> str:
    return ", ".join(f"{ticker}:{count}" for ticker, count in series.value_counts().head(10).items())


def _format_percent(value: object) -> str:
    if value is None or pd.isna(value):
        return "incomplete"
    return f"{float(value) * 100:.2f}%"
