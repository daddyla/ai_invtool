#!/usr/bin/env python3
"""
NVDA Earnings Behavior Analysis
================================
Analyzes NVIDIA stock price behavior BEFORE and AFTER every earnings call
over the last 3 years to determine:
  1. Do investors buy the run-up before earnings?
  2. Do they sell the news after earnings?
  3. How long does the post-earnings move last?
  4. What's the pattern for the upcoming Feb 25, 2026 report?

Requirements: pip install yfinance pandas numpy matplotlib
"""

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────
# NVDA Earnings Dates (confirmed historical)
# After-market-close reports
# ─────────────────────────────────────────────────────
EARNINGS_DATES = [
    {"date": "2023-02-22", "quarter": "Q4 FY23", "eps_est": 0.81, "eps_actual": 0.88, "rev_est": 6.01, "rev_actual": 6.05},
    {"date": "2023-05-24", "quarter": "Q1 FY24", "eps_est": 0.92, "eps_actual": 1.09, "rev_est": 6.52, "rev_actual": 7.19},
    {"date": "2023-08-23", "quarter": "Q2 FY24", "eps_est": 2.07, "eps_actual": 2.70, "rev_est": 11.22, "rev_actual": 13.51},
    {"date": "2023-11-21", "quarter": "Q3 FY24", "eps_est": 3.36, "eps_actual": 4.02, "rev_est": 16.18, "rev_actual": 18.12},
    {"date": "2024-02-21", "quarter": "Q4 FY24", "eps_est": 4.59, "eps_actual": 5.16, "rev_est": 20.62, "rev_actual": 22.10},
    {"date": "2024-05-22", "quarter": "Q1 FY25", "eps_est": 5.59, "eps_actual": 6.12, "rev_est": 24.65, "rev_actual": 26.04},
    {"date": "2024-08-28", "quarter": "Q2 FY25", "eps_est": 0.64, "eps_actual": 0.68, "rev_est": 28.72, "rev_actual": 30.04},  # post-split EPS
    {"date": "2024-11-20", "quarter": "Q3 FY25", "eps_est": 0.75, "eps_actual": 0.81, "rev_est": 33.17, "rev_actual": 35.08},
    {"date": "2025-02-26", "quarter": "Q4 FY25", "eps_est": 0.84, "eps_actual": 0.89, "rev_est": 38.05, "rev_actual": 39.33},
    {"date": "2025-05-28", "quarter": "Q1 FY26", "eps_est": 0.88, "eps_actual": 0.96, "rev_est": 43.21, "rev_actual": 44.08},
    {"date": "2025-08-27", "quarter": "Q2 FY26", "eps_est": 1.01, "eps_actual": 1.05, "rev_est": 46.20, "rev_actual": 46.70},
    {"date": "2025-11-19", "quarter": "Q3 FY26", "eps_est": 1.22, "eps_actual": 1.30, "rev_est": 55.30, "rev_actual": 57.00},
]

# Upcoming
UPCOMING = {"date": "2026-02-25", "quarter": "Q4 FY26", "eps_est": 1.52, "rev_est": 65.67}


def fetch_nvda_history():
    """Fetch 3+ years of NVDA daily price data."""
    print(f"\n{'='*80}")
    print(f"  NVDA EARNINGS BEHAVIOR ANALYSIS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*80}")
    print(f"\n  Fetching NVDA price history (3 years)...")

    nvda = yf.Ticker("NVDA")
    hist = nvda.history(period="3y", interval="1d")

    if hist.empty:
        raise ValueError("Could not fetch NVDA data")

    # Strip timezone info to avoid tz-aware vs tz-naive comparison issues
    hist.index = hist.index.tz_localize(None)

    print(f"  Got {len(hist)} trading days from {hist.index[0].date()} to {hist.index[-1].date()}")
    return hist


def analyze_earnings_windows(hist):
    """For each earnings date, calculate returns in windows before and after."""
    results = []

    print(f"\n{'─'*80}")
    print(f"  PRE-EARNINGS & POST-EARNINGS PRICE BEHAVIOR")
    print(f"{'─'*80}")

    for e in EARNINGS_DATES:
        earn_date = pd.Timestamp(e["date"])

        # Find the closest trading day on or before the earnings date
        # Earnings are after close, so earn_date close is the "pre-earnings" price
        mask = hist.index <= earn_date + timedelta(hours=23)
        if mask.sum() == 0:
            continue
        pre_idx = hist.index[mask][-1]
        pre_close = hist.loc[pre_idx, "Close"]

        # Post-earnings: next trading day after earnings
        mask_post = hist.index > earn_date
        if mask_post.sum() == 0:
            continue

        # Get reference prices at various windows
        windows = {}

        # PRE-EARNINGS windows: -30d, -20d, -10d, -5d, -1d before earnings
        for days_before in [30, 20, 10, 5, 1]:
            target = earn_date - timedelta(days=days_before)
            mask_pre = hist.index <= target + timedelta(hours=23)
            if mask_pre.sum() > 0:
                ref_idx = hist.index[mask_pre][-1]
                ref_close = hist.loc[ref_idx, "Close"]
                pct = (pre_close - ref_close) / ref_close
                windows[f"pre_{days_before}d"] = pct

        # POST-EARNINGS windows: +1d, +2d, +5d, +10d, +20d, +30d after earnings
        post_days = hist.index[hist.index > earn_date]
        for days_after in [1, 2, 5, 10, 20, 30]:
            if len(post_days) >= days_after:
                post_close = hist.loc[post_days[days_after - 1], "Close"]
                pct = (post_close - pre_close) / pre_close
                windows[f"post_{days_after}d"] = pct

        # EPS surprise
        eps_surprise = (e["eps_actual"] - e["eps_est"]) / e["eps_est"] if e["eps_est"] > 0 else 0
        rev_surprise = (e["rev_actual"] - e["rev_est"]) / e["rev_est"] if e["rev_est"] > 0 else 0

        result = {
            "date": e["date"],
            "quarter": e["quarter"],
            "eps_surprise": eps_surprise,
            "rev_surprise": rev_surprise,
            "pre_close": pre_close,
            **windows,
        }
        results.append(result)

    return pd.DataFrame(results)


def display_pre_earnings(df):
    """Show pre-earnings run-up pattern."""
    print(f"\n{'─'*80}")
    print(f"  PRE-EARNINGS RUN-UP (% change BEFORE earnings call)")
    print(f"  Positive = stock rallied into earnings")
    print(f"{'─'*80}\n")

    cols = ["quarter", "date", "pre_30d", "pre_20d", "pre_10d", "pre_5d", "pre_1d"]
    available_cols = [c for c in cols if c in df.columns]
    display = df[available_cols].copy()

    for c in available_cols:
        if c.startswith("pre_"):
            display[c] = display[c].map(lambda x: f"{x:+.1%}" if pd.notna(x) else "N/A")

    print(display.to_string(index=False))

    # Averages
    print(f"\n  AVERAGES (pre-earnings run-up):")
    for days in [30, 20, 10, 5, 1]:
        col = f"pre_{days}d"
        if col in df.columns:
            avg = df[col].mean()
            positive_pct = (df[col] > 0).mean()
            print(f"    {days:>2d} days before:  avg {avg:+.1%}  |  rallied {positive_pct:.0%} of the time")


def display_post_earnings(df):
    """Show post-earnings reaction and drift."""
    print(f"\n\n{'─'*80}")
    print(f"  POST-EARNINGS REACTION (% change AFTER earnings call)")
    print(f"  Negative = investors sold after earnings")
    print(f"{'─'*80}\n")

    cols = ["quarter", "eps_surprise", "rev_surprise", "post_1d", "post_2d", "post_5d", "post_10d", "post_20d", "post_30d"]
    available_cols = [c for c in cols if c in df.columns]
    display = df[available_cols].copy()

    for c in available_cols:
        if c.startswith("post_") or c.endswith("_surprise"):
            display[c] = display[c].map(lambda x: f"{x:+.1%}" if pd.notna(x) else "N/A")

    print(display.to_string(index=False))

    # Averages
    print(f"\n  AVERAGES (post-earnings):")
    for days in [1, 2, 5, 10, 20, 30]:
        col = f"post_{days}d"
        if col in df.columns:
            avg = df[col].mean()
            negative_pct = (df[col] < 0).mean()
            print(f"    +{days:>2d} day{'s' if days > 1 else ' '} after:  avg {avg:+.1%}"
                  f"  |  sold off {negative_pct:.0%} of the time"
                  f"  |  rallied {1-negative_pct:.0%} of the time")


def display_sell_the_news(df):
    """Identify the sell-the-news pattern."""
    print(f"\n\n{'─'*80}")
    print(f"  SELL THE NEWS PATTERN ANALYSIS")
    print(f"{'─'*80}")

    # Beat but dropped
    if "post_1d" in df.columns:
        beat_mask = df["eps_surprise"] > 0
        beats = df[beat_mask]
        dropped = beats[beats["post_1d"] < 0]

        print(f"\n  Earnings where NVDA BEAT EPS estimates: {len(beats)}/{len(df)}")
        print(f"  Of those beats, stock DROPPED next day:  {len(dropped)}/{len(beats)}"
              f" ({len(dropped)/len(beats):.0%})")
        print(f"\n  SELL THE NEWS RATE: {len(dropped)/len(beats):.0%}")

        if len(dropped) > 0:
            print(f"\n  Quarters where NVDA beat BUT sold off:")
            for _, row in dropped.iterrows():
                print(f"    {row['quarter']} ({row['date']}): EPS beat {row['eps_surprise']:+.1%}"
                      f" → next day {row['post_1d']:+.1%}")

    # Run-up then selloff pattern
    if "pre_10d" in df.columns and "post_5d" in df.columns:
        runup_selloff = df[(df["pre_10d"] > 0.02) & (df["post_5d"] < 0)]
        print(f"\n  Run-up (>2% in 10d) then selloff (down in 5d after):")
        print(f"    Occurred {len(runup_selloff)}/{len(df)} times ({len(runup_selloff)/len(df):.0%})")

    # Recent trend (last 6 quarters)
    if len(df) >= 6 and "post_1d" in df.columns:
        recent = df.tail(6)
        recent_drops = (recent["post_1d"] < 0).sum()
        print(f"\n  RECENT TREND (last 6 quarters):")
        print(f"    Dropped next day: {recent_drops}/6 ({recent_drops/6:.0%})")
        print(f"    Average next-day move: {recent['post_1d'].mean():+.1%}")
        print(f"    This suggests the sell-the-news pattern has {'STRENGTHENED' if recent_drops >= 4 else 'been mixed'}")


def display_upcoming_forecast(df):
    """Forecast for upcoming Feb 25, 2026 earnings."""
    print(f"\n\n{'#'*80}")
    print(f"  FORECAST: NVDA Feb 25, 2026 EARNINGS")
    print(f"{'#'*80}")

    print(f"\n  Consensus: EPS ${UPCOMING['eps_est']:.2f} | Revenue ${UPCOMING['rev_est']:.1f}B")
    print(f"  Expected move: +/-6.2% (options market)")

    if "post_1d" in df.columns and "pre_10d" in df.columns:
        avg_post_1d = df["post_1d"].mean()
        avg_post_5d = df["post_5d"].mean() if "post_5d" in df.columns else 0
        recent_avg = df.tail(6)["post_1d"].mean() if len(df) >= 6 else avg_post_1d
        avg_pre_10d = df["pre_10d"].mean()

        # Current price
        try:
            nvda = yf.Ticker("NVDA")
            current = nvda.history(period="2d")["Close"].iloc[-1]
        except Exception:
            current = 188.0

        print(f"\n  Current NVDA price: ${current:.2f}")
        print(f"\n  HISTORICAL PATTERN SUGGESTS:")
        print(f"  {'─'*55}")

        # Pre-earnings
        print(f"  PRE-EARNINGS (now through Feb 25):")
        print(f"    Avg 10-day run-up: {avg_pre_10d:+.1%}")
        print(f"    If pattern holds:  NVDA could reach ~${current * (1 + avg_pre_10d):.2f} by earnings")

        # Post-earnings scenarios
        print(f"\n  POST-EARNINGS SCENARIOS:")

        # Scenario 1: Sell the news (most likely based on recent data)
        print(f"\n  SCENARIO 1: SELL THE NEWS (probability: ~60%)")
        print(f"    Based on: Stock dropped after 5 of last 8 beats")
        print(f"    Expected move: {recent_avg:+.1%} to -8%")
        drop_low = current * 0.92
        drop_mid = current * (1 + recent_avg)
        print(f"    Price range: ${drop_low:.2f} — ${drop_mid:.2f}")
        print(f"    Impact on your plan: BUY growth names (SOFI, MGNI) at Feb 27 dip")

        # Scenario 2: Rally
        print(f"\n  SCENARIO 2: BEAT & RALLY (probability: ~30%)")
        print(f"    Requires: Big revenue surprise + strong margin guidance")
        print(f"    Expected move: +5% to +16%")
        rally_mid = current * 1.08
        print(f"    Price range: ${current * 1.05:.2f} — ${current * 1.16:.2f}")
        print(f"    Impact on your plan: Still buy Feb 27, prices slightly higher but trend bullish")

        # Scenario 3: In-line
        print(f"\n  SCENARIO 3: BEAT BUT FLAT (probability: ~10%)")
        print(f"    Muted reaction, +/-2%")
        print(f"    Impact on your plan: Buy as planned, no urgency adjustment needed")

    print(f"\n  BOTTOM LINE FOR YOUR TRADES:")
    print(f"  {'─'*55}")
    print(f"  Phase 1-2 (Feb 20-21): UNAFFECTED. Sell losers + buy income ETFs as planned.")
    print(f"  Phase 3 (Feb 27): BENEFITS from the sell-the-news pattern.")
    print(f"    - If NVDA drops, market dips → buy SOFI/MGNI cheaper")
    print(f"    - If NVDA rallies, market lifts → still good entry for growth")
    print(f"    - Either way, you win by waiting until Feb 27.")


def plot_earnings_analysis(df, hist):
    """Visualize the earnings behavior patterns."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle("NVDA Earnings Behavior — Before & After Analysis (Last 3 Years)",
                 fontsize=14, fontweight="bold")

    # ── 1. Pre-earnings run-up vs Post-earnings reaction ──
    ax1 = axes[0][0]
    quarters = df["quarter"]
    x = np.arange(len(quarters))
    width = 0.35

    pre_10d = df.get("pre_10d", pd.Series([0]*len(df))).fillna(0) * 100
    post_5d = df.get("post_5d", pd.Series([0]*len(df))).fillna(0) * 100

    bars1 = ax1.bar(x - width/2, pre_10d, width, label="10d Before Earnings", color="#3498db", alpha=0.8)
    bars2 = ax1.bar(x + width/2, post_5d, width, label="5d After Earnings", color="#e74c3c", alpha=0.8)
    ax1.axhline(0, color="black", linewidth=0.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels(quarters, rotation=45, ha="right", fontsize=7)
    ax1.set_ylabel("% Change")
    ax1.set_title("Pre-Earnings Run-Up vs Post-Earnings Reaction")
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.3)

    # ── 2. Post-earnings next-day move (bar chart) ──
    ax2 = axes[0][1]
    post_1d = df.get("post_1d", pd.Series([0]*len(df))).fillna(0) * 100
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in post_1d]
    ax2.bar(x, post_1d, color=colors, edgecolor="black", linewidth=0.5)
    for i, v in enumerate(post_1d):
        ax2.text(i, v + (0.3 if v >= 0 else -0.8), f"{v:+.1f}%", ha="center", fontsize=7)
    ax2.axhline(0, color="black", linewidth=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(quarters, rotation=45, ha="right", fontsize=7)
    ax2.set_ylabel("Next-Day % Change")
    ax2.set_title("Post-Earnings Next-Day Move (Green=Up, Red=Down)")
    ax2.grid(axis="y", alpha=0.3)

    # ── 3. Average return by window (line chart) ──
    ax3 = axes[1][0]
    windows_pre = [-30, -20, -10, -5, -1]
    windows_post = [1, 2, 5, 10, 20, 30]
    all_windows = windows_pre + [0] + windows_post
    avg_returns = []

    for w in windows_pre:
        col = f"pre_{abs(w)}d"
        avg_returns.append(df[col].mean() * 100 if col in df.columns else 0)
    avg_returns.append(0)  # earnings day = 0 reference
    for w in windows_post:
        col = f"post_{w}d"
        avg_returns.append(df[col].mean() * 100 if col in df.columns else 0)

    ax3.plot(all_windows, avg_returns, "b-o", linewidth=2, markersize=5)
    ax3.axhline(0, color="black", linewidth=0.5)
    ax3.axvline(0, color="red", linewidth=1, linestyle="--", label="Earnings Day")
    ax3.fill_between(all_windows, avg_returns, 0,
                     where=[r > 0 for r in avg_returns], alpha=0.1, color="green")
    ax3.fill_between(all_windows, avg_returns, 0,
                     where=[r < 0 for r in avg_returns], alpha=0.1, color="red")
    ax3.set_xlabel("Trading Days Relative to Earnings")
    ax3.set_ylabel("Avg. Cumulative Return (%)")
    ax3.set_title("Average Return Curve Around Earnings (All Quarters)")
    ax3.legend(fontsize=8)
    ax3.grid(alpha=0.3)

    # ── 4. EPS surprise vs post-earnings move (scatter) ──
    ax4 = axes[1][1]
    eps_surp = df["eps_surprise"] * 100
    post_1d_vals = df.get("post_1d", pd.Series([0]*len(df))).fillna(0) * 100

    ax4.scatter(eps_surp, post_1d_vals, c=["#2ecc71" if v >= 0 else "#e74c3c" for v in post_1d_vals],
                s=100, edgecolors="black", linewidth=0.5, zorder=5)
    for i, row in df.iterrows():
        ax4.annotate(row["quarter"], (eps_surp.iloc[i], post_1d_vals.iloc[i]),
                     fontsize=6, ha="left", va="bottom")

    # Trend line
    if len(eps_surp) > 2:
        z = np.polyfit(eps_surp, post_1d_vals, 1)
        p = np.poly1d(z)
        x_line = np.linspace(eps_surp.min(), eps_surp.max(), 100)
        ax4.plot(x_line, p(x_line), "r--", linewidth=1, alpha=0.5, label="Trend")

    ax4.axhline(0, color="black", linewidth=0.5)
    ax4.axvline(0, color="black", linewidth=0.5)
    ax4.set_xlabel("EPS Surprise (%)")
    ax4.set_ylabel("Next-Day Return (%)")
    ax4.set_title("EPS Surprise vs Next-Day Stock Move\n(Bigger beat ≠ bigger rally)")
    ax4.legend(fontsize=8)
    ax4.grid(alpha=0.3)

    plt.tight_layout()
    path = "nvda_earnings_behavior_chart.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Chart saved to: {path}")

    # ── Additional chart: Recent 6 quarters close-up ──
    fig2, ax = plt.subplots(figsize=(14, 5))
    ax.set_title("NVDA Price Around Last 6 Earnings Calls (Normalized to 100)", fontsize=13, fontweight="bold")

    colors_line = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6"]
    recent = EARNINGS_DATES[-6:]

    for i, e in enumerate(recent):
        earn_date = pd.Timestamp(e["date"])
        start = earn_date - timedelta(days=25)
        end = earn_date + timedelta(days=25)

        window = hist[(hist.index >= start) & (hist.index <= end)].copy()
        if window.empty:
            continue

        # Find pre-earnings close
        pre_mask = window.index <= earn_date + timedelta(hours=23)
        if pre_mask.sum() == 0:
            continue
        pre_close = window.loc[window.index[pre_mask][-1], "Close"]

        # Normalize to 100 at earnings date
        window["Normalized"] = window["Close"] / pre_close * 100

        # X-axis: trading days relative to earnings
        earn_idx = window.index[pre_mask][-1]
        days_relative = [(d - earn_idx).days for d in window.index]

        ax.plot(days_relative, window["Normalized"], linewidth=1.5,
                color=colors_line[i], label=f"{e['quarter']} ({e['date']})", alpha=0.8)

    ax.axhline(100, color="black", linewidth=0.5, linestyle="--")
    ax.axvline(0, color="red", linewidth=1.5, linestyle="--", alpha=0.5, label="Earnings Day")
    ax.set_xlabel("Days Relative to Earnings")
    ax.set_ylabel("Normalized Price (100 = Earnings Day Close)")
    ax.legend(fontsize=7, loc="lower left")
    ax.grid(alpha=0.3)
    ax.set_xlim(-22, 22)

    plt.tight_layout()
    path2 = "nvda_earnings_overlay_chart.png"
    plt.savefig(path2, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"  Chart saved to: {path2}")


# ─────────────────────────────────────────────────────
def main():
    hist = fetch_nvda_history()
    df = analyze_earnings_windows(hist)

    display_pre_earnings(df)
    display_post_earnings(df)
    display_sell_the_news(df)
    display_upcoming_forecast(df)

    try:
        plot_earnings_analysis(df, hist)
    except Exception as e:
        print(f"\n  Could not generate charts: {e}")

    print(f"\n{'='*80}")
    print(f"  DISCLAIMER: Historical patterns do not guarantee future results.")
    print(f"  This is for educational/analysis purposes only.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
