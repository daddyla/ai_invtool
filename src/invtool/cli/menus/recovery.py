"""Menu 5: Recovery Strategies."""
from rich import box
from rich.table import Table

from invtool.ui.display import console, show_chart_path
from invtool.ui.prompt import select, text


def run(data):
    choice = select("Recovery:", [
        ("Tax-Loss Harvest Candidates", "tlh"),
        ("Wheel Strategy (specific ticker)", "wheel"),
        ("Recovery Timeline", "timeline"),
        ("Back", "back"),
    ])

    if choice == "back" or choice is None:
        return

    if choice == "tlh":
        from invtool.analysis.portfolio import Portfolio
        pf = Portfolio(data)
        console.print("[dim]Scanning for tax-loss candidates...[/]")
        candidates = pf.tax_loss_candidates()
        if not candidates:
            console.print("[green]No positions with unrealized losses.[/]")
            return

        table = Table(title="Tax-Loss Harvest Candidates", box=box.ROUNDED)
        table.add_column("Ticker", style="cyan")
        table.add_column("Shares", justify="right")
        table.add_column("Loss", justify="right", style="red")
        table.add_column("Tax Benefit", justify="right", style="green")
        total_loss = 0
        total_benefit = 0
        for c in candidates:
            table.add_row(c["ticker"], str(c["shares"]), f"${c['loss']:,.0f}", f"${c['tax_benefit']:,.0f}")
            total_loss += c["loss"]
            total_benefit += c["tax_benefit"]
        table.add_section()
        table.add_row("[bold]TOTAL[/]", "", f"[bold red]${total_loss:,.0f}[/]", f"[bold green]${total_benefit:,.0f}[/]")
        console.print(table)

    elif choice == "wheel":
        from invtool.cli.menus import options
        options.run(data)

    elif choice == "timeline":
        from invtool.analysis.portfolio import Portfolio
        from invtool.ui.charts import chart_recovery_timeline
        pf = Portfolio(data)
        s = pf.summary()
        if s["total_pnl"] >= 0:
            console.print("[green]Portfolio is profitable! No recovery needed.[/]")
            return
        monthly = float(text("Estimated monthly income ($):", default="50") or 50)
        path = chart_recovery_timeline(s["total_pnl"], monthly)
        months = abs(s["total_pnl"]) / monthly if monthly > 0 else float("inf")
        console.print(f"  Total loss: [red]${s['total_pnl']:,.0f}[/]")
        console.print(f"  Monthly income: [green]${monthly:,.0f}[/]")
        console.print(f"  Recovery: [bold]~{months:.0f} months[/]")
        show_chart_path(path)
