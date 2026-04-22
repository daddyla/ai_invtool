"""Earnings analysis engine — windows, patterns, forecasting."""

import pandas as pd
import numpy as np
from datetime import timedelta
from invtool.config import NVDA_EARNINGS, NVDA_UPCOMING


# ── Known earnings data ──
KNOWN_EARNINGS = {
    "NVDA": NVDA_EARNINGS,
}

KNOWN_UPCOMING = {
    "NVDA": NVDA_UPCOMING,
}


def get_earnings_dates(ticker: str, data_provider=None) -> list:
    """Get earnings dates — from built-in data or yfinance."""
    if ticker in KNOWN_EARNINGS:
        return KNOWN_EARNINGS[ticker]
    # Fallback: try yfinance
    if data_provider:
        try:
            t = data_provider.get_ticker(ticker)
            cal = t.get_earnings_dates(limit=20)
            if cal is not None and not cal.empty:
                dates = []
                for idx, row in cal.iterrows():
                    dt = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
                    eps_est = row.get("EPS Estimate", 0) or 0
                    eps_act = row.get("Reported EPS", 0) or 0
                    dates.append({
                        "date": dt,
                        "quarter": dt[:7],
                        "eps_est": float(eps_est) if eps_est else 0,
                        "eps_actual": float(eps_act) if eps_act else 0,
                        "rev_est": 0, "rev_actual": 0,
                    })
                # Filter to dates with actual EPS (historical only)
                dates = [d for d in dates if d["eps_actual"] != 0]
                dates.sort(key=lambda x: x["date"])
                return dates
        except Exception:
            pass
    return []


def analyze_earnings_windows(hist: pd.DataFrame, earnings_dates: list) -> pd.DataFrame:
    """Calculate returns in windows before and after each earnings date."""
    results = []

    for e in earnings_dates:
        earn_date = pd.Timestamp(e["date"])
        mask = hist.index <= earn_date + timedelta(hours=23)
        if mask.sum() == 0:
            continue
        pre_close = hist.loc[hist.index[mask][-1], "Close"]

        mask_post = hist.index > earn_date
        if mask_post.sum() == 0:
            continue

        windows = {}

        # Pre-earnings windows
        for days_before in [30, 20, 10, 5, 1]:
            target = earn_date - timedelta(days=days_before)
            mask_pre = hist.index <= target + timedelta(hours=23)
            if mask_pre.sum() > 0:
                ref_close = hist.loc[hist.index[mask_pre][-1], "Close"]
                windows[f"pre_{days_before}d"] = (pre_close - ref_close) / ref_close

        # Post-earnings windows
        post_days = hist.index[hist.index > earn_date]
        for days_after in [1, 2, 5, 10, 20, 30]:
            if len(post_days) >= days_after:
                post_close = hist.loc[post_days[days_after - 1], "Close"]
                windows[f"post_{days_after}d"] = (post_close - pre_close) / pre_close

        eps_surprise = 0
        rev_surprise = 0
        if e.get("eps_est", 0) > 0 and e.get("eps_actual", 0) > 0:
            eps_surprise = (e["eps_actual"] - e["eps_est"]) / e["eps_est"]
        if e.get("rev_est", 0) > 0 and e.get("rev_actual", 0) > 0:
            rev_surprise = (e["rev_actual"] - e["rev_est"]) / e["rev_est"]

        results.append({
            "date": e["date"],
            "quarter": e.get("quarter", ""),
            "eps_surprise": eps_surprise,
            "rev_surprise": rev_surprise,
            "pre_close": pre_close,
            **windows,
        })

    return pd.DataFrame(results)


def detect_sell_the_news(df: pd.DataFrame) -> dict:
    """Analyze sell-the-news pattern."""
    if df.empty or "post_1d" not in df.columns:
        return {"sell_the_news_rate": 0, "details": "Insufficient data"}

    beat_mask = df["eps_surprise"] > 0
    beats = df[beat_mask]
    if beats.empty:
        return {"sell_the_news_rate": 0, "total_beats": 0}

    dropped = beats[beats["post_1d"] < 0]
    rate = len(dropped) / len(beats)

    recent = df.tail(6)
    recent_drops = (recent["post_1d"] < 0).sum() if "post_1d" in recent.columns else 0

    return {
        "sell_the_news_rate": rate,
        "total_earnings": len(df),
        "total_beats": len(beats),
        "beats_then_dropped": len(dropped),
        "recent_6q_drops": recent_drops,
        "avg_post_1d": float(df["post_1d"].mean()) if "post_1d" in df.columns else 0,
        "avg_pre_10d": float(df["pre_10d"].mean()) if "pre_10d" in df.columns else 0,
    }


def forecast_earnings(df: pd.DataFrame, upcoming: dict = None) -> dict:
    """Generate forecast based on historical patterns."""
    if df.empty:
        return {"forecast": "Insufficient data"}

    stn = detect_sell_the_news(df)
    avg_post_1d = stn.get("avg_post_1d", 0)
    avg_pre_10d = stn.get("avg_pre_10d", 0)

    scenarios = [
        {
            "name": "SELL THE NEWS",
            "probability": 60 if stn["sell_the_news_rate"] > 0.5 else 40,
            "expected_move": f"{avg_post_1d:+.1%} to -8%",
            "description": f"Stock drops after beat ({stn['sell_the_news_rate']:.0%} historical rate)",
        },
        {
            "name": "BEAT & RALLY",
            "probability": 30 if stn["sell_the_news_rate"] > 0.5 else 45,
            "expected_move": "+5% to +16%",
            "description": "Strong beat with upside guidance surprise",
        },
        {
            "name": "FLAT / MUTED",
            "probability": 10 if stn["sell_the_news_rate"] > 0.5 else 15,
            "expected_move": "+/-2%",
            "description": "In-line results, no big move",
        },
    ]

    return {
        "avg_pre_10d_runup": avg_pre_10d,
        "avg_post_1d": avg_post_1d,
        "sell_the_news_rate": stn["sell_the_news_rate"],
        "scenarios": scenarios,
        "upcoming": upcoming,
    }


def full_earnings_analysis(ticker: str, data_provider) -> dict:
    """Complete earnings analysis for a ticker."""
    hist = data_provider.get_history(ticker, "3y")
    if hist.empty:
        return {"error": f"No price data for {ticker}"}

    earnings = get_earnings_dates(ticker, data_provider)
    if not earnings:
        return {"error": f"No earnings data available for {ticker}"}

    df = analyze_earnings_windows(hist, earnings)
    stn = detect_sell_the_news(df)
    upcoming = KNOWN_UPCOMING.get(ticker)
    forecast = forecast_earnings(df, upcoming)

    return {
        "ticker": ticker,
        "earnings_df": df,
        "sell_the_news": stn,
        "forecast": forecast,
        "num_quarters": len(df),
    }
