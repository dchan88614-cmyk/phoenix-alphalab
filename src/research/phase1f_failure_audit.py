from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.account.account_simulator import AccountSettings, EXECUTED
from src.research.auto_loop import CandidateRule
from src.research.historical_replay import HISTORICAL_BUY_CANDIDATE, build_phase1_historical_replay
from src.research.phase1c_robustness import THEME_MAP, simulate_phase1c_policy_trades
from src.research.phase1d_entry_rules import BASELINE_POLICY, build_entry_rule_diagnostics


PHASE_1F_DATA_QUALITY_BLOCKER = "PHASE_1F_DATA_QUALITY_BLOCKER"
PHASE_1F_FAILURES_CONCENTRATED_RESEARCH_ONLY = "PHASE_1F_FAILURES_CONCENTRATED_RESEARCH_ONLY"
PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN = "PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN"

STATIC_TAXONOMY = {
    "AAPL": ("mega-cap platform", "consumer devices / services"),
    "ABNB": ("consumer internet", "travel marketplace"),
    "ACHR": ("EV / mobility", "eVTOL"),
    "ADBE": ("software", "creative software"),
    "AFRM": ("fintech", "consumer credit"),
    "AI": ("AI / software", "enterprise AI"),
    "AMAT": ("semiconductor / hardware", "semicap equipment"),
    "AMD": ("semiconductor / hardware", "accelerators / CPU"),
    "ANET": ("AI infrastructure", "networking"),
    "APP": ("software", "adtech"),
    "ARM": ("semiconductor / hardware", "IP / architecture"),
    "ASML": ("semiconductor / hardware", "lithography"),
    "AVAV": ("space / defense / nuclear", "drones"),
    "AVGO": ("semiconductor / hardware", "networking silicon"),
    "BA": ("space / defense / nuclear", "aerospace"),
    "BBAI": ("AI / software", "defense AI"),
    "BEAM": ("biotech", "gene editing"),
    "BWXT": ("space / defense / nuclear", "nuclear services"),
    "CAVA": ("consumer growth", "restaurants"),
    "CCJ": ("space / defense / nuclear", "uranium"),
    "CEG": ("power / electrification", "nuclear utility"),
    "COIN": ("crypto-adjacent / high beta", "crypto exchange"),
    "CORZ": ("crypto-adjacent / high beta", "bitcoin mining / AI compute"),
    "CRM": ("software", "enterprise SaaS"),
    "CRWD": ("software", "cybersecurity"),
    "DASH": ("consumer internet", "delivery marketplace"),
    "DDOG": ("software", "observability"),
    "DELL": ("AI infrastructure", "servers"),
    "DNA": ("biotech", "synthetic biology"),
    "DUOL": ("consumer internet", "education app"),
    "EDIT": ("biotech", "gene editing"),
    "ELF": ("consumer growth", "beauty"),
    "ESTC": ("software", "search / observability"),
    "ETN": ("power / electrification", "electrical equipment"),
    "F": ("EV / mobility", "auto OEM"),
    "GD": ("space / defense / nuclear", "defense prime"),
    "GEV": ("power / electrification", "grid / turbines"),
    "GM": ("EV / mobility", "auto OEM"),
    "HOOD": ("fintech", "brokerage"),
    "HPE": ("AI infrastructure", "servers / networking"),
    "HUT": ("crypto-adjacent / high beta", "bitcoin mining"),
    "INTC": ("semiconductor / hardware", "CPU / foundry"),
    "IREN": ("crypto-adjacent / high beta", "bitcoin mining / AI compute"),
    "ISRG": ("robotics / automation", "surgical robotics"),
    "JOBY": ("EV / mobility", "eVTOL"),
    "KLAC": ("semiconductor / hardware", "semicap equipment"),
    "KTOS": ("space / defense / nuclear", "defense systems"),
    "LCID": ("EV / mobility", "EV OEM"),
    "LEU": ("space / defense / nuclear", "nuclear fuel"),
    "LI": ("EV / mobility", "China EV"),
    "LMT": ("space / defense / nuclear", "defense prime"),
    "LRCX": ("semiconductor / hardware", "semicap equipment"),
    "MRNA": ("biotech", "mRNA therapeutics"),
    "MRVL": ("semiconductor / hardware", "data-center silicon"),
    "MSFT": ("mega-cap platform", "cloud / AI platform"),
    "MSTR": ("crypto-adjacent / high beta", "bitcoin treasury"),
    "MU": ("semiconductor / hardware", "memory"),
    "NEE": ("power / electrification", "utility / renewables"),
    "NET": ("software", "edge cloud"),
    "NIO": ("EV / mobility", "China EV"),
    "NOC": ("space / defense / nuclear", "defense prime"),
    "NOW": ("software", "workflow SaaS"),
    "NVAX": ("biotech", "vaccines"),
    "NVDA": ("semiconductor / hardware", "AI accelerators"),
    "OKLO": ("space / defense / nuclear", "advanced nuclear"),
    "OKTA": ("software", "identity"),
    "PANW": ("software", "cybersecurity"),
    "PATH": ("AI / software", "automation software"),
    "PLTR": ("AI / software", "analytics / defense AI"),
    "PWR": ("power / electrification", "grid services"),
    "PYPL": ("fintech", "payments"),
    "QCOM": ("semiconductor / hardware", "mobile / edge chips"),
    "RBLX": ("consumer internet", "gaming platform"),
    "RDDT": ("consumer internet", "social platform"),
    "RIVN": ("EV / mobility", "EV OEM"),
    "RKLB": ("space / defense / nuclear", "space launch"),
    "ROKU": ("consumer internet", "streaming platform"),
    "RTX": ("space / defense / nuclear", "defense prime"),
    "RXRX": ("biotech", "AI drug discovery"),
    "S": ("software", "cybersecurity"),
    "SDGR": ("biotech", "computational drug discovery"),
    "SHOP": ("software", "commerce platform"),
    "SMCI": ("AI infrastructure", "servers"),
    "SMR": ("space / defense / nuclear", "small modular nuclear"),
    "SNOW": ("software", "data cloud"),
    "SO": ("power / electrification", "utility"),
    "SOFI": ("fintech", "consumer finance"),
    "SPOT": ("consumer internet", "audio streaming"),
    "TEAM": ("software", "collaboration SaaS"),
    "TER": ("semiconductor / hardware", "test equipment / robotics"),
    "TLN": ("power / electrification", "power producer"),
    "TSLA": ("EV / mobility", "EV / autonomy"),
    "TSM": ("semiconductor / hardware", "foundry"),
    "UBER": ("consumer internet", "mobility marketplace"),
    "UPST": ("fintech", "AI lending"),
    "VST": ("power / electrification", "power producer"),
    "XPEV": ("EV / mobility", "China EV"),
    "ZS": ("software", "cybersecurity"),
}


def build_phase1f_failure_audit(
    data: pd.DataFrame,
    account_settings: AccountSettings,
    rule: CandidateRule,
    replay_rounds: int = 100,
    replay_sample_count: int = 20,
    replay_sample_offset: int = 0,
    benchmark_ticker: str = "SPY",
    rejected_metadata: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["date", "ticker"]).reset_index(drop=True)

    ledger_frames: list[pd.DataFrame] = []
    for sample_index in range(replay_sample_count):
        sample_id = replay_sample_offset + sample_index
        decisions, _, _ = build_phase1_historical_replay(
            frame,
            account_settings,
            rule,
            replay_rounds=replay_rounds,
            benchmark_ticker=benchmark_ticker,
            replay_sample_offset=sample_id,
        )
        decisions["sample_id"] = sample_id
        baseline_trades = simulate_phase1c_policy_trades(decisions, frame, account_settings, BASELINE_POLICY)
        diagnostics = build_entry_rule_diagnostics(sample_id, decisions, baseline_trades, frame, rule)
        ledger_frames.append(build_failure_ledger_for_sample(sample_id, decisions, diagnostics, baseline_trades, frame))

    ledger = pd.concat(ledger_frames, ignore_index=True) if ledger_frames else pd.DataFrame()
    taxonomy = build_theme_taxonomy(ledger, rejected_metadata)
    ledger = apply_taxonomy(ledger, taxonomy)
    regime = build_regime_attribution(ledger)
    drawdown = build_drawdown_attribution(ledger)
    quality = build_data_quality_audit(frame, ledger, rejected_metadata, benchmark_ticker)
    summary = summarize_phase1f(ledger, taxonomy, drawdown, regime, quality, replay_sample_count)
    return ledger, taxonomy, drawdown, regime, quality, summary


def build_failure_ledger_for_sample(
    sample_id: int,
    decisions: pd.DataFrame,
    diagnostics: pd.DataFrame,
    trades: pd.DataFrame,
    data: pd.DataFrame,
) -> pd.DataFrame:
    buys = diagnostics.copy()
    if buys.empty:
        return pd.DataFrame(columns=failure_ledger_columns())
    executed = trades.loc[trades["status"].eq(EXECUTED)].copy() if not trades.empty else pd.DataFrame()
    executed = executed.set_index(["replay_date", "ticker"]) if not executed.empty else pd.DataFrame()
    market = build_market_regime_lookup(data)
    rows = []
    peak = 100.0
    worst_drawdown = 0.0
    worst_key = None
    for _, row in buys.sort_values(["replay_date", "ticker"]).iterrows():
        key = (row["replay_date"], row["ticker"])
        trade = executed.loc[key] if not executed.empty and key in executed.index else pd.Series(dtype=object)
        if isinstance(trade, pd.DataFrame):
            trade = trade.iloc[0]
        before = _num(trade.get("cash_before", row.get("estimated_total_cost", 100.0)))
        after = _num(trade.get("cash_after_exit", before))
        peak = max(peak, before)
        drawdown_after = after / peak - 1.0 if peak else 0.0
        contribution = min(0.0, after - before)
        if drawdown_after < worst_drawdown:
            worst_drawdown = drawdown_after
            worst_key = key
        regime = market.get(pd.Timestamp(row["replay_date"]).strftime("%Y-%m-%d"), {})
        theme, subtheme = ticker_theme_subtheme(str(row["ticker"]))
        rows.append(
            {
                "sample_id": sample_id,
                "replay_date": row["replay_date"],
                "ticker": row["ticker"],
                "theme": theme,
                "subtheme": subtheme,
                "reference_price": row.get("reference_price", pd.NA),
                "entry_price": row.get("entry_price", pd.NA),
                "entry_gap_pct": row.get("entry_gap_pct", pd.NA),
                "shares_with_100": row.get("shares_with_100", pd.NA),
                "estimated_total_cost": row.get("estimated_total_cost", pd.NA),
                "decision_strength": row.get("decision_strength", pd.NA),
                "smoke_score": row.get("smoke_score", pd.NA),
                "volatility_20d": row.get("volatility_20d", pd.NA),
                "atr_pct": row.get("atr_pct", pd.NA),
                "distance_from_52w_high": row.get("distance_from_52w_high_pct", pd.NA),
                "relative_volume_prev20": row.get("relative_volume_prev20", pd.NA),
                "pre_entry_return_5d": row.get("return_5d_prior", pd.NA),
                "pre_entry_return_10d": row.get("return_10d_prior", pd.NA),
                "market_regime_label": regime.get("market_regime_label", "UNKNOWN_MARKET_DATA"),
                "spy_trend_label": regime.get("spy_trend_label", "UNKNOWN_SPY_DATA"),
                "qqq_trend_label": regime.get("qqq_trend_label", "UNKNOWN_QQQ_DATA"),
                "market_volatility_label": regime.get("market_volatility_label", "UNKNOWN_VOLATILITY"),
                "simulated_exit_reason": trade.get("exit_reason", row.get("baseline_exit_reason", "")),
                "simulated_pnl_dollars": trade.get("pnl_dollars", row.get("baseline_pnl_dollars", pd.NA)),
                "simulated_return_pct": trade.get("trade_return_pct", row.get("baseline_trade_return_pct", pd.NA)),
                "forward_return_20d": row.get("forward_return_20d", pd.NA),
                "stopped_out_but_20d_positive": row.get("stopped_out_then_20d_positive", False),
                "running_equity_before_trade": before,
                "running_equity_after_trade": after,
                "drawdown_after_trade": drawdown_after,
                "drawdown_contribution_dollars": contribution,
                "is_worst_drawdown_trade_for_sample": False,
            }
        )
    ledger = pd.DataFrame(rows, columns=failure_ledger_columns())
    if worst_key is not None:
        ledger.loc[ledger["replay_date"].eq(worst_key[0]) & ledger["ticker"].eq(worst_key[1]), "is_worst_drawdown_trade_for_sample"] = True
    return ledger


def build_theme_taxonomy(ledger: pd.DataFrame, rejected_metadata: pd.DataFrame | None = None) -> pd.DataFrame:
    tickers = set(ledger["ticker"].dropna().astype(str).unique()) if not ledger.empty else set()
    if rejected_metadata is not None and not rejected_metadata.empty and "ticker" in rejected_metadata.columns:
        tickers.update(rejected_metadata["ticker"].dropna().astype(str).unique())
    rows = []
    for ticker in sorted(tickers):
        theme, subtheme = ticker_theme_subtheme(ticker)
        mapped = ticker in STATIC_TAXONOMY or ticker in THEME_MAP
        rows.append(
            {
                "ticker": ticker,
                "company_name_if_available": "",
                "theme": theme,
                "subtheme": subtheme,
                "mapping_source": "static_phase1f_taxonomy" if mapped else "low_confidence_fallback",
                "mapping_confidence": "HIGH" if mapped else "LOW",
                "notes": "" if mapped else "UNMAPPED_LOW_CONFIDENCE: no static project mapping available.",
            }
        )
    return pd.DataFrame(rows)


def apply_taxonomy(ledger: pd.DataFrame, taxonomy: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty or taxonomy.empty:
        return ledger
    mapped = taxonomy[["ticker", "theme", "subtheme"]].drop_duplicates("ticker")
    merged = ledger.drop(columns=["theme", "subtheme"], errors="ignore").merge(mapped, on="ticker", how="left")
    merged["theme"] = merged["theme"].fillna("UNMAPPED_LOW_CONFIDENCE")
    merged["subtheme"] = merged["subtheme"].fillna("unknown")
    return merged[failure_ledger_columns()].copy()


def build_drawdown_attribution(ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty:
        return pd.DataFrame()
    frame = ledger.copy()
    frame["calendar_month"] = pd.to_datetime(frame["replay_date"]).dt.to_period("M").astype(str)
    frame["calendar_quarter"] = pd.to_datetime(frame["replay_date"]).dt.to_period("Q").astype(str)
    frame["entry_gap_pct_bucket"] = bucket(frame["entry_gap_pct"], [-0.02, 0.0, 0.02, 0.05])
    frame["volatility_20d_bucket"] = bucket(frame["volatility_20d"], [0.03, 0.05, 0.07, 0.10])
    frame["atr_pct_bucket"] = bucket(frame["atr_pct"], [0.03, 0.05, 0.07, 0.10])
    frame["smoke_score_bucket"] = bucket(frame["smoke_score"], [0.88, 0.90, 0.92, 0.94])
    frame["decision_strength_bucket"] = bucket(frame["decision_strength"], [0.50, 0.65, 0.80, 1.00])
    group_cols = [
        "sample_id",
        "ticker",
        "theme",
        "subtheme",
        "calendar_month",
        "calendar_quarter",
        "entry_gap_pct_bucket",
        "volatility_20d_bucket",
        "atr_pct_bucket",
        "smoke_score_bucket",
        "decision_strength_bucket",
        "simulated_exit_reason",
    ]
    grouped = frame.groupby(group_cols, dropna=False).agg(
        candidate_count=("ticker", "size"),
        win_count=("simulated_pnl_dollars", lambda s: int(pd.to_numeric(s, errors="coerce").gt(0).sum())),
        loss_count=("simulated_pnl_dollars", lambda s: int(pd.to_numeric(s, errors="coerce").lt(0).sum())),
        total_pnl_dollars=("simulated_pnl_dollars", "sum"),
        average_pnl_dollars=("simulated_pnl_dollars", "mean"),
        median_pnl_dollars=("simulated_pnl_dollars", "median"),
        average_20d_forward_return=("forward_return_20d", "mean"),
        median_20d_forward_return=("forward_return_20d", "median"),
        max_single_candidate_loss_dollars=("simulated_pnl_dollars", "min"),
        max_drawdown_contribution_dollars=("drawdown_contribution_dollars", "min"),
    ).reset_index()
    grouped["simulated_win_rate"] = grouped["win_count"] / grouped["candidate_count"]
    return grouped


def build_regime_attribution(ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty:
        return pd.DataFrame()
    group_cols = ["sample_id", "market_regime_label", "spy_trend_label", "qqq_trend_label", "market_volatility_label"]
    grouped = ledger.groupby(group_cols, dropna=False).agg(
        candidate_count=("ticker", "size"),
        win_count=("simulated_pnl_dollars", lambda s: int(pd.to_numeric(s, errors="coerce").gt(0).sum())),
        loss_count=("simulated_pnl_dollars", lambda s: int(pd.to_numeric(s, errors="coerce").lt(0).sum())),
        total_pnl_dollars=("simulated_pnl_dollars", "sum"),
        average_pnl_dollars=("simulated_pnl_dollars", "mean"),
        average_forward_return_20d=("forward_return_20d", "mean"),
        worst_trade_pnl_dollars=("simulated_pnl_dollars", "min"),
    ).reset_index()
    grouped["simulated_win_rate"] = grouped["win_count"] / grouped["candidate_count"]
    return grouped


def build_data_quality_audit(
    data: pd.DataFrame,
    ledger: pd.DataFrame,
    rejected_metadata: pd.DataFrame | None,
    benchmark_ticker: str,
) -> pd.DataFrame:
    rows = []
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    for ticker, group in frame.groupby("ticker"):
        group = group.sort_values("date")
        expected = pd.bdate_range(group["date"].min(), group["date"].max())
        missing = max(0, len(expected) - group["date"].nunique())
        zero_volume = int(pd.to_numeric(group.get("volume", pd.Series(dtype=float)), errors="coerce").fillna(0).eq(0).sum())
        volume = pd.to_numeric(group.get("volume", pd.Series(dtype=float)), errors="coerce")
        abnormal_volume = int((volume > volume.median() * 20).sum()) if volume.notna().any() and volume.median() > 0 else 0
        close = pd.to_numeric(group["close"], errors="coerce")
        daily_ret = close.pct_change(fill_method=None).abs()
        split_like = int(daily_ret.gt(0.45).sum())
        incomplete_forward = int(group.get("fwd_return_20d", pd.Series(dtype=float)).isna().sum()) if "fwd_return_20d" in group.columns else 0
        rows.extend(
            [
                quality_row(ticker, "missing_ohlcv_bars", missing, "WARN" if missing else "OK", "Business-day gap approximation; market holidays may be counted conservatively."),
                quality_row(ticker, "zero_volume_days", zero_volume, "WARN" if zero_volume else "OK", ""),
                quality_row(ticker, "abnormal_volume_days", abnormal_volume, "WARN" if abnormal_volume else "OK", "Volume above 20x ticker median."),
                quality_row(ticker, "split_or_adjustment_anomaly", split_like, "WARN" if split_like else "OK", "Absolute daily close move above 45%."),
                quality_row(ticker, "incomplete_20d_forward_windows", incomplete_forward, "WARN" if incomplete_forward else "OK", ""),
            ]
        )
    if rejected_metadata is not None and not rejected_metadata.empty:
        for _, row in rejected_metadata.iterrows():
            rows.append(quality_row(row["ticker"], "metadata_rejected_symbol", 1, "WARN", str(row.get("reason", ""))))
    if benchmark_ticker not in set(frame["ticker"]):
        rows.append(quality_row(benchmark_ticker, "missing_benchmark_data", 1, "BLOCKER", "Benchmark missing from research dataset."))
    if "QQQ" not in set(frame["ticker"]):
        rows.append(quality_row("QQQ", "missing_qqq_regime_data", 1, "WARN", "QQQ was not downloaded; QQQ trend labels are UNKNOWN_QQQ_DATA."))
    return pd.DataFrame(rows)


def build_market_regime_lookup(data: pd.DataFrame) -> dict[str, dict]:
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    lookup: dict[str, dict] = {}
    spy = regime_source(frame, "SPY")
    qqq = regime_source(frame, "QQQ")
    for date in sorted(frame["date"].dropna().unique()):
        key = pd.Timestamp(date).strftime("%Y-%m-%d")
        spy_row = spy.loc[spy["date"].eq(date)]
        qqq_row = qqq.loc[qqq["date"].eq(date)]
        spy_label = trend_label(spy_row.iloc[0], "SPY") if not spy_row.empty else "UNKNOWN_SPY_DATA"
        qqq_label = trend_label(qqq_row.iloc[0], "QQQ") if not qqq_row.empty else "UNKNOWN_QQQ_DATA"
        vol_label = volatility_label(spy_row.iloc[0].get("realized_vol_20d", pd.NA)) if not spy_row.empty else "UNKNOWN_VOLATILITY"
        dd_label = drawdown_label(spy_row.iloc[0].get("drawdown_50d_high", pd.NA)) if not spy_row.empty else "UNKNOWN_DRAWDOWN"
        market = market_regime_label(spy_label, qqq_label, vol_label, dd_label)
        lookup[key] = {
            "spy_trend_label": spy_label,
            "qqq_trend_label": qqq_label,
            "market_volatility_label": vol_label,
            "market_regime_label": market,
        }
    return lookup


def regime_source(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    source = frame.loc[frame["ticker"].eq(ticker)].sort_values("date").copy()
    if source.empty:
        return source
    close = pd.to_numeric(source["close"], errors="coerce")
    source["sma20"] = close.rolling(20, min_periods=20).mean()
    source["sma50"] = close.rolling(50, min_periods=50).mean()
    source["realized_vol_20d"] = close.pct_change(fill_method=None).rolling(20, min_periods=20).std()
    source["drawdown_50d_high"] = close / close.rolling(50, min_periods=20).max() - 1.0
    return source


def summarize_phase1f(
    ledger: pd.DataFrame,
    taxonomy: pd.DataFrame,
    drawdown: pd.DataFrame,
    regime: pd.DataFrame,
    quality: pd.DataFrame,
    replay_sample_count: int,
) -> dict:
    blocker = quality.loc[quality["severity"].eq("BLOCKER")]
    loss = ledger.loc[pd.to_numeric(ledger["simulated_pnl_dollars"], errors="coerce") < 0].copy()
    total_loss = abs(float(pd.to_numeric(loss["simulated_pnl_dollars"], errors="coerce").sum())) if not loss.empty else 0.0
    theme_loss = loss.groupby("theme")["simulated_pnl_dollars"].sum().abs().sort_values(ascending=False) if not loss.empty else pd.Series(dtype=float)
    ticker_loss = loss.groupby("ticker")["simulated_pnl_dollars"].sum().abs().sort_values(ascending=False) if not loss.empty else pd.Series(dtype=float)
    unmapped_loss = float(theme_loss.get("UNMAPPED_LOW_CONFIDENCE", 0.0))
    top_theme_share = float(theme_loss.iloc[0] / total_loss) if total_loss and len(theme_loss) else 0.0
    top_ticker_share = float(ticker_loss.iloc[0] / total_loss) if total_loss and len(ticker_loss) else 0.0
    status = phase1f_status(bool(len(blocker)), top_theme_share, top_ticker_share, unmapped_loss, total_loss)
    return {
        "phase_1f_status": status,
        "sample_count": replay_sample_count,
        "ledger_rows": int(len(ledger)),
        "loss_rows": int(len(loss)),
        "top_theme_loss_share": top_theme_share,
        "top_ticker_loss_share": top_ticker_share,
        "unmapped_loss_dollars": unmapped_loss,
        "unmapped_loss_share": float(unmapped_loss / total_loss) if total_loss else 0.0,
        "top_theme_losses": theme_loss.head(10).to_dict(),
        "top_ticker_losses": ticker_loss.head(10).to_dict(),
        "data_quality_blockers": int(len(blocker)),
        "data_quality_warn_count": int(quality["severity"].eq("WARN").sum()) if not quality.empty else 0,
        "failure_concentration_assessment": "concentrated" if top_theme_share >= 0.35 or top_ticker_share >= 0.25 else "broad",
    }


def phase1f_status(has_blocker: bool, top_theme_share: float, top_ticker_share: float, unmapped_loss: float, total_loss: float) -> str:
    if has_blocker:
        return PHASE_1F_DATA_QUALITY_BLOCKER
    if top_theme_share >= 0.35 or top_ticker_share >= 0.25:
        return PHASE_1F_FAILURES_CONCENTRATED_RESEARCH_ONLY
    return PHASE_1F_FAILURES_BROAD_RECOMMEND_REDESIGN


def write_phase1f_reports(
    ledger: pd.DataFrame,
    taxonomy: pd.DataFrame,
    drawdown: pd.DataFrame,
    regime: pd.DataFrame,
    quality: pd.DataFrame,
    summary: dict,
    ledger_csv_path: str | Path,
    taxonomy_csv_path: str | Path,
    drawdown_csv_path: str | Path,
    regime_csv_path: str | Path,
    quality_csv_path: str | Path,
    summary_md_path: str | Path,
) -> None:
    for path in [ledger_csv_path, taxonomy_csv_path, drawdown_csv_path, regime_csv_path, quality_csv_path, summary_md_path]:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    ledger.to_csv(ledger_csv_path, index=False)
    taxonomy.to_csv(taxonomy_csv_path, index=False)
    drawdown.to_csv(drawdown_csv_path, index=False)
    regime.to_csv(regime_csv_path, index=False)
    quality.to_csv(quality_csv_path, index=False)
    Path(summary_md_path).write_text(phase1f_summary_markdown(summary, ledger, taxonomy, drawdown, regime, quality), encoding="utf-8")


def phase1f_summary_markdown(summary: dict, ledger: pd.DataFrame, taxonomy: pd.DataFrame, drawdown: pd.DataFrame, regime: pd.DataFrame, quality: pd.DataFrame) -> str:
    lines = [
        "PHOENIX NANO PHASE 1F — FAILURE ATTRIBUTION, TAXONOMY, AND DATA QUALITY AUDIT",
        "",
        "Research-only. This does not change daily scan behavior and does not approve any policy.",
        "",
        "## Phase 1E Recap",
        "",
        "- Phase 1E found no calibration or holdout filter passed all gates.",
        "- Phase 1F audits whether remaining failures are explainable by ticker, theme, regime, or data quality.",
        "",
        "## Failure Sample Summary",
        "",
        f"- Samples audited: {summary['sample_count']}",
        f"- Accepted historical candidates in ledger: {summary['ledger_rows']}",
        f"- Losing simulated candidates: {summary['loss_rows']}",
        "",
        "## Theme Taxonomy Cleanup Results",
        "",
        f"- Taxonomy rows: {len(taxonomy)}",
        f"- Low-confidence mappings: {int(taxonomy['mapping_confidence'].eq('LOW').sum()) if not taxonomy.empty else 0}",
        "",
        "## Remaining Unmapped Loss Contribution",
        "",
        f"- Unmapped loss dollars: ${summary['unmapped_loss_dollars']:.2f}",
        f"- Unmapped loss share: {summary['unmapped_loss_share'] * 100:.2f}%",
        "",
        "## Drawdown Attribution Summary",
        "",
        top_loss_lines(summary["top_theme_losses"], "Theme losses"),
        "",
        top_loss_lines(summary["top_ticker_losses"], "Ticker losses"),
        "",
        "## Market Regime Attribution Summary",
        "",
        regime_summary(regime),
        "",
        "## Data Quality Audit Summary",
        "",
        f"- Data quality blockers: {summary['data_quality_blockers']}",
        f"- Data quality warnings: {summary['data_quality_warn_count']}",
        data_quality_summary(quality),
        "",
        "## Concentration Assessment",
        "",
        f"- Failures are assessed as: {summary['failure_concentration_assessment']}",
        f"- Top theme loss share: {summary['top_theme_loss_share'] * 100:.2f}%",
        f"- Top ticker loss share: {summary['top_ticker_loss_share'] * 100:.2f}%",
        "",
        f"## Final Phase 1F Status: {summary['phase_1f_status']}",
        "",
        "Do not start paper execution or real-money execution.",
        "",
        "## Next Research Task Recommendation",
        "",
        next_recommendation(summary["phase_1f_status"]),
        "",
    ]
    return "\n".join(lines)


def failure_ledger_columns() -> list[str]:
    return [
        "sample_id", "replay_date", "ticker", "theme", "subtheme", "reference_price", "entry_price", "entry_gap_pct",
        "shares_with_100", "estimated_total_cost", "decision_strength", "smoke_score", "volatility_20d", "atr_pct",
        "distance_from_52w_high", "relative_volume_prev20", "pre_entry_return_5d", "pre_entry_return_10d",
        "market_regime_label", "spy_trend_label", "qqq_trend_label", "market_volatility_label", "simulated_exit_reason",
        "simulated_pnl_dollars", "simulated_return_pct", "forward_return_20d", "stopped_out_but_20d_positive",
        "running_equity_before_trade", "running_equity_after_trade", "drawdown_after_trade", "drawdown_contribution_dollars",
        "is_worst_drawdown_trade_for_sample",
    ]


def ticker_theme_subtheme(ticker: str) -> tuple[str, str]:
    if ticker in STATIC_TAXONOMY:
        return STATIC_TAXONOMY[ticker]
    if ticker in THEME_MAP:
        return THEME_MAP[ticker], "mapped_from_phase1c"
    return "UNMAPPED_LOW_CONFIDENCE", "unknown"


def trend_label(row: pd.Series, ticker: str) -> str:
    close = row.get("close", pd.NA)
    sma20 = row.get("sma20", pd.NA)
    sma50 = row.get("sma50", pd.NA)
    if pd.isna(close) or pd.isna(sma20) or pd.isna(sma50):
        return f"{ticker}_TREND_UNKNOWN"
    above20 = float(close) >= float(sma20)
    above50 = float(close) >= float(sma50)
    if above20 and above50:
        return f"{ticker}_ABOVE_20_50"
    if above20 and not above50:
        return f"{ticker}_ABOVE_20_BELOW_50"
    if not above20 and above50:
        return f"{ticker}_BELOW_20_ABOVE_50"
    return f"{ticker}_BELOW_20_50"


def volatility_label(value: object) -> str:
    if pd.isna(value):
        return "VOL_UNKNOWN"
    value = float(value)
    if value < 0.01:
        return "LOW_VOL"
    if value < 0.02:
        return "MEDIUM_VOL"
    return "HIGH_VOL"


def drawdown_label(value: object) -> str:
    if pd.isna(value):
        return "DRAWDOWN_UNKNOWN"
    value = float(value)
    if value > -0.03:
        return "NEAR_50D_HIGH"
    if value > -0.08:
        return "MODERATE_DRAWDOWN"
    return "DEEP_DRAWDOWN"


def market_regime_label(spy_label: str, qqq_label: str, vol_label: str, dd_label: str) -> str:
    if "UNKNOWN" in spy_label:
        return "UNKNOWN_MARKET_DATA"
    if "ABOVE_20_50" in spy_label and vol_label != "HIGH_VOL" and dd_label != "DEEP_DRAWDOWN":
        return "RISK_ON"
    if "BELOW_20_50" in spy_label or vol_label == "HIGH_VOL" or dd_label == "DEEP_DRAWDOWN":
        return "RISK_OFF"
    return "MIXED"


def bucket(series: pd.Series, edges: list[float]) -> pd.Series:
    return pd.cut(pd.to_numeric(series, errors="coerce"), bins=[-float("inf"), *edges, float("inf")], include_lowest=True).astype(str)


def quality_row(ticker: str, issue_type: str, issue_count: int, severity: str, notes: str) -> dict:
    return {"ticker": ticker, "issue_type": issue_type, "issue_count": int(issue_count), "severity": severity, "notes": notes}


def _num(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def top_loss_lines(losses: dict, title: str) -> str:
    if not losses:
        return f"{title}: none"
    lines = [f"{title}:"]
    for key, value in list(losses.items())[:10]:
        lines.append(f"- {key}: ${float(value):.2f}")
    return "\n".join(lines)


def regime_summary(regime: pd.DataFrame) -> str:
    if regime.empty:
        return "No regime rows."
    top = regime.groupby("market_regime_label")["total_pnl_dollars"].sum().sort_values().head(8)
    return "\n".join(f"- {key}: ${float(value):.2f}" for key, value in top.items())


def data_quality_summary(quality: pd.DataFrame) -> str:
    if quality.empty:
        return "- No data quality rows."
    warn = quality.loc[quality["severity"].isin(["WARN", "BLOCKER"])].groupby("issue_type")["issue_count"].sum().sort_values(ascending=False).head(10)
    return "\n".join(f"- {key}: {int(value)}" for key, value in warn.items()) if not warn.empty else "- No warnings or blockers."


def next_recommendation(status: str) -> str:
    if status == PHASE_1F_DATA_QUALITY_BLOCKER:
        return "Fix data-quality blockers before any additional Nano research."
    if status == PHASE_1F_FAILURES_CONCENTRATED_RESEARCH_ONLY:
        return "Ask GPT whether one narrow theme/regime exclusion hypothesis is worth testing as research-only."
    return "Recommend Candidate 34 redesign rather than more threshold tuning."
