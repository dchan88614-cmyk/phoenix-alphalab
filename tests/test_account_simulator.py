from pathlib import Path

import pandas as pd

from src.account.account_simulator import (
    EXECUTED,
    NANO_RESEARCH_QUALIFIED_NOT_LIVE,
    NOT_AFFORDABLE,
    AccountSettings,
    calculate_affordability,
    nano_gate_fail_reasons,
    simulate_nano_account,
    write_nano_summary,
)


def _trade(
    ticker="AAA",
    entry_price=20.0,
    exit_price=24.0,
    signal_date="2025-01-01",
    entry_date="2025-01-02",
    exit_date="2025-01-10",
    candidate_id=1,
):
    return {
        "candidate_id": candidate_id,
        "signal_date": signal_date,
        "entry_date": entry_date,
        "ticker": ticker,
        "entry_price": entry_price,
        "stop_loss": entry_price * 0.9,
        "target_1": entry_price * 1.2,
        "target_2": entry_price * 1.4,
        "exit_date": exit_date,
        "exit_price": exit_price,
        "exit_reason": "TIME_EXIT",
        "holding_days": 5,
        "realized_return": exit_price / entry_price - 1,
        "benchmark_return_same_period": 0.0,
        "realized_excess_return": exit_price / entry_price - 1,
        "decision_strength": 1.0,
        "window_start": "2025-01-01",
        "window_end": "2025-03-31",
    }


def test_100_account_cannot_buy_400_stock_without_fractional_shares():
    status = calculate_affordability(pd.Series(_trade(entry_price=400.0)), 100.0, AccountSettings())

    assert status["affordability_status"] == NOT_AFFORDABLE
    assert status["shares"] == 0


def test_whole_share_count_is_calculated_correctly():
    settings = AccountSettings(slippage_bps=0)
    status = calculate_affordability(pd.Series(_trade(entry_price=30.0)), 100.0, settings)

    assert status["shares"] == 3
    assert status["total_cost"] == 90.0


def test_cash_updates_after_entry_and_exit():
    settings = AccountSettings(slippage_bps=0)
    trades, equity, _ = simulate_nano_account(pd.DataFrame([_trade(entry_price=20.0, exit_price=25.0)]), settings)

    row = trades.iloc[0]
    assert row["affordability_status"] == EXECUTED
    assert row["cash_after_entry"] == 0.0
    assert row["cash_after_exit"] == 125.0
    assert equity.iloc[-1]["equity"] == 125.0


def test_one_position_at_a_time_rule_skips_overlapping_trade():
    settings = AccountSettings(slippage_bps=0)
    trades = pd.DataFrame(
        [
            _trade("AAA", signal_date="2025-01-01", entry_date="2025-01-02", exit_date="2025-01-10"),
            _trade("BBB", signal_date="2025-01-03", entry_date="2025-01-06", exit_date="2025-01-15"),
        ]
    )

    result, _, _ = simulate_nano_account(trades, settings)

    assert list(result["affordability_status"]) == [EXECUTED, "SKIPPED_POSITION_OPEN"]


def test_not_affordable_trade_is_rejected_before_simulated_execution():
    result, _, _ = simulate_nano_account(pd.DataFrame([_trade(entry_price=150.0)]), AccountSettings())

    assert result.iloc[0]["affordability_status"] == NOT_AFFORDABLE
    assert result.iloc[0]["cash_after_exit"] == 100.0


def test_nano_gate_fails_if_ending_equity_lte_120():
    reasons = nano_gate_fail_reasons(
        {
            "executed_trade_count": 20,
            "ending_equity": 120.0,
            "max_drawdown": -0.1,
            "worst_account_trade_loss": -0.1,
            "win_rate": 0.5,
            "profit_factor": 2.0,
            "ending_equity_excluding_best_trade": 110.0,
            "traded_ticker_count": 5,
            "top_ticker_profit_share": 0.4,
        }
    )

    assert "ending_equity_lte_120" in reasons


def test_nano_gate_passes_only_when_all_conditions_met():
    reasons = nano_gate_fail_reasons(
        {
            "executed_trade_count": 20,
            "ending_equity": 121.0,
            "max_drawdown": -0.1,
            "worst_account_trade_loss": -0.1,
            "win_rate": 0.5,
            "profit_factor": 1.2,
            "ending_equity_excluding_best_trade": 101.0,
            "traded_ticker_count": 5,
            "top_ticker_profit_share": 0.4,
        }
    )

    assert reasons == []


def test_nano_summary_explains_prior_non_nano_results_are_invalid(tmp_path):
    summary = pd.DataFrame(
        [
            {
                "candidate_id": 1,
                "max_entry_price": 100.0,
                "executed_trade_count": 20,
                "rejected_not_affordable_count": 1,
                "ending_equity": 121.0,
                "total_return": 0.21,
                "max_drawdown": -0.1,
                "profit_factor": 1.2,
                "win_rate": 0.5,
                "worst_account_trade_loss": -0.1,
                "traded_ticker_count": 5,
                "ending_equity_excluding_best_trade": 101.0,
                "top_ticker_profit_share": 0.4,
                "nano_status": NANO_RESEARCH_QUALIFIED_NOT_LIVE,
                "nano_fail_reasons": "",
                "nano_score": 1.0,
            }
        ]
    )
    path = Path(tmp_path) / "nano_account_summary.md"

    write_nano_summary(summary, pd.DataFrame(), pd.DataFrame(), path, AccountSettings())

    assert "Why prior results were invalid for $100 account" in path.read_text(encoding="utf-8")
