from __future__ import annotations

from dataclasses import dataclass
from math import floor
from pathlib import Path

import pandas as pd


NANO_RESEARCH_ONLY_NOT_TRADABLE = "NANO_RESEARCH_ONLY_NOT_TRADABLE"
NANO_RESEARCH_QUALIFIED_NOT_LIVE = "NANO_RESEARCH_QUALIFIED_NOT_LIVE"
NOT_AFFORDABLE = "NOT_AFFORDABLE"
EXECUTED = "EXECUTED"
SKIPPED_POSITION_OPEN = "SKIPPED_POSITION_OPEN"


@dataclass(frozen=True)
class AccountSettings:
    starting_capital: float = 100.0
    fractional_shares: bool = False
    max_position_fraction: float = 1.0
    min_cash_reserve: float = 0.0
    commission_per_trade: float = 0.0
    slippage_bps: float = 10.0

    @classmethod
    def from_config(cls, config: dict) -> "AccountSettings":
        account = config.get("account", {})
        return cls(
            starting_capital=float(account.get("starting_capital", 100.0)),
            fractional_shares=bool(account.get("fractional_shares", False)),
            max_position_fraction=float(account.get("max_position_fraction", 1.0)),
            min_cash_reserve=float(account.get("min_cash_reserve", 0.0)),
            commission_per_trade=float(account.get("commission_per_trade", 0.0)),
            slippage_bps=float(account.get("slippage_bps", 10.0)),
        )


def calculate_affordability(
    trade: pd.Series,
    cash: float,
    settings: AccountSettings,
) -> dict:
    entry_price = float(trade["entry_price"])
    adjusted_entry_price = entry_price * (1.0 + settings.slippage_bps / 10_000.0)
    available_cash = max(0.0, cash * settings.max_position_fraction - settings.min_cash_reserve)
    if settings.fractional_shares:
        shares = available_cash / adjusted_entry_price
    else:
        shares = floor(available_cash / adjusted_entry_price)
    total_cost = shares * adjusted_entry_price + settings.commission_per_trade
    stop_loss = float(trade["stop_loss"])
    dollar_risk = shares * max(0.0, adjusted_entry_price - stop_loss)
    executable = shares >= 1 and total_cost <= cash and (settings.fractional_shares or adjusted_entry_price <= cash)
    return {
        "adjusted_entry_price": float(adjusted_entry_price),
        "shares": float(shares) if settings.fractional_shares else int(shares),
        "total_cost": float(total_cost),
        "cash_remaining": float(cash - total_cost),
        "dollar_risk": float(dollar_risk),
        "affordability_status": EXECUTED if executable else NOT_AFFORDABLE,
    }


def simulate_nano_account(
    trades: pd.DataFrame,
    settings: AccountSettings,
    max_entry_price: float = 100.0,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    columns = [
        "candidate_id",
        "signal_date",
        "entry_date",
        "exit_date",
        "ticker",
        "entry_price",
        "adjusted_entry_price",
        "shares",
        "total_cost",
        "cash_before",
        "cash_after_entry",
        "exit_price",
        "exit_reason",
        "cash_after_exit",
        "trade_return_pct",
        "account_return_pct",
        "dollar_pnl",
        "stop_loss",
        "target_1",
        "target_2",
        "dollar_risk",
        "affordability_status",
    ]
    if trades.empty:
        return pd.DataFrame(columns=columns), pd.DataFrame(), _nano_summary(pd.DataFrame(), settings)

    frame = trades.copy()
    frame["signal_date"] = pd.to_datetime(frame["signal_date"])
    frame["entry_date"] = pd.to_datetime(frame["entry_date"])
    frame["exit_date"] = pd.to_datetime(frame["exit_date"])
    frame = frame.sort_values(["signal_date", "entry_date", "ticker"]).reset_index(drop=True)

    cash = float(settings.starting_capital)
    open_until = pd.Timestamp.min
    rows: list[dict] = []
    equity_rows: list[dict] = [{"date": "", "candidate_id": "", "equity": cash, "cash": cash, "event": "START"}]

    for _, trade in frame.iterrows():
        if float(trade["entry_price"]) > max_entry_price:
            rows.append(_skipped_row(trade, cash, NOT_AFFORDABLE))
            continue
        if trade["entry_date"] <= open_until:
            rows.append(_skipped_row(trade, cash, SKIPPED_POSITION_OPEN))
            continue
        affordability = calculate_affordability(trade, cash, settings)
        if affordability["affordability_status"] != EXECUTED:
            rows.append(_skipped_row(trade, cash, NOT_AFFORDABLE, affordability))
            continue

        cash_before = cash
        cash_after_entry = affordability["cash_remaining"]
        shares = float(affordability["shares"])
        exit_value = shares * float(trade["exit_price"])
        cash_after_exit = cash_after_entry + exit_value - settings.commission_per_trade
        dollar_pnl = cash_after_exit - cash_before
        trade_return_pct = float(trade["exit_price"]) / affordability["adjusted_entry_price"] - 1.0
        account_return_pct = dollar_pnl / cash_before if cash_before else pd.NA
        cash = cash_after_exit
        open_until = trade["exit_date"]

        rows.append(
            {
                "candidate_id": trade["candidate_id"],
                "signal_date": trade["signal_date"].strftime("%Y-%m-%d"),
                "entry_date": trade["entry_date"].strftime("%Y-%m-%d"),
                "exit_date": trade["exit_date"].strftime("%Y-%m-%d"),
                "ticker": trade["ticker"],
                "entry_price": float(trade["entry_price"]),
                "adjusted_entry_price": affordability["adjusted_entry_price"],
                "shares": affordability["shares"],
                "total_cost": affordability["total_cost"],
                "cash_before": cash_before,
                "cash_after_entry": cash_after_entry,
                "exit_price": float(trade["exit_price"]),
                "exit_reason": trade["exit_reason"],
                "cash_after_exit": cash_after_exit,
                "trade_return_pct": trade_return_pct,
                "account_return_pct": account_return_pct,
                "dollar_pnl": dollar_pnl,
                "stop_loss": float(trade["stop_loss"]),
                "target_1": float(trade["target_1"]),
                "target_2": float(trade["target_2"]),
                "dollar_risk": affordability["dollar_risk"],
                "affordability_status": EXECUTED,
            }
        )
        equity_rows.append(
            {
                "date": trade["exit_date"].strftime("%Y-%m-%d"),
                "candidate_id": trade["candidate_id"],
                "equity": cash,
                "cash": cash,
                "event": "EXIT",
            }
        )

    trades_out = pd.DataFrame(rows, columns=columns)
    equity_curve = pd.DataFrame(equity_rows)
    summary = _nano_summary(trades_out, settings)
    return trades_out, equity_curve, summary


def summarize_nano_candidates(
    all_trades: pd.DataFrame,
    settings: AccountSettings,
    max_entry_prices: list[float],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    trade_frames = []
    equity_frames = []
    for candidate_id, trades in all_trades.groupby("candidate_id"):
        for max_entry_price in max_entry_prices:
            nano_trades, equity, summary = simulate_nano_account(trades, settings, max_entry_price=max_entry_price)
            summary.update({"candidate_id": candidate_id, "max_entry_price": max_entry_price})
            summary_rows.append(summary)
            if not nano_trades.empty:
                nano_trades["max_entry_price"] = max_entry_price
                trade_frames.append(nano_trades)
            if not equity.empty:
                equity["max_entry_price"] = max_entry_price
                equity_frames.append(equity)
    return (
        pd.DataFrame(summary_rows),
        pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame(),
        pd.concat(equity_frames, ignore_index=True) if equity_frames else pd.DataFrame(),
    )


def merge_nano_results(auto_results: pd.DataFrame, nano_summary: pd.DataFrame) -> pd.DataFrame:
    if nano_summary.empty:
        return auto_results.copy()
    best = nano_summary.sort_values(["nano_score", "ending_equity"], ascending=[False, False]).drop_duplicates("candidate_id")
    merged = auto_results.merge(best, on="candidate_id", how="left", suffixes=("", "_nano"))
    if "max_entry_price_nano" in merged.columns:
        merged["nano_max_entry_price"] = merged["max_entry_price_nano"]
    merged["status"] = merged["nano_status"].fillna(merged["status"])
    merged["fail_reasons"] = merged["nano_fail_reasons"].fillna(merged["fail_reasons"])
    return merged


def write_nano_summary(
    nano_summary: pd.DataFrame,
    nano_trades: pd.DataFrame,
    equity_curve: pd.DataFrame,
    output_path: str | Path,
    settings: AccountSettings,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    best = None if nano_summary.empty else nano_summary.sort_values(["nano_score", "ending_equity"], ascending=[False, False]).iloc[0]
    qualified = nano_summary.loc[nano_summary["nano_status"].eq(NANO_RESEARCH_QUALIFIED_NOT_LIVE)] if not nano_summary.empty else pd.DataFrame()
    best_qualified = (
        None
        if qualified.empty
        else qualified.sort_values(["nano_score", "ending_equity"], ascending=[False, False]).iloc[0]
    )
    top = nano_summary.sort_values(["nano_score", "ending_equity"], ascending=[False, False]).head(10) if not nano_summary.empty else pd.DataFrame()
    lines = [
        "# Phoenix Nano Account Summary",
        "",
        "Offline historical research only. Not live-tradable.",
        "",
        "## Account",
        "",
        f"- Starting capital: ${settings.starting_capital:.2f}",
        f"- Fractional shares: {settings.fractional_shares}",
        f"- Max position fraction: {settings.max_position_fraction:.2f}",
        f"- Min cash reserve: ${settings.min_cash_reserve:.2f}",
        f"- Commission per trade: ${settings.commission_per_trade:.2f}",
        f"- Slippage: {settings.slippage_bps:.1f} bps",
        "",
        "## Summary",
        "",
        f"- Nano candidate variants evaluated: {len(nano_summary)}",
        f"- NANO_RESEARCH_QUALIFIED_NOT_LIVE candidates: {len(qualified)}",
        (
            "No Nano research-qualified version found. Do not use Phoenix for live trading."
            if qualified.empty
            else "Nano research-qualified candidates found. GPT review required before paper trading."
        ),
        "",
    ]
    if best is not None:
        lines.extend(
            [
                "## Best Nano Candidate By Score",
                "",
                f"- Candidate ID: {int(best['candidate_id'])}",
                f"- Max entry price: ${float(best['max_entry_price']):.2f}",
                f"- Status: {best['nano_status']}",
                f"- Executed trades: {int(best['executed_trade_count'])}",
                f"- Not-affordable rejections: {int(best['rejected_not_affordable_count'])}",
                f"- Ending equity: ${float(best['ending_equity']):.2f}",
                f"- Total return: {_format_percent(best['total_return'])}",
                f"- Max drawdown: {_format_percent(best['max_drawdown'])}",
                f"- Profit factor: {_format_number(best['profit_factor'])}",
                f"- Win rate: {_format_percent(best['win_rate'])}",
                f"- Worst account trade loss: {_format_percent(best['worst_account_trade_loss'])}",
                f"- Traded ticker count: {int(best['traded_ticker_count'])}",
                f"- Top ticker profit share: {_format_percent(best['top_ticker_profit_share'])}",
                f"- Fail reasons: {best['nano_fail_reasons']}",
                "",
            ]
        )
    if best_qualified is not None:
        lines.extend(
            [
                "## Best Nano Research-Qualified Candidate",
                "",
                f"- Candidate ID: {int(best_qualified['candidate_id'])}",
                f"- Max entry price: ${float(best_qualified['max_entry_price']):.2f}",
                f"- Status: {best_qualified['nano_status']}",
                f"- Executed trades: {int(best_qualified['executed_trade_count'])}",
                f"- Ending equity: ${float(best_qualified['ending_equity']):.2f}",
                f"- Total return: {_format_percent(best_qualified['total_return'])}",
                f"- Max drawdown: {_format_percent(best_qualified['max_drawdown'])}",
                f"- Profit factor: {_format_number(best_qualified['profit_factor'])}",
                f"- Win rate: {_format_percent(best_qualified['win_rate'])}",
                f"- Worst account trade loss: {_format_percent(best_qualified['worst_account_trade_loss'])}",
                f"- Traded ticker count: {int(best_qualified['traded_ticker_count'])}",
                f"- Top ticker profit share: {_format_percent(best_qualified['top_ticker_profit_share'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Top Nano Candidates",
            "",
            top.to_markdown(index=False) if not top.empty else "No Nano candidates.",
            "",
            "## Why prior results were invalid for $100 account",
            "",
            "- Large-account candidate results may select stocks above $100.",
            "- DELL/MSTR style trades may be impossible for a whole-share $100 account.",
            "- Averages across simulated trades are not enough; the account equity curve must be simulated.",
            "- If shares cannot be calculated, the output is not a valid BUY.",
            "",
            "## Top Traded Tickers",
            "",
            _top_tickers_markdown(nano_trades),
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _nano_summary(trades: pd.DataFrame, settings: AccountSettings) -> dict:
    executed = trades.loc[trades["affordability_status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    rejected = trades.loc[trades["affordability_status"].eq(NOT_AFFORDABLE)].copy() if not trades.empty else pd.DataFrame()
    ending_equity = float(executed["cash_after_exit"].iloc[-1]) if not executed.empty else settings.starting_capital
    total_return = ending_equity / settings.starting_capital - 1.0
    max_drawdown = _max_drawdown(executed, settings.starting_capital)
    wins = executed.loc[executed["dollar_pnl"] > 0, "dollar_pnl"].sum() if not executed.empty else 0.0
    losses = executed.loc[executed["dollar_pnl"] < 0, "dollar_pnl"].sum() if not executed.empty else 0.0
    profit_factor = float(wins / abs(losses)) if losses < 0 else (float("inf") if wins > 0 else 0.0)
    win_rate = float((executed["dollar_pnl"] > 0).mean()) if not executed.empty else pd.NA
    worst_account_trade_loss = float(executed["account_return_pct"].min()) if not executed.empty else pd.NA
    traded_ticker_count = int(executed["ticker"].nunique()) if not executed.empty else 0
    without_best_equity = _ending_equity_excluding_best_trade(executed, settings.starting_capital)
    top_profit_share = _top_ticker_profit_share(executed)
    result = {
        "executed_trade_count": int(len(executed)),
        "rejected_not_affordable_count": int(len(rejected)),
        "ending_equity": ending_equity,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "profit_factor": profit_factor,
        "win_rate": win_rate,
        "worst_account_trade_loss": worst_account_trade_loss,
        "traded_ticker_count": traded_ticker_count,
        "ending_equity_excluding_best_trade": without_best_equity,
        "top_ticker_profit_share": top_profit_share,
    }
    fail_reasons = nano_gate_fail_reasons(result)
    result["nano_status"] = NANO_RESEARCH_QUALIFIED_NOT_LIVE if not fail_reasons else NANO_RESEARCH_ONLY_NOT_TRADABLE
    result["nano_fail_reasons"] = ", ".join(fail_reasons)
    result["nano_score"] = _nano_score(result)
    return result


def nano_gate_fail_reasons(result: dict) -> list[str]:
    reasons = []
    if int(result.get("executed_trade_count", 0)) < 20:
        reasons.append("executed_trade_count_lt_20")
    if not _gt(result.get("ending_equity"), 120.0):
        reasons.append("ending_equity_lte_120")
    if not _gt(result.get("max_drawdown"), -0.35):
        reasons.append("max_drawdown_lte_minus_35pct")
    if not _gt(result.get("worst_account_trade_loss"), -0.25):
        reasons.append("worst_account_trade_loss_lte_minus_25pct")
    if not _ge(result.get("win_rate"), 0.45):
        reasons.append("win_rate_lt_45pct")
    if not _gt(result.get("profit_factor"), 1.15):
        reasons.append("profit_factor_lte_1_15")
    if not _gt(result.get("ending_equity_excluding_best_trade"), 100.0):
        reasons.append("ending_equity_excluding_best_trade_lte_starting_capital")
    if int(result.get("traded_ticker_count", 0)) < 5:
        reasons.append("traded_ticker_count_lt_5")
    if not pd.isna(result.get("top_ticker_profit_share")) and float(result["top_ticker_profit_share"]) > 0.50:
        reasons.append("top_ticker_profit_share_above_50pct")
    return reasons


def _skipped_row(trade: pd.Series, cash: float, status: str, affordability: dict | None = None) -> dict:
    affordability = affordability or {}
    return {
        "candidate_id": trade.get("candidate_id"),
        "signal_date": pd.Timestamp(trade["signal_date"]).strftime("%Y-%m-%d"),
        "entry_date": pd.Timestamp(trade["entry_date"]).strftime("%Y-%m-%d"),
        "exit_date": pd.Timestamp(trade["exit_date"]).strftime("%Y-%m-%d"),
        "ticker": trade["ticker"],
        "entry_price": float(trade["entry_price"]),
        "adjusted_entry_price": affordability.get("adjusted_entry_price", pd.NA),
        "shares": affordability.get("shares", 0),
        "total_cost": affordability.get("total_cost", pd.NA),
        "cash_before": cash,
        "cash_after_entry": cash,
        "exit_price": float(trade["exit_price"]),
        "exit_reason": trade["exit_reason"],
        "cash_after_exit": cash,
        "trade_return_pct": pd.NA,
        "account_return_pct": 0.0,
        "dollar_pnl": 0.0,
        "stop_loss": float(trade["stop_loss"]),
        "target_1": float(trade["target_1"]),
        "target_2": float(trade["target_2"]),
        "dollar_risk": affordability.get("dollar_risk", 0.0),
        "affordability_status": status,
    }


def _max_drawdown(executed: pd.DataFrame, starting_capital: float) -> float:
    if executed.empty:
        return 0.0
    equity = pd.Series([starting_capital, *executed["cash_after_exit"].tolist()])
    running_max = equity.cummax()
    drawdowns = equity / running_max - 1.0
    return float(drawdowns.min())


def _ending_equity_excluding_best_trade(executed: pd.DataFrame, starting_capital: float) -> float:
    if executed.empty:
        return starting_capital
    best_idx = executed["dollar_pnl"].idxmax()
    return float(starting_capital + executed.drop(index=best_idx)["dollar_pnl"].sum())


def _top_ticker_profit_share(executed: pd.DataFrame) -> object:
    if executed.empty:
        return pd.NA
    profits = executed.groupby("ticker")["dollar_pnl"].sum().sort_values(ascending=False)
    total_profit = profits[profits > 0].sum()
    if total_profit <= 0:
        return pd.NA
    return float(profits.iloc[0] / total_profit)


def _nano_score(result: dict) -> float:
    return (
        float(result.get("total_return", 0.0)) * 100
        + (0 if pd.isna(result.get("win_rate")) else float(result["win_rate"]) * 20)
        + float(result.get("profit_factor", 0.0))
        + float(result.get("max_drawdown", 0.0)) * 10
    )


def _top_tickers_markdown(trades: pd.DataFrame) -> str:
    if trades.empty:
        return "No executed Nano trades."
    executed = trades.loc[trades["affordability_status"].eq(EXECUTED)]
    if executed.empty:
        return "No executed Nano trades."
    top = executed["ticker"].value_counts().head(10).rename_axis("ticker").reset_index(name="executed_trades")
    return top.to_markdown(index=False)


def _gt(value: object, threshold: float) -> bool:
    return not pd.isna(value) and float(value) > threshold


def _ge(value: object, threshold: float) -> bool:
    return not pd.isna(value) and float(value) >= threshold


def _format_percent(value: object) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        return ""
    return f"{float(value):.2%}"


def _format_number(value: object) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        return ""
    return f"{float(value):.4f}"
