from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


def configure_yfinance_cache(cache_dir: str | Path = "data/raw/yfinance_cache") -> None:
    """Keep yfinance cache writes inside the project directory."""
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    try:
        yf.set_tz_cache_location(str(path))
    except Exception as exc:
        logger.debug("Could not configure yfinance cache: %s", exc)


def _normalize_download_frame(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["date", "ticker", *PRICE_COLUMNS])

    if isinstance(frame.columns, pd.MultiIndex):
        ticker_values = frame.columns.get_level_values(-1)
        if ticker in ticker_values:
            frame = frame.xs(ticker, axis=1, level=-1)
        else:
            frame.columns = [
                "_".join(str(part) for part in column if part)
                for column in frame.columns.to_flat_index()
            ]

    frame = frame.reset_index()
    rename_map = {
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    frame = frame.rename(columns=rename_map)
    frame["date"] = pd.to_datetime(frame["date"]).dt.tz_localize(None)
    frame["ticker"] = ticker.upper()

    for column in PRICE_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA

    return frame[["date", "ticker", *PRICE_COLUMNS]].sort_values("date")


def download_price_history(
    ticker: str,
    start: str,
    end: str,
    raw_prices_dir: str | Path,
    auto_adjust: bool = False,
) -> pd.DataFrame:
    """Download daily OHLCV data and persist the raw normalized CSV."""
    ticker = ticker.upper().strip()
    configure_yfinance_cache()
    raw_dir = Path(raw_prices_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    try:
        frame = yf.download(
            ticker,
            start=start,
            end=end,
            auto_adjust=auto_adjust,
            progress=False,
            threads=False,
        )
    except Exception as exc:
        logger.warning("Failed to download prices for %s: %s", ticker, exc)
        return pd.DataFrame(columns=["date", "ticker", *PRICE_COLUMNS])

    normalized = _normalize_download_frame(frame, ticker)
    if normalized.empty:
        logger.warning("No price data returned for %s", ticker)
        return normalized

    output_path = raw_dir / f"{ticker}.csv"
    normalized.to_csv(output_path, index=False)
    return normalized


def download_many_prices(
    tickers: list[str],
    start: str,
    end: str,
    raw_prices_dir: str | Path,
    auto_adjust: bool = False,
) -> pd.DataFrame:
    """Download and combine price history for many tickers."""
    frames = [
        download_price_history(ticker, start, end, raw_prices_dir, auto_adjust)
        for ticker in tickers
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=["date", "ticker", *PRICE_COLUMNS])
    return pd.concat(frames, ignore_index=True).sort_values(["ticker", "date"])
