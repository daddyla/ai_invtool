"""Tool definitions for the Claude agent (Anthropic API format).

Pure data — no imports, no side effects. Consumed by agent.handlers for execution
and by agent.loop when building the Messages API request.
"""

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
