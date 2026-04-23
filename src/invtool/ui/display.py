"""Rich display helpers — tables, panels, formatters."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import pandas as pd

console = Console()


def format_pnl(value: float) -> Text:
    color = "green" if value >= 0 else "red"
    return Text(f"${value:+,.2f}", style=color)


def format_pct(value: float) -> Text:
    color = "green" if value >= 0 else "red"
    return Text(f"{value:+.1%}", style=color)


def format_dollar(value: float) -> str:
    return f"${value:,.2f}"


def print_header(title: str, subtitle: str = ""):
    from datetime import datetime
    sub = subtitle or datetime.now().strftime("%Y-%m-%d")
    console.print(Panel(
        f"[bold white]{title}[/]\n[dim]{sub}[/]",
        border_style="blue",
        padding=(1, 4),
    ))


def print_stock_summary(ticker: str, price: float, info: dict):
    table = Table(title=f"{ticker} Summary", box=box.ROUNDED, show_header=False, padding=(0, 2))
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Price", f"${price:.2f}")
    table.add_row("52W High", format_dollar(info.get("fiftyTwoWeekHigh", 0)))
    table.add_row("52W Low", format_dollar(info.get("fiftyTwoWeekLow", 0)))
    mcap = info.get("marketCap", 0)
    table.add_row("Market Cap", f"${mcap/1e9:.1f}B" if mcap else "N/A")
    table.add_row("Avg Volume", f"{info.get('averageVolume', 0):,.0f}")
    beta = info.get("beta", None)
    table.add_row("Beta", f"{beta:.2f}" if beta else "N/A")

    console.print(table)


def print_technicals_table(t: dict):
    table = Table(title=f"{t['ticker']} Technical Indicators", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Indicator", style="cyan")
    table.add_column("Value", style="white", justify="right")
    table.add_column("Signal", style="white")

    def trend_arrow(val, ref, above_bull=True):
        if above_bull:
            return "[green]Above (Bullish)[/]" if val > ref else "[red]Below (Bearish)[/]"
        return "[red]Above (Bearish)[/]" if val > ref else "[green]Below (Bullish)[/]"

    p = t["current_price"]
    table.add_row("SMA 20", f"${t['sma_20']:.2f}", trend_arrow(p, t["sma_20"]))
    table.add_row("SMA 50", f"${t['sma_50']:.2f}", trend_arrow(p, t["sma_50"]))
    rsi = t["rsi"]
    rsi_label = "[red]Overbought[/]" if rsi > 70 else "[green]Oversold[/]" if rsi < 30 else "Neutral"
    table.add_row("RSI (14)", f"{rsi:.1f}", rsi_label)
    table.add_row("MACD", f"{t['macd']:.4f}", "[green]Bullish[/]" if t["macd_hist"] > 0 else "[red]Bearish[/]")
    table.add_row("MACD Hist", f"{t['macd_hist']:.4f}", "")
    table.add_row("BB Upper", f"${t['bb_upper']:.2f}", "")
    table.add_row("BB Lower", f"${t['bb_lower']:.2f}", "")
    table.add_row("ATR (14)", f"${t['atr']:.2f}", "")
    table.add_row("Hist Vol (20d)", f"{t['hist_vol']:.1%}", "")
    table.add_row("Support", ", ".join(f"${s:.2f}" for s in t["supports"][-3:]), "")
    table.add_row("Resistance", ", ".join(f"${r:.2f}" for r in t["resistances"][:3]), "")

    trend_color = "green" if t["trend"] == "BULLISH" else "red" if t["trend"] == "BEARISH" else "yellow"
    table.add_row(
        "Overall Trend",
        f"[bold {trend_color}]{t['trend']}[/]",
        f"{t['trend_bullish']}/{t['trend_total']} bullish  ({' | '.join(t['trend_signals'])})",
    )

    console.print(table)


def print_options_table(df: pd.DataFrame, title: str, top_n=10):
    if df.empty:
        console.print(f"[yellow]No options found for {title}[/]")
        return

    table = Table(title=title, box=box.SIMPLE_HEAVY, padding=(0, 1))
    table.add_column("Expiry", style="cyan")
    table.add_column("DTE", justify="right")
    table.add_column("Strike", justify="right")
    table.add_column("Bid", justify="right", style="green")
    table.add_column("IV", justify="right")
    table.add_column("Delta", justify="right")
    table.add_column("P(OTM)", justify="right")
    table.add_column("Ann.Ret", justify="right", style="green")
    table.add_column("Cushion", justify="right")
    table.add_column("OI", justify="right")
    table.add_column("Score", justify="right", style="bold yellow")

    for _, row in df.head(top_n).iterrows():
        cushion = row.get("downside_cushion", row.get("upside_to_strike", 0))
        table.add_row(
            row["expiration"],
            str(int(row["DTE"])),
            f"${row['strike']:.2f}",
            f"${row['premium']:.2f}",
            f"{row['iv']:.0%}",
            f"{row['delta']:.3f}",
            f"{row['prob_otm']:.0%}",
            f"{row['annualized_return']:.0%}",
            f"{cushion:.1%}",
            str(int(row.get("openInterest", 0))),
            f"{row['score']:.1f}",
        )

    console.print(table)

    # Top pick summary
    best = df.iloc[0]
    cushion = best.get("downside_cushion", best.get("upside_to_strike", 0))
    console.print(Panel(
        f"[bold]Strike:[/] ${best['strike']:.2f}  |  "
        f"[bold]Premium:[/] ${best['premium']:.2f}/sh (${best['premium']*100:.0f}/contract)  |  "
        f"[bold]Prob OTM:[/] {best['prob_otm']:.0%}  |  "
        f"[bold]Ann. Return:[/] {best['annualized_return']:.0%}  |  "
        f"[bold]Cushion:[/] {cushion:.1%}",
        title="[bold yellow]Top Pick[/]",
        border_style="yellow",
    ))


def print_portfolio_table(positions: list):
    table = Table(title="Portfolio Holdings", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Ticker", style="bold cyan")
    table.add_column("Type", style="dim")
    table.add_column("Shares", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Current", justify="right")
    table.add_column("Invested", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("P&L $", justify="right")
    table.add_column("P&L %", justify="right")
    table.add_column("Weight", justify="right")

    total_invested = sum(p["shares"] * p["cost"] for p in positions)
    total_value = sum(p["shares"] * p["price"] for p in positions)

    for p in positions:
        invested = p["shares"] * p["cost"]
        value = p["shares"] * p["price"]
        pnl = value - invested
        pnl_pct = pnl / invested if invested > 0 else 0
        weight = value / total_value if total_value > 0 else 0
        pnl_color = "green" if pnl >= 0 else "red"

        table.add_row(
            p["ticker"],
            p.get("type", ""),
            str(p["shares"]),
            f"${p['cost']:.2f}",
            f"${p['price']:.2f}",
            f"${invested:,.0f}",
            f"${value:,.0f}",
            f"[{pnl_color}]${pnl:+,.0f}[/]",
            f"[{pnl_color}]{pnl_pct:+.1%}[/]",
            f"{weight:.0%}",
        )

    total_pnl = total_value - total_invested
    total_pct = total_pnl / total_invested if total_invested > 0 else 0
    tc = "green" if total_pnl >= 0 else "red"
    table.add_section()
    table.add_row(
        "[bold]TOTAL[/]", "", "", "", "",
        f"${total_invested:,.0f}", f"${total_value:,.0f}",
        f"[bold {tc}]${total_pnl:+,.0f}[/]",
        f"[bold {tc}]{total_pct:+.1%}[/]",
        "100%",
    )

    console.print(table)


def print_earnings_table(df: pd.DataFrame):
    table = Table(title="Earnings History", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Quarter", style="cyan")
    table.add_column("Date")
    table.add_column("EPS Surp", justify="right")
    table.add_column("Rev Surp", justify="right")
    table.add_column("Pre 10d", justify="right")
    table.add_column("Post 1d", justify="right")
    table.add_column("Post 5d", justify="right")
    table.add_column("Post 10d", justify="right")

    for _, row in df.iterrows():
        def _fmt(col):
            v = row.get(col)
            if pd.isna(v):
                return "N/A"
            color = "green" if v >= 0 else "red"
            return f"[{color}]{v:+.1%}[/]"

        table.add_row(
            row.get("quarter", ""),
            row.get("date", ""),
            _fmt("eps_surprise"),
            _fmt("rev_surprise"),
            _fmt("pre_10d"),
            _fmt("post_1d"),
            _fmt("post_5d"),
            _fmt("post_10d"),
        )

    console.print(table)


def show_chart_path(path: str):
    console.print(f"\n[dim]Chart saved to:[/] [bold blue]{path}[/]\n")


# ── AI Analytics Display Functions ──


def print_sentiment_table(result: dict):
    """Display sentiment analysis results."""
    label = result["label"]
    color = "green" if label == "BULLISH" else "red" if label == "BEARISH" else "yellow"

    console.print(Panel(
        f"[bold {color}]{label}[/]  |  Score: {result['overall_score']:+.3f}  |  "
        f"Bullish: [green]{result['bullish_count']}[/]  "
        f"Bearish: [red]{result['bearish_count']}[/]  "
        f"Neutral: {result['neutral_count']}  |  "
        f"Total: {result['total_articles']} articles",
        title=f"{result['ticker']} Sentiment",
        border_style=color,
    ))

    headlines = result.get("headlines", [])
    if headlines:
        table = Table(title="News Headlines", box=box.ROUNDED, padding=(0, 1))
        table.add_column("#", style="dim", justify="right")
        table.add_column("Score", justify="right")
        table.add_column("Headline")
        table.add_column("Source", style="dim")

        for i, h in enumerate(headlines[:12], 1):
            s = h["score"]
            sc = "green" if s > 0.1 else "red" if s < -0.1 else "dim"
            table.add_row(str(i), f"[{sc}]{s:+.2f}[/]", h["title"][:80], h["source"])
        console.print(table)


def print_forecast_table(result: dict):
    """Display price forecast results."""
    console.print(Panel(
        f"[bold]Current Price:[/] ${result['current_price']:.2f}  |  "
        f"[bold]Trend:[/] {result['trend_annual']:+.1f}%/yr  |  "
        f"[bold]R²:[/] {result['r_squared']:.3f}",
        title=f"{result['ticker']} Forecast",
        border_style="blue",
    ))

    table = Table(title="Price Projections", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Horizon", style="cyan")
    table.add_column("Target", justify="right", style="bold")
    table.add_column("Change", justify="right")
    table.add_column("1σ Low", justify="right", style="yellow")
    table.add_column("1σ High", justify="right", style="yellow")
    table.add_column("2σ Low", justify="right", style="red")
    table.add_column("2σ High", justify="right", style="green")

    for fc in result["forecasts"]:
        chg_color = "green" if fc["change_pct"] >= 0 else "red"
        table.add_row(
            f"{fc['days']} days",
            f"${fc['price']:.2f}",
            f"[{chg_color}]{fc['change_pct']:+.1f}%[/]",
            f"${fc['low_1s']:.2f}",
            f"${fc['high_1s']:.2f}",
            f"${fc['low_2s']:.2f}",
            f"${fc['high_2s']:.2f}",
        )
    console.print(table)


def print_regime_panel(result: dict):
    """Display market regime analysis."""
    regime = result["regime"]
    regime_colors = {
        "TRENDING_UP": "green", "TRENDING_DOWN": "red",
        "MEAN_REVERTING": "yellow", "HIGH_VOLATILITY": "magenta",
    }
    color = regime_colors.get(regime, "white")
    regime_labels = {
        "TRENDING_UP": "TRENDING UP", "TRENDING_DOWN": "TRENDING DOWN",
        "MEAN_REVERTING": "MEAN REVERTING (RANGE-BOUND)", "HIGH_VOLATILITY": "HIGH VOLATILITY",
    }

    console.print(Panel(
        f"[bold {color}]{regime_labels.get(regime, regime)}[/]  |  "
        f"Confidence: {result['confidence']:.0%}  |  "
        f"Vol Percentile: {result['vol_percentile']:.0%}\n\n"
        f"Signals: {' | '.join(result['signals'])}",
        title=f"{result['ticker']} Market Regime (${result['current_price']:.2f})",
        border_style=color,
    ))

    strategies = result.get("recommended_strategies", [])
    if strategies:
        table = Table(title="Recommended Strategies", box=box.ROUNDED, padding=(0, 1))
        table.add_column("#", style="dim", justify="right")
        table.add_column("Strategy", style="bold cyan")
        table.add_column("Rationale")
        for i, s in enumerate(strategies, 1):
            table.add_row(str(i), s["name"], s["rationale"])
        console.print(table)


def print_anomaly_table(result: dict):
    """Display anomaly detection results."""
    anomalies = result.get("anomalies", [])
    status = "[green]Normal[/]" if not anomalies else f"[red]{len(anomalies)} alerts[/]"

    console.print(Panel(
        f"[bold]{result['ticker']}[/] @ ${result.get('current_price', 0):.2f}  |  "
        f"Status: {status}  |  {result['summary']}",
        title="Anomaly Detection",
        border_style="red" if anomalies else "green",
    ))

    if anomalies:
        table = Table(title="Active Anomalies", box=box.ROUNDED, padding=(0, 1))
        table.add_column("Date", style="cyan")
        table.add_column("Type", style="bold")
        table.add_column("Z-Score", justify="right")
        table.add_column("Description")

        for a in anomalies:
            severity = "red" if abs(a["z_score"]) > 3 else "yellow"
            table.add_row(
                a["date"],
                f"[{severity}]{a['type']}[/]",
                f"{a['z_score']:+.1f}",
                a["description"],
            )
        console.print(table)


def print_montecarlo_table(result: dict):
    """Display Monte Carlo risk results."""
    console.print(Panel(
        f"[bold]Portfolio Value:[/] ${result['portfolio_value']:,.0f}  |  "
        f"[bold]Tickers:[/] {', '.join(result['tickers'])}  |  "
        f"[bold]Simulations:[/] {result['n_sims']:,}",
        title="Monte Carlo Risk Analysis",
        border_style="blue",
    ))

    table = Table(title="Risk Metrics by Horizon", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Horizon", style="cyan")
    table.add_column("VaR 95%", justify="right", style="red")
    table.add_column("VaR 99%", justify="right", style="red bold")
    table.add_column("CVaR 95%", justify="right", style="red")
    table.add_column("P(Loss)", justify="right")
    table.add_column("P(>10%)", justify="right")
    table.add_column("Median", justify="right", style="green")
    table.add_column("Max DD", justify="right", style="red")

    for h in result["horizons"]:
        table.add_row(
            f"{h['days']}d",
            f"${h['var_95']:,.0f}",
            f"${h['var_99']:,.0f}",
            f"${h['cvar_95']:,.0f}",
            f"{h['prob_loss']:.1%}",
            f"{h['prob_loss_10pct']:.1%}",
            f"{h['median_return']:+.2f}%",
            f"{h['avg_max_drawdown']:.1f}%",
        )
    console.print(table)


def print_earnings_prediction(result: dict):
    """Display earnings prediction results."""
    p_beat = result["p_beat"]
    p_stn = result["p_sell_the_news"]
    beat_color = "green" if p_beat > 0.6 else "red" if p_beat < 0.4 else "yellow"
    stn_color = "red" if p_stn > 0.5 else "green" if p_stn < 0.3 else "yellow"

    console.print(Panel(
        f"[bold {beat_color}]P(Beat): {p_beat:.1%}[/]  |  "
        f"[bold {stn_color}]P(Sell-the-News): {p_stn:.1%}[/]  |  "
        f"Expected Move: {result['expected_move']:+.1f}%  |  "
        f"Confidence: [bold]{result['confidence']}[/]  |  "
        f"{'ML Model' if result['ml_used'] else 'Statistical'}",
        title=f"{result['ticker']} Earnings Prediction",
        border_style="blue",
    ))

    console.print(Panel(
        f"[bold]{result['recommendation']}[/]",
        border_style=beat_color,
    ))

    feat = result["features"]
    table = Table(title="Feature Summary", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Feature", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Historical Beat Rate", f"{feat['historical_beat_rate']:.1%}")
    table.add_row("Avg EPS Surprise", f"{feat['avg_eps_surprise']:+.1f}%")
    table.add_row("Consecutive Beats", str(feat["consecutive_beats"]))
    table.add_row("Avg Pre-10d Runup", f"{feat['avg_pre_10d_runup']:+.1f}%")
    table.add_row("Avg Post-1d Move", f"{feat['avg_post_1d_move']:+.1f}%")
    table.add_row("IV Rank", f"{feat['iv_rank']:.0%}")
    table.add_row("Quarters Analyzed", str(feat["quarters_analyzed"]))
    console.print(table)


def print_optimizer_table(result: dict):
    """Display portfolio optimization results."""
    console.print(Panel(
        f"[bold green]Optimal Portfolio[/]  |  "
        f"Return: {result['optimal_return']:+.1f}%  |  "
        f"Vol: {result['optimal_vol']:.1f}%  |  "
        f"Sharpe: {result['optimal_sharpe']:.2f}\n"
        f"[bold yellow]Equal-Weight[/]     |  "
        f"Return: {result['equal_return']:+.1f}%  |  "
        f"Vol: {result['equal_vol']:.1f}%  |  "
        f"Sharpe: {result['equal_sharpe']:.2f}",
        title="Portfolio Optimization",
        border_style="green",
    ))

    table = Table(title="Asset Weights", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Ticker", style="bold cyan")
    table.add_column("Price", justify="right")
    table.add_column("Ann. Return", justify="right")
    table.add_column("Ann. Vol", justify="right")
    table.add_column("Equal Wt", justify="right", style="yellow")
    table.add_column("Optimal Wt", justify="right", style="green bold")

    for ts in result.get("ticker_stats", []):
        ret_color = "green" if ts["annual_return"] >= 0 else "red"
        table.add_row(
            ts["ticker"],
            f"${ts['price']:.2f}",
            f"[{ret_color}]{ts['annual_return']:+.1f}%[/]",
            f"{ts['annual_vol']:.1f}%",
            f"{ts['equal_weight']:.1f}%",
            f"{ts['optimal_weight']:.1f}%",
        )
    console.print(table)


def print_correlation_table(result: dict):
    """Display correlation and clustering results."""
    console.print(Panel(
        f"[bold]Diversification Score:[/] "
        f"{'[green]' if result['diversification_score'] > 0.5 else '[red]'}"
        f"{result['diversification_score']:.2f}[/]  "
        f"(1.0 = perfectly diversified, 0.0 = fully correlated)  |  "
        f"Tickers: {', '.join(result['tickers'])}  |  "
        f"Observations: {result['n_observations']}",
        title="Correlation & Clustering",
        border_style="blue",
    ))

    # High correlation pairs
    pairs = result.get("high_corr_pairs", [])
    if pairs:
        table = Table(title="High Correlation Pairs (|r| > 0.5)", box=box.ROUNDED, padding=(0, 1))
        table.add_column("Ticker 1", style="cyan")
        table.add_column("Ticker 2", style="cyan")
        table.add_column("Correlation", justify="right")

        for p in pairs[:10]:
            c = p["correlation"]
            color = "red" if c > 0.7 else "yellow" if c > 0.5 else "green"
            table.add_row(p["ticker1"], p["ticker2"], f"[{color}]{c:+.3f}[/]")
        console.print(table)

    # Clusters
    clusters = result.get("clusters", [])
    if clusters and len(clusters) > 1:
        table = Table(title="Clusters", box=box.ROUNDED, padding=(0, 1))
        table.add_column("Cluster", style="bold")
        table.add_column("Tickers", style="cyan")
        table.add_column("Avg Internal Corr", justify="right")

        for cl in clusters:
            table.add_row(
                f"#{cl['id'] + 1}",
                ", ".join(cl["tickers"]),
                f"{cl['avg_internal_corr']:.3f}",
            )
        console.print(table)


# ── Market Intelligence Display Functions ──


def print_earnings_calendar(result: dict):
    """Display earnings calendar."""
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return

    console.print(Panel(
        f"[bold]{result['date_range']}[/]  |  {result['total']} earnings announcements",
        title="Earnings Calendar",
        border_style="blue",
    ))

    earnings = result.get("earnings", [])
    if not earnings:
        console.print("[yellow]No earnings scheduled for this period.[/]")
        return

    table = Table(title="Upcoming Earnings", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Date", style="cyan")
    table.add_column("Ticker", style="bold")
    table.add_column("Company")
    table.add_column("Timing", style="dim")
    table.add_column("EPS Est", justify="right")
    table.add_column("Reported", justify="right")
    table.add_column("Surprise", justify="right")
    table.add_column("Mkt Cap", justify="right", style="dim")

    for e in earnings[:25]:
        surprise = ""
        if e["surprise_pct"] is not None:
            color = "green" if e["surprise_pct"] >= 0 else "red"
            surprise = f"[{color}]{e['surprise_pct']:+.1f}%[/]"

        mcap = ""
        if e.get("market_cap"):
            mc = e["market_cap"]
            mcap = f"${mc/1e9:.0f}B" if mc >= 1e9 else f"${mc/1e6:.0f}M"

        table.add_row(
            e["date"],
            e["ticker"],
            e["company"][:35],
            e["timing"],
            f"${e['eps_estimate']:.2f}" if e["eps_estimate"] is not None else "",
            f"${e['reported_eps']:.2f}" if e["reported_eps"] is not None else "",
            surprise,
            mcap,
        )
    console.print(table)


def print_market_movers(result: dict):
    """Display market movers (gainers/losers/actives)."""
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return

    console.print(Panel(
        f"[bold]{result['category']}[/]  |  {result['total']} stocks",
        title="Market Movers",
        border_style="blue",
    ))

    table = Table(title=result["category"], box=box.ROUNDED, padding=(0, 1))
    table.add_column("#", style="dim", justify="right")
    table.add_column("Ticker", style="bold cyan")
    table.add_column("Name")
    table.add_column("Price", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("Change %", justify="right")
    table.add_column("Volume", justify="right", style="dim")
    table.add_column("Mkt Cap", justify="right", style="dim")

    for i, s in enumerate(result["stocks"][:20], 1):
        chg = s.get("change_pct") or 0
        color = "green" if chg >= 0 else "red"
        mc = s.get("market_cap")
        mcap = f"${mc/1e9:.1f}B" if mc and mc >= 1e9 else f"${mc/1e6:.0f}M" if mc else ""

        table.add_row(
            str(i),
            s["ticker"],
            s["name"][:30],
            f"${s['price']:.2f}" if s["price"] else "",
            f"[{color}]{s.get('change', 0):+.2f}[/]",
            f"[{color}]{chg:+.1f}%[/]",
            f"{s['volume']:,}" if s["volume"] else "",
            mcap,
        )
    console.print(table)


def print_sector_performance(result: dict):
    """Display sector performance."""
    console.print(Panel(
        f"[bold]Sector Performance[/]  |  {result['total']} sectors tracked via ETFs",
        title="Sector Heatmap",
        border_style="blue",
    ))

    table = Table(title="Sector Returns", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Sector", style="bold")
    table.add_column("ETF", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("1 Day", justify="right")
    table.add_column("1 Week", justify="right")
    table.add_column("1 Month", justify="right")
    table.add_column("3 Month", justify="right")

    def _color(val):
        if val is None:
            return "N/A"
        color = "green" if val >= 0 else "red"
        return f"[{color}]{val:+.1f}%[/]"

    for s in result["sectors"]:
        table.add_row(
            s["name"],
            s["etf"],
            f"${s['price']:.2f}",
            _color(s["change_1d"]),
            _color(s["change_1w"]),
            _color(s["change_1m"]),
            _color(s["change_3m"]),
        )
    console.print(table)


def print_analyst_ratings(result: dict):
    """Display analyst ratings and price targets."""
    pt = result.get("price_targets", {})
    rb = result.get("ratings_breakdown", {})
    consensus = result.get("consensus", "N/A")
    cons_color = "green" if "BUY" in consensus else "red" if "SELL" in consensus else "yellow"

    # Header panel
    target_info = ""
    if pt.get("mean"):
        target_info = (f"Mean Target: ${pt['mean']:.2f}  |  "
                       f"Range: ${pt.get('low', 0):.2f} - ${pt.get('high', 0):.2f}")
        if pt.get("upside_pct") is not None:
            up_color = "green" if pt["upside_pct"] >= 0 else "red"
            target_info += f"  |  [{up_color}]Upside: {pt['upside_pct']:+.1f}%[/]"

    console.print(Panel(
        f"[bold {cons_color}]Consensus: {consensus}[/]  |  "
        f"Price: ${result['current_price']:.2f}  |  "
        f"{target_info}\n"
        f"Analysts: {rb.get('total_analysts', 'N/A')}  |  "
        f"Strong Buy: {rb.get('strongBuy', 0)}  Buy: {rb.get('buy', 0)}  "
        f"Hold: {rb.get('hold', 0)}  Sell: {rb.get('sell', 0)}  "
        f"Strong Sell: {rb.get('strongSell', 0)}",
        title=f"{result['ticker']} Analyst Ratings",
        border_style=cons_color,
    ))

    # Recent changes
    changes = result.get("recent_changes", [])
    if changes:
        table = Table(title="Recent Upgrades/Downgrades", box=box.ROUNDED, padding=(0, 1))
        table.add_column("Date", style="cyan")
        table.add_column("Firm", style="bold")
        table.add_column("Action")
        table.add_column("Rating")
        table.add_column("Price Target", justify="right")

        for c in changes[:10]:
            action_color = "green" if c["action"] in ("up", "init") else "red" if c["action"] == "down" else "white"
            pt_str = ""
            if c.get("price_target"):
                pt_str = f"${c['price_target']:.0f}"
                if c.get("prior_target"):
                    pt_str += f" (was ${c['prior_target']:.0f})"

            table.add_row(
                c["date"],
                c["firm"],
                f"[{action_color}]{c['action'].upper()}[/]",
                f"{c['to_grade']}",
                pt_str,
            )
        console.print(table)


def print_insider_table(result: dict):
    """Display insider trading activity."""
    sentiment = result["net_sentiment"]
    sent_color = "green" if sentiment == "NET BUYING" else "red" if sentiment == "NET SELLING" else "yellow"

    summary = result.get("summary", {})
    summary_text = ""
    if summary:
        summary_text = (f"6M Buys: {summary.get('total_buys', 'N/A'):,}  |  "
                        f"6M Sells: {summary.get('total_sells', 'N/A'):,}  |  "
                        f"Net: {summary.get('net_shares', 0):,}")

    console.print(Panel(
        f"[bold {sent_color}]{sentiment}[/]  |  {summary_text}",
        title=f"{result['ticker']} Insider Activity",
        border_style=sent_color,
    ))

    transactions = result.get("transactions", [])
    if transactions:
        table = Table(title="Recent Transactions", box=box.ROUNDED, padding=(0, 1))
        table.add_column("Date", style="cyan")
        table.add_column("Insider")
        table.add_column("Position", style="dim")
        table.add_column("Type")
        table.add_column("Shares", justify="right")
        table.add_column("Value", justify="right")

        for t in transactions[:12]:
            trans = t["transaction"]
            color = "green" if "Purchase" in trans or "Buy" in trans else "red" if "Sale" in trans or "Sell" in trans else "white"
            val_str = f"${t['value']:,.0f}" if t.get("value") else ""
            table.add_row(
                t["date"],
                t["insider"][:25],
                t["position"][:20],
                f"[{color}]{trans}[/]",
                f"{t['shares']:,}",
                val_str,
            )
        console.print(table)
    else:
        console.print("[yellow]No recent insider transactions found.[/]")


def print_economic_calendar(result: dict):
    """Display economic calendar."""
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return

    console.print(Panel(
        f"[bold]Upcoming Economic Events[/]  |  {result['total']} events",
        title="Economic Calendar",
        border_style="blue",
    ))

    events = result.get("events", [])
    if not events:
        console.print("[yellow]No upcoming events.[/]")
        return

    table = Table(title="Economic Events", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Date", style="cyan")
    table.add_column("Region", style="dim")
    table.add_column("Event", style="bold")
    table.add_column("Period", style="dim")
    table.add_column("Expected", justify="right")
    table.add_column("Actual", justify="right")
    table.add_column("Last", justify="right", style="dim")

    for e in events[:20]:
        table.add_row(
            e["date"][:10] if e["date"] else "",
            e["region"],
            e["event"][:40],
            e["for_period"],
            e["expected"],
            e["actual"],
            e["last"],
        )
    console.print(table)


# ── Web News Display ──

def print_news_headlines(result: dict, max_rows: int = 25):
    """Display news headlines from crawl_market_news, ticker_news_crawl, or search_financial_news."""
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return

    articles = result.get("articles", [])
    ticker = result.get("ticker", "")
    query = result.get("query", "")
    total = result.get("total", len(articles))
    srcs = result.get("sources_fetched", "")

    if ticker:
        subtitle = f"[cyan]{ticker}[/] — {total} articles"
        title = "Ticker News"
    elif query:
        subtitle = f"[cyan]{query}[/] — {total} articles"
        title = "News Search"
    else:
        subtitle = f"{total} headlines from {srcs} sources"
        title = "Market News"

    console.print(Panel(subtitle, title=title, border_style="cyan"))

    if not articles:
        console.print("[yellow]No articles found.[/]")
        return

    table = Table(box=box.ROUNDED, padding=(0, 1), show_lines=False)
    table.add_column("Date", style="dim", width=14, no_wrap=True)
    table.add_column("Source", style="cyan", width=16, no_wrap=True)
    table.add_column("Headline", style="bold", ratio=3)
    table.add_column("Summary", style="dim", ratio=2)

    for a in articles[:max_rows]:
        date = (a.get("date") or "")[:14]
        source = (a.get("source") or "")[:16]
        title_text = a.get("title", "")[:100]
        summary = (a.get("summary") or "")[:120]
        table.add_row(date, source, title_text, summary)

    console.print(table)

    # Show URLs for top 5 (for fetch_article_content)
    console.print()
    console.print("[dim]Top article URLs (for full-text fetch):[/]")
    for i, a in enumerate(articles[:5], 1):
        url = a.get("url", "")
        title_text = (a.get("title") or "")[:60]
        console.print(f"  [dim]{i}.[/] [blue]{title_text}[/]")
        console.print(f"     [dim]{url}[/]")


def print_article_content(result: dict):
    """Display full article content from fetch_article_content."""
    if not result.get("success"):
        console.print(Panel(
            f"[red]Could not extract content from:[/]\n{result.get('url', '')}\n\n"
            f"[dim]{result.get('content', 'Unknown error')}[/]",
            title="Article Fetch Failed",
            border_style="red",
        ))
        return

    title = result.get("title") or "Article"
    url = result.get("url", "")
    word_count = result.get("word_count", 0)
    content = result.get("content", "")

    console.print(Panel(
        f"[bold]{title}[/]\n[dim]{url}[/]\n[dim]{word_count} words extracted[/]",
        title="Article Content",
        border_style="green",
    ))
    console.print()
    # Print content in wrapped paragraphs
    for para in content.split("  "):
        para = para.strip()
        if para:
            console.print(para)
            console.print()
