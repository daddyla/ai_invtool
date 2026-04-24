"""Menu 10: Market Intelligence (composite — 6 sub-handlers)."""
from invtool.cli.common import ask_ticker
from invtool.ui.display import console, show_chart_path
from invtool.ui.prompt import confirm, select


def run(data):
    choice = select("Market Intelligence:", [
        ("1. Earnings Calendar", "earnings_cal"),
        ("2. Market Movers", "movers"),
        ("3. Sector Performance", "sectors"),
        ("4. Analyst Ratings", "analyst"),
        ("5. Insider Activity", "insider"),
        ("6. Economic Calendar", "economic"),
        ("Back", "back"),
    ])

    if choice == "back" or choice is None:
        return

    dispatch = {
        "earnings_cal": _earnings_cal,
        "movers": _movers,
        "sectors": _sectors,
        "analyst": _analyst,
        "insider": _insider,
        "economic": _economic,
    }
    handler = dispatch.get(choice)
    if handler:
        handler(data)


def _earnings_cal(data):
    period = select("Show earnings for:", [
        ("Today", "today"),
        ("Tomorrow", "tomorrow"),
        ("This Week", "this_week"),
        ("Next Week", "next_week"),
    ])
    if period is None:
        return
    console.print("[dim]Fetching earnings calendar...[/]")
    from invtool.market.intel import earnings_calendar
    from invtool.ui.display import print_earnings_calendar
    result = earnings_calendar(period)
    print_earnings_calendar(result)


def _movers(data):
    category = select("Show:", [
        ("Top Gainers", "day_gainers"),
        ("Top Losers", "day_losers"),
        ("Most Active", "most_actives"),
    ])
    if category is None:
        return
    console.print("[dim]Fetching market movers...[/]")
    from invtool.market.intel import market_movers
    from invtool.ui.display import print_market_movers
    result = market_movers(category)
    print_market_movers(result)


def _sectors(data):
    console.print("[dim]Fetching sector performance...[/]")
    from invtool.market.intel import sector_performance
    from invtool.ui.display import print_sector_performance
    result = sector_performance()
    print_sector_performance(result)
    if confirm("Generate chart?", default=True):
        from invtool.ui.charts import chart_sector_performance
        path = chart_sector_performance(result)
        if path:
            show_chart_path(path)


def _analyst(data):
    ticker = ask_ticker()
    console.print(f"[dim]Fetching {ticker} analyst ratings...[/]")
    from invtool.market.intel import analyst_ratings
    from invtool.ui.display import print_analyst_ratings
    result = analyst_ratings(ticker)
    print_analyst_ratings(result)


def _insider(data):
    ticker = ask_ticker()
    console.print(f"[dim]Fetching {ticker} insider activity...[/]")
    from invtool.market.intel import insider_activity
    from invtool.ui.display import print_insider_table
    result = insider_activity(ticker)
    print_insider_table(result)


def _economic(data):
    console.print("[dim]Fetching economic calendar...[/]")
    from invtool.market.intel import economic_calendar
    from invtool.ui.display import print_economic_calendar
    result = economic_calendar()
    print_economic_calendar(result)
