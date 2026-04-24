"""Menu 6: Execution Planning."""
from rich import box
from rich.table import Table

from invtool.ui.display import console
from invtool.ui.prompt import select, text


def run(data):
    choice = select("Execution:", [
        ("Wash Sale Calendar", "wash"),
        ("Dividend Calendar", "div"),
        ("Back", "back"),
    ])

    if choice == "back" or choice is None:
        return

    if choice == "wash":
        from invtool.analysis.execution import wash_sale_calendar
        sells = text("Tickers sold (comma-separated):", default="FIG,DOCS,TMF,BLSH")
        date = text("Sell date (YYYY-MM-DD):", default="2026-02-20")
        tickers = [t.strip().upper() for t in sells.split(",")]
        cal = wash_sale_calendar({t: date for t in tickers})

        table = Table(title="Wash Sale Calendar", box=box.ROUNDED)
        table.add_column("Ticker", style="cyan")
        table.add_column("Sell Date")
        table.add_column("Blackout Ends")
        table.add_column("Days Left", justify="right")
        for c in cal:
            color = "red" if c["days_remaining"] > 0 else "green"
            table.add_row(c["ticker"], c["sell_date"], c["blackout_ends"], f"[{color}]{c['days_remaining']}[/]")
        console.print(table)

    elif choice == "div":
        from invtool.analysis.execution import dividend_calendar
        tickers_input = text("Tickers to check (comma-separated):", default="JEPQ,JEPI,SPHD,SCHD,SVOL")
        tickers = [t.strip().upper() for t in tickers_input.split(",")]
        console.print("[dim]Fetching dividend data...[/]")
        cal = dividend_calendar(tickers, data)

        if not cal:
            console.print("[yellow]No dividend data found.[/]")
            return

        table = Table(title="Dividend Calendar", box=box.ROUNDED)
        table.add_column("Ticker", style="cyan")
        table.add_column("Div Rate", justify="right")
        table.add_column("Yield", justify="right", style="green")
        table.add_column("Ex-Div Date")
        for c in cal:
            table.add_row(
                c["ticker"],
                f"${c['dividend_rate']:.2f}",
                f"{c['yield']:.1%}" if c["yield"] else "N/A",
                c["ex_date"],
            )
        console.print(table)
