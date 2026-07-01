from __future__ import annotations

import pandas as pd


STOP = "STOP"
TARGET_1 = "TARGET_1"
TARGET_2 = "TARGET_2"
TIME_EXIT = "TIME_EXIT"


def simulate_trades(
    buy_signals: pd.DataFrame,
    price_data: pd.DataFrame,
    benchmark_ticker: str,
    max_holding_days: int = 20,
) -> pd.DataFrame:
    """Simulate next-session entries and fixed stop/target exits for BUY signals."""
    columns = [
        "signal_date",
        "entry_date",
        "ticker",
        "entry_price",
        "stop_loss",
        "target_1",
        "target_2",
        "exit_date",
        "exit_price",
        "exit_reason",
        "holding_days",
        "realized_return",
        "benchmark_return_same_period",
        "realized_excess_return",
        "candidate_id",
        "window_start",
        "window_end",
    ]
    if buy_signals.empty:
        return pd.DataFrame(columns=columns)

    required = {"date", "ticker", "open", "high", "low", "close"}
    missing = required.difference(price_data.columns)
    if missing:
        raise ValueError(f"Trade simulator missing price columns: {', '.join(sorted(missing))}")

    history = price_data.copy()
    history["date"] = pd.to_datetime(history["date"])
    history = history.sort_values(["ticker", "date"])
    by_ticker = {ticker: frame.reset_index(drop=True) for ticker, frame in history.groupby("ticker")}
    benchmark = by_ticker.get(benchmark_ticker)

    rows: list[dict] = []
    signals = buy_signals.copy()
    signals["date"] = pd.to_datetime(signals["date"])
    for _, signal in signals.sort_values(["date", "ticker"]).iterrows():
        ticker_history = by_ticker.get(signal["ticker"])
        if ticker_history is None:
            continue

        future = ticker_history.loc[ticker_history["date"].gt(signal["date"])].head(max_holding_days)
        if future.empty:
            continue

        entry = future.iloc[0]
        entry_price = _first_valid(entry, ["open", "close"])
        if pd.isna(entry_price) or float(entry_price) <= 0:
            continue
        entry_price = float(entry_price)

        atr = signal.get("atr", pd.NA)
        if pd.isna(atr) or float(atr) <= 0:
            stop_loss = entry_price * 0.92
        else:
            stop_loss = entry_price - 1.5 * float(atr)
        risk = entry_price - stop_loss
        target_1 = entry_price + 2.0 * risk
        target_2 = entry_price + 4.0 * risk

        exit_row = future.iloc[-1]
        exit_price = float(exit_row["close"])
        exit_reason = TIME_EXIT
        holding_days = int(len(future))

        for day_index, (_, day) in enumerate(future.iterrows(), start=1):
            low = day["low"]
            high = day["high"]
            if not pd.isna(low) and float(low) <= stop_loss:
                exit_row = day
                exit_price = stop_loss
                exit_reason = STOP
                holding_days = day_index
                break
            if not pd.isna(high) and float(high) >= target_2:
                exit_row = day
                exit_price = target_2
                exit_reason = TARGET_2
                holding_days = day_index
                break
            if not pd.isna(high) and float(high) >= target_1:
                exit_row = day
                exit_price = target_1
                exit_reason = TARGET_1
                holding_days = day_index
                break

        benchmark_return = _benchmark_return(benchmark, entry["date"], exit_row["date"])
        realized_return = exit_price / entry_price - 1.0
        rows.append(
            {
                "signal_date": signal["date"].strftime("%Y-%m-%d"),
                "entry_date": pd.Timestamp(entry["date"]).strftime("%Y-%m-%d"),
                "ticker": signal["ticker"],
                "entry_price": entry_price,
                "stop_loss": float(stop_loss),
                "target_1": float(target_1),
                "target_2": float(target_2),
                "exit_date": pd.Timestamp(exit_row["date"]).strftime("%Y-%m-%d"),
                "exit_price": float(exit_price),
                "exit_reason": exit_reason,
                "holding_days": holding_days,
                "realized_return": float(realized_return),
                "benchmark_return_same_period": benchmark_return,
                "realized_excess_return": (
                    float(realized_return - benchmark_return) if not pd.isna(benchmark_return) else pd.NA
                ),
                "candidate_id": signal.get("candidate_id", pd.NA),
                "window_start": signal.get("window_start", ""),
                "window_end": signal.get("window_end", ""),
            }
        )

    return pd.DataFrame(rows, columns=columns)


def _first_valid(row: pd.Series, columns: list[str]) -> object:
    for column in columns:
        value = row.get(column, pd.NA)
        if not pd.isna(value):
            return value
    return pd.NA


def _benchmark_return(benchmark: pd.DataFrame | None, entry_date: pd.Timestamp, exit_date: pd.Timestamp) -> object:
    if benchmark is None or benchmark.empty:
        return pd.NA
    entry_rows = benchmark.loc[benchmark["date"].ge(entry_date)]
    exit_rows = benchmark.loc[benchmark["date"].le(exit_date)]
    if entry_rows.empty or exit_rows.empty:
        return pd.NA
    entry = entry_rows.iloc[0]
    exit_row = exit_rows.iloc[-1]
    entry_price = _first_valid(entry, ["open", "close"])
    exit_price = exit_row.get("close", pd.NA)
    if pd.isna(entry_price) or pd.isna(exit_price) or float(entry_price) <= 0:
        return pd.NA
    return float(exit_price) / float(entry_price) - 1.0
