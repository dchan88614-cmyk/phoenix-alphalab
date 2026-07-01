from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv

from src.backtest.factor_test import DEFAULT_FACTORS, build_factor_report
from src.backtest.forward_returns import add_forward_returns
from src.backtest.multi_window_smoke_test import build_multi_window_smoke_test, write_multi_window_smoke_markdown
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

    all_download_tickers = sorted(set(passed_tickers + [benchmark]))
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
    dataset = add_forward_returns(filtered, horizons)
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
        auto_results, auto_summary = run_auto_research_loop(
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
        write_csv(auto_results, auto_csv_path)
        write_auto_research_summary(auto_results, auto_summary, auto_md_path)
        logger.info("Wrote auto research generations CSV: %s", auto_csv_path)
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
