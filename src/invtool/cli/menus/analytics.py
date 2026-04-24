"""Menu 9: AI Analytics (composite — 8 sub-handlers)."""
from invtool.cli.common import ask_ticker
from invtool.ui.display import console, show_chart_path
from invtool.ui.prompt import confirm, select, text


def run(data):
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
        "sentiment": _sentiment,
        "forecast": _forecast,
        "regime": _regime,
        "anomaly": _anomaly,
        "montecarlo": _montecarlo,
        "earnings_ml": _earnings_ml,
        "optimizer": _optimizer,
        "correlation": _correlation,
    }
    handler = dispatch.get(choice)
    if handler:
        handler(data)


def _sentiment(data):
    ticker = ask_ticker()
    console.print(f"\n[dim]Analyzing {ticker} news sentiment...[/]")
    from invtool.ai.sentiment import analyze_sentiment
    from invtool.ui.display import print_sentiment_table
    result = analyze_sentiment(ticker, data)
    print_sentiment_table(result)
    if result.get("headlines") and confirm("Generate chart?", default=True):
        from invtool.ui.charts import chart_sentiment
        path = chart_sentiment(result)
        if path:
            show_chart_path(path)


def _forecast(data):
    ticker = ask_ticker()
    console.print(f"\n[dim]Forecasting {ticker} price...[/]")
    from invtool.ai.forecast import price_forecast
    from invtool.ui.display import print_forecast_table
    result = price_forecast(ticker, data)
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return
    print_forecast_table(result)
    if confirm("Generate chart?", default=True):
        from invtool.ui.charts import chart_forecast
        path = chart_forecast(result)
        show_chart_path(path)


def _regime(data):
    ticker = ask_ticker()
    console.print(f"\n[dim]Detecting {ticker} market regime...[/]")
    from invtool.ai.regime import detect_regime
    from invtool.ui.display import print_regime_panel
    result = detect_regime(ticker, data)
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return
    print_regime_panel(result)


def _anomaly(data):
    choice = select("Anomaly Detection:", [
        ("Single Ticker", "single"),
        ("Scan Portfolio", "portfolio"),
        ("Back", "back"),
    ])
    if choice == "back" or choice is None:
        return

    from invtool.ui.display import print_anomaly_table

    if choice == "single":
        ticker = ask_ticker()
        console.print(f"\n[dim]Scanning {ticker} for anomalies...[/]")
        from invtool.ai.anomaly import detect_anomalies
        result = detect_anomalies(ticker, data)
        print_anomaly_table(result)
        if result.get("anomalies") and confirm("Generate chart?", default=True):
            from invtool.ui.charts import chart_anomaly
            path = chart_anomaly(result)
            if path:
                show_chart_path(path)
    else:
        from invtool.ai.anomaly import scan_portfolio_anomalies
        from invtool.config import load_portfolio
        console.print("[dim]Scanning all holdings for anomalies...[/]")
        holdings = load_portfolio()
        results = scan_portfolio_anomalies(data, holdings)
        if not results:
            console.print("[green]No anomalies detected across portfolio.[/]")
        else:
            for r in results:
                console.print(f"\n[bold red]{r['ticker']}: {r['alert_count']} anomalies[/]")
                for a in r["anomalies"]:
                    console.print(f"  [{a['date']}] {a['description']}")


def _montecarlo(data):
    console.print("[dim]Running Monte Carlo simulation (10,000 paths)...[/]")
    from invtool.ai.montecarlo import monte_carlo_simulation
    from invtool.ui.display import print_montecarlo_table
    result = monte_carlo_simulation(data)
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return
    print_montecarlo_table(result)
    if confirm("Generate chart?", default=True):
        from invtool.ui.charts import chart_montecarlo
        idx = 1 if len(result["horizons"]) > 1 else 0
        path = chart_montecarlo(result, idx)
        show_chart_path(path)


def _earnings_ml(data):
    ticker = ask_ticker("NVDA")
    console.print(f"\n[dim]Predicting {ticker} earnings outcome...[/]")
    from invtool.ai.earnings_ml import predict_earnings
    from invtool.ui.display import print_earnings_prediction
    result = predict_earnings(ticker, data)
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return
    print_earnings_prediction(result)


def _optimizer(data):
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
    from invtool.ui.display import print_optimizer_table
    result = optimize_portfolio(data, tickers, target)
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return
    print_optimizer_table(result)
    if confirm("Generate chart?", default=True):
        from invtool.ui.charts import chart_efficient_frontier
        path = chart_efficient_frontier(result)
        show_chart_path(path)


def _correlation(data):
    from invtool.config import load_portfolio
    holdings = load_portfolio()
    default_tickers = ",".join(h["ticker"] for h in holdings)
    tickers_input = text("Tickers to analyze (comma-separated):", default=default_tickers)
    tickers = [t.strip().upper() for t in tickers_input.split(",")]

    console.print(f"[dim]Analyzing correlations for {len(tickers)} tickers...[/]")
    from invtool.ai.correlation import analyze_correlations
    from invtool.ui.display import print_correlation_table
    result = analyze_correlations(data, tickers)
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return
    print_correlation_table(result)
    if confirm("Generate chart?", default=True):
        from invtool.ui.charts import chart_correlation
        path = chart_correlation(result)
        show_chart_path(path)
