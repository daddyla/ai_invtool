"""Market intelligence — earnings calendar, movers, sectors, analysts, insiders, economic events."""

import warnings
warnings.filterwarnings("ignore")

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf


# Sector ETF mapping
SECTOR_ETFS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Energy": "XLE",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Consumer Staples": "XLP",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Consumer Disc.": "XLY",
    "Communication": "XLC",
}


def earnings_calendar(date_range="this_week") -> dict:
    """Get upcoming earnings announcements.

    date_range: "today", "tomorrow", "this_week", or "next_week"
    """
    try:
        cal = yf.Calendars()
        df = cal.earnings_calendar
    except Exception:
        df = None

    if df is None or df.empty:
        return {"date_range": date_range, "earnings": [], "error": "Could not fetch earnings calendar"}

    # Parse dates
    today = datetime.now().date()
    if date_range == "today":
        start, end = today, today
        label = f"Today ({today})"
    elif date_range == "tomorrow":
        tmr = today + timedelta(days=1)
        start, end = tmr, tmr
        label = f"Tomorrow ({tmr})"
    elif date_range == "next_week":
        start = today + timedelta(days=(7 - today.weekday()))
        end = start + timedelta(days=4)
        label = f"Next Week ({start} to {end})"
    else:  # this_week
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=4)
        label = f"This Week ({start} to {end})"

    # Filter by date range
    earnings = []
    for idx, row in df.iterrows():
        ticker = idx if isinstance(idx, str) else str(idx)
        event_date = row.get("Event Start Date")
        if event_date is None:
            continue

        try:
            if isinstance(event_date, str):
                ed = datetime.strptime(event_date[:10], "%Y-%m-%d").date()
            elif hasattr(event_date, "date"):
                ed = event_date.date()
            else:
                ed = pd.Timestamp(event_date).date()
        except Exception:
            continue

        if start <= ed <= end:
            earnings.append({
                "ticker": ticker,
                "company": str(row.get("Company", "")),
                "date": str(ed),
                "timing": str(row.get("Timing", "")),
                "eps_estimate": _safe_float(row.get("EPS Estimate")),
                "reported_eps": _safe_float(row.get("Reported EPS")),
                "surprise_pct": _safe_float(row.get("Surprise(%)")),
                "market_cap": _safe_float(row.get("Marketcap")),
            })

    # Sort by date then market cap
    earnings.sort(key=lambda x: (x["date"], -(x["market_cap"] or 0)))

    return {
        "date_range": label,
        "total": len(earnings),
        "earnings": earnings,
    }


def market_movers(category="day_gainers") -> dict:
    """Get top market movers: gainers, losers, or most active.

    category: "day_gainers", "day_losers", "most_actives"
    """
    valid = {"day_gainers": "Top Gainers", "day_losers": "Top Losers",
             "most_actives": "Most Active"}
    title = valid.get(category, "Top Gainers")

    try:
        result = yf.screen(category)
        quotes = result.get("quotes", [])
    except Exception as e:
        return {"category": title, "stocks": [], "error": str(e)}

    stocks = []
    for q in quotes[:25]:
        stocks.append({
            "ticker": q.get("symbol", ""),
            "name": q.get("shortName", q.get("longName", ""))[:40],
            "price": _safe_float(q.get("regularMarketPrice")),
            "change": _safe_float(q.get("regularMarketChange")),
            "change_pct": _safe_float(q.get("regularMarketChangePercent")),
            "volume": int(q.get("regularMarketVolume", 0) or 0),
            "market_cap": _safe_float(q.get("marketCap")),
        })

    return {
        "category": title,
        "total": len(stocks),
        "stocks": stocks,
    }


def sector_performance(data_provider=None) -> dict:
    """Get sector performance using sector ETFs."""
    sectors = []

    for name, etf in SECTOR_ETFS.items():
        try:
            t = yf.Ticker(etf)
            hist = t.history(period="3mo", interval="1d")
            if hist.empty:
                continue

            hist.index = hist.index.tz_localize(None)
            current = float(hist["Close"].iloc[-1])

            def _ret(days):
                if len(hist) > days:
                    return float((current / hist["Close"].iloc[-days - 1] - 1) * 100)
                return None

            sectors.append({
                "name": name,
                "etf": etf,
                "price": round(current, 2),
                "change_1d": round(_ret(1), 2) if _ret(1) is not None else None,
                "change_1w": round(_ret(5), 2) if _ret(5) is not None else None,
                "change_1m": round(_ret(21), 2) if _ret(21) is not None else None,
                "change_3m": round(_ret(63), 2) if len(hist) > 63 else None,
            })
        except Exception:
            continue

    # Sort by 1d change
    sectors.sort(key=lambda x: x.get("change_1d") or 0, reverse=True)

    return {
        "total": len(sectors),
        "sectors": sectors,
    }


def analyst_ratings(ticker: str, data_provider=None) -> dict:
    """Get analyst ratings, price targets, and recent upgrades/downgrades."""
    ticker = ticker.upper()
    t = yf.Ticker(ticker)
    current_price = 0.0
    try:
        hist = t.history(period="5d")
        if not hist.empty:
            current_price = float(hist["Close"].iloc[-1])
    except Exception:
        pass

    # Price targets
    price_targets = {}
    try:
        pt = t.analyst_price_targets
        if pt and isinstance(pt, dict):
            price_targets = {
                "current": _safe_float(pt.get("current")),
                "low": _safe_float(pt.get("low")),
                "high": _safe_float(pt.get("high")),
                "mean": _safe_float(pt.get("mean")),
                "median": _safe_float(pt.get("median")),
            }
            if price_targets.get("mean") and current_price > 0:
                price_targets["upside_pct"] = round(
                    (price_targets["mean"] / current_price - 1) * 100, 1
                )
    except Exception:
        pass

    # Recommendations breakdown
    ratings_breakdown = {}
    try:
        rec = t.recommendations
        if rec is not None and not rec.empty:
            latest = rec.iloc[0]
            ratings_breakdown = {
                "strongBuy": int(latest.get("strongBuy", 0)),
                "buy": int(latest.get("buy", 0)),
                "hold": int(latest.get("hold", 0)),
                "sell": int(latest.get("sell", 0)),
                "strongSell": int(latest.get("strongSell", 0)),
            }
            total = sum(ratings_breakdown.values())
            if total > 0:
                bull = ratings_breakdown["strongBuy"] + ratings_breakdown["buy"]
                ratings_breakdown["total_analysts"] = total
                ratings_breakdown["bullish_pct"] = round(bull / total * 100, 0)
    except Exception:
        pass

    # Determine consensus
    if ratings_breakdown:
        bull = ratings_breakdown.get("strongBuy", 0) + ratings_breakdown.get("buy", 0)
        bear = ratings_breakdown.get("sell", 0) + ratings_breakdown.get("strongSell", 0)
        total = ratings_breakdown.get("total_analysts", 1)
        if bull / total > 0.6:
            consensus = "STRONG BUY" if bull / total > 0.8 else "BUY"
        elif bear / total > 0.3:
            consensus = "SELL"
        else:
            consensus = "HOLD"
    else:
        consensus = "N/A"

    # Recent upgrades/downgrades
    recent_changes = []
    try:
        ud = t.upgrades_downgrades
        if ud is not None and not ud.empty:
            for idx, row in ud.head(10).iterrows():
                date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
                recent_changes.append({
                    "date": date_str,
                    "firm": str(row.get("Firm", "")),
                    "action": str(row.get("Action", "")),
                    "to_grade": str(row.get("ToGrade", "")),
                    "from_grade": str(row.get("FromGrade", "")),
                    "price_target": _safe_float(row.get("currentPriceTarget")),
                    "prior_target": _safe_float(row.get("priorPriceTarget")),
                })
    except Exception:
        pass

    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "consensus": consensus,
        "price_targets": price_targets,
        "ratings_breakdown": ratings_breakdown,
        "recent_changes": recent_changes,
    }


def insider_activity(ticker: str, data_provider=None) -> dict:
    """Get insider trading activity for a ticker."""
    ticker = ticker.upper()
    t = yf.Ticker(ticker)

    transactions = []
    try:
        it = t.insider_transactions
        if it is not None and not it.empty:
            for _, row in it.head(15).iterrows():
                trans_type = str(row.get("Transaction", ""))
                shares = int(row.get("Shares", 0) or 0)
                value = _safe_float(row.get("Value"))

                transactions.append({
                    "insider": str(row.get("Insider", "")),
                    "position": str(row.get("Position", "")),
                    "date": str(row.get("Start Date", ""))[:10],
                    "transaction": trans_type,
                    "shares": shares,
                    "value": round(value, 0) if value else None,
                    "ownership": str(row.get("Ownership", "")),
                })
    except Exception:
        pass

    # Summary from insider_purchases
    summary = {}
    try:
        ip = t.insider_purchases
        if ip is not None and not ip.empty:
            for _, row in ip.iterrows():
                label = str(row.get("Insider Purchases Last 6m", "")).strip()
                shares = row.get("Shares")
                if label == "Purchases":
                    summary["total_buys"] = int(shares) if pd.notna(shares) else 0
                elif label == "Sales":
                    summary["total_sells"] = int(shares) if pd.notna(shares) else 0
                elif label == "Net Shares Purchased (Sold)":
                    summary["net_shares"] = int(shares) if pd.notna(shares) else 0
                elif label == "% Net Shares Purchased (Sold)":
                    summary["net_pct"] = float(shares) if pd.notna(shares) else 0
    except Exception:
        pass

    # Net sentiment
    net = summary.get("net_shares", 0)
    if net > 0:
        sentiment = "NET BUYING"
    elif net < 0:
        sentiment = "NET SELLING"
    else:
        sentiment = "NEUTRAL"

    return {
        "ticker": ticker,
        "net_sentiment": sentiment,
        "transactions": transactions,
        "summary": summary,
    }


def economic_calendar() -> dict:
    """Get upcoming economic events."""
    try:
        cal = yf.Calendars()
        df = cal.economic_events_calendar
    except Exception:
        return {"events": [], "error": "Could not fetch economic calendar"}

    if df is None or df.empty:
        return {"events": [], "error": "No economic events data"}

    events = []
    for event_name, row in df.iterrows():
        event_time = row.get("Event Time")
        time_str = ""
        if event_time is not None:
            try:
                if hasattr(event_time, "strftime"):
                    time_str = event_time.strftime("%Y-%m-%d %H:%M")
                else:
                    time_str = str(event_time)[:16]
            except Exception:
                time_str = str(event_time)[:16]

        events.append({
            "event": str(event_name),
            "region": str(row.get("Region", "")),
            "date": time_str,
            "for_period": str(row.get("For", "")),
            "actual": str(row.get("Actual", "")) if pd.notna(row.get("Actual")) else "",
            "expected": str(row.get("Expected", "")) if pd.notna(row.get("Expected")) else "",
            "last": str(row.get("Last", "")) if pd.notna(row.get("Last")) else "",
        })

    # Filter to US events primarily, show all if few
    us_events = [e for e in events if e["region"] == "US"]
    if len(us_events) >= 5:
        display_events = us_events[:20]
    else:
        display_events = events[:20]

    return {
        "total": len(display_events),
        "events": display_events,
    }


def _safe_float(val) -> float:
    """Safely convert to float."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
