"""AI-powered natural language analysis using Anthropic API directly."""

import os
import json
import traceback
import warnings
warnings.filterwarnings("ignore")

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner

console = Console()

# Lazy-import
_SDK_AVAILABLE = False
try:
    import anthropic
    _SDK_AVAILABLE = True
except ImportError:
    pass

# Global data provider
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


# ── Tool Definitions (Anthropic API format) ──

TOOL_DEFINITIONS = [
    {
        "name": "get_stock_price",
        "description": "Get current stock price and basic info for a ticker",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol (e.g. NVDA, AAPL)"}
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "technical_analysis",
        "description": "Run full technical analysis (SMA, RSI, MACD, Bollinger Bands, ATR, trend, support/resistance) for a ticker",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"}
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "screen_puts",
        "description": "Screen and rank put options for selling (cash-secured puts). Returns top puts ranked by score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
                "max_results": {"type": "integer", "description": "Max results to return (default 5)"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "screen_calls",
        "description": "Screen and rank call options for selling (covered calls). Returns top calls ranked by score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
                "cost_basis": {"type": "number", "description": "Your cost basis per share (optional)"},
                "max_results": {"type": "integer", "description": "Max results to return (default 5)"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "wheel_analysis",
        "description": "Full wheel strategy analysis (best puts + calls + monthly income projections)",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
                "shares": {"type": "integer", "description": "Shares currently owned (default 0)"},
                "cost_basis": {"type": "number", "description": "Cost basis per share (default 0)"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "earnings_analysis",
        "description": "Analyze historical earnings behavior and patterns (pre/post earnings moves, sell-the-news detection)",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol (NVDA has richest data)"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "portfolio_summary",
        "description": "Get current portfolio P&L and allocation breakdown with live prices",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "portfolio_strategies",
        "description": "Get per-position strategy recommendations for the portfolio",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "tax_loss_candidates",
        "description": "Identify tax-loss harvesting opportunities in the portfolio",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "generate_chart",
        "description": "Generate an analysis chart and save to PNG file",
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["technical", "portfolio_pnl", "portfolio_allocation", "earnings", "recovery",
                             "sentiment", "forecast", "anomaly", "montecarlo", "frontier", "correlation",
                             "sector_performance"],
                    "description": "Type of chart to generate",
                },
                "ticker": {"type": "string", "description": "Stock ticker (required for technical/earnings/sentiment/forecast/anomaly charts)"},
                "tickers": {"type": "string", "description": "Comma-separated tickers (for correlation chart)"},
            },
            "required": ["chart_type"],
        },
    },
    # ── AI Analytics Tools ──
    {
        "name": "sentiment_analysis",
        "description": "Analyze news sentiment for a stock using financial keyword scoring. Returns bullish/bearish/neutral with headline scores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "price_forecast",
        "description": "Forecast stock price using trend extrapolation with confidence intervals (30/60/90 day projections).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "market_regime",
        "description": "Detect market regime (TRENDING_UP, TRENDING_DOWN, MEAN_REVERTING, HIGH_VOLATILITY) and recommend options strategies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "detect_anomalies",
        "description": "Detect unusual activity in a stock: volume spikes, price gaps, extreme moves, volatility changes. Uses z-score analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol (omit for portfolio scan)"},
            },
        },
    },
    {
        "name": "monte_carlo_risk",
        "description": "Run Monte Carlo simulation on portfolio (10,000 paths). Returns VaR, CVaR, probability of loss at 7/30/90 day horizons.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "predict_earnings",
        "description": "ML-based earnings prediction: probability of beat, probability of sell-the-news, expected post-earnings move.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol (NVDA has richest data)"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "optimize_portfolio",
        "description": "Mean-variance portfolio optimization (Markowitz). Finds optimal weights for max Sharpe ratio. Shows efficient frontier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {"type": "string", "description": "Comma-separated ticker symbols to optimize"},
                "target": {"type": "string", "enum": ["sharpe", "min_vol"], "description": "Optimization target (default: sharpe)"},
            },
            "required": ["tickers"],
        },
    },
    {
        "name": "correlation_analysis",
        "description": "Analyze correlations between tickers with K-means clustering. Shows diversification score and high-correlation pairs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {"type": "string", "description": "Comma-separated ticker symbols to analyze"},
            },
            "required": ["tickers"],
        },
    },
    # ── Market Intelligence Tools ──
    {
        "name": "earnings_calendar",
        "description": "Get upcoming earnings announcements. Find which stocks report earnings today, tomorrow, or this/next week.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_range": {
                    "type": "string",
                    "enum": ["today", "tomorrow", "this_week", "next_week"],
                    "description": "Time period to show (default: this_week)",
                },
            },
        },
    },
    {
        "name": "market_movers",
        "description": "Get top market movers: biggest gainers, biggest losers, or most actively traded stocks today.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["day_gainers", "day_losers", "most_actives"],
                    "description": "Type of movers (default: day_gainers)",
                },
            },
        },
    },
    {
        "name": "sector_performance",
        "description": "Get sector performance using ETF proxies (XLK, XLF, XLE, etc.). Shows 1d, 1w, 1m, 3m returns.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "analyst_ratings",
        "description": "Get analyst consensus ratings, price targets, and recent upgrades/downgrades for a stock.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "insider_activity",
        "description": "Get insider trading activity: recent buys/sells by company executives and directors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "economic_calendar",
        "description": "Get upcoming economic events: CPI, jobs, GDP, FOMC, and other market-moving data releases.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    # ── Web Crawler Tools ──
    {
        "name": "crawl_market_news",
        "description": "Crawl live market news headlines from Reuters, CNBC, MarketWatch, Yahoo Finance, and Benzinga. Returns the latest financial headlines with summaries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sources": {
                    "type": "string",
                    "description": "Comma-separated source keys to crawl (optional). Options: reuters_business, reuters_finance, cnbc_top, cnbc_markets, marketwatch, yahoo_finance, benzinga, wsj_markets, seeking_alpha. Default: top 6 sources.",
                },
                "max_per_source": {
                    "type": "integer",
                    "description": "Max articles per source (default 8, max 20)",
                },
            },
        },
    },
    {
        "name": "ticker_news_crawl",
        "description": "Crawl recent news articles specifically about a stock ticker from Yahoo Finance RSS and Google News. Better than sentiment_analysis for finding full article context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol (e.g. NVDA, AAPL)"},
                "max_results": {"type": "integer", "description": "Max articles to return (default 15)"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "search_financial_news",
        "description": "Search financial news by topic or keyword via Google News RSS. Use for broad topics like 'Fed rate cut', 'AI chip demand', 'banking sector stress', 'oil prices'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, e.g. 'Fed interest rates', 'NVDA earnings', 'semiconductor shortage'"},
                "max_results": {"type": "integer", "description": "Max articles to return (default 15)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_article_content",
        "description": "Fetch and extract the full text of a news article from its URL. Use after crawl_market_news or ticker_news_crawl to read the full content of important articles.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL of the article to fetch"},
            },
            "required": ["url"],
        },
    },
]


# ── Tool Handlers ──

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
        from invtool import charts
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

    # ── AI Analytics Tool Handlers ──
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
            # Strip simulations array (too large for JSON)
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

    # ── Market Intelligence Tool Handlers ──
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

    # ── Web Crawler Tool Handlers ──
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


# ── Agent System Prompt ──

AGENT_SYSTEM_PROMPT = """You are an expert senior investment analyst assistant. You have access to tools for:
- Real-time stock prices and market data
- Technical analysis (SMA, RSI, MACD, Bollinger Bands, ATR, support/resistance)
- Options screening (sell puts, covered calls, wheel strategy)
- Earnings behavior analysis (pre/post patterns, sell-the-news detection)
- Portfolio tracking (P&L, allocation, per-position strategies)
- Tax-loss harvesting identification
- Chart generation

AI Analytics tools:
- Sentiment analysis (news headline scoring)
- Price forecasting (trend extrapolation with confidence bands)
- Market regime detection (trending/mean-reverting/high-volatility + strategy recommendations)
- Anomaly detection (volume spikes, price gaps, volatility changes)
- Monte Carlo risk simulation (VaR, CVaR, probability of loss)
- Earnings prediction (ML-based beat/miss probability)
- Portfolio optimization (Markowitz efficient frontier, optimal weights)
- Correlation & clustering (diversification score, K-means grouping)

Market Intelligence tools:
- Earnings calendar (which stocks report today/tomorrow/this week)
- Market movers (top gainers, losers, most active)
- Sector performance (all 11 S&P sectors via ETFs)
- Analyst ratings (consensus, price targets, upgrades/downgrades)
- Insider activity (insider buys/sells, net sentiment)
- Economic calendar (CPI, jobs, GDP, FOMC events)

Web News tools:
- crawl_market_news: Live headlines from Reuters, CNBC, MarketWatch, Yahoo Finance, Benzinga
- ticker_news_crawl: Recent news specifically about a stock ticker
- search_financial_news: Search news by topic ("Fed rate cut", "AI chip demand")
- fetch_article_content: Read the full text of any article from its URL

When answering questions:
1. Always use tools to fetch real data — never make up numbers
2. Present data in clear tables and summaries
3. Include specific numbers (prices, returns, probabilities)
4. Give actionable recommendations with rationale
5. Warn about risks when appropriate
6. Use markdown formatting for readability

The user's portfolio contains: TMF (36 shares @ $45.29), JEPQ (20 @ $53.70),
BLSH (11 @ $37.00), FIG (11 @ $133.00), DOCS (6 @ $41.00).
"""


def _run_conversation(client, messages: list) -> str:
    """Run a multi-turn conversation with tool use, return final text."""
    while True:
        # Show spinner while waiting for API response
        with Live(Spinner("dots", text="[dim]Thinking...[/]"), console=console, transient=True):
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=AGENT_SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

        # Collect text and tool calls from response
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        # If no tool calls, we're done — return the text
        if response.stop_reason == "end_turn" or not tool_calls:
            return "\n".join(text_parts)

        # Process tool calls
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            console.print(f"  [dim]Calling {tc.name}({json.dumps(tc.input, default=str)[:80]})...[/]")
            try:
                result_str = _handle_tool(tc.name, tc.input)
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
                console.print(f"  [red]Tool error: {e}[/]")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})


def check_api_key() -> bool:
    """Check if ANTHROPIC_API_KEY is set (loads .env first)."""
    from dotenv import load_dotenv
    load_dotenv()
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _save_response(result_text: str):
    """Prompt user to save the last AI response to a file."""
    from invtool.prompt import text as prompt_text
    from invtool.config import REPORTS_DIR
    from datetime import datetime

    filename = prompt_text("Filename (without extension):", default=f"ai_response_{datetime.now().strftime('%Y%m%d')}")
    if not filename:
        return
    filename = filename.strip().replace(" ", "_")
    for ch in '<>:"/\\|?*':
        filename = filename.replace(ch, "")

    fmt = prompt_text("Format (md/txt):", default="md")
    ext = ".txt" if fmt.strip().lower() == "txt" else ".md"
    filepath = REPORTS_DIR / f"{filename}{ext}"

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            if ext == ".txt":
                import re
                plain = result_text
                plain = re.sub(r'#{1,6}\s+', '', plain)
                plain = re.sub(r'\*\*(.+?)\*\*', r'\1', plain)
                plain = re.sub(r'\*(.+?)\*', r'\1', plain)
                plain = re.sub(r'`(.+?)`', r'\1', plain)
                f.write(plain)
            else:
                f.write(result_text)
        console.print(f"[green]Saved to: {filepath}[/]")
    except Exception as e:
        console.print(f"[red]Failed to save: {e}[/]")


def ai_chat_loop(data_provider):
    """Interactive AI chat loop."""
    if not _SDK_AVAILABLE:
        console.print(Panel(
            "[red]anthropic SDK is not installed.[/]\n\n"
            "Install with: [bold]pip install anthropic[/]",
            title="AI Agent Unavailable",
            border_style="red",
        ))
        return

    if not check_api_key():
        console.print(Panel(
            "[red]ANTHROPIC_API_KEY environment variable not set.[/]\n\n"
            "Add to .env file:\n"
            "  [bold]ANTHROPIC_API_KEY=sk-ant-...[/]",
            title="API Key Required",
            border_style="red",
        ))
        return

    set_data_provider(data_provider)
    client = anthropic.Anthropic()
    messages = []

    console.print(Panel(
        "Ask me anything about stocks, options, earnings, or your portfolio.\n"
        "Type [bold]save[/] to save the last response to a file.\n"
        "Type [bold]back[/] to return to the menu.",
        title="[bold blue]AI Investment Analyst[/]",
        border_style="blue",
    ))

    from invtool.prompt import text as prompt_text

    last_result = None

    while True:
        user_input = prompt_text("You:")
        if user_input is None or user_input.lower().strip() in ("back", "quit", "exit", "q"):
            break
        if not user_input.strip():
            continue

        # Save command
        if user_input.strip().lower() == "save":
            if last_result:
                _save_response(last_result)
            else:
                console.print("[yellow]No response to save yet.[/]")
            continue

        messages.append({"role": "user", "content": user_input})

        console.print()
        try:
            result_text = _run_conversation(client, messages)
            if result_text:
                messages.append({"role": "assistant", "content": result_text})
                console.print(Markdown(result_text))
                console.print()
                last_result = result_text
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
            console.print(f"[dim]{traceback.format_exc()}[/]")
