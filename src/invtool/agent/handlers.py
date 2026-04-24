"""Tool execution — dispatches a named tool call to the right invtool module.

_handle_tool(name, args) returns a JSON-serialized result string. All module
imports are lazy so importing agent.handlers itself is cheap.
"""
import json

_data_provider = None


def set_data_provider(dp):
    global _data_provider
    _data_provider = dp


def _ensure_provider():
    global _data_provider
    if _data_provider is None:
        from invtool.config.data_provider import DataProvider
        _data_provider = DataProvider()
    return _data_provider


def _handle_tool(name: str, args: dict) -> str:
    """Execute a tool and return JSON result string."""
    dp = _ensure_provider()

    if name == "get_stock_price":
        ticker = args["ticker"].upper()
        price = dp.get_current_price(ticker)
        info = dp.get_info(ticker)
        result = {
            "ticker": ticker,
            "price": round(price, 2),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "market_cap": info.get("marketCap"),
            "avg_volume": info.get("averageVolume"),
            "beta": info.get("beta"),
            "dividend_yield": info.get("dividendYield"),
        }

    elif name == "technical_analysis":
        from invtool.analysis.technical import full_technical_analysis
        t = full_technical_analysis(args["ticker"].upper(), dp)
        result = {k: v for k, v in t.items() if k != "df"}

    elif name == "screen_puts":
        from invtool.analysis.options import screen_puts
        df = screen_puts(args["ticker"].upper(), dp)
        if df.empty:
            return json.dumps(f"No put options found for {args['ticker']}")
        n = args.get("max_results", 5)
        cols = ["expiration", "DTE", "strike", "premium", "iv", "delta",
                "prob_otm", "annualized_return", "breakeven", "downside_cushion",
                "openInterest", "score"]
        available = [c for c in cols if c in df.columns]
        records = df.head(n)[available].to_dict("records")
        for r in records:
            for k, v in r.items():
                if isinstance(v, float):
                    r[k] = round(v, 4)
        result = records

    elif name == "screen_calls":
        from invtool.analysis.options import screen_calls
        df = screen_calls(args["ticker"].upper(), dp, cost_basis=args.get("cost_basis"))
        if df.empty:
            return json.dumps(f"No call options found for {args['ticker']}")
        n = args.get("max_results", 5)
        cols = ["expiration", "DTE", "strike", "premium", "iv", "delta",
                "prob_otm", "annualized_return", "upside_to_strike",
                "openInterest", "score"]
        available = [c for c in cols if c in df.columns]
        records = df.head(n)[available].to_dict("records")
        for r in records:
            for k, v in r.items():
                if isinstance(v, float):
                    r[k] = round(v, 4)
        result = records

    elif name == "wheel_analysis":
        from invtool.analysis.options import wheel_analysis
        raw = wheel_analysis(
            args["ticker"].upper(), dp,
            shares=args.get("shares", 0),
            cost_basis=args.get("cost_basis", 0),
        )
        result = {k: v for k, v in raw.items() if k not in ("best_puts", "best_calls")}
        if raw.get("best_puts"):
            result["top_put"] = {k: round(v, 4) if isinstance(v, float) else v
                                 for k, v in raw["best_puts"][0].items()
                                 if k in ("expiration", "strike", "premium", "prob_otm", "annualized_return")}
        if raw.get("best_calls"):
            result["top_call"] = {k: round(v, 4) if isinstance(v, float) else v
                                  for k, v in raw["best_calls"][0].items()
                                  if k in ("expiration", "strike", "premium", "prob_otm", "annualized_return")}

    elif name == "earnings_analysis":
        from invtool.analysis.earnings import full_earnings_analysis
        raw = full_earnings_analysis(args["ticker"].upper(), dp)
        if "error" in raw:
            result = raw
        else:
            result = {k: v for k, v in raw.items() if k != "earnings_df"}
            if "earnings_df" in raw and not raw["earnings_df"].empty:
                result["earnings_data"] = raw["earnings_df"].to_dict("records")
                for r in result["earnings_data"]:
                    for k, v in r.items():
                        if isinstance(v, float):
                            r[k] = round(v, 4)

    elif name == "portfolio_summary":
        from invtool.analysis.portfolio import Portfolio
        pf = Portfolio(dp)
        result = pf.summary()
        for p in result["positions"]:
            for k in list(p.keys()):
                if isinstance(p[k], float):
                    p[k] = round(p[k], 2)

    elif name == "portfolio_strategies":
        from invtool.analysis.portfolio import Portfolio
        pf = Portfolio(dp)
        result = pf.per_position_strategies()

    elif name == "tax_loss_candidates":
        from invtool.analysis.portfolio import Portfolio
        pf = Portfolio(dp)
        result = pf.tax_loss_candidates()

    elif name == "generate_chart":
        from invtool.ui import charts
        chart_type = args["chart_type"]
        ticker = args.get("ticker", "").upper()
        tickers_str = args.get("tickers", "")
        if chart_type == "technical" and ticker:
            from invtool.analysis.technical import full_technical_analysis
            t = full_technical_analysis(ticker, dp)
            path = charts.chart_technical(t)
        elif chart_type == "portfolio_pnl":
            from invtool.analysis.portfolio import Portfolio
            pf = Portfolio(dp)
            s = pf.summary()
            path = charts.chart_portfolio_pnl(s["positions"])
        elif chart_type == "portfolio_allocation":
            from invtool.analysis.portfolio import Portfolio
            pf = Portfolio(dp)
            s = pf.summary()
            path = charts.chart_portfolio_allocation(s["positions"])
        elif chart_type == "earnings" and ticker:
            from invtool.analysis.earnings import full_earnings_analysis
            raw = full_earnings_analysis(ticker, dp)
            if "earnings_df" in raw:
                path = charts.chart_earnings_behavior(raw["earnings_df"], ticker)
            else:
                return json.dumps("No earnings data available")
        elif chart_type == "recovery":
            from invtool.analysis.portfolio import Portfolio
            pf = Portfolio(dp)
            s = pf.summary()
            path = charts.chart_recovery_timeline(s["total_pnl"], 50)
        elif chart_type == "sentiment" and ticker:
            from invtool.ai.sentiment import analyze_sentiment
            r = analyze_sentiment(ticker, dp)
            path = charts.chart_sentiment(r)
        elif chart_type == "forecast" and ticker:
            from invtool.ai.forecast import price_forecast
            r = price_forecast(ticker, dp)
            path = charts.chart_forecast(r)
        elif chart_type == "anomaly" and ticker:
            from invtool.ai.anomaly import detect_anomalies
            r = detect_anomalies(ticker, dp)
            path = charts.chart_anomaly(r)
        elif chart_type == "montecarlo":
            from invtool.ai.montecarlo import monte_carlo_simulation
            r = monte_carlo_simulation(dp)
            path = charts.chart_montecarlo(r, 1 if len(r["horizons"]) > 1 else 0)
        elif chart_type == "frontier":
            tickers = [t.strip() for t in tickers_str.split(",")] if tickers_str else ["NVDA", "AAPL", "MSFT"]
            from invtool.ai.optimizer import optimize_portfolio
            r = optimize_portfolio(dp, tickers)
            path = charts.chart_efficient_frontier(r)
        elif chart_type == "correlation":
            tickers = [t.strip() for t in tickers_str.split(",")] if tickers_str else ["NVDA", "AAPL", "MSFT"]
            from invtool.ai.correlation import analyze_correlations
            r = analyze_correlations(dp, tickers)
            path = charts.chart_correlation(r)
        elif chart_type == "sector_performance":
            from invtool.market.intel import sector_performance
            r = sector_performance()
            path = charts.chart_sector_performance(r)
        else:
            return json.dumps(f"Unknown chart type: {chart_type}")
        result = f"Chart saved to: {path}"

    elif name == "sentiment_analysis":
        from invtool.ai.sentiment import analyze_sentiment
        result = analyze_sentiment(args["ticker"].upper(), dp)

    elif name == "price_forecast":
        from invtool.ai.forecast import price_forecast
        raw = price_forecast(args["ticker"].upper(), dp)
        result = {k: v for k, v in raw.items() if k not in ("hist_df", "proj_df")}

    elif name == "market_regime":
        from invtool.ai.regime import detect_regime
        result = detect_regime(args["ticker"].upper(), dp)

    elif name == "detect_anomalies":
        ticker = args.get("ticker", "").upper()
        if ticker:
            from invtool.ai.anomaly import detect_anomalies as _detect
            raw = _detect(ticker, dp)
            result = {k: v for k, v in raw.items() if k != "df"}
        else:
            from invtool.ai.anomaly import scan_portfolio_anomalies
            from invtool.config import load_portfolio
            result = scan_portfolio_anomalies(dp, load_portfolio())

    elif name == "monte_carlo_risk":
        from invtool.ai.montecarlo import monte_carlo_simulation
        raw = monte_carlo_simulation(dp)
        if "error" in raw:
            result = raw
        else:
            result = {k: v for k, v in raw.items()}
            for h in result.get("horizons", []):
                h.pop("simulations", None)

    elif name == "predict_earnings":
        from invtool.ai.earnings_ml import predict_earnings
        result = predict_earnings(args["ticker"].upper(), dp)

    elif name == "optimize_portfolio":
        from invtool.ai.optimizer import optimize_portfolio
        tickers = [t.strip().upper() for t in args["tickers"].split(",")]
        target = args.get("target", "sharpe")
        result = optimize_portfolio(dp, tickers, target)

    elif name == "correlation_analysis":
        from invtool.ai.correlation import analyze_correlations
        tickers = [t.strip().upper() for t in args["tickers"].split(",")]
        raw = analyze_correlations(dp, tickers)
        result = {k: v for k, v in raw.items() if k != "corr_matrix_list"}

    elif name == "earnings_calendar":
        from invtool.market.intel import earnings_calendar
        result = earnings_calendar(args.get("date_range", "this_week"))

    elif name == "market_movers":
        from invtool.market.intel import market_movers
        result = market_movers(args.get("category", "day_gainers"))

    elif name == "sector_performance":
        from invtool.market.intel import sector_performance
        result = sector_performance()

    elif name == "analyst_ratings":
        from invtool.market.intel import analyst_ratings
        result = analyst_ratings(args["ticker"].upper())

    elif name == "insider_activity":
        from invtool.market.intel import insider_activity
        result = insider_activity(args["ticker"].upper())

    elif name == "economic_calendar":
        from invtool.market.intel import economic_calendar
        result = economic_calendar()

    elif name == "crawl_market_news":
        from invtool.market.webcrawler import crawl_market_news
        sources_str = args.get("sources", "")
        sources = [s.strip() for s in sources_str.split(",")] if sources_str else None
        max_per = min(args.get("max_per_source", 8), 20)
        result = crawl_market_news(sources=sources, max_per_source=max_per)

    elif name == "ticker_news_crawl":
        from invtool.market.webcrawler import ticker_news_crawl
        result = ticker_news_crawl(
            args["ticker"].upper(),
            max_results=args.get("max_results", 15),
        )

    elif name == "search_financial_news":
        from invtool.market.webcrawler import search_financial_news
        result = search_financial_news(
            args["query"],
            max_results=args.get("max_results", 15),
        )

    elif name == "fetch_article_content":
        from invtool.market.webcrawler import fetch_article_content
        result = fetch_article_content(args["url"])

    else:
        result = f"Unknown tool: {name}"

    return json.dumps(result, default=str)
