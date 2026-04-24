"""Menu 2: Options Screening."""
from rich.panel import Panel

from invtool.cli.common import ask_ticker
from invtool.ui.display import console, print_options_table, show_chart_path
from invtool.ui.prompt import confirm, select, text


def run(data):
    ticker = ask_ticker()
    strategy = select("Strategy:", [
        ("Sell Put (cash-secured)", "put"),
        ("Sell Covered Call", "call"),
        ("Wheel Strategy Analysis", "wheel"),
        ("Back", "back"),
    ])

    if strategy == "back" or strategy is None:
        return

    console.print(f"\n[dim]Screening {ticker} options...[/]")

    if strategy == "put":
        from invtool.analysis.options import screen_puts
        df = screen_puts(ticker, data)
        print_options_table(df, f"{ticker} — Sell Put Candidates")
        if not df.empty and confirm("Generate chart?", default=True):
            from invtool.analysis.technical import full_technical_analysis
            from invtool.ui.charts import chart_technical
            t = full_technical_analysis(ticker, data)
            if "error" not in t:
                path = chart_technical(t, df)
                show_chart_path(path)

    elif strategy == "call":
        from invtool.analysis.options import screen_calls
        cost = text("Cost basis per share (0 if none):", default="0")
        df = screen_calls(ticker, data, cost_basis=float(cost or 0))
        print_options_table(df, f"{ticker} — Covered Call Candidates")

    elif strategy == "wheel":
        from invtool.analysis.options import screen_calls, screen_puts, wheel_analysis
        shares = int(text("Shares owned:", default="0") or 0)
        cost = float(text("Cost basis/share:", default="0") or 0)
        result = wheel_analysis(ticker, data, shares, cost)

        console.print(Panel(
            f"[bold]Price:[/] ${result['price']:.2f}  |  "
            f"[bold]Can Wheel:[/] {'Yes' if result['can_wheel'] else 'No (need 100 shares)'}",
            title=f"{ticker} Wheel Analysis",
            border_style="blue",
        ))

        if result.get("best_puts"):
            df = screen_puts(ticker, data)
            print_options_table(df, f"{ticker} — Best Puts to Sell")

        if result.get("best_calls") and result["can_wheel"]:
            df = screen_calls(ticker, data, cost)
            print_options_table(df, f"{ticker} — Best Calls to Sell")

        if "put_monthly_est" in result:
            console.print(f"  Estimated monthly put income: [green]${result['put_monthly_est']:.0f}[/]")
        if "call_monthly_est" in result:
            console.print(f"  Estimated monthly call income: [green]${result['call_monthly_est']:.0f}[/]")
