"""Chart generation — all matplotlib, save to PNG."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from invtool.config import CHART_DIR

COLORS = {"bullish": "#2ecc71", "bearish": "#e74c3c", "neutral": "#3498db", "accent": "#e67e22"}


def _save(fig, name):
    path = str(CHART_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def chart_technical(technicals: dict, options_df=None) -> str:
    """Price + indicators + RSI + optional payoff chart."""
    df = technicals["df"]
    ticker = technicals["ticker"]
    n_panels = 3 if (options_df is not None and not options_df.empty) else 2
    ratios = [3, 1, 1][:n_panels]

    fig, axes = plt.subplots(n_panels, 1, figsize=(14, 4 * n_panels),
                             gridspec_kw={"height_ratios": ratios})
    if n_panels == 1:
        axes = [axes]
    fig.suptitle(f"{ticker} — Technical Analysis", fontsize=14, fontweight="bold")

    # Price chart
    ax1 = axes[0]
    ax1.plot(df.index, df["Close"], label="Close", color="black", linewidth=1.5)
    ax1.plot(df.index, df["SMA_20"], label="SMA 20", color="blue", linewidth=0.8, linestyle="--")
    ax1.plot(df.index, df["SMA_50"], label="SMA 50", color="red", linewidth=0.8, linestyle="--")
    ax1.fill_between(df.index, df["BB_Upper"], df["BB_Lower"], alpha=0.1, color="gray", label="BB")
    for s in technicals["supports"][-3:]:
        ax1.axhline(y=s, color="green", linewidth=0.6, linestyle=":", alpha=0.7)
    if options_df is not None and not options_df.empty:
        for _, row in options_df.head(3).iterrows():
            ax1.axhline(y=row["strike"], color="orange", linewidth=1, linestyle="-.", alpha=0.7)
    ax1.set_ylabel("Price ($)")
    ax1.legend(loc="upper left", fontsize=7)
    ax1.grid(True, alpha=0.3)

    # RSI
    ax2 = axes[1]
    ax2.plot(df.index, df["RSI"], color="purple", linewidth=1)
    ax2.axhline(70, color="red", linewidth=0.7, linestyle="--")
    ax2.axhline(30, color="green", linewidth=0.7, linestyle="--")
    ax2.fill_between(df.index, 30, 70, alpha=0.05, color="gray")
    ax2.set_ylabel("RSI")
    ax2.set_ylim(10, 90)
    ax2.grid(True, alpha=0.3)

    # Payoff diagram
    if n_panels == 3:
        ax3 = axes[2]
        best = options_df.iloc[0]
        strike = best["strike"]
        premium = best["premium"]
        cp = technicals["current_price"]
        prices = np.linspace(strike * 0.6, cp * 1.3, 200)
        payoff = np.where(prices >= strike, premium, premium - (strike - prices))
        ax3.plot(prices, payoff * 100, color="blue", linewidth=1.5)
        ax3.axhline(0, color="black", linewidth=0.5)
        ax3.axvline(cp, color="gray", linewidth=0.8, linestyle="--", label=f"Current ${cp:.2f}")
        ax3.axvline(strike, color="orange", linewidth=0.8, linestyle="--", label=f"Strike ${strike:.2f}")
        ax3.fill_between(prices, payoff * 100, 0, where=(payoff > 0), alpha=0.15, color="green")
        ax3.fill_between(prices, payoff * 100, 0, where=(payoff < 0), alpha=0.15, color="red")
        ax3.set_xlabel("Stock Price at Expiration")
        ax3.set_ylabel("P/L ($)")
        ax3.set_title(f"Sell Put: {best['expiration']} ${strike:.0f}P @ ${premium:.2f}")
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    return _save(fig, f"{ticker}_technical")


def chart_portfolio_pnl(positions: list) -> str:
    """Horizontal bar chart of P&L by position."""
    fig, ax = plt.subplots(figsize=(10, max(4, len(positions) * 0.8)))
    tickers = [p["ticker"] for p in positions]
    pnls = [p["shares"] * (p["price"] - p["cost"]) for p in positions]
    colors = [COLORS["bullish"] if x >= 0 else COLORS["bearish"] for x in pnls]

    bars = ax.barh(tickers, pnls, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars, pnls):
        offset = 10 if val >= 0 else -10
        ax.text(bar.get_width() + offset, bar.get_y() + bar.get_height() / 2,
                f"${val:,.0f}", ha="left" if val >= 0 else "right", va="center", fontsize=10)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Unrealized P&L ($)")
    ax.set_title("Portfolio P&L by Position")
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    return _save(fig, "portfolio_pnl")


def chart_portfolio_allocation(positions: list) -> str:
    """Pie chart of portfolio allocation."""
    fig, ax = plt.subplots(figsize=(8, 8))
    labels = [p["ticker"] for p in positions]
    values = [p["shares"] * p["price"] for p in positions]
    total = sum(values)
    pcts = [v / total * 100 for v in values]

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct="%1.0f%%",
        colors=plt.cm.Set3(np.linspace(0, 1, len(labels))),
        startangle=90, textprops={"fontsize": 11},
    )
    ax.set_title(f"Portfolio Allocation (Total: ${total:,.0f})")

    plt.tight_layout()
    return _save(fig, "portfolio_allocation")


def chart_earnings_behavior(df: pd.DataFrame, ticker: str) -> str:
    """4-panel earnings behavior chart."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(f"{ticker} Earnings Behavior Analysis", fontsize=14, fontweight="bold")

    quarters = df["quarter"]
    x = np.arange(len(quarters))
    width = 0.35

    # Pre vs Post
    ax1 = axes[0][0]
    pre_10d = df.get("pre_10d", pd.Series([0] * len(df))).fillna(0) * 100
    post_5d = df.get("post_5d", pd.Series([0] * len(df))).fillna(0) * 100
    ax1.bar(x - width / 2, pre_10d, width, label="10d Before", color="#3498db", alpha=0.8)
    ax1.bar(x + width / 2, post_5d, width, label="5d After", color="#e74c3c", alpha=0.8)
    ax1.axhline(0, color="black", linewidth=0.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels(quarters, rotation=45, ha="right", fontsize=7)
    ax1.set_ylabel("% Change")
    ax1.set_title("Pre vs Post Earnings")
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.3)

    # Next-day move
    ax2 = axes[0][1]
    post_1d = df.get("post_1d", pd.Series([0] * len(df))).fillna(0) * 100
    colors = [COLORS["bullish"] if v >= 0 else COLORS["bearish"] for v in post_1d]
    ax2.bar(x, post_1d, color=colors, edgecolor="black", linewidth=0.5)
    for i, v in enumerate(post_1d):
        ax2.text(i, v + (0.3 if v >= 0 else -0.8), f"{v:+.1f}%", ha="center", fontsize=7)
    ax2.axhline(0, color="black", linewidth=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(quarters, rotation=45, ha="right", fontsize=7)
    ax2.set_ylabel("Next-Day % Change")
    ax2.set_title("Post-Earnings Next-Day Move")
    ax2.grid(axis="y", alpha=0.3)

    # Average return curve
    ax3 = axes[1][0]
    windows_pre = [-30, -20, -10, -5, -1]
    windows_post = [1, 2, 5, 10, 20, 30]
    all_windows = windows_pre + [0] + windows_post
    avg_returns = []
    for w in windows_pre:
        col = f"pre_{abs(w)}d"
        avg_returns.append(df[col].mean() * 100 if col in df.columns else 0)
    avg_returns.append(0)
    for w in windows_post:
        col = f"post_{w}d"
        avg_returns.append(df[col].mean() * 100 if col in df.columns else 0)
    ax3.plot(all_windows, avg_returns, "b-o", linewidth=2, markersize=5)
    ax3.axhline(0, color="black", linewidth=0.5)
    ax3.axvline(0, color="red", linewidth=1, linestyle="--", label="Earnings Day")
    ax3.set_xlabel("Trading Days Relative to Earnings")
    ax3.set_ylabel("Avg Cumulative Return (%)")
    ax3.set_title("Average Return Curve Around Earnings")
    ax3.legend(fontsize=8)
    ax3.grid(alpha=0.3)

    # EPS surprise vs move scatter
    ax4 = axes[1][1]
    eps_surp = df["eps_surprise"] * 100
    post_1d_v = df.get("post_1d", pd.Series([0] * len(df))).fillna(0) * 100
    sc = [COLORS["bullish"] if v >= 0 else COLORS["bearish"] for v in post_1d_v]
    ax4.scatter(eps_surp, post_1d_v, c=sc, s=80, edgecolors="black", linewidth=0.5)
    if len(eps_surp) > 2:
        z = np.polyfit(eps_surp, post_1d_v, 1)
        p = np.poly1d(z)
        xl = np.linspace(eps_surp.min(), eps_surp.max(), 100)
        ax4.plot(xl, p(xl), "r--", linewidth=1, alpha=0.5)
    ax4.set_xlabel("EPS Surprise (%)")
    ax4.set_ylabel("Next-Day Return (%)")
    ax4.set_title("EPS Surprise vs Stock Move")
    ax4.grid(alpha=0.3)

    plt.tight_layout()
    return _save(fig, f"{ticker}_earnings")


def chart_recovery_timeline(total_loss: float, monthly_income: float) -> str:
    """Recovery timeline projection."""
    fig, ax = plt.subplots(figsize=(10, 5))
    months = list(range(0, 25))
    remaining = [abs(total_loss) - m * monthly_income for m in months]

    ax.plot(months, remaining, color="blue", linewidth=2)
    ax.axhline(0, color="green", linewidth=1.5, linestyle="--", label="Fully Recovered")
    ax.fill_between(months, remaining, 0, where=[r > 0 for r in remaining], alpha=0.1, color="red")
    ax.fill_between(months, remaining, 0, where=[r <= 0 for r in remaining], alpha=0.1, color="green")
    ax.set_xlabel("Months")
    ax.set_ylabel("Remaining Loss ($)")
    ax.set_title(f"Recovery Timeline (~${monthly_income:.0f}/month income)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    return _save(fig, "recovery_timeline")


# ── AI Analytics Charts ──


def chart_sentiment(result: dict) -> str:
    """Sentiment bar chart for news headlines."""
    headlines = result.get("headlines", [])
    if not headlines:
        return ""

    fig, axes = plt.subplots(1, 2, figsize=(14, max(4, len(headlines[:12]) * 0.5)),
                             gridspec_kw={"width_ratios": [3, 1]})

    # Left: headline scores bar chart
    ax1 = axes[0]
    titles = [h["title"][:60] + ("..." if len(h["title"]) > 60 else "") for h in headlines[:12]]
    scores = [h["score"] for h in headlines[:12]]
    colors = [COLORS["bullish"] if s > 0.1 else COLORS["bearish"] if s < -0.1 else COLORS["neutral"]
              for s in scores]

    y = np.arange(len(titles))
    ax1.barh(y, scores, color=colors, edgecolor="black", linewidth=0.3)
    ax1.set_yticks(y)
    ax1.set_yticklabels(titles, fontsize=7)
    ax1.set_xlabel("Sentiment Score")
    ax1.set_title(f"{result['ticker']} News Sentiment")
    ax1.axvline(0, color="black", linewidth=0.5)
    ax1.set_xlim(-1.1, 1.1)
    ax1.grid(axis="x", alpha=0.3)
    ax1.invert_yaxis()

    # Right: summary gauge
    ax2 = axes[1]
    overall = result["overall_score"]
    label = result["label"]
    color = COLORS["bullish"] if overall > 0.15 else COLORS["bearish"] if overall < -0.15 else COLORS["neutral"]

    # Simple gauge as colored bar
    ax2.barh([0], [overall], color=color, height=0.4, edgecolor="black")
    ax2.set_xlim(-1, 1)
    ax2.set_yticks([])
    ax2.axvline(0, color="black", linewidth=0.8)
    ax2.set_title(f"Overall: {label}\n({overall:+.2f})", fontsize=12, fontweight="bold")
    ax2.text(0, -0.5, f"Bullish: {result['bullish_count']} | Bearish: {result['bearish_count']}",
             ha="center", fontsize=9)
    ax2.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    return _save(fig, f"{result['ticker']}_sentiment")


def chart_forecast(result: dict) -> str:
    """Price history + forecast projection with confidence bands."""
    hist_df = result["hist_df"]
    proj_df = result["proj_df"]

    fig, ax = plt.subplots(figsize=(14, 6))

    # Historical prices
    ax.plot(hist_df.index, hist_df["Close"], color="black", linewidth=1.5, label="Historical")

    # Forecast line
    ax.plot(proj_df.index, proj_df["price"], color="blue", linewidth=1.5, linestyle="--",
            label="Forecast")

    # 1σ band
    ax.fill_between(proj_df.index, proj_df["low_1s"], proj_df["high_1s"],
                     alpha=0.2, color="blue", label="68% CI (1σ)")

    # 2σ band
    ax.fill_between(proj_df.index, proj_df["low_2s"], proj_df["high_2s"],
                     alpha=0.1, color="blue", label="95% CI (2σ)")

    # Forecast points
    for fc in result["forecasts"]:
        idx = proj_df.index[min(fc["days"] - 1, len(proj_df) - 1)]
        ax.plot(idx, fc["price"], "ro", markersize=8)
        ax.annotate(f"${fc['price']:.0f} ({fc['change_pct']:+.1f}%)",
                    xy=(idx, fc["price"]), xytext=(5, 10),
                    textcoords="offset points", fontsize=8,
                    arrowprops=dict(arrowstyle="->", color="red"))

    ax.set_xlabel("Date")
    ax.set_ylabel("Price ($)")
    ax.set_title(f"{result['ticker']} — Price Forecast (R²={result['r_squared']:.3f}, "
                 f"Trend: {result['trend_annual']:+.1f}%/yr)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    return _save(fig, f"{result['ticker']}_forecast")


def chart_anomaly(result: dict) -> str:
    """Price chart with anomaly markers."""
    df = result.get("df")
    if df is None or df.empty:
        return ""

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [2, 1]})

    # Price with anomaly markers
    ax1 = axes[0]
    ax1.plot(df.index, df["Close"], color="black", linewidth=1)
    ax1.set_ylabel("Price ($)")
    ax1.set_title(f"{result['ticker']} — Anomaly Detection")

    # Mark anomalies on price chart
    for a in result["anomalies"]:
        try:
            date = pd.Timestamp(a["date"])
            if date in df.index:
                price = df.loc[date, "Close"]
                color = COLORS["bearish"] if a["z_score"] < 0 else COLORS["accent"]
                ax1.plot(date, price, "v" if a["z_score"] < 0 else "^",
                         color=color, markersize=12, zorder=5)
                ax1.annotate(a["type"].replace("_", " "), xy=(date, price),
                             xytext=(0, 15), textcoords="offset points",
                             fontsize=6, ha="center", color=color)
        except Exception:
            pass
    ax1.grid(alpha=0.3)

    # Volume with z-score coloring
    ax2 = axes[1]
    if "Volume" in df.columns:
        vol_colors = []
        for _, row in df.iterrows():
            z = row.get("vol_z", 0)
            if pd.notna(z) and abs(z) >= 2:
                vol_colors.append(COLORS["accent"])
            else:
                vol_colors.append(COLORS["neutral"])
        ax2.bar(df.index, df["Volume"], color=vol_colors, width=1, alpha=0.7)
        ax2.set_ylabel("Volume")
        ax2.set_title("Volume (orange = anomalous)")
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    return _save(fig, f"{result['ticker']}_anomaly")


def chart_montecarlo(result: dict, horizon_idx=0) -> str:
    """Monte Carlo simulation histogram with VaR lines."""
    h = result["horizons"][horizon_idx]
    sims = np.array(h["simulations"])

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: histogram
    ax1 = axes[0]
    ax1.hist(sims, bins=100, color=COLORS["neutral"], alpha=0.7, edgecolor="black", linewidth=0.3)
    ax1.axvline(h["var_95"], color="red", linewidth=2, linestyle="--",
                label=f"VaR 95%: ${h['var_95']:,.0f}")
    ax1.axvline(h["var_99"], color="darkred", linewidth=2, linestyle=":",
                label=f"VaR 99%: ${h['var_99']:,.0f}")
    ax1.axvline(0, color="black", linewidth=1)
    ax1.set_xlabel("Portfolio P&L ($)")
    ax1.set_ylabel("Frequency")
    ax1.set_title(f"{h['days']}-Day Portfolio Return Distribution\n"
                  f"({result['n_sims']:,} simulations)")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    # Right: summary stats
    ax2 = axes[1]
    ax2.axis("off")
    stats_text = (
        f"Portfolio Value: ${result['portfolio_value']:,.0f}\n\n"
        f"── {h['days']}-Day Risk Metrics ──\n\n"
        f"VaR (95%):   ${h['var_95']:,.0f}\n"
        f"VaR (99%):   ${h['var_99']:,.0f}\n"
        f"CVaR (95%):  ${h['cvar_95']:,.0f}\n\n"
        f"Prob of Loss:      {h['prob_loss']:.1%}\n"
        f"Prob of >10% Loss: {h['prob_loss_10pct']:.1%}\n\n"
        f"Median Return: {h['median_return']:+.2f}%\n"
        f"Best Case (95th):  ${h['best_case']:,.0f}\n"
        f"Worst Case (5th):  ${h['worst_case']:,.0f}\n\n"
        f"Avg Max Drawdown: {h['avg_max_drawdown']:.1f}%"
    )
    ax2.text(0.1, 0.95, stats_text, transform=ax2.transAxes, fontsize=11,
             verticalalignment="top", fontfamily="monospace",
             bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    plt.tight_layout()
    return _save(fig, "montecarlo_risk")


def chart_efficient_frontier(result: dict) -> str:
    """Efficient frontier scatter plot."""
    fig, ax = plt.subplots(figsize=(10, 7))

    # Frontier curve
    if result.get("frontier"):
        vols = [p["volatility"] for p in result["frontier"]]
        rets = [p["return"] for p in result["frontier"]]
        ax.plot(vols, rets, "b-", linewidth=2, label="Efficient Frontier")
        ax.scatter(vols, rets, c=rets, cmap="RdYlGn", s=30, zorder=3)

    # Individual assets
    for ts in result.get("ticker_stats", []):
        ax.scatter(ts["annual_vol"], ts["annual_return"], s=100,
                   edgecolors="black", linewidth=1, zorder=4)
        ax.annotate(ts["ticker"], xy=(ts["annual_vol"], ts["annual_return"]),
                    xytext=(5, 5), textcoords="offset points", fontsize=9, fontweight="bold")

    # Optimal portfolio
    ax.scatter(result["optimal_vol"], result["optimal_return"], marker="*",
               s=300, c="gold", edgecolors="black", linewidth=1, zorder=5,
               label=f"Optimal (Sharpe={result['optimal_sharpe']:.2f})")

    # Equal-weight portfolio
    ax.scatter(result["equal_vol"], result["equal_return"], marker="D",
               s=150, c="red", edgecolors="black", linewidth=1, zorder=5,
               label=f"Equal-Weight (Sharpe={result['equal_sharpe']:.2f})")

    ax.set_xlabel("Annual Volatility (%)")
    ax.set_ylabel("Annual Return (%)")
    ax.set_title("Efficient Frontier — Portfolio Optimization")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    return _save(fig, "efficient_frontier")


def chart_correlation(result: dict) -> str:
    """Correlation heatmap with clustering."""
    tickers = result["tickers"]
    corr = np.array(result["corr_matrix_list"])
    n = len(tickers)

    fig, ax = plt.subplots(figsize=(max(8, n * 1.2), max(6, n)))

    # Heatmap
    im = ax.imshow(corr, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
    fig.colorbar(im, ax=ax, label="Correlation", shrink=0.8)

    # Labels
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(tickers, rotation=45, ha="right", fontsize=10)
    ax.set_yticklabels(tickers, fontsize=10)

    # Annotate cells
    for i in range(n):
        for j in range(n):
            color = "white" if abs(corr[i, j]) > 0.6 else "black"
            ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center",
                    fontsize=9, color=color)

    # Cluster borders
    clusters = result.get("clusters", [])
    if len(clusters) > 1:
        for cl in clusters:
            members = cl["tickers"]
            indices = [tickers.index(t) for t in members if t in tickers]
            if indices:
                min_i, max_i = min(indices), max(indices)
                rect = plt.Rectangle((min_i - 0.5, min_i - 0.5),
                                     max_i - min_i + 1, max_i - min_i + 1,
                                     linewidth=2, edgecolor="blue", facecolor="none")
                ax.add_patch(rect)

    ax.set_title(f"Correlation Matrix (Diversification Score: {result['diversification_score']:.2f})")

    plt.tight_layout()
    return _save(fig, "correlation_heatmap")


def chart_sector_performance(result: dict) -> str:
    """Horizontal bar chart of sector performance."""
    sectors = result.get("sectors", [])
    if not sectors:
        return ""

    fig, ax = plt.subplots(figsize=(12, max(5, len(sectors) * 0.6)))

    names = [s["name"] for s in sectors]
    changes = [s.get("change_1d") or 0 for s in sectors]
    colors = [COLORS["bullish"] if c >= 0 else COLORS["bearish"] for c in changes]

    y = np.arange(len(names))
    bars = ax.barh(y, changes, color=colors, edgecolor="black", linewidth=0.3)

    for bar, val in zip(bars, changes):
        offset = 0.1 if val >= 0 else -0.1
        ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
                f"{val:+.1f}%", ha="left" if val >= 0 else "right",
                va="center", fontsize=9)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("1-Day Return (%)")
    ax.set_title("Sector Performance (Today)")
    ax.grid(axis="x", alpha=0.3)
    ax.invert_yaxis()

    plt.tight_layout()
    return _save(fig, "sector_performance")
