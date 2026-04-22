#!/usr/bin/env python3
"""
FIG (Figma) Position Recovery Strategy
=======================================
You own: 11 shares @ $100 cost basis
Goal: Maximize profit / minimize loss recovery time

Strategies analyzed:
  A) Sell puts to accumulate to 100 shares → run the Wheel (sell covered calls)
  B) Buy 89 shares now to reach 100 → immediately sell covered calls
  C) Tax-loss harvest (sell now, book the loss)

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
# Your Position
# ─────────────────────────────────────────────────────
TICKER = "FIG"
SHARES_OWNED = 11
COST_BASIS = 100.00  # per share
RISK_FREE_RATE = 0.043

pd.set_option("display.width", 200)


def fetch_data():
    stock = yf.Ticker(TICKER)
    hist = stock.history(period="6mo", interval="1d")
    current_price = hist["Close"].iloc[-1]
    info = stock.info
    return stock, hist, current_price, info


def print_position_summary(current_price):
    total_invested = SHARES_OWNED * COST_BASIS
    current_value = SHARES_OWNED * current_price
    unrealized_pnl = current_value - total_invested
    pnl_pct = unrealized_pnl / total_invested

    print(f"\n{'='*70}")
    print(f"  FIG POSITION RECOVERY STRATEGY")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")
    print(f"\n  YOUR CURRENT POSITION")
    print(f"  {'─'*50}")
    print(f"  Shares:             {SHARES_OWNED}")
    print(f"  Cost Basis:         ${COST_BASIS:.2f}/share")
    print(f"  Total Invested:     ${total_invested:,.2f}")
    print(f"  Current Price:      ${current_price:.2f}")
    print(f"  Current Value:      ${current_value:,.2f}")
    print(f"  Unrealized P&L:     ${unrealized_pnl:,.2f} ({pnl_pct:.1%})")
    print(f"  To Break Even:      FIG needs to reach ${COST_BASIS:.2f} (+{(COST_BASIS/current_price - 1)*100:.0f}%)")

    return total_invested, current_value, unrealized_pnl


# ─────────────────────────────────────────────────────
# STRATEGY A: Sell Puts to Accumulate → Wheel
# ─────────────────────────────────────────────────────
def strategy_a_sell_puts_accumulate(stock, current_price):
    """
    Sell 1 cash-secured put repeatedly.
    - If assigned: you get 100 shares at strike, total = 111 shares
    - New blended cost basis drops dramatically
    - Then sell covered calls on 100 shares to generate income
    - Keep collecting premium either way
    """
    print(f"\n{'='*70}")
    print(f"  STRATEGY A: SELL PUTS TO ACCUMULATE → WHEEL")
    print(f"{'='*70}")
    print(f"  Goal: Sell puts to collect premium & potentially get assigned")
    print(f"        100 more shares at a low price. Then sell covered calls.")
    print()

    try:
        expirations = stock.options
    except Exception as e:
        print(f"  Could not fetch options: {e}")
        return

    today = datetime.now().date()
    all_puts = []

    for exp_str in expirations:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        dte = (exp_date - today).days
        if dte < 14 or dte > 60:
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
        all_puts.append(puts)

    if not all_puts:
        print("  No suitable puts found.")
        return

    df = pd.concat(all_puts, ignore_index=True)
    df = df[(df["strike"] <= current_price) & (df["bid"] > 0.05) & (df["openInterest"] >= 20)].copy()

    if df.empty:
        print("  No qualifying puts after filtering.")
        return

    # Calculate blended cost basis if assigned
    # You'd own: 11 shares @ $100 + 100 shares @ strike - premium
    df["effective_buy_price"] = df["strike"] - df["bid"]
    df["blended_cost_if_assigned"] = (
        (SHARES_OWNED * COST_BASIS + 100 * df["effective_buy_price"])
        / (SHARES_OWNED + 100)
    )
    # Premium income regardless of assignment
    df["premium_income"] = df["bid"] * 100
    # Annualized premium yield on capital at risk
    df["capital_required"] = df["strike"] * 100
    df["ann_yield"] = (df["bid"] / df["strike"]) * (365 / df["DTE"])
    # If NOT assigned, premium reduces your overall cost basis on existing shares
    df["cost_basis_reduction"] = df["bid"] * 100 / SHARES_OWNED  # per-share reduction
    df["new_cost_if_otm"] = COST_BASIS - df["cost_basis_reduction"]

    # Rank by: good assignment price + decent premium
    df["score"] = (
        (1 - df["blended_cost_if_assigned"] / COST_BASIS) * 40  # lower blended = better
        + df["ann_yield"] * 20
        + np.log1p(df["openInterest"]) * 2
    )
    df = df.sort_values("score", ascending=False)

    # ── Scenario 1: Aggressive (want assignment — sell ATM/near-ATM puts) ──
    print(f"  SCENARIO A1: AGGRESSIVE — Sell Near-ATM Puts (WANT assignment)")
    print(f"  {'─'*55}")
    print(f"  You WANT to be assigned to quickly get to 100+ shares.\n")

    aggressive = df[df["strike"] >= current_price * 0.90].head(5)
    if not aggressive.empty:
        for _, row in aggressive.iterrows():
            print(f"  SELL {row['expiration']} ${row['strike']:.2f}P @ ${row['bid']:.2f}")
            print(f"    Premium:          ${row['premium_income']:.0f}")
            print(f"    Capital needed:   ${row['capital_required']:,.0f}")
            print(f"    If ASSIGNED:      Buy 100 shares @ ${row['effective_buy_price']:.2f} effective")
            print(f"                      New blended cost: ${row['blended_cost_if_assigned']:.2f}/share"
                  f" (down from ${COST_BASIS:.2f})")
            print(f"                      Then sell covered calls on 100 shares")
            print(f"    If NOT assigned:  Keep ${row['premium_income']:.0f} premium")
            print(f"                      Existing cost basis drops to: ${row['new_cost_if_otm']:.2f}/share")
            print()

    # ── Scenario 2: Conservative (happy either way — sell OTM puts) ──
    print(f"\n  SCENARIO A2: CONSERVATIVE — Sell OTM Puts (collect premium, maybe assigned)")
    print(f"  {'─'*55}")
    print(f"  Lower chance of assignment but accumulate premium over time.\n")

    conservative = df[df["strike"] < current_price * 0.85].head(5)
    if not conservative.empty:
        for _, row in conservative.iterrows():
            print(f"  SELL {row['expiration']} ${row['strike']:.2f}P @ ${row['bid']:.2f}")
            print(f"    Premium: ${row['premium_income']:.0f}  |  "
                  f"Assigned cost: ${row['blended_cost_if_assigned']:.2f}/share  |  "
                  f"OTM cost basis: ${row['new_cost_if_otm']:.2f}/share")

    return df


# ─────────────────────────────────────────────────────
# STRATEGY B: Buy 89 Shares Now → Sell Covered Calls
# ─────────────────────────────────────────────────────
def strategy_b_buy_and_wheel(stock, current_price):
    """
    Buy 89 more shares now to reach 100 total.
    Immediately start selling covered calls.
    """
    print(f"\n\n{'='*70}")
    print(f"  STRATEGY B: BUY 89 SHARES NOW → SELL COVERED CALLS")
    print(f"{'='*70}")

    additional_shares = 100 - SHARES_OWNED  # 89
    additional_cost = additional_shares * current_price
    total_shares = 100
    blended_cost = (SHARES_OWNED * COST_BASIS + additional_shares * current_price) / total_shares

    print(f"\n  Buy {additional_shares} shares @ ${current_price:.2f} = ${additional_cost:,.2f}")
    print(f"  Total position:    {total_shares} shares")
    print(f"  Blended cost:      ${blended_cost:.2f}/share")
    print(f"  Total invested:    ${SHARES_OWNED * COST_BASIS + additional_cost:,.2f}")
    print(f"  Break-even price:  ${blended_cost:.2f} (vs ${COST_BASIS:.2f} before)")
    print(f"  Distance to B/E:   {(blended_cost/current_price - 1)*100:+.1f}% from current price")
    print()

    # Now find covered calls to sell
    try:
        expirations = stock.options
    except Exception:
        print("  Could not fetch options.")
        return

    today = datetime.now().date()
    all_calls = []

    for exp_str in expirations:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        dte = (exp_date - today).days
        if dte < 14 or dte > 60:
            continue
        try:
            chain = stock.option_chain(exp_str)
            calls = chain.calls.copy()
        except Exception:
            continue
        if calls.empty:
            continue
        calls["expiration"] = exp_str
        calls["DTE"] = dte
        all_calls.append(calls)

    if not all_calls:
        print("  No suitable calls found.")
        return

    df = pd.concat(all_calls, ignore_index=True)
    df = df[(df["strike"] >= current_price) & (df["bid"] > 0.05) & (df["openInterest"] >= 10)].copy()

    if df.empty:
        print("  No qualifying calls found.")
        return

    df["premium_income"] = df["bid"] * 100
    df["ann_yield"] = (df["bid"] / current_price) * (365 / df["DTE"])
    df["max_profit_if_called"] = (df["strike"] - blended_cost + df["bid"]) * 100
    df["breakeven_after_premium"] = blended_cost - df["bid"]

    # Monthly income projection (repeat selling calls)
    df["monthly_premium_est"] = df["bid"] * (30 / df["DTE"]) * 100

    df = df.sort_values("ann_yield", ascending=False)

    print(f"  COVERED CALL CANDIDATES (sell 1 call against 100 shares)")
    print(f"  {'─'*55}")
    print(f"  Blended cost basis: ${blended_cost:.2f}/share\n")

    for _, row in df.head(8).iterrows():
        called_away = row["strike"] >= blended_cost
        print(f"  SELL {row['expiration']} ${row['strike']:.2f}C @ ${row['bid']:.2f}")
        print(f"    Premium: ${row['premium_income']:.0f}  |  "
              f"Ann. yield: {row['ann_yield']:.0%}  |  "
              f"~${row['monthly_premium_est']:.0f}/mo")
        if called_away:
            print(f"    If called away: PROFIT ${row['max_profit_if_called']:.0f} total"
                  f" (shares sold @ ${row['strike']:.2f} + premium)")
        else:
            print(f"    If called away: LOSS ${row['max_profit_if_called']:.0f}"
                  f" (selling below ${blended_cost:.2f} cost)")
        print(f"    Effective B/E: ${row['breakeven_after_premium']:.2f}/share")
        print()

    # Recovery timeline estimate
    print(f"\n  RECOVERY TIMELINE ESTIMATE")
    print(f"  {'─'*55}")
    total_loss = (blended_cost - current_price) * 100
    # Use median monthly premium from top candidates
    med_monthly = df.head(5)["monthly_premium_est"].median()
    if med_monthly > 0:
        months_to_recover = total_loss / med_monthly
        print(f"  Total unrealized loss:      ${total_loss:,.0f}")
        print(f"  Est. monthly CC premium:    ~${med_monthly:.0f}")
        print(f"  Months to recover via CC:   ~{months_to_recover:.0f} months")
        print(f"  (Assumes stock stays flat and you keep selling monthly calls)")
    else:
        print(f"  Could not estimate — premiums too low.")

    return df, blended_cost


# ─────────────────────────────────────────────────────
# STRATEGY C: Tax-Loss Harvest
# ─────────────────────────────────────────────────────
def strategy_c_tax_loss(current_price):
    print(f"\n\n{'='*70}")
    print(f"  STRATEGY C: TAX-LOSS HARVEST")
    print(f"{'='*70}")

    realized_loss = (current_price - COST_BASIS) * SHARES_OWNED

    print(f"\n  Sell all {SHARES_OWNED} shares @ ${current_price:.2f}")
    print(f"  Realized loss:     ${realized_loss:,.2f}")
    print(f"  Tax benefit:       ~${abs(realized_loss) * 0.30:,.0f} "
          f"(assuming ~30% marginal tax rate)")
    print(f"  Cash recovered:    ${SHARES_OWNED * current_price:,.2f}")
    print()
    print(f"  WASH SALE RULE: Cannot buy FIG back within 30 days")
    print(f"                  or the loss is disallowed.")
    print()
    print(f"  After 30 days, you could:")
    print(f"  - Re-enter with 100 shares and run the Wheel strategy")
    print(f"  - Deploy capital elsewhere")
    print(f"  - Use the tax loss to offset up to $3,000/year in ordinary income")
    print(f"    (or unlimited capital gains)")


# ─────────────────────────────────────────────────────
# Comparison Summary
# ─────────────────────────────────────────────────────
def comparison_summary(current_price, puts_df=None, calls_result=None):
    print(f"\n\n{'='*70}")
    print(f"  STRATEGY COMPARISON")
    print(f"{'='*70}")

    additional_cost_b = (100 - SHARES_OWNED) * current_price
    blended_b = (SHARES_OWNED * COST_BASIS + (100 - SHARES_OWNED) * current_price) / 100

    # Best put for strategy A (if available)
    put_strike = put_premium = 0
    if puts_df is not None and not puts_df.empty:
        best_put = puts_df.iloc[0]
        put_strike = best_put["strike"]
        put_premium = best_put["bid"]

    blended_a = (SHARES_OWNED * COST_BASIS + 100 * (put_strike - put_premium)) / 111 if put_strike > 0 else 0

    print(f"""
  ┌─────────────────────┬──────────────────┬──────────────────┬──────────────────┐
  │                     │  A: Sell Puts    │  B: Buy 89 Now   │  C: Tax Harvest  │
  │                     │  + Wheel         │  + Covered Calls │  + Redeploy      │
  ├─────────────────────┼──────────────────┼──────────────────┼──────────────────┤
  │ Additional Capital  │ ${put_strike*100 if put_strike else 0:>10,.0f}       │ ${additional_cost_b:>10,.0f}       │ $         0      │
  │ Shares After        │ 111 (if assign)  │ 100              │ 0                │
  │ Blended Cost/Share  │ ${blended_a:>10.2f}       │ ${blended_b:>10.2f}       │       N/A        │
  │ Can Sell CC?        │ Yes (if 100+)    │ Yes immediately  │ No               │
  │ Immediate Income    │ Put premium      │ Call premium     │ Tax savings      │
  │ Risk Level          │ Medium           │ Medium-High      │ Low              │
  │ Best For            │ Patient, bullish │ Bullish, active  │ Bearish/neutral  │
  └─────────────────────┴──────────────────┴──────────────────┴──────────────────┘""")

    print(f"\n  RECOMMENDATION (based on current setup):")
    print(f"  {'─'*55}")
    print(f"\n  With only 11 shares, you CANNOT sell covered calls yet (need 100).")
    print(f"  The key decision: Do you want to stay in FIG or exit?")
    print()
    print(f"  IF BULLISH on FIG:")
    print(f"    Best path: STRATEGY B — Buy 89 shares @ ${current_price:.2f}")
    print(f"    - Drops your cost basis from ${COST_BASIS:.2f} to ~${blended_b:.2f}")
    print(f"    - Immediately sell covered calls for ~${current_price*0.03*100:.0f}-${current_price*0.06*100:.0f}/month income")
    print(f"    - Each month of CC income chips away at the loss")
    print(f"    - Additional capital needed: ${additional_cost_b:,.0f}")
    print()
    print(f"  IF NEUTRAL on FIG:")
    print(f"    Best path: STRATEGY A — Sell cash-secured puts repeatedly")
    print(f"    - Collect premium while waiting (reduces effective cost)")
    print(f"    - If assigned, you get 100 shares at a discount → start selling CC")
    print(f"    - Capital needed: ~${put_strike*100:,.0f} (held as cash collateral)")
    print()
    print(f"  IF BEARISH on FIG:")
    print(f"    Best path: STRATEGY C — Tax-loss harvest")
    print(f"    - Realize ~${abs((current_price - COST_BASIS) * SHARES_OWNED):,.0f} loss")
    print(f"    - Use loss to offset gains or $3K/year income")
    print(f"    - Redeploy cash elsewhere")


# ─────────────────────────────────────────────────────
# Visualization
# ─────────────────────────────────────────────────────
def plot_recovery(current_price, calls_result=None):
    """Chart the cost basis recovery path."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("FIG Position Recovery — Strategy Comparison", fontsize=13, fontweight="bold")

    # ── Left: Cost basis comparison ──
    ax1 = axes[0]
    blended_b = (SHARES_OWNED * COST_BASIS + (100 - SHARES_OWNED) * current_price) / 100

    strategies = ["Current\n(11 shares)", "Strategy A\n(if assigned)", "Strategy B\n(buy 89 now)"]
    # Estimate blended for A with a typical near-ATM put
    est_blended_a = (SHARES_OWNED * COST_BASIS + 100 * (current_price * 0.95 - current_price * 0.04)) / 111
    costs = [COST_BASIS, est_blended_a, blended_b]
    colors = ["#e74c3c", "#f39c12", "#2ecc71"]

    bars = ax1.bar(strategies, costs, color=colors, width=0.5, edgecolor="black", linewidth=0.5)
    ax1.axhline(current_price, color="blue", linestyle="--", linewidth=1, label=f"Current price ${current_price:.2f}")
    for bar, cost in zip(bars, costs):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f"${cost:.2f}", ha="center", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Cost Basis ($/share)")
    ax1.set_title("Cost Basis Comparison")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    # ── Right: Recovery timeline via covered calls ──
    ax2 = axes[1]
    # Assume monthly CC premium = ~3-5% of stock price
    monthly_premiums = [current_price * pct for pct in [0.03, 0.04, 0.05]]
    months = range(0, 25)

    for prem, pct, style in zip(monthly_premiums, [3, 4, 5], ["-", "--", ":"]):
        cumulative = [blended_b - (m * prem) for m in months]
        ax2.plot(months, cumulative, style, linewidth=1.5, label=f"{pct}% monthly premium (${prem:.2f})")

    ax2.axhline(current_price, color="blue", linestyle="--", linewidth=1, label=f"Stock price ${current_price:.2f}")
    ax2.axhline(0, color="black", linewidth=0.5)
    ax2.set_xlabel("Months of Selling Covered Calls")
    ax2.set_ylabel("Effective Cost Basis ($/share)")
    ax2.set_title(f"Strategy B: Cost Basis Recovery Path\n(starting at ${blended_b:.2f})")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    path = "fig_recovery_chart.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Chart saved to: {path}")


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────
def main():
    stock, hist, current_price, info = fetch_data()

    # Position summary
    print_position_summary(current_price)

    # Strategy A
    puts_df = strategy_a_sell_puts_accumulate(stock, current_price)

    # Strategy B
    calls_result = strategy_b_buy_and_wheel(stock, current_price)

    # Strategy C
    strategy_c_tax_loss(current_price)

    # Comparison
    comparison_summary(current_price, puts_df, calls_result)

    # Chart
    try:
        plot_recovery(current_price, calls_result)
    except Exception as e:
        print(f"\n  Could not generate chart: {e}")

    print(f"\n{'='*70}")
    print(f"  DISCLAIMER: Educational/analysis purposes only. Not financial advice.")
    print(f"  Options trading involves significant risk of loss.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
