"""Dashboard shell — banner, main menu, and dispatch to menu modules."""
import warnings

warnings.filterwarnings("ignore")

from invtool.cli.menus import (
    ai,
    analytics,
    deep_research,
    earnings,
    execution,
    market_intel,
    options,
    portfolio,
    recovery,
    settings,
    technical,
    web_news,
)
from invtool.config.data_provider import DataProvider
from invtool.ui.display import console, print_header
from invtool.ui.prompt import select

BANNER = r"""[bold blue]
 ___                     _                        _
|_ _|_ ___   _____  ___| |_ _ __ ___   ___ _ __ | |_
 | || '_ \ / / _ \/ __| __| '_ ` _ \ / _ \ '_ \| __|
 | || | | V /  __/\__ \ |_| | | | | |  __/ | | | |_
|___|_| |_\_/ \___||___/\__|_| |_| |_|\___|_| |_|\__|
[/]  [dim]Dashboard v1.0 — Rich CLI + AI Agent[/]
"""

MENU_OPTIONS = [
    ("1. Technical Analysis", "technical"),
    ("2. Options Screening", "options"),
    ("3. Earnings Analysis", "earnings"),
    ("4. Portfolio Tracker", "portfolio"),
    ("5. Recovery Strategies", "recovery"),
    ("6. Execution Planning", "execution"),
    ("7. Ask AI", "ai"),
    ("8. Settings", "settings"),
    ("9. AI Analytics", "analytics"),
    ("10. Market Intelligence", "market_intel"),
    ("11. Deep Research", "deep_research"),
    ("12. Web News", "web_news"),
    ("Quit", "quit"),
]

DISPATCH = {
    "technical": technical.run,
    "options": options.run,
    "earnings": earnings.run,
    "portfolio": portfolio.run,
    "recovery": recovery.run,
    "execution": execution.run,
    "ai": ai.run,
    "settings": settings.run,
    "analytics": analytics.run,
    "market_intel": market_intel.run,
    "deep_research": deep_research.run,
    "web_news": web_news.run,
}


class InvestmentDashboard:
    def __init__(self):
        self.data = DataProvider()

    def run(self):
        console.print(BANNER)
        print_header("Investment Dashboard", "Type a number to begin")

        while True:
            try:
                choice = select("What would you like to do?", MENU_OPTIONS)
                if choice is None or choice == "quit":
                    console.print("[dim]Goodbye![/]")
                    break
                handler = DISPATCH.get(choice)
                if handler:
                    handler(self.data)
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'Quit' to exit.[/]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")


def main():
    app = InvestmentDashboard()
    app.run()


if __name__ == "__main__":
    main()
