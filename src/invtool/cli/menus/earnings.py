"""Menu 3: Earnings Analysis."""
from rich import box
from rich.panel import Panel
from rich.table import Table

from invtool.cli.common import ask_ticker
from invtool.ui.display import console, print_earnings_table, show_chart_path
from invtool.ui.prompt import confirm


def run(data):
    ticker = ask_ticker("NVDA")
    console.print(f"\n[dim]Analyzing {ticker} earnings history...[/]")

    from invtool.analysis.earnings import full_earnings_analysis
    result = full_earnings_analysis(ticker, data)
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return

    print_earnings_table(result["earnings_df"])

    stn = result["sell_the_news"]
    console.print(Panel(
        f"[bold]Sell-the-News Rate:[/] {stn['sell_the_news_rate']:.0%}\n"
        f"Beats then dropped: {stn.get('beats_then_dropped', 0)}/{stn.get('total_beats', 0)}\n"
        f"Avg post-earnings 1d move: {stn.get('avg_post_1d', 0):+.1%}\n"
        f"Recent 6Q drops: {stn.get('recent_6q_drops', 0)}/6",
        title="Sell-the-News Pattern",
        border_style="yellow",
    ))

    fc = result["forecast"]
    if "scenarios" in fc:
        table = Table(title="Earnings Forecast", box=box.ROUNDED)
        table.add_column("Scenario", style="cyan")
        table.add_column("Probability", justify="right")
        table.add_column("Expected Move", justify="right")
        table.add_column("Description")
        for s in fc["scenarios"]:
            table.add_row(s["name"], f"{s['probability']}%", s["expected_move"], s["description"])
        console.print(table)

    if confirm("Generate chart?", default=True):
        from invtool.ui.charts import chart_earnings_behavior
        path = chart_earnings_behavior(result["earnings_df"], ticker)
        show_chart_path(path)
