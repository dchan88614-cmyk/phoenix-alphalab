from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, calculate_affordability
from src.backtest.smoke_test import SMOKE_RANK_FACTORS
from src.research.auto_loop import CandidateRule, generate_candidate_rules, row_passes_candidate


MANUAL_REVIEW_CANDIDATE = "MANUAL_REVIEW_CANDIDATE"
NO_TRADE_MANUAL_REVIEW = "NO_TRADE_MANUAL_REVIEW"
STALE_DATA = "STALE_DATA"


def candidate_34_nano_rule() -> CandidateRule:
    """Return the current Nano Candidate 34 rule with the $50 Nano entry cap."""
    candidates = generate_candidate_rules(100)
    candidate = next((item for item in candidates if item.candidate_id == 34), None)
    if candidate is None:
        return CandidateRule(
            candidate_id=34,
            max_buy_rate=0.30,
            min_relative_volume_prev20=1.5,
            min_smoke_score=0.85,
            min_rank_gap=0.0,
            require_return_5d_positive=True,
            require_return_20d_positive=False,
            distance_to_52w_high_prev_min=-0.35,
            dollar_volume_min=20_000_000,
            max_trades_per_ticker_per_year=None,
            max_entry_price=50.0,
        )
    return replace(candidate, max_entry_price=50.0)


def build_nano_daily_scan(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    benchmark_ticker: str = "SPY",
    requested_end: str | None = None,
    stale_after_calendar_days: int = 7,
    rule: CandidateRule | None = None,
) -> tuple[pd.DataFrame, dict]:
    required = ["date", "ticker", "close", "atr", *SMOKE_RANK_FACTORS]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Nano daily scan missing required columns: {', '.join(missing)}")

    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    research = frame.loc[~frame["ticker"].eq(benchmark_ticker)].copy()
    research = research.dropna(subset=["date", "ticker", "close", *SMOKE_RANK_FACTORS])
    if research.empty:
        return _no_trade_result(
            latest_data_date="",
            reason="NO_ELIGIBLE_DATA",
            account_settings=account_settings,
            top_candidates=pd.DataFrame(),
            stale=True,
        )

    latest_date = research["date"].max()
    latest = research.loc[research["date"].eq(latest_date)].copy()
    latest_data_date = latest_date.strftime("%Y-%m-%d")
    stale = _is_stale(latest_date, requested_end, stale_after_calendar_days)
    candidate_rule = rule or candidate_34_nano_rule()

    scanned = _score_latest_candidates(latest, candidate_rule, account_settings)
    if stale:
        return _no_trade_result(
            latest_data_date=latest_data_date,
            reason=STALE_DATA,
            account_settings=account_settings,
            top_candidates=scanned,
            stale=True,
        )

    passed = scanned.loc[scanned["all_rule_checks_passed"]].copy()
    if passed.empty:
        return _no_trade_result(
            latest_data_date=latest_data_date,
            reason="NO_CANDIDATE_PASSED_RULES",
            account_settings=account_settings,
            top_candidates=scanned,
            stale=False,
        )

    best = passed.sort_values(["decision_strength", "smoke_score", "ticker"], ascending=[False, False, True]).iloc[0]
    result = _result_from_candidate(best, latest_data_date, account_settings, candidate_rule, scanned, stale=False)
    return result


def write_nano_daily_scan_reports(
    scan: pd.DataFrame,
    metadata: dict,
    csv_path: str | Path,
    md_path: str | Path,
) -> None:
    csv_output = Path(csv_path)
    md_output = Path(md_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    scan.to_csv(csv_output, index=False)
    md_output.write_text(_daily_scan_markdown(scan, metadata), encoding="utf-8")


def _score_latest_candidates(
    latest: pd.DataFrame,
    rule: CandidateRule,
    account_settings: AccountSettings,
) -> pd.DataFrame:
    scored = latest.copy()
    score_columns: list[str] = []
    for factor in SMOKE_RANK_FACTORS:
        score_column = f"{factor}_score"
        scored[score_column] = scored[factor].rank(method="first", pct=True)
        score_columns.append(score_column)
    scored["smoke_score"] = scored[score_columns].mean(axis=1)
    scored = scored.sort_values(["smoke_score", "ticker"], ascending=[False, True]).reset_index(drop=True)
    second_score = float(scored.iloc[1]["smoke_score"]) if len(scored) > 1 else 0.0
    scored["rank"] = range(1, len(scored) + 1)
    scored["rank_gap"] = scored["smoke_score"].apply(lambda value: float(value) - second_score)
    scored["decision_strength"] = scored.apply(_decision_strength, axis=1)

    rows: list[dict] = []
    for _, row in scored.iterrows():
        stop_loss, target_1, target_2 = _risk_levels(row)
        affordability = calculate_affordability(
            pd.Series({"entry_price": row["close"], "stop_loss": stop_loss}),
            account_settings.starting_capital,
            account_settings,
        )
        signal_rule_pass = row_passes_candidate(row, rule)
        max_entry_pass = float(row["close"]) <= rule.max_entry_price
        affordable_pass = int(affordability["shares"]) >= 1 and affordability["total_cost"] <= account_settings.starting_capital
        rows.append(
            {
                "rank": int(row["rank"]),
                "ticker": row["ticker"],
                "reference_price": float(row["close"]),
                "smoke_score": float(row["smoke_score"]),
                "decision_strength": float(row["decision_strength"]),
                "relative_volume_prev20": float(row["relative_volume_prev20"]),
                "return_5d": float(row["return_5d"]),
                "return_20d": float(row["return_20d"]),
                "distance_to_52w_high_prev": float(row["distance_to_52w_high_prev"]),
                "dollar_volume": float(row["dollar_volume"]),
                "stop_loss": stop_loss,
                "target_1": target_1,
                "target_2": target_2,
                "shares_with_100": affordability["shares"],
                "estimated_total_cost": affordability["total_cost"],
                "estimated_cash_remaining": affordability["cash_remaining"],
                "max_dollar_risk": affordability["dollar_risk"],
                "signal_rule_pass": bool(signal_rule_pass),
                "max_entry_price_pass": bool(max_entry_pass),
                "affordability_pass": bool(affordable_pass),
                "all_rule_checks_passed": bool(signal_rule_pass and max_entry_pass and affordable_pass),
            }
        )
    return pd.DataFrame(rows)


def _result_from_candidate(
    candidate: pd.Series,
    latest_data_date: str,
    account_settings: AccountSettings,
    rule: CandidateRule,
    scanned: pd.DataFrame,
    stale: bool,
) -> tuple[pd.DataFrame, dict]:
    result = pd.DataFrame(
        [
            {
                "action": MANUAL_REVIEW_CANDIDATE,
                "ticker": candidate["ticker"],
                "latest_data_date": latest_data_date,
                "reference_price": candidate["reference_price"],
                "shares_with_100": candidate["shares_with_100"],
                "estimated_total_cost": candidate["estimated_total_cost"],
                "estimated_cash_remaining": candidate["estimated_cash_remaining"],
                "stop_loss": candidate["stop_loss"],
                "target_1": candidate["target_1"],
                "target_2": candidate["target_2"],
                "max_dollar_risk": candidate["max_dollar_risk"],
                "expected_holding_period": "up to 20 trading days",
                "reason": "Candidate 34 Nano rule passed with $100 whole-share affordability.",
                "all_rule_checks_passed": True,
                "is_stale": stale,
            }
        ]
    )
    return result, _metadata(rule, account_settings, scanned, latest_data_date, stale)


def _no_trade_result(
    latest_data_date: str,
    reason: str,
    account_settings: AccountSettings,
    top_candidates: pd.DataFrame,
    stale: bool,
) -> tuple[pd.DataFrame, dict]:
    rule = candidate_34_nano_rule()
    result = pd.DataFrame(
        [
            {
                "action": NO_TRADE_MANUAL_REVIEW,
                "ticker": "",
                "latest_data_date": latest_data_date,
                "reference_price": pd.NA,
                "shares_with_100": 0,
                "estimated_total_cost": 0.0,
                "estimated_cash_remaining": account_settings.starting_capital,
                "stop_loss": pd.NA,
                "target_1": pd.NA,
                "target_2": pd.NA,
                "max_dollar_risk": 0.0,
                "expected_holding_period": "",
                "reason": reason,
                "all_rule_checks_passed": False,
                "is_stale": stale,
            }
        ]
    )
    return result, _metadata(rule, account_settings, top_candidates, latest_data_date, stale)


def _metadata(
    rule: CandidateRule,
    account_settings: AccountSettings,
    scanned: pd.DataFrame,
    latest_data_date: str,
    stale: bool,
) -> dict:
    return {
        "rule": rule,
        "account_settings": account_settings,
        "top_candidates": scanned.head(5).copy() if not scanned.empty else pd.DataFrame(),
        "latest_data_date": latest_data_date,
        "is_stale": stale,
    }


def _risk_levels(row: pd.Series) -> tuple[float, float, float]:
    reference_price = float(row["close"])
    atr = row.get("atr", pd.NA)
    stop_loss = reference_price * 0.92 if pd.isna(atr) or float(atr) <= 0 else reference_price - 1.5 * float(atr)
    risk = max(0.0, reference_price - stop_loss)
    return float(stop_loss), float(reference_price + 2.0 * risk), float(reference_price + 4.0 * risk)


def _decision_strength(row: pd.Series) -> float:
    smoke_score = _clip(float(row.get("smoke_score", 0.0)), 0.0, 1.0)
    rank_gap = _clip(float(row.get("rank_gap", 0.0)) / 0.20, 0.0, 1.0)
    rel_volume = row.get("relative_volume_prev20", 0.0)
    rel_volume_score = 0.0 if pd.isna(rel_volume) else _clip(float(rel_volume) / 3.0, 0.0, 1.0)
    return float((smoke_score + rank_gap + rel_volume_score) / 3.0)


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _is_stale(latest_data_date: pd.Timestamp, requested_end: str | None, stale_after_calendar_days: int) -> bool:
    if not requested_end:
        return False
    end = pd.Timestamp(requested_end).normalize()
    latest = pd.Timestamp(latest_data_date).normalize()
    return (end - latest).days > stale_after_calendar_days


def _daily_scan_markdown(scan: pd.DataFrame, metadata: dict) -> str:
    row = scan.iloc[0]
    action = row["action"]
    lines = [
        "PHOENIX NANO DAILY SCAN",
        f"Action: {action}",
        "",
        "Research only. Not live trading. Not financial advice.",
        "",
        f"Ticker: {row['ticker']}",
        f"Latest data date: {row['latest_data_date']}",
        f"Reference price: {_format_money(row['reference_price'])}",
        f"Shares with $100: {row['shares_with_100']}",
        f"Estimated total cost: {_format_money(row['estimated_total_cost'])}",
        f"Estimated cash remaining: {_format_money(row['estimated_cash_remaining'])}",
        f"Stop loss: {_format_money(row['stop_loss'])}",
        f"Target 1: {_format_money(row['target_1'])}",
        f"Target 2: {_format_money(row['target_2'])}",
        f"Max dollar risk: {_format_money(row['max_dollar_risk'])}",
        f"Expected holding period: {row['expected_holding_period']}",
        f"Reason: {row['reason']}",
        "",
        "## Rule",
        "",
        "- Factor timing: EOD",
        "- Uses only latest-date-safe factors; forward returns and realized trade outcomes are not ranking inputs.",
        "- Account: $100, whole shares only.",
        "- Candidate rule: Candidate 34 Nano with max_entry_price $50.",
        f"- Stale data: {metadata['is_stale']}",
        "",
        "## Top 5 Scanned Candidates",
        "",
    ]
    top = metadata.get("top_candidates", pd.DataFrame())
    if top is None or top.empty:
        lines.append("No scanned candidates.")
    else:
        display = top[
            [
                "rank",
                "ticker",
                "reference_price",
                "smoke_score",
                "decision_strength",
                "shares_with_100",
                "estimated_total_cost",
                "signal_rule_pass",
                "max_entry_price_pass",
                "affordability_pass",
                "all_rule_checks_passed",
            ]
        ].copy()
        lines.append(display.to_markdown(index=False))
    return "\n".join(lines) + "\n"


def _format_money(value: object) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        return ""
    return f"${float(value):.2f}"
