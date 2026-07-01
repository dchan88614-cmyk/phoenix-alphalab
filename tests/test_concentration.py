from pathlib import Path

import pandas as pd
import pytest

from src.reports.csv_export import write_csv
from src.research.concentration import (
    apply_per_ticker_cap,
    build_concentration_report,
    build_regime_diagnostics,
    build_robustness_report,
    equal_ticker_weighted_metrics,
    excluding_most_selected_ticker,
    excluding_mstr,
    robustness_gate_fail_reasons,
    write_concentration_markdown,
    write_regime_markdown,
)


def _trade(ticker, ret, excess, strength, signal_date="2025-01-01", candidate_id=1, exit_reason="TIME_EXIT"):
    return {
        "signal_date": signal_date,
        "entry_date": "2025-01-02",
        "ticker": ticker,
        "entry_price": 100.0,
        "stop_loss": 92.0,
        "target_1": 116.0,
        "target_2": 132.0,
        "exit_date": "2025-01-10",
        "exit_price": 100.0 * (1 + ret),
        "exit_reason": exit_reason,
        "holding_days": 5,
        "realized_return": ret,
        "benchmark_return_same_period": ret - excess,
        "realized_excess_return": excess,
        "candidate_id": candidate_id,
        "decision_strength": strength,
        "window_start": "2025-01-01",
        "window_end": "2025-03-31",
    }


def test_concentration_report_computes_ticker_trade_share():
    trades = pd.DataFrame([_trade("AAA", 0.1, 0.1, 0.1), _trade("AAA", 0.1, 0.1, 0.2), _trade("BBB", 0.1, 0.1, 0.3)])

    report, _ = build_concentration_report(trades)

    aaa = report.loc[report["ticker"].eq("AAA")].iloc[0]
    assert aaa["trade_share"] == pytest.approx(2 / 3)


def test_excluding_mstr_removes_only_mstr_trades():
    trades = pd.DataFrame([_trade("MSTR", 0.1, 0.1, 0.9), _trade("AAA", 0.1, 0.1, 0.1)])

    remaining = excluding_mstr(trades)

    assert set(remaining["ticker"]) == {"AAA"}


def test_excluding_most_selected_ticker_uses_counts_not_returns():
    trades = pd.DataFrame(
        [
            _trade("AAA", -0.5, -0.5, 0.1),
            _trade("AAA", -0.4, -0.4, 0.2),
            _trade("BBB", 2.0, 2.0, 0.3),
        ]
    )

    remaining = excluding_most_selected_ticker(trades)

    assert set(remaining["ticker"]) == {"BBB"}


def test_per_ticker_cap_keeps_signal_safe_decision_strength_only():
    trades = pd.DataFrame(
        [
            _trade("AAA", -1.0, -1.0, 0.9, signal_date="2025-01-03"),
            _trade("AAA", 5.0, 5.0, 0.1, signal_date="2025-01-01"),
            _trade("AAA", 4.0, 4.0, 0.8, signal_date="2025-01-02"),
        ]
    )

    capped = apply_per_ticker_cap(trades, max_trades=1)

    assert len(capped) == 1
    assert capped.iloc[0]["decision_strength"] == pytest.approx(0.9)
    assert capped.iloc[0]["realized_return"] == pytest.approx(-1.0)


def test_equal_ticker_weighted_performance_gives_each_ticker_equal_weight():
    trades = pd.DataFrame(
        [
            _trade("AAA", 0.10, 0.10, 0.1),
            _trade("AAA", 0.10, 0.10, 0.2),
            _trade("BBB", -0.20, -0.20, 0.3),
        ]
    )

    metrics = equal_ticker_weighted_metrics(trades)

    assert metrics["avg_realized_excess_return"] == pytest.approx(-0.05)


def test_robustness_gate_fails_if_mstr_removal_destroys_positive_excess():
    result = {
        "excluding_mstr_avg_realized_excess_return": -0.01,
        "excluding_most_selected_avg_realized_excess_return": 0.01,
        "top1_ticker_trade_share": 0.2,
        "top3_ticker_trade_share": 0.4,
        "equal_ticker_weighted_avg_realized_excess_return": 0.01,
    }

    assert "excluding_mstr_excess_not_positive" in robustness_gate_fail_reasons(result)


def test_robustness_gate_fails_if_top1_ticker_share_exceeds_25pct():
    result = {
        "excluding_mstr_avg_realized_excess_return": 0.01,
        "excluding_most_selected_avg_realized_excess_return": 0.01,
        "top1_ticker_trade_share": 0.26,
        "top3_ticker_trade_share": 0.4,
        "equal_ticker_weighted_avg_realized_excess_return": 0.01,
    }

    assert "top1_ticker_trade_share_above_25pct" in robustness_gate_fail_reasons(result)


def test_regime_diagnostics_use_signal_date_or_prior_data():
    trades = pd.DataFrame([_trade("AAA", 0.1, 0.1, 0.1, signal_date="2025-10-08")])
    dates = pd.bdate_range("2025-01-01", periods=210)
    data = pd.DataFrame(
        {"date": date, "ticker": "SPY", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100 + index}
        for index, date in enumerate(dates)
    )

    report = build_regime_diagnostics(trades, data)

    assert not report.empty
    assert "spy_above_50dma" in set(report["regime"])


def test_concentration_reports_are_written(tmp_path):
    trades = pd.DataFrame([_trade("AAA", 0.1, 0.1, 0.1), _trade("BBB", -0.1, -0.1, 0.2)])
    concentration, summary = build_concentration_report(trades)
    robustness = build_robustness_report(trades)
    regime = build_regime_diagnostics(
        trades,
        pd.DataFrame(
            {"date": date, "ticker": "SPY", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100 + index}
            for index, date in enumerate(pd.bdate_range("2024-01-01", periods=220))
        ),
    )
    concentration_csv = Path(tmp_path) / "concentration_report.csv"
    concentration_md = Path(tmp_path) / "concentration_report.md"
    robustness_csv = Path(tmp_path) / "robustness_report.csv"
    regime_md = Path(tmp_path) / "regime_diagnostics.md"

    write_csv(concentration, concentration_csv)
    write_csv(robustness, robustness_csv)
    write_concentration_markdown(concentration, summary, concentration_md)
    write_regime_markdown(regime, regime_md)

    assert concentration_csv.exists()
    assert concentration_md.exists()
    assert robustness_csv.exists()
    assert regime_md.exists()
