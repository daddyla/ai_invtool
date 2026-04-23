"""Main application — menu loop and module orchestration."""

import warnings
warnings.filterwarnings("ignore")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from invtool.config.data_provider import DataProvider
from invtool.display import (
    console, print_header, print_stock_summary, print_technicals_table,
    print_options_table, print_portfolio_table, print_earnings_table,
    show_chart_path,
)
from invtool.prompt import select, text, confirm

BANNER = """[bold blue]
 ___                     _                        _
|_ _|_ ___   _____  ___| |_ _ __ ___   ___ _ __ | |_
 | || '_ \\ / / _ \\/ __| __| '_ ` _ \\ / _ \\ '_ \\| __|
 | || | | V /  __/\\__ \\ |_| | | | | |  __/ | | | |_
|___|_| |_\\_/ \\___||___/\\__|_| |_| |_|\\___|_| |_|\\__|
[/]  [dim]Dashboard v1.0 — Rich CLI + AI Agent[/]
"""


class InvestmentDashboard:
    def __init__(self):
        self.data = DataProvider()

    def run(self):
        console.print(BANNER)
        print_header("Investment Dashboard", "Type a number to begin")

        while True:
            try:
                choice = self._main_menu()
                if choice is None or choice == "quit":
                    console.print("[dim]Goodbye![/]")
                    break
                self._dispatch(choice)
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'Quit' to exit.[/]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")

    def _main_menu(self):
        return select("What would you like to do?", [
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
        ])

    def _dispatch(self, choice):
        handlers = {
            "technical": self._technical_menu,
            "options": self._options_menu,
            "earnings": self._earnings_menu,
            "portfolio": self._portfolio_menu,
            "recovery": self._recovery_menu,
            "execution": self._execution_menu,
            "ai": self._ai_menu,
            "settings": self._settings_menu,
            "analytics": self._analytics_menu,
            "market_intel": self._market_intel_menu,
            "deep_research": self._deep_research_menu,
            "web_news": self._web_news_menu,
        }
        handler = handlers.get(choice)
        if handler:
            handler()

    def _ask_ticker(self, default="NVDA"):
        result = text("Enter stock ticker:", default=default)
        return result.upper().strip() if result else default

    # ── 1. Technical Analysis ──
    def _technical_menu(self):
        ticker = self._ask_ticker()
        console.print(f"\n[dim]Analyzing {ticker}...[/]")

        from invtool.analysis.technical import full_technical_analysis
        t = full_technical_analysis(ticker, self.data)
        if "error" in t:
            console.print(f"[red]{t['error']}[/]")
            return

        info = self.data.get_info(ticker)
        print_stock_summary(ticker, t["current_price"], info)
        print_technicals_table(t)

        if confirm("Generate chart?", default=True):
            from invtool.charts import chart_technical
            path = chart_technical(t)
            show_chart_path(path)

    # ── 2. Options Screening ──
    def _options_menu(self):
        ticker = self._ask_ticker()
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
            df = screen_puts(ticker, self.data)
            print_options_table(df, f"{ticker} — Sell Put Candidates")
            if not df.empty and confirm("Generate chart?", default=True):
                from invtool.analysis.technical import full_technical_analysis
                from invtool.charts import chart_technical
                t = full_technical_analysis(ticker, self.data)
                if "error" not in t:
                    path = chart_technical(t, df)
                    show_chart_path(path)

        elif strategy == "call":
            from invtool.analysis.options import screen_calls
            cost = text("Cost basis per share (0 if none):", default="0")
            df = screen_calls(ticker, self.data, cost_basis=float(cost or 0))
            print_options_table(df, f"{ticker} — Covered Call Candidates")

        elif strategy == "wheel":
            from invtool.analysis.options import wheel_analysis
            shares = int(text("Shares owned:", default="0") or 0)
            cost = float(text("Cost basis/share:", default="0") or 0)
            result = wheel_analysis(ticker, self.data, shares, cost)

            console.print(Panel(
                f"[bold]Price:[/] ${result['price']:.2f}  |  "
                f"[bold]Can Wheel:[/] {'Yes' if result['can_wheel'] else 'No (need 100 shares)'}",
                title=f"{ticker} Wheel Analysis",
                border_style="blue",
            ))

            if result.get("best_puts"):
                from invtool.analysis.options import screen_puts
                df = screen_puts(ticker, self.data)
                print_options_table(df, f"{ticker} — Best Puts to Sell")

            if result.get("best_calls") and result["can_wheel"]:
                from invtool.analysis.options import screen_calls
                df = screen_calls(ticker, self.data, cost)
                print_options_table(df, f"{ticker} — Best Calls to Sell")

            if "put_monthly_est" in result:
                console.print(f"  Estimated monthly put income: [green]${result['put_monthly_est']:.0f}[/]")
            if "call_monthly_est" in result:
                console.print(f"  Estimated monthly call income: [green]${result['call_monthly_est']:.0f}[/]")

    # ── 3. Earnings Analysis ──
    def _earnings_menu(self):
        ticker = self._ask_ticker("NVDA")
        console.print(f"\n[dim]Analyzing {ticker} earnings history...[/]")

        from invtool.analysis.earnings import full_earnings_analysis
        result = full_earnings_analysis(ticker, self.data)
        if "error" in result:
            console.print(f"[red]{result['error']}[/]")
            return

        print_earnings_table(result["earnings_df"])

        # Sell the news stats
        stn = result["sell_the_news"]
        console.print(Panel(
            f"[bold]Sell-the-News Rate:[/] {stn['sell_the_news_rate']:.0%}\n"
            f"Beats then dropped: {stn.get('beats_then_dropped', 0)}/{stn.get('total_beats', 0)}\n"
            f"Avg post-earnings 1d move: {stn.get('avg_post_1d', 0):+.1%}\n"
            f"Recent 6Q drops: {stn.get('recent_6q_drops', 0)}/6",
            title="Sell-the-News Pattern",
            border_style="yellow",
        ))

        # Forecast
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
            from invtool.charts import chart_earnings_behavior
            path = chart_earnings_behavior(result["earnings_df"], ticker)
            show_chart_path(path)

    # ── 4. Portfolio Tracker ──
    def _portfolio_menu(self):
        choice = select("Portfolio:", [
            ("View Current P&L", "pnl"),
            ("Per-Position Strategies", "strategies"),
            ("Rebalance Plans", "rebalance"),
            ("Back", "back"),
        ])

        if choice == "back" or choice is None:
            return

        from invtool.analysis.portfolio import Portfolio
        pf = Portfolio(self.data)

        if choice == "pnl":
            console.print("[dim]Fetching live prices...[/]")
            s = pf.summary()
            print_portfolio_table(s["positions"])

            if confirm("Generate charts?", default=True):
                from invtool.charts import chart_portfolio_pnl, chart_portfolio_allocation
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

    # ── 5. Recovery Strategies ──
    def _recovery_menu(self):
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
            pf = Portfolio(self.data)
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
            self._options_menu()

        elif choice == "timeline":
            from invtool.analysis.portfolio import Portfolio
            from invtool.charts import chart_recovery_timeline
            pf = Portfolio(self.data)
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

    # ── 6. Execution Planning ──
    def _execution_menu(self):
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
            cal = dividend_calendar(tickers, self.data)

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

    # ── 7. AI Agent ──
    def _ai_menu(self):
        from invtool.agent import ai_chat_loop
        ai_chat_loop(self.data)

    # ── 8. Settings ──
    def _settings_menu(self):
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
            pf = Portfolio(self.data)
            pf.add_holding(ticker, shares, cost, htype)
            console.print(f"[green]Added {shares} {ticker} @ ${cost:.2f}[/]")

        elif choice == "remove":
            from invtool.config import load_portfolio
            holdings = load_portfolio()
            tickers = [(h["ticker"], h["ticker"]) for h in holdings]
            ticker = select("Remove which ticker?", tickers)
            if ticker:
                from invtool.analysis.portfolio import Portfolio
                pf = Portfolio(self.data)
                pf.remove_holding(ticker)
                console.print(f"[yellow]Removed {ticker}[/]")

        elif choice == "cache":
            self.data.clear_cache()
            console.print("[green]Cache cleared.[/]")


    # ── 9. AI Analytics ──
    def _analytics_menu(self):
        choice = select("AI Analytics:", [
            ("1. Sentiment Analysis", "sentiment"),
            ("2. Price Forecast", "forecast"),
            ("3. Market Regime", "regime"),
            ("4. Anomaly Detection", "anomaly"),
            ("5. Monte Carlo Risk", "montecarlo"),
            ("6. Earnings Prediction", "earnings_ml"),
            ("7. Portfolio Optimizer", "optimizer"),
            ("8. Correlation & Clusters", "correlation"),
            ("Back", "back"),
        ])

        if choice == "back" or choice is None:
            return

        dispatch = {
            "sentiment": self._sentiment,
            "forecast": self._forecast,
            "regime": self._regime,
            "anomaly": self._anomaly,
            "montecarlo": self._montecarlo,
            "earnings_ml": self._earnings_ml,
            "optimizer": self._optimizer,
            "correlation": self._correlation,
        }
        handler = dispatch.get(choice)
        if handler:
            handler()

    def _sentiment(self):
        ticker = self._ask_ticker()
        console.print(f"\n[dim]Analyzing {ticker} news sentiment...[/]")
        from invtool.ai.sentiment import analyze_sentiment
        from invtool.display import print_sentiment_table
        result = analyze_sentiment(ticker, self.data)
        print_sentiment_table(result)
        if result.get("headlines") and confirm("Generate chart?", default=True):
            from invtool.charts import chart_sentiment
            path = chart_sentiment(result)
            if path:
                show_chart_path(path)

    def _forecast(self):
        ticker = self._ask_ticker()
        console.print(f"\n[dim]Forecasting {ticker} price...[/]")
        from invtool.ai.forecast import price_forecast
        from invtool.display import print_forecast_table
        result = price_forecast(ticker, self.data)
        if "error" in result:
            console.print(f"[red]{result['error']}[/]")
            return
        print_forecast_table(result)
        if confirm("Generate chart?", default=True):
            from invtool.charts import chart_forecast
            path = chart_forecast(result)
            show_chart_path(path)

    def _regime(self):
        ticker = self._ask_ticker()
        console.print(f"\n[dim]Detecting {ticker} market regime...[/]")
        from invtool.ai.regime import detect_regime
        from invtool.display import print_regime_panel
        result = detect_regime(ticker, self.data)
        if "error" in result:
            console.print(f"[red]{result['error']}[/]")
            return
        print_regime_panel(result)

    def _anomaly(self):
        choice = select("Anomaly Detection:", [
            ("Single Ticker", "single"),
            ("Scan Portfolio", "portfolio"),
            ("Back", "back"),
        ])
        if choice == "back" or choice is None:
            return

        from invtool.display import print_anomaly_table

        if choice == "single":
            ticker = self._ask_ticker()
            console.print(f"\n[dim]Scanning {ticker} for anomalies...[/]")
            from invtool.ai.anomaly import detect_anomalies
            result = detect_anomalies(ticker, self.data)
            print_anomaly_table(result)
            if result.get("anomalies") and confirm("Generate chart?", default=True):
                from invtool.charts import chart_anomaly
                path = chart_anomaly(result)
                if path:
                    show_chart_path(path)
        else:
            from invtool.ai.anomaly import scan_portfolio_anomalies
            from invtool.config import load_portfolio
            console.print("[dim]Scanning all holdings for anomalies...[/]")
            holdings = load_portfolio()
            results = scan_portfolio_anomalies(self.data, holdings)
            if not results:
                console.print("[green]No anomalies detected across portfolio.[/]")
            else:
                for r in results:
                    console.print(f"\n[bold red]{r['ticker']}: {r['alert_count']} anomalies[/]")
                    for a in r["anomalies"]:
                        console.print(f"  [{a['date']}] {a['description']}")

    def _montecarlo(self):
        console.print("[dim]Running Monte Carlo simulation (10,000 paths)...[/]")
        from invtool.ai.montecarlo import monte_carlo_simulation
        from invtool.display import print_montecarlo_table
        result = monte_carlo_simulation(self.data)
        if "error" in result:
            console.print(f"[red]{result['error']}[/]")
            return
        print_montecarlo_table(result)
        if confirm("Generate chart?", default=True):
            from invtool.charts import chart_montecarlo
            # Show 30-day horizon by default (index 1 if exists)
            idx = 1 if len(result["horizons"]) > 1 else 0
            path = chart_montecarlo(result, idx)
            show_chart_path(path)

    def _earnings_ml(self):
        ticker = self._ask_ticker("NVDA")
        console.print(f"\n[dim]Predicting {ticker} earnings outcome...[/]")
        from invtool.ai.earnings_ml import predict_earnings
        from invtool.display import print_earnings_prediction
        result = predict_earnings(ticker, self.data)
        if "error" in result:
            console.print(f"[red]{result['error']}[/]")
            return
        print_earnings_prediction(result)

    def _optimizer(self):
        default_tickers = "NVDA,AAPL,MSFT,GOOGL,AMZN"
        tickers_input = text("Tickers to optimize (comma-separated):", default=default_tickers)
        tickers = [t.strip().upper() for t in tickers_input.split(",")]

        target = select("Optimization target:", [
            ("Max Sharpe Ratio (Recommended)", "sharpe"),
            ("Minimum Volatility", "min_vol"),
            ("Back", "back"),
        ])
        if target == "back" or target is None:
            return

        console.print(f"[dim]Optimizing portfolio of {len(tickers)} assets...[/]")
        from invtool.ai.optimizer import optimize_portfolio
        from invtool.display import print_optimizer_table
        result = optimize_portfolio(self.data, tickers, target)
        if "error" in result:
            console.print(f"[red]{result['error']}[/]")
            return
        print_optimizer_table(result)
        if confirm("Generate chart?", default=True):
            from invtool.charts import chart_efficient_frontier
            path = chart_efficient_frontier(result)
            show_chart_path(path)

    def _correlation(self):
        from invtool.config import load_portfolio
        holdings = load_portfolio()
        default_tickers = ",".join(h["ticker"] for h in holdings)
        tickers_input = text("Tickers to analyze (comma-separated):", default=default_tickers)
        tickers = [t.strip().upper() for t in tickers_input.split(",")]

        console.print(f"[dim]Analyzing correlations for {len(tickers)} tickers...[/]")
        from invtool.ai.correlation import analyze_correlations
        from invtool.display import print_correlation_table
        result = analyze_correlations(self.data, tickers)
        if "error" in result:
            console.print(f"[red]{result['error']}[/]")
            return
        print_correlation_table(result)
        if confirm("Generate chart?", default=True):
            from invtool.charts import chart_correlation
            path = chart_correlation(result)
            show_chart_path(path)


    # ── 10. Market Intelligence ──
    def _market_intel_menu(self):
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
            "earnings_cal": self._earnings_cal,
            "movers": self._movers,
            "sectors": self._sectors,
            "analyst": self._analyst,
            "insider": self._insider,
            "economic": self._economic,
        }
        handler = dispatch.get(choice)
        if handler:
            handler()

    def _earnings_cal(self):
        period = select("Show earnings for:", [
            ("Today", "today"),
            ("Tomorrow", "tomorrow"),
            ("This Week", "this_week"),
            ("Next Week", "next_week"),
        ])
        if period is None:
            return
        console.print("[dim]Fetching earnings calendar...[/]")
        from invtool.market_intel import earnings_calendar
        from invtool.display import print_earnings_calendar
        result = earnings_calendar(period)
        print_earnings_calendar(result)

    def _movers(self):
        category = select("Show:", [
            ("Top Gainers", "day_gainers"),
            ("Top Losers", "day_losers"),
            ("Most Active", "most_actives"),
        ])
        if category is None:
            return
        console.print("[dim]Fetching market movers...[/]")
        from invtool.market_intel import market_movers
        from invtool.display import print_market_movers
        result = market_movers(category)
        print_market_movers(result)

    def _sectors(self):
        console.print("[dim]Fetching sector performance...[/]")
        from invtool.market_intel import sector_performance
        from invtool.display import print_sector_performance
        result = sector_performance()
        print_sector_performance(result)
        if confirm("Generate chart?", default=True):
            from invtool.charts import chart_sector_performance
            path = chart_sector_performance(result)
            if path:
                show_chart_path(path)

    def _analyst(self):
        ticker = self._ask_ticker()
        console.print(f"[dim]Fetching {ticker} analyst ratings...[/]")
        from invtool.market_intel import analyst_ratings
        from invtool.display import print_analyst_ratings
        result = analyst_ratings(ticker)
        print_analyst_ratings(result)

    def _insider(self):
        ticker = self._ask_ticker()
        console.print(f"[dim]Fetching {ticker} insider activity...[/]")
        from invtool.market_intel import insider_activity
        from invtool.display import print_insider_table
        result = insider_activity(ticker)
        print_insider_table(result)

    def _economic(self):
        console.print("[dim]Fetching economic calendar...[/]")
        from invtool.market_intel import economic_calendar
        from invtool.display import print_economic_calendar
        result = economic_calendar()
        print_economic_calendar(result)

    # ── 11. Deep Research ──
    def _deep_research_menu(self):
        from invtool.deep_research import deep_research_menu
        deep_research_menu(self.data)

    # ── 12. Web News ──
    def _web_news_menu(self):
        from invtool.prompt import select, text as prompt_text
        from invtool.webcrawler import (
            crawl_market_news, ticker_news_crawl,
            search_financial_news, fetch_article_content,
        )
        from invtool.display import print_news_headlines, print_article_content

        choice = select("Web News", [
            ("Market Headlines (Reuters, CNBC, MarketWatch, Yahoo, Benzinga)", "headlines"),
            ("Stock News (by ticker)", "ticker"),
            ("Topic Search (e.g. 'Fed rate cut', 'AI stocks')", "search"),
            ("Read Full Article (paste URL)", "article"),
            ("Back", "back"),
        ])
        if not choice or choice == "back":
            return

        if choice == "headlines":
            console.print("[dim]Crawling news sources...[/]")
            result = crawl_market_news()
            print_news_headlines(result)

        elif choice == "ticker":
            ticker = self._ask_ticker()
            console.print(f"[dim]Fetching news for {ticker}...[/]")
            result = ticker_news_crawl(ticker)
            print_news_headlines(result)

        elif choice == "search":
            query = prompt_text("Search query:", default="Federal Reserve interest rates")
            if query:
                console.print(f"[dim]Searching: {query}...[/]")
                result = search_financial_news(query)
                print_news_headlines(result)

        elif choice == "article":
            url = prompt_text("Article URL:")
            if url and url.startswith("http"):
                console.print("[dim]Fetching article...[/]")
                result = fetch_article_content(url)
                print_article_content(result)


def main():
    app = InvestmentDashboard()
    app.run()


if __name__ == "__main__":
    main()
