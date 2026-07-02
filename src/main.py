from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv

from src.account.account_simulator import (
    AccountSettings,
    merge_nano_results,
    summarize_nano_candidates,
    write_nano_summary,
)
from src.backtest.factor_test import DEFAULT_FACTORS, build_factor_report
from src.backtest.forward_returns import add_forward_returns
from src.backtest.multi_window_smoke_test import build_multi_window_smoke_test, write_multi_window_smoke_markdown
from src.backtest.nano_daily_scan import (
    MISSING_OR_AMBIGUOUS_CANDIDATE_34_RULES,
    build_nano_daily_scan,
    extract_candidate_34_rule,
    write_candidate_34_frozen_rules,
    write_nano_daily_scan_reports,
)
from src.backtest.smoke_test import build_smoke_test, summarize_smoke_test, write_smoke_test_markdown
from src.data.filters import apply_price_liquidity_filters
from src.data.prices import download_many_prices
from src.data.universe import build_universe
from src.decision.decision_engine import (
    build_decision_simulation,
    summarize_decision_simulation,
    write_decision_simulation_markdown,
)
from src.factors.technical import add_all_factors
from src.reports.csv_export import write_csv
from src.reports.markdown_report import write_markdown_report
from src.research.auto_loop import run_auto_research_loop, write_auto_research_summary
from src.research.concentration import (
    build_concentration_report,
    build_regime_diagnostics,
    build_robustness_report,
    write_concentration_markdown,
    write_regime_markdown,
)
from src.research.historical_replay import build_phase1_historical_replay, write_phase1_historical_replay_reports
from src.research.execution_diagnostics import build_phase1b_execution_diagnostics, write_phase1b_reports
from src.research.phase1c_robustness import build_phase1c_robustness_analysis, write_phase1c_reports
from src.research.phase1d_entry_rules import build_phase1d_entry_rule_analysis, write_phase1d_reports
from src.research.phase1e_filter_validation import build_phase1e_filter_validation, write_phase1e_reports
from src.research.phase1f_failure_audit import build_phase1f_failure_audit, write_phase1f_reports
from src.research.phase1g_redesign_sandbox import build_phase1g_redesign_sandbox, write_phase1g_reports
from src.research.phase1h_risk_overlay import build_phase1h_risk_overlay_sandbox, write_phase1h_reports
from src.research.phase1i_data_universe_audit import build_phase1i_data_universe_audit, write_phase1i_reports
from src.research.phase1j_data_readiness import build_phase1j_data_readiness_gate, write_phase1j_reports
from src.utils.dates import parse_date
from src.utils.logging import configure_logging

logger = logging.getLogger(__name__)


def load_settings(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def parse_tickers(value: str) -> list[str]:
    tickers = [ticker.strip().upper() for ticker in value.split(",") if ticker.strip()]
    if not tickers:
        raise ValueError("At least one ticker is required.")
    return sorted(set(tickers))


def read_watchlist(path: str | Path) -> list[str]:
    tickers: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        value = line.split("#", 1)[0].strip().upper()
        if value:
            tickers.append(value)
    if not tickers:
        raise ValueError(f"Watchlist is empty: {path}")
    return sorted(set(tickers))


def run(args: argparse.Namespace) -> None:
    load_dotenv()
    settings = load_settings(args.config)

    if args.watchlist:
        tickers = read_watchlist(args.watchlist)
    elif args.tickers:
        tickers = parse_tickers(args.tickers)
    else:
        raise ValueError("Either --tickers or --watchlist is required.")
    research_start = parse_date(args.start)
    research_end = parse_date(args.end)
    data_start = (pd.Timestamp(research_start) - pd.Timedelta(days=300)).strftime("%Y-%m-%d")
    benchmark = args.benchmark or settings["data"].get("benchmark", "SPY")
    all_download_tickers = sorted(set(tickers + [benchmark]))

    logger.info("Building ticker universe for %s", ", ".join(tickers))
    universe = build_universe(tickers, settings)
    passed_tickers = universe.loc[universe["pass_universe"], "ticker"].tolist()
    rejected = universe.loc[~universe["pass_universe"], ["ticker", "reason"]]
    if not rejected.empty:
        logger.warning("Rejected tickers:\n%s", rejected.to_string(index=False))

    if not passed_tickers:
        raise RuntimeError("No tickers passed the configured universe filters.")

    market_context_tickers = [benchmark]
    if args.phase1g_redesign_sandbox or args.phase1h_risk_overlay_sandbox or args.phase1i_data_universe_audit or args.phase1j_data_readiness_gate:
        market_context_tickers.append("QQQ")
    all_download_tickers = sorted(set(passed_tickers + market_context_tickers))
    logger.info("Downloading OHLCV data for %s", ", ".join(all_download_tickers))
    prices = download_many_prices(
        all_download_tickers,
        data_start,
        research_end,
        raw_prices_dir=settings["data"]["raw_prices_dir"],
        auto_adjust=bool(settings["data"].get("auto_adjust", False)),
    )
    if prices.empty:
        raise RuntimeError("No price data was downloaded.")

    prices = prices.merge(
        universe[["ticker", "market_cap"]],
        on="ticker",
        how="left",
    )

    factors = add_all_factors(prices, settings)
    filtered = apply_price_liquidity_filters(factors, settings)
    horizons = [int(horizon) for horizon in settings["backtest"].get("forward_return_horizons", [5, 10, 20])]
    replay_horizons = sorted(set(horizons + [1, 3, 5, 10, 20]))
    dataset = add_forward_returns(filtered, replay_horizons)
    dataset["date"] = pd.to_datetime(dataset["date"])
    research_dataset = dataset.loc[
        dataset["date"].between(pd.Timestamp(research_start), pd.Timestamp(research_end))
    ].copy()
    warmup_available_start = dataset["date"].min()
    requested_data_start = pd.Timestamp(data_start)
    warmup_limitation = ""
    if pd.isna(warmup_available_start) or warmup_available_start > requested_data_start + pd.Timedelta(days=7):
        warmup_limitation = (
            f"Requested warmup from {data_start}, earliest available data is "
            f"{warmup_available_start.strftime('%Y-%m-%d') if not pd.isna(warmup_available_start) else 'unknown'}."
        )

    processed_dir = Path(settings["data"]["processed_dir"])
    reports_dir = Path(settings["data"]["reports_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = processed_dir / "factor_dataset.csv"
    write_csv(research_dataset, dataset_path)

    report = build_factor_report(
        research_dataset,
        factors=DEFAULT_FACTORS,
        horizons=horizons,
        benchmark_ticker=benchmark,
        quantiles=int(settings["backtest"].get("quantiles", 5)),
    )
    csv_path = reports_dir / "factor_report.csv"
    md_path = reports_dir / "factor_report.md"
    write_csv(report, csv_path)
    write_markdown_report(
        report,
        md_path,
        passed_tickers,
        research_start,
        research_end,
        benchmark,
        data_source=str(settings["data"].get("provider", "unknown")),
    )

    logger.info("Wrote processed dataset: %s", dataset_path)
    logger.info("Wrote CSV report: %s", csv_path)
    logger.info("Wrote Markdown report: %s", md_path)

    if args.nano_daily_scan:
        account_settings = AccountSettings.from_config(settings)
        candidate_rule = None
        candidate_row = None
        extraction_error = ""
        candidate_rules_path = reports_dir / "nano_daily_candidate_34_frozen_rules.md"
        try:
            candidate_rule, candidate_row = extract_candidate_34_rule(
                reports_dir / "auto_research_generations.csv",
                candidate_id=int(args.candidate_id),
            )
        except Exception as exc:
            extraction_error = MISSING_OR_AMBIGUOUS_CANDIDATE_34_RULES
            logger.warning("Candidate 34 rule extraction failed: %s", exc)
        write_candidate_34_frozen_rules(
            candidate_rules_path,
            candidate_rule,
            account_settings,
            source_path=reports_dir / "auto_research_generations.csv",
            source_row=candidate_row,
            error=extraction_error,
        )
        scan_data = filtered.loc[
            filtered["date"].between(pd.Timestamp(research_start), pd.Timestamp(research_end))
        ].copy()
        nano_daily_scan, nano_daily_metadata = build_nano_daily_scan(
            scan_data,
            account_settings=account_settings,
            benchmark_ticker=benchmark,
            requested_end=research_end,
            rule=candidate_rule,
            data_source=str(settings["data"].get("provider", "unknown")),
            scan_timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )
        nano_daily_csv_path = reports_dir / "nano_daily_scan.csv"
        nano_daily_md_path = reports_dir / "nano_daily_scan.md"
        nano_daily_history_path = reports_dir / "nano_daily_scan_history.csv"
        write_nano_daily_scan_reports(
            nano_daily_scan,
            nano_daily_metadata,
            nano_daily_csv_path,
            nano_daily_md_path,
            history_csv_path=nano_daily_history_path,
        )
        logger.info("Wrote Nano daily frozen Candidate 34 rules: %s", candidate_rules_path)
        logger.info("Wrote Nano daily scan CSV: %s", nano_daily_csv_path)
        logger.info("Wrote Nano daily scan Markdown report: %s", nano_daily_md_path)
        logger.info("Wrote Nano daily scan history CSV: %s", nano_daily_history_path)

    if args.phase1_historical_replay:
        account_settings = AccountSettings.from_config(settings)
        candidate_rule, _ = extract_candidate_34_rule(
            reports_dir / "auto_research_generations.csv",
            candidate_id=int(args.candidate_id),
        )
        replay_decisions, replay_near_misses, replay_summary = build_phase1_historical_replay(
            research_dataset,
            account_settings=account_settings,
            rule=candidate_rule,
            replay_rounds=int(args.replay_rounds),
            benchmark_ticker=benchmark,
        )
        replay_decisions_path = reports_dir / "phase1_historical_replay_decisions.csv"
        replay_summary_path = reports_dir / "phase1_historical_replay_summary.md"
        replay_near_misses_path = reports_dir / "phase1_historical_replay_near_misses.csv"
        write_phase1_historical_replay_reports(
            replay_decisions,
            replay_near_misses,
            replay_summary,
            replay_decisions_path,
            replay_summary_path,
            replay_near_misses_path,
        )
        logger.info("Wrote Phase 1A historical replay decisions CSV: %s", replay_decisions_path)
        logger.info("Wrote Phase 1A historical replay summary Markdown: %s", replay_summary_path)
        logger.info("Wrote Phase 1A historical replay near misses CSV: %s", replay_near_misses_path)

    if args.phase1b_execution_diagnostics:
        account_settings = AccountSettings.from_config(settings)
        candidate_rule, _ = extract_candidate_34_rule(
            reports_dir / "auto_research_generations.csv",
            candidate_id=int(args.candidate_id),
        )
        diagnostics, comparison, attribution, phase1b_summary = build_phase1b_execution_diagnostics(
            research_dataset,
            account_settings=account_settings,
            rule=candidate_rule,
            replay_rounds=int(args.replay_rounds),
            replay_sample_offset=int(args.replay_sample_offset),
            replay_sample_count=int(args.replay_sample_count),
            benchmark_ticker=benchmark,
        )
        phase1b_diagnostics_path = reports_dir / "phase1b_execution_diagnostics.csv"
        phase1b_summary_path = reports_dir / "phase1b_execution_summary.md"
        phase1b_comparison_path = reports_dir / "phase1b_exit_policy_comparison.csv"
        phase1b_attribution_path = reports_dir / "phase1b_ticker_risk_attribution.csv"
        write_phase1b_reports(
            diagnostics,
            comparison,
            attribution,
            phase1b_summary,
            phase1b_diagnostics_path,
            phase1b_summary_path,
            phase1b_comparison_path,
            phase1b_attribution_path,
        )
        logger.info("Wrote Phase 1B execution diagnostics CSV: %s", phase1b_diagnostics_path)
        logger.info("Wrote Phase 1B execution summary Markdown: %s", phase1b_summary_path)
        logger.info("Wrote Phase 1B exit policy comparison CSV: %s", phase1b_comparison_path)
        logger.info("Wrote Phase 1B ticker risk attribution CSV: %s", phase1b_attribution_path)

    if args.phase1c_robustness_analysis:
        account_settings = AccountSettings.from_config(settings)
        candidate_rule, _ = extract_candidate_34_rule(
            reports_dir / "auto_research_generations.csv",
            candidate_id=int(args.candidate_id),
        )
        phase1c_matrix, phase1c_failures, phase1c_realism, phase1c_regime, phase1c_summary = (
            build_phase1c_robustness_analysis(
                research_dataset,
                account_settings=account_settings,
                rule=candidate_rule,
                replay_rounds=int(args.replay_rounds),
                replay_sample_count=int(args.replay_sample_count),
                replay_sample_offset=int(args.replay_sample_offset),
                benchmark_ticker=benchmark,
            )
        )
        phase1c_matrix_path = reports_dir / "phase1c_policy_robustness_matrix.csv"
        phase1c_failures_path = reports_dir / "phase1c_sample_failure_trades.csv"
        phase1c_realism_path = reports_dir / "phase1c_close_stop_realism.csv"
        phase1c_regime_path = reports_dir / "phase1c_regime_attribution.csv"
        phase1c_summary_path = reports_dir / "phase1c_robustness_summary.md"
        write_phase1c_reports(
            phase1c_matrix,
            phase1c_failures,
            phase1c_realism,
            phase1c_regime,
            phase1c_summary,
            phase1c_matrix_path,
            phase1c_failures_path,
            phase1c_realism_path,
            phase1c_regime_path,
            phase1c_summary_path,
        )
        logger.info("Wrote Phase 1C policy robustness matrix CSV: %s", phase1c_matrix_path)
        logger.info("Wrote Phase 1C sample failure trades CSV: %s", phase1c_failures_path)
        logger.info("Wrote Phase 1C close-stop realism CSV: %s", phase1c_realism_path)
        logger.info("Wrote Phase 1C regime attribution CSV: %s", phase1c_regime_path)
        logger.info("Wrote Phase 1C robustness summary Markdown: %s", phase1c_summary_path)

    if args.phase1d_entry_rule_analysis:
        account_settings = AccountSettings.from_config(settings)
        candidate_rule, _ = extract_candidate_34_rule(
            reports_dir / "auto_research_generations.csv",
            candidate_id=int(args.candidate_id),
        )
        (
            phase1d_diagnostics,
            phase1d_attribution,
            phase1d_matrix,
            phase1d_excluded,
            phase1d_candidate_filter_md,
            phase1d_summary,
        ) = build_phase1d_entry_rule_analysis(
            research_dataset,
            account_settings=account_settings,
            rule=candidate_rule,
            replay_rounds=int(args.replay_rounds),
            replay_sample_count=int(args.replay_sample_count),
            replay_sample_offset=int(args.replay_sample_offset),
            benchmark_ticker=benchmark,
        )
        phase1d_diagnostics_path = reports_dir / "phase1d_entry_rule_diagnostics.csv"
        phase1d_attribution_path = reports_dir / "phase1d_loser_feature_attribution.csv"
        phase1d_matrix_path = reports_dir / "phase1d_filter_backtest_matrix.csv"
        phase1d_excluded_path = reports_dir / "phase1d_filter_excluded_decisions.csv"
        phase1d_candidate_filter_path = reports_dir / "phase1d_candidate_filter_summary.md"
        phase1d_summary_path = reports_dir / "phase1d_entry_rule_summary.md"
        write_phase1d_reports(
            phase1d_diagnostics,
            phase1d_attribution,
            phase1d_matrix,
            phase1d_excluded,
            phase1d_candidate_filter_md,
            phase1d_summary,
            phase1d_diagnostics_path,
            phase1d_attribution_path,
            phase1d_matrix_path,
            phase1d_excluded_path,
            phase1d_candidate_filter_path,
            phase1d_summary_path,
        )
        logger.info("Wrote Phase 1D entry rule diagnostics CSV: %s", phase1d_diagnostics_path)
        logger.info("Wrote Phase 1D loser feature attribution CSV: %s", phase1d_attribution_path)
        logger.info("Wrote Phase 1D filter backtest matrix CSV: %s", phase1d_matrix_path)
        logger.info("Wrote Phase 1D filter excluded decisions CSV: %s", phase1d_excluded_path)
        logger.info("Wrote Phase 1D candidate filter Markdown: %s", phase1d_candidate_filter_path)
        logger.info("Wrote Phase 1D entry rule summary Markdown: %s", phase1d_summary_path)

    if args.phase1e_filter_validation:
        account_settings = AccountSettings.from_config(settings)
        candidate_rule, _ = extract_candidate_34_rule(
            reports_dir / "auto_research_generations.csv",
            candidate_id=int(args.candidate_id),
        )
        phase1e_threshold_sweep, phase1e_validation_matrix, phase1e_holdout_results, phase1e_excluded, phase1e_summary_md, _ = (
            build_phase1e_filter_validation(
                research_dataset,
                account_settings=account_settings,
                rule=candidate_rule,
                replay_rounds=int(args.replay_rounds),
                replay_sample_count=int(args.replay_sample_count),
                replay_sample_offset=int(args.replay_sample_offset),
                benchmark_ticker=benchmark,
            )
        )
        phase1e_threshold_path = reports_dir / "phase1e_threshold_sweep.csv"
        phase1e_validation_path = reports_dir / "phase1e_filter_validation_matrix.csv"
        phase1e_holdout_path = reports_dir / "phase1e_holdout_results.csv"
        phase1e_excluded_path = reports_dir / "phase1e_excluded_decision_audit.csv"
        phase1e_summary_path = reports_dir / "phase1e_filter_summary.md"
        write_phase1e_reports(
            phase1e_threshold_sweep,
            phase1e_validation_matrix,
            phase1e_holdout_results,
            phase1e_excluded,
            phase1e_summary_md,
            phase1e_threshold_path,
            phase1e_validation_path,
            phase1e_holdout_path,
            phase1e_excluded_path,
            phase1e_summary_path,
        )
        logger.info("Wrote Phase 1E threshold sweep CSV: %s", phase1e_threshold_path)
        logger.info("Wrote Phase 1E filter validation matrix CSV: %s", phase1e_validation_path)
        logger.info("Wrote Phase 1E holdout results CSV: %s", phase1e_holdout_path)
        logger.info("Wrote Phase 1E excluded decision audit CSV: %s", phase1e_excluded_path)
        logger.info("Wrote Phase 1E filter summary Markdown: %s", phase1e_summary_path)

    if args.phase1f_failure_audit:
        account_settings = AccountSettings.from_config(settings)
        candidate_rule, _ = extract_candidate_34_rule(
            reports_dir / "auto_research_generations.csv",
            candidate_id=int(args.candidate_id),
        )
        phase1f_ledger, phase1f_taxonomy, phase1f_drawdown, phase1f_regime, phase1f_quality, phase1f_summary = (
            build_phase1f_failure_audit(
                research_dataset,
                account_settings=account_settings,
                rule=candidate_rule,
                replay_rounds=int(args.replay_rounds),
                replay_sample_count=int(args.replay_sample_count),
                replay_sample_offset=int(args.replay_sample_offset),
                benchmark_ticker=benchmark,
                rejected_metadata=rejected,
            )
        )
        phase1f_ledger_path = reports_dir / "phase1f_failure_trade_ledger.csv"
        phase1f_taxonomy_path = reports_dir / "phase1f_theme_taxonomy.csv"
        phase1f_drawdown_path = reports_dir / "phase1f_drawdown_attribution.csv"
        phase1f_regime_path = reports_dir / "phase1f_regime_attribution.csv"
        phase1f_quality_path = reports_dir / "phase1f_data_quality_audit.csv"
        phase1f_summary_path = reports_dir / "phase1f_viability_summary.md"
        write_phase1f_reports(
            phase1f_ledger,
            phase1f_taxonomy,
            phase1f_drawdown,
            phase1f_regime,
            phase1f_quality,
            phase1f_summary,
            phase1f_ledger_path,
            phase1f_taxonomy_path,
            phase1f_drawdown_path,
            phase1f_regime_path,
            phase1f_quality_path,
            phase1f_summary_path,
        )
        logger.info("Wrote Phase 1F failure trade ledger CSV: %s", phase1f_ledger_path)
        logger.info("Wrote Phase 1F theme taxonomy CSV: %s", phase1f_taxonomy_path)
        logger.info("Wrote Phase 1F drawdown attribution CSV: %s", phase1f_drawdown_path)
        logger.info("Wrote Phase 1F regime attribution CSV: %s", phase1f_regime_path)
        logger.info("Wrote Phase 1F data quality audit CSV: %s", phase1f_quality_path)
        logger.info("Wrote Phase 1F viability summary Markdown: %s", phase1f_summary_path)

    if args.phase1g_redesign_sandbox:
        account_settings = AccountSettings.from_config(settings)
        candidate_rule, _ = extract_candidate_34_rule(
            reports_dir / "auto_research_generations.csv",
            candidate_id=int(args.candidate_id),
        )
        (
            phase1g_preflight,
            phase1g_definitions,
            phase1g_calibration,
            phase1g_validation,
            phase1g_holdout,
            phase1g_comparison,
            phase1g_rejected,
            phase1g_summary_md,
            _,
        ) = build_phase1g_redesign_sandbox(
            research_dataset,
            account_settings=account_settings,
            rule=candidate_rule,
            replay_rounds=int(args.replay_rounds),
            replay_sample_count=int(args.replay_sample_count),
            replay_sample_offset=int(args.replay_sample_offset),
            benchmark_ticker=benchmark,
            rejected_metadata=rejected,
        )
        phase1g_preflight_path = reports_dir / "phase1g_data_regime_preflight.csv"
        phase1g_definitions_path = reports_dir / "phase1g_candidate_family_definitions.md"
        phase1g_calibration_path = reports_dir / "phase1g_redesign_calibration_matrix.csv"
        phase1g_validation_path = reports_dir / "phase1g_redesign_validation_matrix.csv"
        phase1g_holdout_path = reports_dir / "phase1g_redesign_holdout_results.csv"
        phase1g_comparison_path = reports_dir / "phase1g_candidate34_vs_35_comparison.csv"
        phase1g_rejected_path = reports_dir / "phase1g_rejected_decision_audit.csv"
        phase1g_summary_path = reports_dir / "phase1g_redesign_summary.md"
        write_phase1g_reports(
            phase1g_preflight,
            phase1g_definitions,
            phase1g_calibration,
            phase1g_validation,
            phase1g_holdout,
            phase1g_comparison,
            phase1g_rejected,
            phase1g_summary_md,
            phase1g_preflight_path,
            phase1g_definitions_path,
            phase1g_calibration_path,
            phase1g_validation_path,
            phase1g_holdout_path,
            phase1g_comparison_path,
            phase1g_rejected_path,
            phase1g_summary_path,
        )
        logger.info("Wrote Phase 1G data/regime preflight CSV: %s", phase1g_preflight_path)
        logger.info("Wrote Phase 1G family definitions Markdown: %s", phase1g_definitions_path)
        logger.info("Wrote Phase 1G calibration matrix CSV: %s", phase1g_calibration_path)
        logger.info("Wrote Phase 1G validation matrix CSV: %s", phase1g_validation_path)
        logger.info("Wrote Phase 1G holdout results CSV: %s", phase1g_holdout_path)
        logger.info("Wrote Phase 1G Candidate 34 vs 35 comparison CSV: %s", phase1g_comparison_path)
        logger.info("Wrote Phase 1G rejected decision audit CSV: %s", phase1g_rejected_path)
        logger.info("Wrote Phase 1G redesign summary Markdown: %s", phase1g_summary_path)

    if args.phase1h_risk_overlay_sandbox:
        account_settings = AccountSettings.from_config(settings)
        candidate_rule, _ = extract_candidate_34_rule(
            reports_dir / "auto_research_generations.csv",
            candidate_id=int(args.candidate_id),
        )
        (
            phase1h_definitions,
            phase1h_calibration,
            phase1h_validation,
            phase1h_holdout,
            phase1h_comparison,
            phase1h_drawdown,
            phase1h_theme,
            phase1h_counterfactual,
            _,
            phase1h_summary_md,
            _,
        ) = build_phase1h_risk_overlay_sandbox(
            research_dataset,
            account_settings=account_settings,
            rule=candidate_rule,
            replay_rounds=int(args.replay_rounds),
            replay_sample_count=int(args.replay_sample_count),
            replay_sample_offset=int(args.replay_sample_offset),
            benchmark_ticker=benchmark,
            rejected_metadata=rejected,
        )
        phase1h_definitions_path = reports_dir / "phase1h_overlay_definitions.md"
        phase1h_calibration_path = reports_dir / "phase1h_overlay_calibration_matrix.csv"
        phase1h_validation_path = reports_dir / "phase1h_overlay_validation_matrix.csv"
        phase1h_holdout_path = reports_dir / "phase1h_overlay_holdout_results.csv"
        phase1h_comparison_path = reports_dir / "phase1h_candidate34_vs_35_vs_overlay.csv"
        phase1h_drawdown_path = reports_dir / "phase1h_drawdown_compression_attribution.csv"
        phase1h_theme_path = reports_dir / "phase1h_theme_concentration_audit.csv"
        phase1h_counterfactual_path = reports_dir / "phase1h_excluded_trade_counterfactual.csv"
        phase1h_summary_path = reports_dir / "phase1h_risk_overlay_summary.md"
        write_phase1h_reports(
            phase1h_definitions,
            phase1h_calibration,
            phase1h_validation,
            phase1h_holdout,
            phase1h_comparison,
            phase1h_drawdown,
            phase1h_theme,
            phase1h_counterfactual,
            phase1h_summary_md,
            phase1h_definitions_path,
            phase1h_calibration_path,
            phase1h_validation_path,
            phase1h_holdout_path,
            phase1h_comparison_path,
            phase1h_drawdown_path,
            phase1h_theme_path,
            phase1h_counterfactual_path,
            phase1h_summary_path,
        )
        logger.info("Wrote Phase 1H overlay definitions Markdown: %s", phase1h_definitions_path)
        logger.info("Wrote Phase 1H calibration matrix CSV: %s", phase1h_calibration_path)
        logger.info("Wrote Phase 1H validation matrix CSV: %s", phase1h_validation_path)
        logger.info("Wrote Phase 1H holdout results CSV: %s", phase1h_holdout_path)
        logger.info("Wrote Phase 1H Candidate 34 vs 35 vs overlay CSV: %s", phase1h_comparison_path)
        logger.info("Wrote Phase 1H drawdown compression CSV: %s", phase1h_drawdown_path)
        logger.info("Wrote Phase 1H theme concentration audit CSV: %s", phase1h_theme_path)
        logger.info("Wrote Phase 1H excluded trade counterfactual CSV: %s", phase1h_counterfactual_path)
        logger.info("Wrote Phase 1H risk overlay summary Markdown: %s", phase1h_summary_path)

    if args.phase1i_data_universe_audit:
        account_settings = AccountSettings.from_config(settings)
        candidate_rule, _ = extract_candidate_34_rule(
            reports_dir / "auto_research_generations.csv",
            candidate_id=int(args.candidate_id),
        )
        (
            phase1i_quality,
            phase1i_vendor,
            phase1i_composition,
            phase1i_matrix,
            phase1i_holdout,
            phase1i_incidents,
            phase1i_rejected,
            phase1i_attribution,
            phase1i_summary_md,
            _,
        ) = build_phase1i_data_universe_audit(
            research_dataset,
            account_settings=account_settings,
            rule=candidate_rule,
            watchlist_tickers=tickers,
            universe=universe,
            rejected_metadata=rejected,
            requested_start_date=research_start,
            requested_end_date=research_end,
            replay_rounds=int(args.replay_rounds),
            replay_sample_count=int(args.replay_sample_count),
            replay_sample_offset=int(args.replay_sample_offset),
            benchmark_ticker=benchmark,
        )
        phase1i_paths = {
            "quality": reports_dir / "phase1i_symbol_data_quality_audit.csv",
            "vendor": reports_dir / "phase1i_vendor_validation_matrix.csv",
            "composition": reports_dir / "phase1i_universe_composition_audit.csv",
            "matrix": reports_dir / "phase1i_universe_variant_backtest_matrix.csv",
            "holdout": reports_dir / "phase1i_universe_variant_holdout_results.csv",
            "incidents": reports_dir / "phase1i_data_gap_incident_log.csv",
            "rejected": reports_dir / "phase1i_rejected_symbol_audit.csv",
            "attribution": reports_dir / "phase1i_strategy_vs_universe_attribution.csv",
            "summary": reports_dir / "phase1i_data_universe_summary.md",
        }
        write_phase1i_reports(
            phase1i_quality,
            phase1i_vendor,
            phase1i_composition,
            phase1i_matrix,
            phase1i_holdout,
            phase1i_incidents,
            phase1i_rejected,
            phase1i_attribution,
            phase1i_summary_md,
            phase1i_paths,
        )
        logger.info("Wrote Phase 1I symbol data quality audit CSV: %s", phase1i_paths["quality"])
        logger.info("Wrote Phase 1I vendor validation matrix CSV: %s", phase1i_paths["vendor"])
        logger.info("Wrote Phase 1I universe composition audit CSV: %s", phase1i_paths["composition"])
        logger.info("Wrote Phase 1I universe variant backtest matrix CSV: %s", phase1i_paths["matrix"])
        logger.info("Wrote Phase 1I universe variant holdout results CSV: %s", phase1i_paths["holdout"])
        logger.info("Wrote Phase 1I data gap incident log CSV: %s", phase1i_paths["incidents"])
        logger.info("Wrote Phase 1I rejected symbol audit CSV: %s", phase1i_paths["rejected"])
        logger.info("Wrote Phase 1I strategy-vs-universe attribution CSV: %s", phase1i_paths["attribution"])
        logger.info("Wrote Phase 1I data universe summary Markdown: %s", phase1i_paths["summary"])

    if args.phase1j_data_readiness_gate:
        (
            phase1j_symbol_master,
            phase1j_listing,
            phase1j_secondary,
            phase1j_scorecard,
            phase1j_quarantine,
            phase1j_taxonomy,
            phase1j_clean_watchlist,
            phase1j_summary_md,
            _,
        ) = build_phase1j_data_readiness_gate(
            research_dataset,
            watchlist_path=args.watchlist,
            watchlist_tickers=tickers,
            universe=universe,
            rejected_metadata=rejected,
            requested_start_date=research_start,
            requested_end_date=research_end,
            benchmark_ticker=benchmark,
        )
        phase1j_paths = {
            "symbol_master": reports_dir / "phase1j_symbol_master.csv",
            "listing": reports_dir / "phase1j_listing_validation_matrix.csv",
            "secondary": reports_dir / "phase1j_secondary_ohlcv_validation.csv",
            "scorecard": reports_dir / "phase1j_data_readiness_scorecard.csv",
            "quarantine": reports_dir / "phase1j_quarantine_list.csv",
            "taxonomy": reports_dir / "phase1j_taxonomy_resolution.csv",
            "clean_watchlist": reports_dir / "phase1j_clean_watchlist_candidate.txt",
            "summary": reports_dir / "phase1j_data_readiness_summary.md",
        }
        write_phase1j_reports(
            phase1j_symbol_master,
            phase1j_listing,
            phase1j_secondary,
            phase1j_scorecard,
            phase1j_quarantine,
            phase1j_taxonomy,
            phase1j_clean_watchlist,
            phase1j_summary_md,
            phase1j_paths,
        )
        logger.info("Wrote Phase 1J symbol master CSV: %s", phase1j_paths["symbol_master"])
        logger.info("Wrote Phase 1J listing validation matrix CSV: %s", phase1j_paths["listing"])
        logger.info("Wrote Phase 1J secondary OHLCV validation CSV: %s", phase1j_paths["secondary"])
        logger.info("Wrote Phase 1J data readiness scorecard CSV: %s", phase1j_paths["scorecard"])
        logger.info("Wrote Phase 1J quarantine list CSV: %s", phase1j_paths["quarantine"])
        logger.info("Wrote Phase 1J taxonomy resolution CSV: %s", phase1j_paths["taxonomy"])
        logger.info("Wrote Phase 1J clean watchlist candidate TXT: %s", phase1j_paths["clean_watchlist"])
        logger.info("Wrote Phase 1J data readiness summary Markdown: %s", phase1j_paths["summary"])

    smoke_results = None
    if args.smoke_test or args.decision_simulation:
        smoke_results = build_smoke_test(
            research_dataset,
            benchmark_ticker=benchmark,
            horizons=horizons,
            smoke_days=int(args.smoke_days),
            top_n=5,
        )

    if args.smoke_test:
        smoke_summary = summarize_smoke_test(smoke_results, horizons)
        smoke_csv_path = reports_dir / "smoke_test.csv"
        smoke_md_path = reports_dir / "smoke_test.md"
        write_csv(smoke_results, smoke_csv_path)
        write_smoke_test_markdown(
            smoke_results,
            smoke_summary,
            smoke_md_path,
            benchmark,
            horizons,
            universe_ticker_count=len(passed_tickers),
        )
        logger.info("Wrote smoke test CSV: %s", smoke_csv_path)
        logger.info("Wrote smoke test Markdown report: %s", smoke_md_path)

    if args.decision_simulation:
        decision_results = build_decision_simulation(smoke_results, horizons)
        decision_summary = summarize_decision_simulation(decision_results, smoke_results, horizons)
        decision_csv_path = reports_dir / "decision_simulation.csv"
        decision_md_path = reports_dir / "decision_simulation.md"
        write_csv(decision_results, decision_csv_path)
        write_decision_simulation_markdown(decision_results, decision_summary, decision_md_path, horizons)
        logger.info("Wrote decision simulation CSV: %s", decision_csv_path)
        logger.info("Wrote decision simulation Markdown report: %s", decision_md_path)

    if args.multi_window_smoke_test:
        multi_window_summary = build_multi_window_smoke_test(
            dataset,
            benchmark_ticker=benchmark,
            horizons=horizons,
            universe_ticker_count=len(passed_tickers),
            top_n=5,
        )
        multi_csv_path = reports_dir / "multi_window_smoke_test.csv"
        multi_md_path = reports_dir / "multi_window_smoke_test.md"
        write_csv(multi_window_summary, multi_csv_path)
        write_multi_window_smoke_markdown(multi_window_summary, multi_md_path, benchmark)
        logger.info("Wrote multi-window smoke test CSV: %s", multi_csv_path)
        logger.info("Wrote multi-window smoke test Markdown report: %s", multi_md_path)

    if args.auto_research_loop:
        auto_results, auto_summary, trade_results = run_auto_research_loop(
            dataset,
            benchmark_ticker=benchmark,
            horizons=horizons,
            data_start=data_start,
            research_start=research_start,
            research_end=research_end,
            warmup_limitation=warmup_limitation,
        )
        auto_csv_path = reports_dir / "auto_research_generations.csv"
        auto_md_path = reports_dir / "auto_research_summary.md"
        trade_csv_path = reports_dir / "trade_simulation_trades.csv"
        concentration_csv_path = reports_dir / "concentration_report.csv"
        concentration_md_path = reports_dir / "concentration_report.md"
        robustness_csv_path = reports_dir / "robustness_report.csv"
        regime_csv_path = reports_dir / "regime_diagnostics.csv"
        regime_md_path = reports_dir / "regime_diagnostics.md"
        if args.nano_account_simulation:
            account_settings = AccountSettings.from_config(settings)
            nano_summary, nano_trades, nano_equity = summarize_nano_candidates(
                trade_results,
                account_settings,
                max_entry_prices=[20.0, 30.0, 50.0, 75.0, 100.0],
            )
            auto_results = merge_nano_results(auto_results, nano_summary)
            nano_trades_path = reports_dir / "nano_account_trades.csv"
            nano_equity_path = reports_dir / "nano_account_equity_curve.csv"
            nano_summary_path = reports_dir / "nano_account_summary.md"
            write_csv(nano_trades, nano_trades_path)
            write_csv(nano_equity, nano_equity_path)
            write_nano_summary(nano_summary, nano_trades, nano_equity, nano_summary_path, account_settings)
            logger.info("Wrote Nano account trades CSV: %s", nano_trades_path)
            logger.info("Wrote Nano account equity curve CSV: %s", nano_equity_path)
            logger.info("Wrote Nano account summary Markdown: %s", nano_summary_path)
        concentration_report, concentration_summary = build_concentration_report(trade_results)
        robustness_report = build_robustness_report(trade_results)
        regime_report = build_regime_diagnostics(trade_results, dataset)
        write_csv(auto_results, auto_csv_path)
        write_csv(trade_results, trade_csv_path)
        write_csv(concentration_report, concentration_csv_path)
        write_csv(robustness_report, robustness_csv_path)
        write_csv(regime_report, regime_csv_path)
        write_auto_research_summary(auto_results, auto_summary, auto_md_path)
        write_concentration_markdown(concentration_report, concentration_summary, concentration_md_path)
        write_regime_markdown(regime_report, regime_md_path)
        logger.info("Wrote auto research generations CSV: %s", auto_csv_path)
        logger.info("Wrote trade simulation trades CSV: %s", trade_csv_path)
        logger.info("Wrote concentration report CSV: %s", concentration_csv_path)
        logger.info("Wrote concentration report Markdown: %s", concentration_md_path)
        logger.info("Wrote robustness report CSV: %s", robustness_csv_path)
        logger.info("Wrote regime diagnostics CSV: %s", regime_csv_path)
        logger.info("Wrote regime diagnostics Markdown: %s", regime_md_path)
        logger.info("Wrote auto research summary Markdown report: %s", auto_md_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phoenix AlphaLab factor research runner.")
    parser.add_argument("--tickers", default=None, help="Comma-separated ticker list, e.g. AAPL,NVDA,SMCI,PLTR")
    parser.add_argument("--watchlist", default=None, help="Path to a newline-delimited ticker watchlist. Overrides --tickers.")
    parser.add_argument("--start", required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end", required=True, help="End date in YYYY-MM-DD format")
    parser.add_argument("--benchmark", default=None, help="Benchmark ticker for excess returns. Defaults to settings.yaml")
    parser.add_argument("--config", default="config/settings.yaml", help="Path to YAML settings file")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--smoke-test", action="store_true", help="Run the simple recent-window Top 5 smoke test")
    parser.add_argument("--smoke-days", type=int, default=60, help="Number of recent eligible signal days for smoke test")
    parser.add_argument("--decision-simulation", action="store_true", help="Run Generation 1 BUY / NO_TRADE decision simulation")
    parser.add_argument(
        "--multi-window-smoke-test",
        action="store_true",
        help="Run the fixed-rule smoke test across default non-overlapping windows",
    )
    parser.add_argument("--auto-research-loop", action="store_true", help="Run offline candidate decision-rule research loop")
    parser.add_argument(
        "--nano-account-simulation",
        action="store_true",
        help="Run Phoenix Nano $100 whole-share account simulation after the auto research loop",
    )
    parser.add_argument(
        "--nano-daily-scan",
        action="store_true",
        help="Run latest EOD Phoenix Nano daily scan for one manual-review candidate or NO_TRADE",
    )
    parser.add_argument("--candidate-id", type=int, default=34, help="Candidate rule id for Nano daily scan. Defaults to 34.")
    parser.add_argument(
        "--phase1-historical-replay",
        action="store_true",
        help="Run Phoenix Nano Phase 1A historical replay rounds",
    )
    parser.add_argument("--replay-rounds", type=int, default=100, help="Number of Phase 1A historical replay rounds")
    parser.add_argument(
        "--phase1b-execution-diagnostics",
        action="store_true",
        help="Run Phoenix Nano Phase 1B execution risk and drawdown diagnostics",
    )
    parser.add_argument("--replay-sample-offset", type=int, default=0, help="Deterministic Phase 1 replay sample offset")
    parser.add_argument("--replay-sample-count", type=int, default=1, help="Number of deterministic replay samples for Phase 1B")
    parser.add_argument(
        "--phase1c-robustness-analysis",
        action="store_true",
        help="Run Phoenix Nano Phase 1C robustness failure and close-stop realism analysis",
    )
    parser.add_argument(
        "--phase1d-entry-rule-analysis",
        action="store_true",
        help="Run Phoenix Nano Phase 1D entry-rule failure diagnostics",
    )
    parser.add_argument(
        "--phase1e-filter-validation",
        action="store_true",
        help="Run Phoenix Nano Phase 1E cross-validated conservative filter validation",
    )
    parser.add_argument(
        "--phase1f-failure-audit",
        action="store_true",
        help="Run Phoenix Nano Phase 1F failure attribution, taxonomy, and data quality audit",
    )
    parser.add_argument(
        "--phase1g-redesign-sandbox",
        action="store_true",
        help="Run Phoenix Nano Phase 1G Candidate 35 redesign sandbox",
    )
    parser.add_argument(
        "--phase1h-risk-overlay-sandbox",
        action="store_true",
        help="Run Phoenix Nano Phase 1H trend-quality risk overlay sandbox",
    )
    parser.add_argument(
        "--phase1i-data-universe-audit",
        action="store_true",
        help="Run Phoenix Nano Phase 1I data quality and universe design audit",
    )
    parser.add_argument(
        "--phase1j-data-readiness-gate",
        action="store_true",
        help="Run Phoenix Nano Phase 1J symbol master and data readiness gate",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)
    try:
        run(args)
    except Exception as exc:
        logger.error("Run failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
