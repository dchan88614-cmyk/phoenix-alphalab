from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def configure_yfinance_cache(cache_dir: str = "data/raw/yfinance_cache") -> None:
    """Keep yfinance cache writes inside the project directory."""
    try:
        from pathlib import Path

        path = Path(cache_dir)
        path.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(path))
    except Exception as exc:
        logger.debug("Could not configure yfinance cache: %s", exc)


@dataclass(frozen=True)
class TickerMetadata:
    ticker: str
    quote_type: str | None
    exchange: str | None
    short_name: str | None
    long_name: str | None
    market_cap: float | None
    pass_universe: bool
    reason: str


def fetch_ticker_metadata(ticker: str) -> dict:
    """Fetch best-effort ticker metadata from yfinance."""
    configure_yfinance_cache()
    try:
        return yf.Ticker(ticker).get_info()
    except Exception as exc:
        logger.warning("Failed to fetch metadata for %s: %s", ticker, exc)
        return {}


def classify_ticker(ticker: str, settings: dict) -> TickerMetadata:
    """Classify whether a ticker fits the configured common-stock universe."""
    ticker = ticker.upper().strip()
    metadata = fetch_ticker_metadata(ticker)
    quote_type = metadata.get("quoteType")
    exchange = metadata.get("exchange")
    short_name = metadata.get("shortName")
    long_name = metadata.get("longName")
    market_cap = metadata.get("marketCap")

    allowed_quote_types = set(settings["universe"].get("allowed_quote_types", []))
    allowed_exchanges = set(settings["universe"].get("allowed_exchanges", []))
    excluded_keywords = [
        keyword.upper() for keyword in settings["universe"].get("excluded_keywords", [])
    ]
    require_metadata_pass = bool(settings["universe"].get("require_metadata_pass", False))

    if not metadata:
        return TickerMetadata(
            ticker, None, None, None, None, None, not require_metadata_pass, "metadata_missing"
        )

    if quote_type and allowed_quote_types and quote_type not in allowed_quote_types:
        return TickerMetadata(
            ticker, quote_type, exchange, short_name, long_name, market_cap, False, "quote_type_excluded"
        )

    if exchange and allowed_exchanges and exchange not in allowed_exchanges:
        return TickerMetadata(
            ticker, quote_type, exchange, short_name, long_name, market_cap, False, "exchange_excluded"
        )

    combined_name = f"{short_name or ''} {long_name or ''}".upper()
    for keyword in excluded_keywords:
        if keyword in combined_name:
            return TickerMetadata(
                ticker, quote_type, exchange, short_name, long_name, market_cap, False, f"keyword_excluded:{keyword}"
            )

    return TickerMetadata(
        ticker, quote_type, exchange, short_name, long_name, market_cap, True, "pass"
    )


def build_universe(tickers: list[str], settings: dict) -> pd.DataFrame:
    """Return one metadata row per input ticker."""
    rows = [classify_ticker(ticker, settings).__dict__ for ticker in tickers]
    return pd.DataFrame(rows)
