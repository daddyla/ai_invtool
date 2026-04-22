"""Execution planning — trade sequencing, wash sale, dividends."""

from datetime import datetime, timedelta


def generate_execution_plan(sells: list, buys: list, start_date=None) -> dict:
    """Generate phased execution plan."""
    start = start_date or datetime.now().date()

    phases = [
        {
            "phase": 1,
            "name": "Sell Losers & Harvest Tax Losses",
            "date": str(start),
            "actions": [
                f"SELL {s['shares']} {s['ticker']} @ market (limit: ${s.get('price', 0):.2f})"
                for s in sells
            ],
            "notes": "Trade 10:00-11:30 AM ET for best fills. Use LIMIT orders.",
        },
        {
            "phase": 2,
            "name": "Buy Income ETFs (before ex-div dates)",
            "date": str(start + timedelta(days=1)),
            "actions": [
                f"BUY {b['ticker']} — allocate ${b.get('amount', 0):.0f}"
                for b in buys if b.get("type") == "income"
            ],
            "notes": "Settlement is T+1. Own stock BEFORE ex-dividend date.",
        },
        {
            "phase": 3,
            "name": "Buy Growth Positions",
            "date": str(start + timedelta(days=7)),
            "actions": [
                f"BUY {b['ticker']} — allocate ${b.get('amount', 0):.0f}"
                for b in buys if b.get("type") == "growth"
            ],
            "notes": "Wait for post-earnings volatility to settle.",
        },
    ]

    return {
        "start_date": str(start),
        "phases": phases,
        "total_sell_value": sum(s.get("value", 0) for s in sells),
        "total_buy_value": sum(b.get("amount", 0) for b in buys),
    }


def wash_sale_calendar(sell_dates: dict) -> list:
    """Given {ticker: sell_date}, compute wash sale end dates."""
    calendar = []
    for ticker, date_str in sell_dates.items():
        sell_date = datetime.strptime(date_str, "%Y-%m-%d").date() if isinstance(date_str, str) else date_str
        end_date = sell_date + timedelta(days=30)
        calendar.append({
            "ticker": ticker,
            "sell_date": str(sell_date),
            "blackout_ends": str(end_date),
            "days_remaining": max(0, (end_date - datetime.now().date()).days),
        })
    return calendar


def dividend_calendar(tickers: list, data_provider) -> list:
    """Get upcoming ex-dividend dates from yfinance."""
    calendar = []
    for ticker in tickers:
        try:
            info = data_provider.get_info(ticker)
            ex_date = info.get("exDividendDate")
            div_rate = info.get("dividendRate", 0) or 0
            div_yield = info.get("dividendYield", 0) or 0
            if div_rate > 0:
                calendar.append({
                    "ticker": ticker,
                    "dividend_rate": div_rate,
                    "yield": div_yield,
                    "ex_date": str(ex_date) if ex_date else "N/A",
                })
        except Exception:
            pass
    return calendar
