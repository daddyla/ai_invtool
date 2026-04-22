#!/usr/bin/env python3
"""
Portfolio Recovery Optimizer
============================
Analyzes full portfolio, computes unrealized P&L, and recommends
options strategies (sell puts, covered calls, wheel) + rebalancing
to recover cost basis as fast as possible.

Requirements: pip install yfinance pandas numpy matplotlib scipy
"""

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from scipy.stats import norm

# ─────────────────────────────────────────────────────
# Portfolio Definition
# ─────────────────────────────────────────────────────
PORTFOLIO = [
    {"ticker": "TMF",  "shares": 36, "cost": 45.29, "type": "ETF-Leveraged",
     "note": "3x Long-Term Treasury Bull. Has options. Pays ~3.7% div."},
    {"ticker": "JEPQ", "shares": 20, "cost": 53.70, "type": "ETF-Income",
     "note": "Nasdaq covered-call income ETF. ~10% yield. Monthly dividends."},
    {"ticker": "BLSH", "shares": 11, "cost": 37.00, "type": "Stock-Crypto",
     "note": "Bullish crypto exchange. Has options. High volatility."},
    {"ticker": "FIG",  "shares": 11, "cost": 133.00, "type": "Stock-Tech",
     "note": "Figma design platform. Has options. Down 80%+ from highs."},
    {"ticker": "DOCS", "shares": 6,  "cost": 41.00, "type": "Stock-Health",
     "note": "Doximity health-tech. Has options. Crashed 30% on guidance."},
]

RISK_FREE_RATE = 0.043
MIN_DTE = 14
MAX_DTE = 60

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 20)


# ─────────────────────────────────────────────────────
# 1. Fetch Current Prices
# ─────────────────────────────────────────────────────
def fetch_portfolio_prices():
    """Fetch current prices for all holdings."""
    print(f"\n{'='*80}")
    print(f"  PORTFOLIO RECOVERY OPTIMIZER  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*80}")
    print(f"\n  Fetching live data...")

    for pos in PORTFOLIO:
        try:
            t = yf.Ticker(pos["ticker"])
            hist = t.history(period="5d")
            pos["current_price"] = hist["Close"].iloc[-1]
            pos["stock_obj"] = t

            # Get 3-month history for volatility
            h3m = t.history(period="3mo")
            if len(h3m) > 20:
                log_ret = np.log(h3m["Close"] / h3m["Close"].shift(1)).dropna()
                pos["hist_vol"] = log_ret.std() * np.sqrt(252)
            else:
                pos["hist_vol"] = 0.5  # default
        except Exception as e:
            print(f"  WARNING: Could not fetch {pos['ticker']}: {e}")
            pos["current_price"] = 0
            pos["stock_obj"] = None
            pos["hist_vol"] = 0.5

    return PORTFOLIO


# ─────────────────────────────────────────────────────
# 2. Portfolio Summary
# ─────────────────────────────────────────────────────
def portfolio_summary(portfolio):
    """Print portfolio P&L summary."""
    print(f"\n{'─'*80}")
    print(f"  PORTFOLIO OVERVIEW")
    print(f"{'─'*80}")

    total_invested = 0
    total_value = 0
    rows = []

    for p in portfolio:
        invested = p["shares"] * p["cost"]
        value = p["shares"] * p["current_price"]
        pnl = value - invested
        pnl_pct = pnl / invested if invested > 0 else 0

        total_invested += invested
        total_value += value

        rows.append({
            "Ticker": p["ticker"],
            "Type": p["type"],
            "Shares": p["shares"],
            "Cost": f"${p['cost']:.2f}",
            "Current": f"${p['current_price']:.2f}",
            "Invested": f"${invested:,.0f}",
            "Value": f"${value:,.0f}",
            "P&L": f"${pnl:,.0f}",
            "P&L%": f"{pnl_pct:+.1%}",
            "HV%": f"{p['hist_vol']:.0%}",
            "Weight": f"{value / total_value:.0%}" if total_value > 0 else "0%",
        })

    df = pd.DataFrame(rows)
    print(f"\n{df.to_string(index=False)}")

    total_pnl = total_value - total_invested
    print(f"\n  {'─'*60}")
    print(f"  Total Invested:     ${total_invested:,.2f}")
    print(f"  Total Value:        ${total_value:,.2f}")
    print(f"  Total P&L:          ${total_pnl:,.2f} ({total_pnl/total_invested:+.1%})")
    print(f"  Need to Recover:    ${abs(total_pnl):,.2f}" if total_pnl < 0 else "  Portfolio is profitable!")

    return total_invested, total_value, total_pnl


# ─────────────────────────────────────────────────────
# 3. Per-Position Strategy Engine
# ─────────────────────────────────────────────────────
def get_options_chain(stock_obj, ticker, current_price, direction="puts"):
    """Fetch and filter options chain for a given ticker."""
    try:
        expirations = stock_obj.options
    except Exception:
        return pd.DataFrame()

    today = datetime.now().date()
    all_opts = []

    for exp_str in expirations:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        dte = (exp_date - today).days
        if dte < MIN_DTE or dte > MAX_DTE:
            continue
        try:
            chain = stock_obj.option_chain(exp_str)
            opts = chain.puts.copy() if direction == "puts" else chain.calls.copy()
        except Exception:
            continue
        if opts.empty:
            continue
        opts["expiration"] = exp_str
        opts["DTE"] = dte
        all_opts.append(opts)

    if not all_opts:
        return pd.DataFrame()

    df = pd.concat(all_opts, ignore_index=True)
    df = df[df["bid"] > 0.03].copy()

    if direction == "puts":
        df = df[df["strike"] <= current_price].copy()
    else:
        df = df[df["strike"] >= current_price].copy()

    # Filter for minimum liquidity
    df = df[df["openInterest"] >= 5].copy()
    return df


def analyze_position(pos):
    """Determine the best recovery strategy for a single position."""
    ticker = pos["ticker"]
    shares = pos["shares"]
    cost = pos["cost"]
    price = pos["current_price"]
    stock = pos["stock_obj"]
    vol = pos["hist_vol"]

    invested = shares * cost
    value = shares * price
    pnl = value - invested
    is_loss = pnl < 0

    result = {
        "ticker": ticker,
        "shares": shares,
        "cost": cost,
        "price": price,
        "pnl": pnl,
        "strategies": [],
    }

    if stock is None:
        result["strategies"].append({"name": "HOLD", "detail": "Cannot fetch data."})
        return result

    can_sell_cc = shares >= 100
    needs_100 = 100 - shares

    # ── Strategy: Sell Covered Calls (if 100+ shares) ──
    if can_sell_cc:
        calls_df = get_options_chain(stock, ticker, price, "calls")
        if not calls_df.empty:
            calls_df["premium_income"] = calls_df["bid"] * 100
            calls_df["ann_yield"] = (calls_df["bid"] / price) * (365 / calls_df["DTE"])
            calls_df["profit_if_called"] = (calls_df["strike"] - cost + calls_df["bid"]) * 100
            best_cc = calls_df.sort_values("ann_yield", ascending=False).head(3)

            for _, row in best_cc.iterrows():
                result["strategies"].append({
                    "name": "SELL COVERED CALL",
                    "action": f"SELL {row['expiration']} ${row['strike']:.2f}C @ ${row['bid']:.2f}",
                    "premium": row["bid"] * 100,
                    "ann_yield": row["ann_yield"],
                    "dte": row["DTE"],
                    "detail": f"Premium ${row['premium_income']:.0f} | Ann. {row['ann_yield']:.0%}"
                              f" | {'Profit' if row['profit_if_called'] > 0 else 'Loss'}"
                              f" if called: ${row['profit_if_called']:.0f}",
                })

    # ── Strategy: Sell Cash-Secured Puts ──
    puts_df = get_options_chain(stock, ticker, price, "puts")
    if not puts_df.empty:
        puts_df["premium_income"] = puts_df["bid"] * 100
        puts_df["ann_yield"] = (puts_df["bid"] / puts_df["strike"]) * (365 / puts_df["DTE"])
        puts_df["effective_buy"] = puts_df["strike"] - puts_df["bid"]

        if not can_sell_cc:
            # Calculate blended cost if assigned (accumulate to 100+)
            puts_df["blended_if_assigned"] = (
                (shares * cost + 100 * puts_df["effective_buy"]) / (shares + 100)
            )

        best_puts = puts_df.sort_values("ann_yield", ascending=False).head(3)
        for _, row in best_puts.iterrows():
            detail = (f"Premium ${row['premium_income']:.0f} | Ann. {row['ann_yield']:.0%}"
                      f" | Eff. buy ${row['effective_buy']:.2f}")
            if not can_sell_cc and "blended_if_assigned" in row:
                detail += f" | Blended cost if assigned: ${row['blended_if_assigned']:.2f}"
            result["strategies"].append({
                "name": "SELL PUT",
                "action": f"SELL {row['expiration']} ${row['strike']:.2f}P @ ${row['bid']:.2f}",
                "premium": row["bid"] * 100,
                "ann_yield": row["ann_yield"],
                "dte": row["DTE"],
                "capital_needed": row["strike"] * 100,
                "detail": detail,
            })

    # ── Strategy: Buy shares to reach 100 → Wheel ──
    if not can_sell_cc and shares > 0:
        additional_cost = needs_100 * price
        blended = (shares * cost + needs_100 * price) / 100
        result["strategies"].append({
            "name": "BUY TO 100 SHARES",
            "action": f"Buy {needs_100} shares @ ${price:.2f}",
            "capital_needed": additional_cost,
            "detail": f"Cost ${additional_cost:,.0f} | Blended basis: ${blended:.2f}"
                      f" | Then sell covered calls for income",
        })

    # ── Strategy: Tax-Loss Harvest ──
    if is_loss:
        realized_loss = pnl
        tax_benefit = abs(realized_loss) * 0.30
        result["strategies"].append({
            "name": "TAX-LOSS HARVEST",
            "action": f"Sell all {shares} shares @ ${price:.2f}",
            "detail": f"Realize ${realized_loss:,.0f} loss | Tax benefit ~${tax_benefit:,.0f}"
                      f" | Wash sale: no rebuy for 30 days",
        })

    # ── Strategy: HOLD + Collect Dividends (for income ETFs) ──
    if ticker == "JEPQ":
        monthly_div = 0.48 * shares  # ~$0.48/share/month average
        annual_div = monthly_div * 12
        result["strategies"].append({
            "name": "HOLD + REINVEST DIVIDENDS",
            "action": "Keep collecting ~10% annual yield",
            "detail": f"~${monthly_div:.0f}/month (${annual_div:.0f}/year) in dividends"
                      f" | Reinvest to compound",
        })
    elif ticker == "TMF":
        quarterly_div = 0.38 * shares  # ~$1.51/year / 4 quarters
        result["strategies"].append({
            "name": "HOLD + COLLECT DIVIDENDS",
            "action": "Collect ~3.7% annual yield while waiting for rate cuts",
            "detail": f"~${quarterly_div:.0f}/quarter | Fed expected to cut 1-3x in 2026"
                      f" | Rate cuts = TMF rally (3x leverage)",
        })

    return result


# ─────────────────────────────────────────────────────
# 4. Display Strategies
# ─────────────────────────────────────────────────────
def display_strategies(results):
    """Print per-position strategy recommendations."""
    for r in results:
        ticker = r["ticker"]
        pnl = r["pnl"]
        status = "PROFIT" if pnl >= 0 else "LOSS"

        print(f"\n{'='*80}")
        print(f"  {ticker}  |  {r['shares']} shares @ ${r['cost']:.2f}  →  "
              f"${r['price']:.2f}  |  {status}: ${pnl:,.0f} ({pnl/(r['shares']*r['cost']):+.1%})")
        print(f"{'='*80}")

        if not r["strategies"]:
            print(f"  No strategies available (no options / insufficient data).")
            continue

        for i, s in enumerate(r["strategies"], 1):
            print(f"\n  [{i}] {s['name']}")
            if "action" in s:
                print(f"      Action:  {s['action']}")
            print(f"      Detail:  {s['detail']}")
            if "capital_needed" in s:
                print(f"      Capital: ${s['capital_needed']:,.0f}")


# ─────────────────────────────────────────────────────
# 5. Optimal Recovery Plan
# ─────────────────────────────────────────────────────
def optimal_recovery_plan(portfolio, results, total_pnl):
    """Generate the recommended action plan prioritized by impact."""
    print(f"\n\n{'#'*80}")
    print(f"  OPTIMAL RECOVERY PLAN")
    print(f"{'#'*80}")
    print(f"\n  Total loss to recover: ${abs(total_pnl):,.0f}")

    # Sort positions by loss magnitude (worst first)
    ranked = sorted(results, key=lambda x: x["pnl"])

    print(f"\n  PRIORITY ORDER (biggest losses first):")
    print(f"  {'─'*70}")

    priority = 1
    total_monthly_income = 0
    total_capital_needed = 0
    actions = []

    for r in ranked:
        ticker = r["ticker"]
        shares = r["shares"]
        price = r["price"]
        cost = r["cost"]
        pnl = r["pnl"]
        can_cc = shares >= 100

        print(f"\n  PRIORITY {priority}: {ticker} (P&L: ${pnl:,.0f})")
        priority += 1

        # ── FIG: Biggest loser — sell puts to accumulate ──
        if ticker == "FIG":
            put_strats = [s for s in r["strategies"] if s["name"] == "SELL PUT"]
            if put_strats:
                best = put_strats[0]
                print(f"    >> ACTION: {best['action']}")
                print(f"       {best['detail']}")
                print(f"       WHY: Only 11 shares, can't sell CC. Sell puts to accumulate")
                print(f"            to 100 shares at a low blended cost, then Wheel.")
                est_monthly = best.get("premium", 0) * (30 / best.get("dte", 30))
                total_monthly_income += est_monthly
                total_capital_needed += best.get("capital_needed", 0)
                actions.append(f"SELL PUT on {ticker}: ~${est_monthly:.0f}/mo premium")

        # ── DOCS: Small position, sell puts or tax-loss harvest ──
        elif ticker == "DOCS":
            put_strats = [s for s in r["strategies"] if s["name"] == "SELL PUT"]
            tlh = [s for s in r["strategies"] if s["name"] == "TAX-LOSS HARVEST"]
            if put_strats:
                best = put_strats[0]
                print(f"    >> OPTION A: {best['action']}")
                print(f"       {best['detail']}")
                print(f"       WHY: High IV after 30% crash = fat put premiums.")
            if tlh:
                print(f"    >> OPTION B: {tlh[0]['action']}")
                print(f"       {tlh[0]['detail']}")
                print(f"       WHY: Small position, loss can offset other gains.")
            if put_strats:
                est_monthly = put_strats[0].get("premium", 0) * (30 / put_strats[0].get("dte", 30))
                total_monthly_income += est_monthly
                total_capital_needed += put_strats[0].get("capital_needed", 0)
                actions.append(f"SELL PUT on {ticker}: ~${est_monthly:.0f}/mo premium")

        # ── BLSH: Crypto volatile — sell puts for premium ──
        elif ticker == "BLSH":
            put_strats = [s for s in r["strategies"] if s["name"] == "SELL PUT"]
            if put_strats:
                best = put_strats[0]
                print(f"    >> ACTION: {best['action']}")
                print(f"       {best['detail']}")
                print(f"       WHY: High volatility = rich premiums. Accumulate to 100 or collect income.")
                est_monthly = best.get("premium", 0) * (30 / best.get("dte", 30))
                total_monthly_income += est_monthly
                total_capital_needed += best.get("capital_needed", 0)
                actions.append(f"SELL PUT on {ticker}: ~${est_monthly:.0f}/mo premium")

        # ── TMF: Leveraged ETF — hold for rate cuts + sell puts ──
        elif ticker == "TMF":
            div_strats = [s for s in r["strategies"] if "DIVIDEND" in s["name"]]
            put_strats = [s for s in r["strategies"] if s["name"] == "SELL PUT"]
            if div_strats:
                print(f"    >> ACTION 1: {div_strats[0]['action']}")
                print(f"       {div_strats[0]['detail']}")
            if put_strats:
                best = put_strats[0]
                print(f"    >> ACTION 2: {best['action']}")
                print(f"       {best['detail']}")
                print(f"       WHY: Sell puts to accumulate or collect premium while")
                print(f"            waiting for Fed rate cuts (catalyst for TMF).")
                est_monthly = best.get("premium", 0) * (30 / best.get("dte", 30))
                total_monthly_income += est_monthly
                total_capital_needed += best.get("capital_needed", 0)
                actions.append(f"SELL PUT on {ticker} + dividends: ~${est_monthly:.0f}/mo")

        # ── JEPQ: Winner — hold & reinvest dividends ──
        elif ticker == "JEPQ":
            div_strats = [s for s in r["strategies"] if "DIVIDEND" in s["name"]]
            if div_strats:
                print(f"    >> ACTION: {div_strats[0]['action']}")
                print(f"       {div_strats[0]['detail']}")
                print(f"       WHY: JEPQ is your only profitable holding. ~10% yield.")
                print(f"            Reinvest dividends into losers to lower their cost basis.")
                # ~$0.48/share/month * 20 shares
                monthly_div = 0.48 * shares
                total_monthly_income += monthly_div
                actions.append(f"JEPQ dividends: ~${monthly_div:.0f}/mo → reinvest into losers")

    # ── Summary ──
    print(f"\n\n  {'='*70}")
    print(f"  RECOVERY INCOME SUMMARY")
    print(f"  {'='*70}")
    print(f"\n  Estimated Monthly Income from All Strategies:")
    for a in actions:
        print(f"    - {a}")
    print(f"  {'─'*50}")
    print(f"  Total Est. Monthly Income:  ~${total_monthly_income:,.0f}")
    print(f"  Total Est. Annual Income:   ~${total_monthly_income * 12:,.0f}")
    print(f"  Additional Capital Needed:  ~${total_capital_needed:,.0f} (for put collateral)")
    if total_monthly_income > 0:
        months = abs(total_pnl) / total_monthly_income
        print(f"\n  Months to Recover ${abs(total_pnl):,.0f} Loss:  ~{months:.0f} months")
        print(f"  (Assumes strategies repeated monthly, stock prices stable)")

    return total_monthly_income


# ─────────────────────────────────────────────────────
# 6. Visualization
# ─────────────────────────────────────────────────────
def plot_portfolio(portfolio, total_pnl, monthly_income):
    """Generate portfolio charts."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("Portfolio Recovery Dashboard", fontsize=14, fontweight="bold")

    # ── Chart 1: P&L by Position ──
    ax1 = axes[0]
    tickers = [p["ticker"] for p in portfolio]
    pnls = [p["shares"] * (p["current_price"] - p["cost"]) for p in portfolio]
    colors = ["#2ecc71" if x >= 0 else "#e74c3c" for x in pnls]

    bars = ax1.barh(tickers, pnls, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars, pnls):
        ax1.text(bar.get_width() + (10 if val >= 0 else -10), bar.get_y() + bar.get_height()/2,
                 f"${val:,.0f}", ha="left" if val >= 0 else "right", va="center", fontsize=10)
    ax1.axvline(0, color="black", linewidth=0.8)
    ax1.set_xlabel("Unrealized P&L ($)")
    ax1.set_title("P&L by Position")
    ax1.grid(axis="x", alpha=0.3)

    # ── Chart 2: Cost vs Current Price ──
    ax2 = axes[1]
    x = np.arange(len(tickers))
    width = 0.35
    costs = [p["cost"] for p in portfolio]
    currents = [p["current_price"] for p in portfolio]

    ax2.bar(x - width/2, costs, width, label="Cost Basis", color="#3498db", edgecolor="black", linewidth=0.5)
    ax2.bar(x + width/2, currents, width, label="Current Price", color="#e67e22", edgecolor="black", linewidth=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(tickers)
    ax2.set_ylabel("Price ($)")
    ax2.set_title("Cost Basis vs Current Price")
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3)

    # ── Chart 3: Recovery Timeline ──
    ax3 = axes[2]
    if monthly_income > 0:
        months = range(0, 25)
        remaining = [abs(total_pnl) - m * monthly_income for m in months]
        ax3.plot(months, remaining, color="blue", linewidth=2)
        ax3.axhline(0, color="green", linewidth=1.5, linestyle="--", label="Fully Recovered")
        ax3.fill_between(months, remaining, 0, where=[r > 0 for r in remaining],
                         alpha=0.1, color="red", label="Remaining Loss")
        ax3.fill_between(months, remaining, 0, where=[r <= 0 for r in remaining],
                         alpha=0.1, color="green", label="Profit Zone")
        ax3.set_xlabel("Months")
        ax3.set_ylabel("Remaining Loss ($)")
        ax3.set_title(f"Recovery Timeline (~${monthly_income:.0f}/mo)")
        ax3.legend(fontsize=8)
    else:
        ax3.text(0.5, 0.5, "No income strategies\navailable", transform=ax3.transAxes,
                 ha="center", va="center", fontsize=12)
        ax3.set_title("Recovery Timeline")
    ax3.grid(alpha=0.3)

    plt.tight_layout()
    path = "portfolio_recovery_chart.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Chart saved to: {path}")


# ─────────────────────────────────────────────────────
# 7. Rebalancing Recommendations
# ─────────────────────────────────────────────────────
def rebalancing_advice(portfolio, total_value):
    """Suggest rebalancing moves."""
    print(f"\n\n{'#'*80}")
    print(f"  REBALANCING & RISK ASSESSMENT")
    print(f"{'#'*80}")

    print(f"\n  CURRENT ALLOCATION:")
    for p in portfolio:
        val = p["shares"] * p["current_price"]
        weight = val / total_value if total_value > 0 else 0
        print(f"    {p['ticker']:6s}  ${val:>8,.0f}  ({weight:>5.1%})  {p['type']}")

    print(f"\n  OBSERVATIONS:")
    print(f"  {'─'*60}")

    # Check concentration
    weights = {p["ticker"]: p["shares"] * p["current_price"] / total_value for p in portfolio}

    # TMF check
    if weights.get("TMF", 0) > 0.3:
        print(f"  ! TMF is {weights['TMF']:.0%} of portfolio — HEAVY concentration in 3x leverage")
        print(f"    Consider: Reduce TMF and add to JEPQ for stable income")

    # JEPQ check
    if weights.get("JEPQ", 0) > 0:
        print(f"  + JEPQ ({weights['JEPQ']:.0%}) is your best performer — consider adding more")
        print(f"    Redirect JEPQ dividends (~$10/mo) into buying more JEPQ shares")

    # Small positions
    for t in ["FIG", "DOCS", "BLSH"]:
        if weights.get(t, 0) < 0.15:
            pos = next(p for p in portfolio if p["ticker"] == t)
            if pos["shares"] * (pos["current_price"] - pos["cost"]) < -50:
                print(f"  ? {t} is a small losing position ({weights[t]:.0%}) — "
                      f"consider tax-loss harvesting")

    print(f"\n  KEY RISKS:")
    print(f"  {'─'*60}")
    print(f"  - TMF: 3x leveraged = compounding decay. NOT a long-term hold.")
    print(f"    If holding, have a clear exit target (e.g., if Fed cuts 2-3x).")
    print(f"  - FIG: Down 80% from IPO. Recovery to $133 is extremely unlikely.")
    print(f"    Focus on lowering cost basis, not reaching original cost.")
    print(f"  - BLSH: Crypto-correlated. Extremely volatile. Position size wisely.")
    print(f"  - DOCS: Post-crash IV is elevated. Good time to SELL options for premium.")


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────
def main():
    # Fetch data
    portfolio = fetch_portfolio_prices()

    # Portfolio summary
    total_invested, total_value, total_pnl = portfolio_summary(portfolio)

    # Analyze each position
    results = []
    for pos in portfolio:
        r = analyze_position(pos)
        results.append(r)

    # Display per-position strategies
    print(f"\n\n{'#'*80}")
    print(f"  PER-POSITION STRATEGIES")
    print(f"{'#'*80}")
    display_strategies(results)

    # Optimal plan
    monthly_income = optimal_recovery_plan(portfolio, results, total_pnl)

    # Rebalancing
    rebalancing_advice(portfolio, total_value)

    # Charts
    try:
        plot_portfolio(portfolio, total_pnl, monthly_income)
    except Exception as e:
        print(f"\n  Could not generate chart: {e}")

    print(f"\n{'='*80}")
    print(f"  DISCLAIMER: Educational purposes only. Not financial advice.")
    print(f"  Options involve significant risk. Do your own due diligence.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
