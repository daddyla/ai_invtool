#!/usr/bin/env python3
"""
Figma (FIG) Stock Analysis & Sell Put Option Strategy
=====================================================
Analyzes FIG stock technicals and screens the options chain
to find attractive cash-secured put selling opportunities.

Requirements: pip install yfinance pandas numpy matplotlib scipy
"""

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from scipy.stats import norm

# ─────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────
TICKER = "FIG"
RISK_FREE_RATE = 0.043  # ~4.3% (US 10-yr yield approx)
MIN_OPEN_INTEREST = 50  # minimum liquidity filter
MIN_DAYS_TO_EXPIRY = 14  # skip weeklies expiring too soon
MAX_DAYS_TO_EXPIRY = 90  # focus on near-term expirations
TARGET_DELTA = -0.25     # typical sell-put sweet spot (~75% prob OTM)
MAX_ASSIGNMENT_RISK_PCT = 0.10  # max 10% below current price for conservative

pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 200)
pd.set_option("display.float_format", "{:.4f}".format)


# ─────────────────────────────────────────────────────
# 1. Fetch Stock Data
# ─────────────────────────────────────────────────────
def fetch_stock_data(ticker: str) -> tuple:
    """Download historical price data and basic info."""
    stock = yf.Ticker(ticker)
    info = stock.info

    # Get ~6 months of daily data for technical analysis
    hist = stock.history(period="6mo", interval="1d")
    if hist.empty:
        raise ValueError(f"No historical data returned for {ticker}")

    print(f"\n{'='*70}")
    print(f"  FIGMA (FIG) STOCK ANALYSIS  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")

    current_price = hist["Close"].iloc[-1]
    print(f"\n  Current Price:      ${current_price:.2f}")
    print(f"  52-Week High:       ${info.get('fiftyTwoWeekHigh', 'N/A')}")
    print(f"  52-Week Low:        ${info.get('fiftyTwoWeekLow', 'N/A')}")
    print(f"  Market Cap:         ${info.get('marketCap', 0)/1e9:.2f}B")
    print(f"  Avg Volume:         {info.get('averageVolume', 0):,.0f}")
    print(f"  Beta:               {info.get('beta', 'N/A')}")

    return stock, hist, info, current_price


# ─────────────────────────────────────────────────────
# 2. Technical Analysis
# ─────────────────────────────────────────────────────
def technical_analysis(hist: pd.DataFrame, current_price: float) -> dict:
    """Compute key technical indicators and support levels."""
    df = hist.copy()

    # Moving Averages
    df["SMA_20"] = df["Close"].rolling(20).mean()
    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["EMA_12"] = df["Close"].ewm(span=12).mean()
    df["EMA_26"] = df["Close"].ewm(span=26).mean()

    # MACD
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    df["MACD_Hist"] = df["MACD"] - df["Signal"]

    # RSI (14-period)
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # Bollinger Bands (20, 2)
    df["BB_Mid"] = df["Close"].rolling(20).mean()
    bb_std = df["Close"].rolling(20).std()
    df["BB_Upper"] = df["BB_Mid"] + 2 * bb_std
    df["BB_Lower"] = df["BB_Mid"] - 2 * bb_std

    # Average True Range (14-period)
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR_14"] = tr.rolling(14).mean()

    # Historical Volatility (20-day annualized)
    df["Log_Return"] = np.log(df["Close"] / df["Close"].shift(1))
    hist_vol_20 = df["Log_Return"].rolling(20).std() * np.sqrt(252)

    # Support levels: recent swing lows
    lookback = min(60, len(df))
    recent = df.tail(lookback)
    support_levels = []

    # Simple swing-low detection (local minima within 5-day window)
    for i in range(2, len(recent) - 2):
        if (recent["Low"].iloc[i] <= recent["Low"].iloc[i-1] and
            recent["Low"].iloc[i] <= recent["Low"].iloc[i-2] and
            recent["Low"].iloc[i] <= recent["Low"].iloc[i+1] and
            recent["Low"].iloc[i] <= recent["Low"].iloc[i+2]):
            support_levels.append(round(recent["Low"].iloc[i], 2))

    # Also add 52-week low and round numbers near price
    all_time_low = df["Low"].min()
    support_levels.append(round(all_time_low, 2))

    # Round number supports
    for level in range(int(current_price * 0.7), int(current_price * 1.0), 1):
        if level % 5 == 0:  # $5 increments
            support_levels.append(float(level))

    support_levels = sorted(set([s for s in support_levels if s < current_price]))

    latest = df.iloc[-1]

    print(f"\n{'─'*70}")
    print(f"  TECHNICAL INDICATORS")
    print(f"{'─'*70}")
    print(f"  SMA 20:             ${latest['SMA_20']:.2f}  {'▲' if current_price > latest['SMA_20'] else '▼'}")
    print(f"  SMA 50:             ${latest['SMA_50']:.2f}  {'▲' if current_price > latest['SMA_50'] else '▼'}")
    print(f"  RSI (14):           {latest['RSI']:.1f}  {'(Overbought)' if latest['RSI'] > 70 else '(Oversold)' if latest['RSI'] < 30 else '(Neutral)'}")
    print(f"  MACD:               {latest['MACD']:.4f}  Signal: {latest['Signal']:.4f}")
    print(f"  MACD Histogram:     {latest['MACD_Hist']:.4f}  {'(Bullish)' if latest['MACD_Hist'] > 0 else '(Bearish)'}")
    print(f"  Bollinger Upper:    ${latest['BB_Upper']:.2f}")
    print(f"  Bollinger Lower:    ${latest['BB_Lower']:.2f}")
    print(f"  ATR (14):           ${latest['ATR_14']:.2f}")
    print(f"  Hist Vol (20d ann): {hist_vol_20.iloc[-1]*100:.1f}%")
    print(f"  Key Support Levels: {support_levels[-5:]}")

    # Trend assessment
    trend_signals = []
    if current_price > latest["SMA_20"]:
        trend_signals.append("+SMA20")
    else:
        trend_signals.append("-SMA20")
    if current_price > latest["SMA_50"]:
        trend_signals.append("+SMA50")
    else:
        trend_signals.append("-SMA50")
    if latest["MACD_Hist"] > 0:
        trend_signals.append("+MACD")
    else:
        trend_signals.append("-MACD")
    if latest["RSI"] > 50:
        trend_signals.append("+RSI")
    else:
        trend_signals.append("-RSI")

    bullish = sum(1 for s in trend_signals if s.startswith("+"))
    total = len(trend_signals)
    trend = "BULLISH" if bullish >= 3 else "BEARISH" if bullish <= 1 else "NEUTRAL"

    print(f"\n  Trend Signals:      {' | '.join(trend_signals)}")
    print(f"  Overall Trend:      {trend} ({bullish}/{total} bullish)")

    return {
        "df": df,
        "support_levels": support_levels,
        "current_price": current_price,
        "hist_vol": hist_vol_20.iloc[-1],
        "atr": latest["ATR_14"],
        "rsi": latest["RSI"],
        "trend": trend,
        "sma_20": latest["SMA_20"],
        "sma_50": latest["SMA_50"],
        "bb_lower": latest["BB_Lower"],
    }


# ─────────────────────────────────────────────────────
# 3. Options Chain Analysis
# ─────────────────────────────────────────────────────
def black_scholes_delta_put(S, K, T, r, sigma):
    """Calculate Black-Scholes delta for a put option."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1) - 1  # put delta is negative


def prob_otm_at_expiry(S, K, T, r, sigma):
    """Probability that put expires OTM (stock stays above K)."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d2 = (np.log(S / K) + (r - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d2)  # P(S_T > K)


def analyze_options_chain(stock, current_price: float, technicals: dict) -> pd.DataFrame:
    """Fetch and analyze put options for sell-put strategy."""
    try:
        expirations = stock.options
    except Exception as e:
        print(f"\n  ⚠ Could not fetch options expirations: {e}")
        return pd.DataFrame()

    if not expirations:
        print("\n  ⚠ No options available for this ticker.")
        return pd.DataFrame()

    print(f"\n{'─'*70}")
    print(f"  OPTIONS CHAIN ANALYSIS — SELL PUT SCREENING")
    print(f"{'─'*70}")
    print(f"  Available expirations: {len(expirations)}")

    today = datetime.now().date()
    all_puts = []

    for exp_str in expirations:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        dte = (exp_date - today).days

        if dte < MIN_DAYS_TO_EXPIRY or dte > MAX_DAYS_TO_EXPIRY:
            continue

        try:
            chain = stock.option_chain(exp_str)
            puts = chain.puts.copy()
        except Exception:
            continue

        if puts.empty:
            continue

        puts["expiration"] = exp_str
        puts["DTE"] = dte
        puts["T"] = dte / 365.0

        all_puts.append(puts)

    if not all_puts:
        print("  ⚠ No puts found within the target DTE range.")
        return pd.DataFrame()

    df = pd.concat(all_puts, ignore_index=True)

    # Filter: OTM puts only (strike < current price)
    df = df[df["strike"] < current_price].copy()

    # Filter: minimum open interest for liquidity
    df = df[df["openInterest"] >= MIN_OPEN_INTEREST].copy()

    # Filter: reasonable bid (must have a bid to sell)
    df = df[df["bid"] > 0.01].copy()

    if df.empty:
        print("  ⚠ No qualifying put options found after filtering.")
        return pd.DataFrame()

    # ── Compute strategy metrics ──
    S = current_price
    r = RISK_FREE_RATE

    # Use implied vol from chain where available, fallback to historical
    df["iv"] = df["impliedVolatility"].fillna(technicals["hist_vol"])

    df["delta"] = df.apply(
        lambda row: black_scholes_delta_put(S, row["strike"], row["T"], r, row["iv"]),
        axis=1,
    )

    df["prob_otm"] = df.apply(
        lambda row: prob_otm_at_expiry(S, row["strike"], row["T"], r, row["iv"]),
        axis=1,
    )

    # Use bid price as the premium received (conservative — you sell at the bid)
    df["premium"] = df["bid"]

    # Annualized return on capital (if put expires OTM)
    # Capital required = strike * 100 (cash-secured put)
    df["return_on_capital"] = df["premium"] / df["strike"]
    df["annualized_return"] = df["return_on_capital"] * (365.0 / df["DTE"])

    # Break-even price (strike - premium received)
    df["breakeven"] = df["strike"] - df["premium"]

    # Downside cushion (% below current price to breakeven)
    df["downside_cushion"] = (S - df["breakeven"]) / S

    # Distance from current price to strike
    df["otm_pct"] = (S - df["strike"]) / S

    # Expected return = prob_otm * premium - prob_itm * (expected_loss)
    # Simplified: expected_value = prob_otm * premium - (1 - prob_otm) * max_loss_estimate
    df["max_loss_per_share"] = df["strike"] - df["premium"]  # worst case: stock -> 0
    df["expected_value"] = (
        df["prob_otm"] * df["premium"]
        - (1 - df["prob_otm"]) * (df["strike"] * 0.15)  # assume ~15% avg drawdown if ITM
    )

    # ── Scoring system ──
    # Higher score = more attractive put to sell
    df["score"] = (
        df["annualized_return"] * 30          # reward higher premium yield
        + df["prob_otm"] * 25                 # reward higher probability of profit
        + df["downside_cushion"] * 20         # reward more cushion
        + np.log1p(df["openInterest"]) * 3    # reward liquidity
        + (df["expected_value"] > 0).astype(float) * 10  # bonus for +EV
    )

    # Penalty if strike is above key support (less margin of safety)
    for support in technicals["support_levels"]:
        df.loc[df["strike"] > support, "score"] -= 1

    # Sort by score descending
    df = df.sort_values("score", ascending=False)

    return df


# ─────────────────────────────────────────────────────
# 4. Display Recommendations
# ─────────────────────────────────────────────────────
def display_recommendations(df: pd.DataFrame, current_price: float, technicals: dict):
    """Print the top sell-put candidates."""
    if df.empty:
        print("\n  No recommendations available.")
        return

    top = df.head(15)

    print(f"\n  Showing top {len(top)} sell-put candidates (sorted by composite score):")
    print(f"  Current FIG Price: ${current_price:.2f}")
    print()

    cols = [
        "expiration", "DTE", "strike", "bid", "ask", "iv",
        "delta", "prob_otm", "annualized_return", "breakeven",
        "downside_cushion", "openInterest", "volume", "score",
    ]

    display = top[cols].copy()
    display.columns = [
        "Expiry", "DTE", "Strike", "Bid", "Ask", "IV",
        "Delta", "P(OTM)", "Ann.Ret%", "B/E",
        "Cushion%", "OI", "Vol", "Score",
    ]
    display["IV"] = display["IV"].map("{:.1%}".format)
    display["Delta"] = display["Delta"].map("{:.3f}".format)
    display["P(OTM)"] = display["P(OTM)"].map("{:.1%}".format)
    display["Ann.Ret%"] = display["Ann.Ret%"].map("{:.1%}".format)
    display["Cushion%"] = display["Cushion%"].map("{:.1%}".format)
    display["Strike"] = display["Strike"].map("${:.2f}".format)
    display["Bid"] = display["Bid"].map("${:.2f}".format)
    display["Ask"] = display["Ask"].map("${:.2f}".format)
    display["B/E"] = display["B/E"].map("${:.2f}".format)
    display["OI"] = display["OI"].astype(int)
    display["Vol"] = display["Vol"].fillna(0).astype(int)
    display["Score"] = display["Score"].map("{:.1f}".format)

    print(display.to_string(index=False))

    # ── Top Pick Summary ──
    best = df.iloc[0]
    print(f"\n{'─'*70}")
    print(f"  ★  TOP RECOMMENDATION")
    print(f"{'─'*70}")
    print(f"  Action:             SELL PUT")
    print(f"  Ticker:             FIG (Figma)")
    print(f"  Expiration:         {best['expiration']}  ({best['DTE']:.0f} DTE)")
    print(f"  Strike:             ${best['strike']:.2f}")
    print(f"  Premium (bid):      ${best['premium']:.2f} per share  (${best['premium']*100:.0f} per contract)")
    print(f"  Break-even:         ${best['breakeven']:.2f}")
    print(f"  Downside Cushion:   {best['downside_cushion']:.1%} below current price")
    print(f"  Prob. of Profit:    {best['prob_otm']:.1%}")
    print(f"  Delta:              {best['delta']:.3f}")
    print(f"  Implied Vol:        {best['iv']:.1%}")
    print(f"  Ann. Return (OTM):  {best['annualized_return']:.1%}")
    print(f"  Capital Required:   ${best['strike']*100:.0f} per contract (cash-secured)")
    print(f"  Max Profit:         ${best['premium']*100:.0f} per contract")

    # Risk summary
    print(f"\n{'─'*70}")
    print(f"  RISK ASSESSMENT")
    print(f"{'─'*70}")

    if best["prob_otm"] > 0.80:
        risk_level = "LOW"
    elif best["prob_otm"] > 0.65:
        risk_level = "MODERATE"
    else:
        risk_level = "HIGH"

    print(f"  Risk Level:         {risk_level}")
    print(f"  If Assigned:        Buy 100 shares of FIG at ${best['strike']:.2f}")
    print(f"  Effective Cost:     ${best['breakeven']:.2f}/share (strike - premium)")
    print(f"  vs Current Price:   {best['downside_cushion']:.1%} discount to ${current_price:.2f}")

    trend = technicals["trend"]
    print(f"\n  Trend Context:      {trend}")
    if trend == "BEARISH":
        print(f"  ⚠  Caution: Stock is in a BEARISH trend. Consider:")
        print(f"     - Using lower strike prices for wider margin of safety")
        print(f"     - Smaller position sizes")
        print(f"     - Shorter DTE to reduce exposure time")
    elif trend == "NEUTRAL":
        print(f"  ℹ  Neutral trend — standard sell-put approach is reasonable.")
    else:
        print(f"  ✓  Bullish trend favors selling puts (stock likely stays above strike).")

    print(f"\n  Support Levels:     {technicals['support_levels'][-5:]}")
    if best["strike"] <= technicals.get("bb_lower", 0):
        print(f"  ✓  Strike is at/below Bollinger Lower Band — strong support zone.")


# ─────────────────────────────────────────────────────
# 5. Charting
# ─────────────────────────────────────────────────────
def plot_analysis(technicals: dict, options_df: pd.DataFrame, current_price: float):
    """Generate visual charts for the analysis."""
    df = technicals["df"]

    fig, axes = plt.subplots(3, 1, figsize=(14, 12), gridspec_kw={"height_ratios": [3, 1, 1]})
    fig.suptitle(f"FIG (Figma) — Sell Put Strategy Analysis", fontsize=14, fontweight="bold")

    # ── Chart 1: Price with technicals ──
    ax1 = axes[0]
    ax1.plot(df.index, df["Close"], label="Close", color="black", linewidth=1.5)
    ax1.plot(df.index, df["SMA_20"], label="SMA 20", color="blue", linewidth=0.8, linestyle="--")
    ax1.plot(df.index, df["SMA_50"], label="SMA 50", color="red", linewidth=0.8, linestyle="--")
    ax1.fill_between(df.index, df["BB_Upper"], df["BB_Lower"], alpha=0.1, color="gray", label="Bollinger Bands")

    # Plot support levels
    for level in technicals["support_levels"][-5:]:
        ax1.axhline(y=level, color="green", linewidth=0.6, linestyle=":", alpha=0.7)

    # Plot top 3 recommended strike prices
    if not options_df.empty:
        for i, (_, row) in enumerate(options_df.head(3).iterrows()):
            ax1.axhline(
                y=row["strike"], color="orange", linewidth=1.2, linestyle="-.",
                label=f"Put Strike ${row['strike']:.0f} ({row['expiration']})" if i < 3 else "",
            )

    ax1.set_ylabel("Price ($)")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.set_title("Price Action & Key Levels")
    ax1.grid(True, alpha=0.3)

    # ── Chart 2: RSI ──
    ax2 = axes[1]
    ax2.plot(df.index, df["RSI"], color="purple", linewidth=1)
    ax2.axhline(70, color="red", linewidth=0.7, linestyle="--")
    ax2.axhline(30, color="green", linewidth=0.7, linestyle="--")
    ax2.fill_between(df.index, 30, 70, alpha=0.05, color="gray")
    ax2.set_ylabel("RSI")
    ax2.set_ylim(10, 90)
    ax2.set_title("RSI (14)")
    ax2.grid(True, alpha=0.3)

    # ── Chart 3: Put strategy payoff diagram ──
    ax3 = axes[2]
    if not options_df.empty:
        best = options_df.iloc[0]
        strike = best["strike"]
        premium = best["premium"]

        prices = np.linspace(strike * 0.6, current_price * 1.3, 200)
        payoff = np.where(
            prices >= strike,
            premium,  # max profit if stock stays above strike
            premium - (strike - prices),  # loss if stock drops below strike
        )

        ax3.plot(prices, payoff * 100, color="blue", linewidth=1.5)
        ax3.axhline(0, color="black", linewidth=0.5)
        ax3.axvline(current_price, color="gray", linewidth=0.8, linestyle="--", label=f"Current ${current_price:.2f}")
        ax3.axvline(strike, color="orange", linewidth=0.8, linestyle="--", label=f"Strike ${strike:.2f}")
        ax3.axvline(best["breakeven"], color="red", linewidth=0.8, linestyle="--", label=f"B/E ${best['breakeven']:.2f}")
        ax3.fill_between(prices, payoff * 100, 0, where=(payoff > 0), alpha=0.15, color="green")
        ax3.fill_between(prices, payoff * 100, 0, where=(payoff < 0), alpha=0.15, color="red")
        ax3.set_xlabel("FIG Stock Price at Expiration")
        ax3.set_ylabel("P/L per Contract ($)")
        ax3.set_title(f"Sell Put Payoff — {best['expiration']} ${strike:.0f}P @ ${premium:.2f}")
        ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    chart_path = "fig_put_analysis_chart.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Chart saved to: {chart_path}")


# ─────────────────────────────────────────────────────
# 6. Position Sizing Guidance
# ─────────────────────────────────────────────────────
def position_sizing_guidance(options_df: pd.DataFrame, current_price: float):
    """Print position sizing recommendations."""
    if options_df.empty:
        return

    best = options_df.iloc[0]

    print(f"\n{'─'*70}")
    print(f"  POSITION SIZING GUIDE")
    print(f"{'─'*70}")
    print(f"  Cash-secured put requires holding cash = Strike x 100 per contract")
    print()

    for portfolio_size in [10_000, 25_000, 50_000, 100_000]:
        capital_per_contract = best["strike"] * 100
        max_contracts = int(portfolio_size * 0.05 / capital_per_contract)  # 5% max per position
        max_contracts = max(max_contracts, 1) if portfolio_size >= capital_per_contract else 0
        total_premium = max_contracts * best["premium"] * 100
        total_capital = max_contracts * capital_per_contract

        if max_contracts > 0:
            print(f"  Portfolio ${portfolio_size:>8,}:  {max_contracts} contracts"
                  f"  |  Capital: ${total_capital:>8,.0f}"
                  f"  |  Premium: ${total_premium:>6,.0f}"
                  f"  |  {total_capital/portfolio_size:.0%} of portfolio")

    print(f"\n  ⚠  General guideline: allocate no more than 3-5% of portfolio per position.")
    print(f"  ⚠  FIG is a high-volatility recent-IPO stock — use smaller sizing.")


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────
def main():
    # Step 1: Fetch data
    stock, hist, info, current_price = fetch_stock_data(TICKER)

    # Step 2: Technical analysis
    technicals = technical_analysis(hist, current_price)

    # Step 3: Options chain analysis
    options_df = analyze_options_chain(stock, current_price, technicals)

    # Step 4: Display recommendations
    display_recommendations(options_df, current_price, technicals)

    # Step 5: Position sizing
    position_sizing_guidance(options_df, current_price)

    # Step 6: Plot charts
    try:
        plot_analysis(technicals, options_df, current_price)
    except Exception as e:
        print(f"\n  ⚠ Could not generate charts: {e}")
        print(f"     (Charts require a display. Run in a GUI environment.)")

    print(f"\n{'='*70}")
    print(f"  DISCLAIMER: This is for educational/analysis purposes only.")
    print(f"  Not financial advice. Options involve significant risk.")
    print(f"  Always do your own due diligence before trading.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
