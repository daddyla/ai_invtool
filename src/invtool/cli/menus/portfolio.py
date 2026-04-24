"""Menu 4: Portfolio Tracker."""
from rich import box
from rich.panel import Panel
from rich.table import Table

from invtool.ui.display import console, print_portfolio_table, show_chart_path
from invtool.ui.prompt import confirm, select


def run(data):
    choice = select("Portfolio:", [
        ("View Current P&L", "pnl"),
        ("Per-Position Strategies", "strategies"),
        ("Rebalance Plans", "rebalance"),
        ("Back", "back"),
    ])

    if choice == "back" or choice is None:
        return

    from invtool.analysis.portfolio import Portfolio
    pf = Portfolio(data)

    if choice == "pnl":
        console.print("[dim]Fetching live prices...[/]")
        s = pf.summary()
        print_portfolio_table(s["positions"])

        if confirm("Generate charts?", default=True):
            from invtool.ui.charts import chart_portfolio_allocation, chart_portfolio_pnl
            p1 = chart_portfolio_pnl(s["positions"])
            p2 = chart_portfolio_allocation(s["positions"])
            show_chart_path(p1)
            show_chart_path(p2)

    elif choice == "strategies":
        console.print("[dim]Analyzing positions...[/]")
        results = pf.per_position_strategies()
        for r in results:
            pnl_color = "green" if r["pnl"] >= 0 else "red"
            console.print(Panel(
                f"[bold]{r['ticker']}[/]  {r['shares']} shares @ ${r['cost']:.2f} -> "
                f"${r['price']:.2f}  |  [{pnl_color}]P&L: ${r['pnl']:+,.0f}[/]",
                border_style=pnl_color,
            ))
            for i, s in enumerate(r["strategies"], 1):
                console.print(f"  [{i}] [bold]{s['name']}[/]")
                console.print(f"      {s['action']}")
                if "premium" in s:
                    console.print(f"      Premium: ${s['premium']:.0f}/contract | Ann. yield: {s['ann_yield']:.0%}")
                if "capital_needed" in s:
                    console.print(f"      Capital needed: ${s['capital_needed']:,.0f}")
                if "tax_benefit" in s:
                    console.print(f"      Tax benefit: ~${s['tax_benefit']:,.0f}")
            console.print()

    elif choice == "rebalance":
        plans = pf.rebalance_plans()
        table = Table(title="Rebalance Plans", box=box.ROUNDED)
        table.add_column("Plan", style="cyan")
        table.add_column("Mix")
        table.add_column("Recovery", justify="right")
        table.add_column("Risk", justify="right")
        table.add_column("Growth $", justify="right", style="green")
        table.add_column("Income $", justify="right", style="blue")
        for p in plans:
            table.add_row(
                p["name"], p["mix"], p["recovery"], p["risk"],
                f"${p['growth_allocation']:,.0f}", f"${p['income_allocation']:,.0f}",
            )
        console.print(table)
