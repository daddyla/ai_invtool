"""Menu 8: Settings (portfolio holdings + cache)."""
from rich import box
from rich.table import Table

from invtool.ui.display import console
from invtool.ui.prompt import select, text


def run(data):
    choice = select("Settings:", [
        ("View Portfolio Holdings", "view"),
        ("Add Holding", "add"),
        ("Remove Holding", "remove"),
        ("Clear Data Cache", "cache"),
        ("Back", "back"),
    ])

    if choice == "back" or choice is None:
        return

    if choice == "view":
        from invtool.config import load_portfolio
        holdings = load_portfolio()
        table = Table(title="Portfolio Holdings", box=box.ROUNDED)
        table.add_column("Ticker", style="cyan")
        table.add_column("Shares", justify="right")
        table.add_column("Cost Basis", justify="right")
        table.add_column("Type")
        for h in holdings:
            table.add_row(h["ticker"], str(h["shares"]), f"${h['cost']:.2f}", h.get("type", ""))
        console.print(table)

    elif choice == "add":
        ticker = text("Ticker:").upper().strip()
        shares = int(text("Shares:") or 0)
        cost = float(text("Cost basis per share:") or 0)
        htype = text("Type (e.g. ETF-Income):", default="")
        from invtool.analysis.portfolio import Portfolio
        pf = Portfolio(data)
        pf.add_holding(ticker, shares, cost, htype)
        console.print(f"[green]Added {shares} {ticker} @ ${cost:.2f}[/]")

    elif choice == "remove":
        from invtool.analysis.portfolio import Portfolio
        from invtool.config import load_portfolio
        holdings = load_portfolio()
        tickers = [(h["ticker"], h["ticker"]) for h in holdings]
        ticker = select("Remove which ticker?", tickers)
        if ticker:
            pf = Portfolio(data)
            pf.remove_holding(ticker)
            console.print(f"[yellow]Removed {ticker}[/]")

    elif choice == "cache":
        data.clear_cache()
        console.print("[green]Cache cleared.[/]")
