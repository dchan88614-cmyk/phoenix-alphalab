import pandas as pd

from src.trading.trade_simulator import STOP, TARGET_1, TIME_EXIT, simulate_trades


def _signal(date="2025-01-01"):
    return pd.DataFrame(
        [
            {
                "date": date,
                "ticker": "AAA",
                "atr": 2.0,
                "candidate_id": 1,
                "window_start": "2025-01-01",
                "window_end": "2025-01-31",
            }
        ]
    )


def _prices(rows):
    spy = [
        {"date": row["date"], "ticker": "SPY", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0}
        for row in rows
    ]
    return pd.DataFrame(rows + spy)


def test_trade_simulator_enters_next_trading_day_not_signal_day():
    prices = _prices(
        [
            {"date": "2025-01-01", "ticker": "AAA", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
            {"date": "2025-01-02", "ticker": "AAA", "open": 105.0, "high": 106.0, "low": 104.0, "close": 105.0},
            {"date": "2025-01-03", "ticker": "AAA", "open": 105.0, "high": 106.0, "low": 104.0, "close": 105.0},
        ]
    )

    trades = simulate_trades(_signal(), prices, benchmark_ticker="SPY")

    assert trades.iloc[0]["entry_date"] == "2025-01-02"
    assert trades.iloc[0]["entry_price"] == 105.0


def test_stop_wins_when_stop_and_target_hit_same_day():
    prices = _prices(
        [
            {"date": "2025-01-01", "ticker": "AAA", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0},
            {"date": "2025-01-02", "ticker": "AAA", "open": 100.0, "high": 120.0, "low": 90.0, "close": 110.0},
        ]
    )

    trades = simulate_trades(_signal(), prices, benchmark_ticker="SPY")

    assert trades.iloc[0]["exit_reason"] == STOP
    assert trades.iloc[0]["realized_return"] < 0


def test_time_exit_works_if_no_stop_or_target_hit():
    prices = _prices(
        [
            {"date": "2025-01-01", "ticker": "AAA", "open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0},
            {"date": "2025-01-02", "ticker": "AAA", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5},
            {"date": "2025-01-03", "ticker": "AAA", "open": 100.5, "high": 101.0, "low": 99.5, "close": 101.0},
        ]
    )

    trades = simulate_trades(_signal(), prices, benchmark_ticker="SPY", max_holding_days=2)

    assert trades.iloc[0]["exit_reason"] == TIME_EXIT
    assert trades.iloc[0]["exit_date"] == "2025-01-03"


def test_target_exit_is_recorded():
    prices = _prices(
        [
            {"date": "2025-01-01", "ticker": "AAA", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0},
            {"date": "2025-01-02", "ticker": "AAA", "open": 100.0, "high": 107.0, "low": 99.0, "close": 106.0},
        ]
    )

    trades = simulate_trades(_signal(), prices, benchmark_ticker="SPY")

    assert trades.iloc[0]["exit_reason"] == TARGET_1
