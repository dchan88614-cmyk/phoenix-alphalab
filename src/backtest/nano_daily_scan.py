from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, calculate_affordability
from src.backtest.smoke_test import SMOKE_RANK_FACTORS
from src.research.auto_loop import CandidateRule, row_passes_candidate


MANUAL_REVIEW_CANDIDATE = "MANUAL_REVIEW_CANDIDATE"
NO_TRADE_MANUAL_REVIEW = "NO_TRADE_MANUAL_REVIEW"
STALE_DATA = "STALE_DATA"
MISSING_OR_AMBIGUOUS_CANDIDATE_34_RULES = "MISSING_OR_AMBIGUOUS_CANDIDATE_34_RULES"
MANUAL_VERIFY_ONLY_NOT_TRADE_SIGNAL = "MANUAL_VERIFY_ONLY_NOT_TRADE_SIGNAL"
RESEARCH_ONLY_NOT_TRADABLE = "RESEARCH_ONLY_NOT_TRADABLE"


def extract_candidate_34_rule(
    auto_research_path: str | Path = "data/reports/auto_research_generations.csv",
    candidate_id: int = 34,
) -> tuple[CandidateRule, pd.Series]:
    """Extract the single qualified Candidate 34 row from prior Nano research output."""
    frame = pd.read_csv(auto_research_path)
    matches = frame.loc[
        frame["candidate_id"].eq(candidate_id)
        & frame["nano_status"].eq("NANO_RESEARCH_QUALIFIED_NOT_LIVE")
    ].copy()
    if len(matches) != 1:
        raise ValueError(MISSING_OR_AMBIGUOUS_CANDIDATE_34_RULES)

    row = matches.iloc[0]
    max_entry_price = row.get("nano_max_entry_price", pd.NA)
    if pd.isna(max_entry_price):
        max_entry_price = row.get("max_entry_price_nano", pd.NA)
    if pd.isna(max_entry_price):
        max_entry_price = row.get("max_entry_price", pd.NA)
    if pd.isna(max_entry_price):
        raise ValueError(MISSING_OR_AMBIGUOUS_CANDIDATE_34_RULES)

    rule = CandidateRule(
        candidate_id=int(row["candidate_id"]),
        max_buy_rate=float(row["max_buy_rate"]),
        min_relative_volume_prev20=float(row["min_relative_volume_prev20"]),
        min_smoke_score=float(row["min_smoke_score"]),
        min_rank_gap=float(row["min_rank_gap"]),
        require_return_5d_positive=_as_bool(row["require_return_5d_positive"]),
        require_return_20d_positive=_as_bool(row["require_return_20d_positive"]),
        distance_to_52w_high_prev_min=float(row["distance_to_52w_high_prev_min"]),
        dollar_volume_min=float(row["dollar_volume_min"]),
        max_trades_per_ticker_per_year=(
            None if pd.isna(row["max_trades_per_ticker_per_year"]) else int(row["max_trades_per_ticker_per_year"])
        ),
        max_entry_price=float(max_entry_price),
    )
    return rule, row


def write_candidate_34_frozen_rules(
    output_path: str | Path,
    rule: CandidateRule | None,
    account_settings: AccountSettings,
    source_path: str | Path = "data/reports/auto_research_generations.csv",
    source_row: pd.Series | None = None,
    error: str = "",
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phoenix Nano Candidate 34 Frozen Rules",
        "",
        "Research only. Candidate 34 is not approved for paper trading or live trading.",
        "",
        f"- Source: `{source_path}`",
        f"- Frozen timestamp UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    if rule is None:
        lines.extend(["## Extraction Failed", "", f"- Reason: {error or MISSING_OR_AMBIGUOUS_CANDIDATE_34_RULES}", ""])
    else:
        rule_rows = [{"parameter": key, "value": value} for key, value in asdict(rule).items()]
        account_rows = [
            {"parameter": "starting_capital", "value": account_settings.starting_capital},
            {"parameter": "fractional_shares", "value": account_settings.fractional_shares},
            {"parameter": "max_position_fraction", "value": account_settings.max_position_fraction},
            {"parameter": "min_cash_reserve", "value": account_settings.min_cash_reserve},
            {"parameter": "commission_per_trade", "value": account_settings.commission_per_trade},
            {"parameter": "slippage_bps", "value": account_settings.slippage_bps},
        ]
        lines.extend(
            [
                "## Candidate Rule",
                "",
                pd.DataFrame(rule_rows).to_markdown(index=False),
                "",
                "## Account Settings",
                "",
                pd.DataFrame(account_rows).to_markdown(index=False),
                "",
                "## Simulator Logic",
                "",
                "- Entry reference for daily scan: latest completed EOD close.",
                "- Stop loss: close - 1.5 * ATR, or 8% below close when ATR is unavailable.",
                "- Target 1: entry + 2R.",
                "- Target 2: entry + 4R.",
                "- Expected holding period: up to 20 trading days.",
                "- Affordability: $100 whole-share account after slippage.",
                "- Forward returns and realized trade outcomes are not daily scan inputs.",
                "",
            ]
        )
        if source_row is not None:
            summary_columns = [
                "candidate_id",
                "nano_status",
                "executed_trade_count",
                "ending_equity",
                "max_drawdown",
                "profit_factor",
                "win_rate",
                "worst_account_trade_loss",
            ]
            existing = [column for column in summary_columns if column in source_row.index]
            lines.extend(
                [
                    "## Historical Nano Summary",
                    "",
                    pd.DataFrame(
                        [{"metric": column, "value": source_row[column]} for column in existing]
                    ).to_markdown(index=False),
                    "",
                ]
            )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_nano_daily_scan(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    benchmark_ticker: str = "SPY",
    requested_end: str | None = None,
    stale_after_calendar_days: int = 7,
    rule: CandidateRule | None = None,
    data_source: str = "unknown",
    scan_timestamp_utc: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    required = ["date", "ticker", "close", "atr", *SMOKE_RANK_FACTORS]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Nano daily scan missing required columns: {', '.join(missing)}")

    expected_latest = expected_latest_trading_date(requested_end) if requested_end else None

    if rule is None:
        try:
            rule, _ = extract_candidate_34_rule()
        except Exception:
            return _no_trade_result(
                latest_data_date="",
                reason=MISSING_OR_AMBIGUOUS_CANDIDATE_34_RULES,
                account_settings=account_settings,
                top_candidates=pd.DataFrame(),
                rejected_candidates=pd.DataFrame(),
                stale=True,
                rule=None,
                expected_latest=expected_latest,
                data_source=data_source,
                scan_timestamp_utc=scan_timestamp_utc,
            )

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
            rejected_candidates=pd.DataFrame(),
            stale=True,
            rule=rule,
            expected_latest=expected_latest,
            data_source=data_source,
            scan_timestamp_utc=scan_timestamp_utc,
        )

    latest_date = research["date"].max()
    latest = research.loc[research["date"].eq(latest_date)].copy()
    latest_data_date = latest_date.strftime("%Y-%m-%d")
    expected_latest = expected_latest or latest_date
    stale = pd.Timestamp(latest_date).normalize() < pd.Timestamp(expected_latest).normalize()

    scanned, rejected = _score_latest_candidates(latest, rule, account_settings)
    if stale:
        return _no_trade_result(
            latest_data_date=latest_data_date,
            reason=STALE_DATA,
            account_settings=account_settings,
            top_candidates=scanned,
            rejected_candidates=rejected,
            stale=True,
            rule=rule,
            expected_latest=expected_latest,
            data_source=data_source,
            scan_timestamp_utc=scan_timestamp_utc,
        )

    passed = scanned.loc[scanned["all_rule_checks_passed"]].copy()
    if passed.empty:
        return _no_trade_result(
            latest_data_date=latest_data_date,
            reason="NO_CANDIDATE_PASSED_RULES",
            account_settings=account_settings,
            top_candidates=scanned,
            rejected_candidates=rejected,
            stale=False,
            rule=rule,
            expected_latest=expected_latest,
            data_source=data_source,
            scan_timestamp_utc=scan_timestamp_utc,
        )

    best = passed.sort_values(["decision_strength", "smoke_score", "ticker"], ascending=[False, False, True]).iloc[0]
    return _result_from_candidate(
        best,
        latest_data_date,
        account_settings,
        rule,
        scanned,
        rejected,
        stale=False,
        expected_latest=expected_latest,
        data_source=data_source,
        scan_timestamp_utc=scan_timestamp_utc,
    )


def write_nano_daily_scan_reports(
    scan: pd.DataFrame,
    metadata: dict,
    csv_path: str | Path,
    md_path: str | Path,
    history_csv_path: str | Path | None = None,
) -> None:
    csv_output = Path(csv_path)
    md_output = Path(md_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    diagnostic = _daily_scan_csv(scan, metadata)
    diagnostic.to_csv(csv_output, index=False)
    if history_csv_path is not None:
        history_path = Path(history_csv_path)
        before_count = len(pd.read_csv(history_path)) if history_path.exists() else 0
        history = append_scan_history(diagnostic, history_path)
        metadata["history_rows_written"] = int(len(history) - before_count)
        metadata["history_file_path"] = str(history_path)
        metadata["history_total_row_count"] = int(len(history))
    else:
        metadata["history_rows_written"] = 0
        metadata["history_file_path"] = ""
        metadata["history_total_row_count"] = 0
    md_output.write_text(_daily_scan_markdown(scan, metadata), encoding="utf-8")


def append_scan_history(diagnostic_rows: pd.DataFrame, history_csv_path: str | Path) -> pd.DataFrame:
    path = Path(history_csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=diagnostic_rows.columns)
    combined = diagnostic_rows.copy() if existing.empty else pd.concat([existing, diagnostic_rows], ignore_index=True)
    for column in ["scan_timestamp_utc", "latest_data_date", "row_type", "ticker"]:
        if column not in combined.columns:
            combined[column] = ""
        combined[column] = combined[column].fillna("").astype(str)
    combined = combined.drop_duplicates(
        subset=["scan_timestamp_utc", "latest_data_date", "row_type", "ticker"],
        keep="last",
    )
    combined.to_csv(path, index=False)
    return combined


def _score_latest_candidates(
    latest: pd.DataFrame,
    rule: CandidateRule,
    account_settings: AccountSettings,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prechecked_rows: list[dict] = []
    for _, row in latest.copy().iterrows():
        stop_loss, target_1, target_2 = _risk_levels(row)
        affordability = calculate_affordability(
            pd.Series({"entry_price": row["close"], "stop_loss": stop_loss}),
            account_settings.starting_capital,
            account_settings,
        )
        max_entry_pass = float(row["close"]) <= rule.max_entry_price
        affordable_pass = int(affordability["shares"]) >= 1 and affordability["total_cost"] <= account_settings.starting_capital
        prechecked_rows.append(
            {
                "ticker": row["ticker"],
                "reference_price": float(row["close"]),
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
                "max_entry_price_pass": bool(max_entry_pass),
                "affordability_pass": bool(affordable_pass),
                "executable_pre_rank": bool(max_entry_pass and affordable_pass),
            }
        )

    prechecked = pd.DataFrame(prechecked_rows)
    if prechecked.empty:
        return pd.DataFrame(), pd.DataFrame()

    rejected = prechecked.loc[~prechecked["executable_pre_rank"]].copy()
    if not rejected.empty:
        rejected["rejection_reason"] = rejected.apply(_rejection_reason, axis=1)

    executable = prechecked.loc[prechecked["executable_pre_rank"]].copy()
    if executable.empty:
        return pd.DataFrame(), rejected.sort_values(["reference_price", "ticker"], ascending=[False, True]).reset_index(drop=True)

    scored = executable.copy()
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
        signal_rule_pass = row_passes_candidate(row, rule)
        failed_checks = _candidate_failed_checks(row, rule)
        rows.append(
            {
                "rank": int(row["rank"]),
                "ticker": row["ticker"],
                "reference_price": float(row["reference_price"]),
                "smoke_score": float(row["smoke_score"]),
                "decision_strength": float(row["decision_strength"]),
                "relative_volume_prev20": float(row["relative_volume_prev20"]),
                "return_5d": float(row["return_5d"]),
                "return_20d": float(row["return_20d"]),
                "distance_to_52w_high_prev": float(row["distance_to_52w_high_prev"]),
                "dollar_volume": float(row["dollar_volume"]),
                "stop_loss": float(row["stop_loss"]),
                "target_1": float(row["target_1"]),
                "target_2": float(row["target_2"]),
                "shares_with_100": row["shares_with_100"],
                "estimated_total_cost": row["estimated_total_cost"],
                "estimated_cash_remaining": row["estimated_cash_remaining"],
                "max_dollar_risk": row["max_dollar_risk"],
                "signal_rule_pass": bool(signal_rule_pass),
                "max_entry_price_pass": True,
                "affordability_pass": True,
                "all_rule_checks_passed": bool(signal_rule_pass),
                "failed_checks": failed_checks,
            }
        )
    return pd.DataFrame(rows), rejected.sort_values(["reference_price", "ticker"], ascending=[False, True]).reset_index(drop=True)


def _result_from_candidate(
    candidate: pd.Series,
    latest_data_date: str,
    account_settings: AccountSettings,
    rule: CandidateRule,
    scanned: pd.DataFrame,
    rejected: pd.DataFrame,
    stale: bool,
    expected_latest: pd.Timestamp,
    data_source: str,
    scan_timestamp_utc: str | None,
) -> tuple[pd.DataFrame, dict]:
    result = pd.DataFrame(
        [
            {
                "action": MANUAL_REVIEW_CANDIDATE,
                "status": MANUAL_VERIFY_ONLY_NOT_TRADE_SIGNAL,
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
                "executable_universe_count": int(len(scanned)),
                "rejected_not_affordable_count": _rejected_not_affordable_count(rejected),
                "rejected_above_max_entry_price_count": _rejected_above_max_entry_price_count(rejected),
            }
        ]
    )
    return result, _metadata(
        rule, account_settings, scanned, rejected, latest_data_date, stale, expected_latest, data_source, scan_timestamp_utc
    )


def _no_trade_result(
    latest_data_date: str,
    reason: str,
    account_settings: AccountSettings,
    top_candidates: pd.DataFrame,
    rejected_candidates: pd.DataFrame,
    stale: bool,
    rule: CandidateRule | None,
    expected_latest: pd.Timestamp | None,
    data_source: str,
    scan_timestamp_utc: str | None,
) -> tuple[pd.DataFrame, dict]:
    result = pd.DataFrame(
        [
            {
                "action": NO_TRADE_MANUAL_REVIEW,
                "status": RESEARCH_ONLY_NOT_TRADABLE,
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
                "executable_universe_count": int(len(top_candidates)),
                "rejected_not_affordable_count": _rejected_not_affordable_count(rejected_candidates),
                "rejected_above_max_entry_price_count": _rejected_above_max_entry_price_count(rejected_candidates),
            }
        ]
    )
    return result, _metadata(
        rule,
        account_settings,
        top_candidates,
        rejected_candidates,
        latest_data_date,
        stale,
        expected_latest,
        data_source,
        scan_timestamp_utc,
    )


def _metadata(
    rule: CandidateRule | None,
    account_settings: AccountSettings,
    scanned: pd.DataFrame,
    rejected: pd.DataFrame,
    latest_data_date: str,
    stale: bool,
    expected_latest: pd.Timestamp | None,
    data_source: str,
    scan_timestamp_utc: str | None,
) -> dict:
    return {
        "rule": rule,
        "account_settings": account_settings,
        "top_candidates": scanned.head(5).copy() if not scanned.empty else pd.DataFrame(),
        "rejected_candidates": rejected.copy() if not rejected.empty else pd.DataFrame(),
        "latest_data_date": latest_data_date,
        "expected_latest_trading_date": (
            pd.Timestamp(expected_latest).strftime("%Y-%m-%d") if expected_latest is not None else ""
        ),
        "is_stale": stale,
        "data_source": data_source,
        "scan_timestamp_utc": scan_timestamp_utc or datetime.now(timezone.utc).isoformat(),
        "executable_universe_count": int(len(scanned)),
        "rejected_not_affordable_count": _rejected_not_affordable_count(rejected),
        "rejected_above_max_entry_price_count": _rejected_above_max_entry_price_count(rejected),
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


def _daily_scan_markdown(scan: pd.DataFrame, metadata: dict) -> str:
    row = scan.iloc[0]
    action = row["action"]
    lines = [
        "PHOENIX NANO DAILY SCAN",
        f"Action: {action}",
        f"Status: {row['status']}",
        "",
        "This is not active paper trading or live trading. It is only a research-derived manual verification candidate.",
        "",
        f"Ticker: {row['ticker']}",
        f"Latest data date: {row['latest_data_date']}",
        f"Expected latest trading date: {metadata['expected_latest_trading_date']}",
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
        f"- Candidate rule: Candidate 34 Nano with max_entry_price ${_rule_max_entry(metadata)}.",
        f"- Executable universe count: {metadata['executable_universe_count']}",
        f"- Rejected not affordable count: {metadata['rejected_not_affordable_count']}",
        f"- Rejected above max entry price count: {metadata['rejected_above_max_entry_price_count']}",
        f"- Stale data: {metadata['is_stale']}",
        f"- Data source: {metadata['data_source']}",
        f"- Scan timestamp UTC: {metadata['scan_timestamp_utc']}",
        f"- History rows written: {metadata.get('history_rows_written', 0)}",
        f"- History total row count: {metadata.get('history_total_row_count', 0)}",
        f"- History file path: {metadata.get('history_file_path', '')}",
        "",
    ]
    if action == MANUAL_REVIEW_CANDIDATE:
        lines.extend(
            [
                "## Manual Checks Still Required",
                "",
                "- Verify live quote manually before any action.",
                "- Verify current volume / RVOL manually.",
                "- Verify no fresh major negative news.",
                "- Do not chase a large intraday spike.",
                "",
                f"Why selected by rules: {row['reason']}",
                "",
            ]
        )
    if action == MANUAL_REVIEW_CANDIDATE:
        lines.extend(["## Top Executable Candidates", ""])
    else:
        lines.extend(["## Closest Executable Near-Misses", ""])
    top = metadata.get("top_candidates", pd.DataFrame())
    if top is None or top.empty:
        lines.append("No executable candidates were available for Nano ranking.")
    else:
        display = top[
            [
                "ticker",
                "reference_price",
                "shares_with_100",
                "estimated_total_cost",
                "estimated_cash_remaining",
                "smoke_score",
                "decision_strength",
                "relative_volume_prev20",
                "return_5d",
                "return_20d",
                "distance_to_52w_high_prev",
                "dollar_volume",
                "signal_rule_pass",
                "failed_checks",
            ]
        ].copy()
        lines.append(display.to_markdown(index=False))
    lines.extend(["", "## Rejected Before Nano Ranking", ""])
    rejected = metadata.get("rejected_candidates", pd.DataFrame())
    if rejected is None or rejected.empty:
        lines.append("No candidates were rejected before Nano ranking.")
    else:
        lines.append(
            "These names were not eligible for Nano ranking because they failed account executability filters before ranking."
        )
        rejected_display = rejected[
            [
                "ticker",
                "reference_price",
                "shares_with_100",
                "estimated_total_cost",
                "max_entry_price_pass",
                "affordability_pass",
                "rejection_reason",
            ]
        ].head(10)
        lines.append("")
        lines.append(rejected_display.to_markdown(index=False))
    return "\n".join(lines) + "\n"


def _daily_scan_csv(scan: pd.DataFrame, metadata: dict) -> pd.DataFrame:
    row = scan.iloc[0]
    base = {
        "scan_timestamp_utc": metadata["scan_timestamp_utc"],
        "latest_data_date": row["latest_data_date"],
        "expected_latest_trading_date": metadata["expected_latest_trading_date"],
        "is_stale": row["is_stale"],
        "data_source": metadata["data_source"],
    }
    rows = [
        {
            **base,
            "row_type": "FINAL",
            "ticker": row["ticker"],
            "action": row["action"],
            "status": row["status"],
            "reference_price": row["reference_price"],
            "shares_with_100": row["shares_with_100"],
            "estimated_total_cost": row["estimated_total_cost"],
            "estimated_cash_remaining": row["estimated_cash_remaining"],
            "affordability_pass": pd.NA,
            "max_entry_price_pass": pd.NA,
            "signal_rule_pass": row["all_rule_checks_passed"],
            "full_rule_pass": row["all_rule_checks_passed"],
            "smoke_score": pd.NA,
            "decision_strength": pd.NA,
            "relative_volume_prev20": pd.NA,
            "return_5d": pd.NA,
            "return_20d": pd.NA,
            "distance_to_52w_high_prev": pd.NA,
            "dollar_volume": pd.NA,
            "failed_checks": "" if bool(row["all_rule_checks_passed"]) else row["reason"],
            "rejection_reason": "",
        }
    ]
    top = metadata.get("top_candidates", pd.DataFrame())
    if top is not None and not top.empty:
        for _, item in top.head(5).iterrows():
            rows.append(
                {
                    **base,
                    "row_type": "EXECUTABLE_NEAR_MISS",
                    "ticker": item["ticker"],
                    "action": row["action"],
                    "status": row["status"],
                    "reference_price": item["reference_price"],
                    "shares_with_100": item["shares_with_100"],
                    "estimated_total_cost": item["estimated_total_cost"],
                    "estimated_cash_remaining": item["estimated_cash_remaining"],
                    "affordability_pass": item["affordability_pass"],
                    "max_entry_price_pass": item["max_entry_price_pass"],
                    "signal_rule_pass": item["signal_rule_pass"],
                    "full_rule_pass": item["all_rule_checks_passed"],
                    "smoke_score": item["smoke_score"],
                    "decision_strength": item["decision_strength"],
                    "relative_volume_prev20": item["relative_volume_prev20"],
                    "return_5d": item["return_5d"],
                    "return_20d": item["return_20d"],
                    "distance_to_52w_high_prev": item["distance_to_52w_high_prev"],
                    "dollar_volume": item["dollar_volume"],
                    "failed_checks": item["failed_checks"],
                    "rejection_reason": "",
                }
            )
    rejected = metadata.get("rejected_candidates", pd.DataFrame())
    if rejected is not None and not rejected.empty:
        for _, item in rejected.head(10).iterrows():
            rows.append(
                {
                    **base,
                    "row_type": "REJECTED_BEFORE_NANO_RANKING",
                    "ticker": item["ticker"],
                    "action": row["action"],
                    "status": row["status"],
                    "reference_price": item["reference_price"],
                    "shares_with_100": item["shares_with_100"],
                    "estimated_total_cost": item["estimated_total_cost"],
                    "estimated_cash_remaining": item["estimated_cash_remaining"],
                    "affordability_pass": item["affordability_pass"],
                    "max_entry_price_pass": item["max_entry_price_pass"],
                    "signal_rule_pass": False,
                    "full_rule_pass": False,
                    "smoke_score": pd.NA,
                    "decision_strength": pd.NA,
                    "relative_volume_prev20": item["relative_volume_prev20"],
                    "return_5d": item["return_5d"],
                    "return_20d": item["return_20d"],
                    "distance_to_52w_high_prev": item["distance_to_52w_high_prev"],
                    "dollar_volume": item["dollar_volume"],
                    "failed_checks": item["rejection_reason"],
                    "rejection_reason": item["rejection_reason"],
                }
            )
    return pd.DataFrame(rows)


def _is_stale(latest_data_date: pd.Timestamp, requested_end: str | None, stale_after_calendar_days: int) -> bool:
    if not requested_end:
        return False
    end = pd.Timestamp(requested_end).normalize()
    latest = pd.Timestamp(latest_data_date).normalize()
    return (end - latest).days > stale_after_calendar_days


def expected_latest_trading_date(as_of_date: str | pd.Timestamp) -> pd.Timestamp:
    day = pd.Timestamp(as_of_date).normalize() - pd.Timedelta(days=1)
    while not _is_trading_day(day):
        day -= pd.Timedelta(days=1)
    return day


def _is_trading_day(day: pd.Timestamp) -> bool:
    day = pd.Timestamp(day).normalize()
    if day.weekday() >= 5:
        return False
    return day.date() not in _nyse_holidays(day.year)


def _nyse_holidays(year: int) -> set:
    holidays = {
        _observed_fixed_holiday(year, 1, 1),
        _nth_weekday(year, 1, 0, 3),  # Martin Luther King Jr. Day
        _nth_weekday(year, 2, 0, 3),  # Presidents Day
        _good_friday(year),
        _last_weekday(year, 5, 0),  # Memorial Day
        _observed_fixed_holiday(year, 6, 19),
        _observed_fixed_holiday(year, 7, 4),
        _nth_weekday(year, 9, 0, 1),  # Labor Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
        _observed_fixed_holiday(year, 12, 25),
    }
    return holidays


def _observed_fixed_holiday(year: int, month: int, day: int):
    value = datetime(year, month, day).date()
    if value.weekday() == 5:
        return value - timedelta(days=1)
    if value.weekday() == 6:
        return value + timedelta(days=1)
    return value


def _nth_weekday(year: int, month: int, weekday: int, n: int):
    day = datetime(year, month, 1).date()
    while day.weekday() != weekday:
        day += timedelta(days=1)
    return day + timedelta(days=7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int):
    if month == 12:
        day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        day = datetime(year, month + 1, 1).date() - timedelta(days=1)
    while day.weekday() != weekday:
        day -= timedelta(days=1)
    return day


def _good_friday(year: int):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime(year, month, day).date() - timedelta(days=2)


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _format_money(value: object) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        return ""
    return f"${float(value):.2f}"


def _rule_max_entry(metadata: dict) -> str:
    rule = metadata.get("rule")
    if rule is None:
        return ""
    return f"{float(rule.max_entry_price):.2f}"


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _rejection_reason(row: pd.Series) -> str:
    reasons = []
    if not bool(row["affordability_pass"]):
        reasons.append("not_affordable")
    if not bool(row["max_entry_price_pass"]):
        reasons.append("above_candidate_34_max_entry_price")
    return ", ".join(reasons)


def _candidate_failed_checks(row: pd.Series, rule: CandidateRule) -> str:
    failed = []
    if float(row["smoke_score"]) < rule.min_smoke_score:
        failed.append("smoke_score_below_min")
    if float(row.get("rank_gap", 0.0)) < rule.min_rank_gap:
        failed.append("rank_gap_below_min")
    if pd.isna(row["relative_volume_prev20"]) or float(row["relative_volume_prev20"]) < rule.min_relative_volume_prev20:
        failed.append("relative_volume_prev20_below_min")
    if rule.require_return_5d_positive and float(row["return_5d"]) <= 0:
        failed.append("return_5d_not_positive")
    if rule.require_return_20d_positive and float(row["return_20d"]) <= 0:
        failed.append("return_20d_not_positive")
    if pd.isna(row["distance_to_52w_high_prev"]) or float(row["distance_to_52w_high_prev"]) < rule.distance_to_52w_high_prev_min:
        failed.append("distance_to_52w_high_prev_below_min")
    if float(row["dollar_volume"]) < rule.dollar_volume_min:
        failed.append("dollar_volume_below_min")
    return ", ".join(failed)


def _rejected_not_affordable_count(rejected: pd.DataFrame) -> int:
    if rejected.empty or "affordability_pass" not in rejected.columns:
        return 0
    return int((~rejected["affordability_pass"].astype(bool)).sum())


def _rejected_above_max_entry_price_count(rejected: pd.DataFrame) -> int:
    if rejected.empty or "max_entry_price_pass" not in rejected.columns:
        return 0
    return int((~rejected["max_entry_price_pass"].astype(bool)).sum())
