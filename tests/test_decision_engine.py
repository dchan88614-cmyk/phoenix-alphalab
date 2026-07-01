from pathlib import Path

import pandas as pd
import pytest

from src.decision.decision_engine import (
    BUY,
    NO_TRADE,
    build_decision_record,
    build_decision_simulation,
    summarize_decision_simulation,
    write_decision_simulation_markdown,
)
from src.reports.csv_export import write_csv


def _candidate(smoke_score=0.8, return_5d=0.05, return_20d=0.10, fwd_20=-0.5):
    return pd.Series(
        {
            "date": "2026-05-01",
            "ticker": "AAA",
            "rank": 1,
            "close": 100.0,
            "atr": 4.0,
            "smoke_score": smoke_score,
            "relative_volume_prev20": 1.5,
            "return_5d": return_5d,
            "return_20d": return_20d,
            "distance_to_52w_high_prev": -0.10,
            "dollar_volume": 50_000_000.0,
            "fwd_return_5d": -0.1,
            "fwd_return_10d": -0.2,
            "fwd_return_20d": fwd_20,
            "excess_return_5d": -0.1,
            "excess_return_10d": -0.2,
            "excess_return_20d": fwd_20,
        }
    )


def test_decision_engine_emits_buy_when_baseline_conditions_pass():
    record = build_decision_record(_candidate())

    assert record.action == BUY
    assert record.ticker == "AAA"
    assert record.confidence == 80


def test_decision_engine_emits_no_trade_when_smoke_score_too_low():
    record = build_decision_record(_candidate(smoke_score=0.69))

    assert record.action == NO_TRADE


def test_stop_loss_and_targets_are_calculated_correctly():
    record = build_decision_record(_candidate())

    assert record.entry_price == pytest.approx(100.0)
    assert record.entry_low == pytest.approx(99.5)
    assert record.entry_high == pytest.approx(100.5)
    assert record.stop_loss == pytest.approx(94.0)
    assert record.target_1 == pytest.approx(112.0)
    assert record.target_2 == pytest.approx(124.0)


def test_decision_simulation_does_not_use_forward_returns_to_decide_buy():
    frame = pd.DataFrame([_candidate(fwd_20=-0.9)])

    decisions = build_decision_simulation(frame, horizons=[5, 10, 20])

    assert decisions.loc[0, "action"] == BUY
    assert decisions.loc[0, "fwd_return_20d"] == pytest.approx(-0.9)


def test_decision_report_files_are_written(tmp_path):
    frame = pd.DataFrame([_candidate(fwd_20=0.2)])
    decisions = build_decision_simulation(frame, horizons=[5, 10, 20])
    summary = summarize_decision_simulation(decisions, frame, horizons=[5, 10, 20])
    csv_path = Path(tmp_path) / "decision_simulation.csv"
    md_path = Path(tmp_path) / "decision_simulation.md"

    write_csv(decisions, csv_path)
    write_decision_simulation_markdown(decisions, summary, md_path, horizons=[5, 10, 20])

    assert csv_path.exists()
    assert md_path.exists()
