"""Menu 1: Technical Analysis."""
from invtool.cli.common import ask_ticker
from invtool.ui.display import (
    console,
    print_stock_summary,
    print_technicals_table,
    show_chart_path,
)
from invtool.ui.prompt import confirm


def run(data):
    ticker = ask_ticker()
    console.print(f"\n[dim]Analyzing {ticker}...[/]")

    from invtool.analysis.technical import full_technical_analysis
    t = full_technical_analysis(ticker, data)
    if "error" in t:
        console.print(f"[red]{t['error']}[/]")
        return

    info = data.get_info(ticker)
    print_stock_summary(ticker, t["current_price"], info)
    print_technicals_table(t)

    if confirm("Generate chart?", default=True):
        from invtool.ui.charts import chart_technical
        path = chart_technical(t)
        show_chart_path(path)
