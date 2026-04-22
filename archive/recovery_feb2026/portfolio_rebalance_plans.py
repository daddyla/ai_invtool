#!/usr/bin/env python3
"""
Portfolio Rebalance Plans — Multi-Bucket Strategy
==================================================
Splits freed capital into 3 buckets:
  1. SHORT-TERM GROWTH (catalysts, momentum — 20-30%)
  2. LONG-TERM GROWTH  (compounders — 30-40%)
  3. HIGH YIELD INCOME  (dividends + options — 30-40%)

No new capital. Sell losers, redeploy smartly.

Requirements: pip install yfinance pandas numpy matplotlib
"""

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# ─────────────────────────────────────────────────────
# Current Holdings
# ─────────────────────────────────────────────────────
CURRENT = [
    {"ticker": "TMF",  "shares": 36, "cost": 45.29},
    {"ticker": "JEPQ", "shares": 20, "cost": 53.70},
    {"ticker": "BLSH", "shares": 11, "cost": 37.00},
    {"ticker": "FIG",  "shares": 11, "cost": 133.00},
    {"ticker": "DOCS", "shares": 6,  "cost": 41.00},
]

# ─────────────────────────────────────────────────────
# Candidate Universe (researched Feb 2026)
# ─────────────────────────────────────────────────────
SHORT_TERM_CANDIDATES = [
    {"ticker": "SOUN", "category": "AI Voice",
     "thesis": "Earnings Feb 26. Revenue est $54M (+28% QoQ). Target $16 (+117%)",
     "risk": "HIGH", "catalyst": "Earnings Feb 26"},
    {"ticker": "MARA", "category": "Crypto/BTC Mining",
     "thesis": "53K BTC holder. Target $19.60 (+161%). Bitcoin recovery play",
     "risk": "VERY HIGH", "catalyst": "Bitcoin recovery"},
    {"ticker": "RIOT", "category": "Crypto/AI Data Center",
     "thesis": "AI/HPC pivot + AMD lease. Target $26 (+75%). Strong Buy consensus",
     "risk": "HIGH", "catalyst": "AI pivot + BTC"},
    {"ticker": "SOFI", "category": "Fintech",
     "thesis": "Digital bank. 30% member growth. Target $26.50 (+35%). Best risk/reward",
     "risk": "MODERATE", "catalyst": "Banking platform growth"},
    {"ticker": "MGNI", "category": "Ad-Tech CTV",
     "thesis": "CTV ad leader. Streaming ad spend surge. Buy consensus. Target ~$15",
     "risk": "MODERATE-HIGH", "catalyst": "CTV ad spend acceleration"},
]

LONG_TERM_CANDIDATES = [
    {"ticker": "SCHG", "category": "Growth ETF",
     "thesis": "197 large-cap growth stocks. 0.04% fee. 10-yr avg 16%/yr. $30/share",
     "risk": "MODERATE", "yield": 0},
    {"ticker": "SOFI", "category": "Fintech Compounder",
     "thesis": "Full-stack digital bank. $4.65B rev target 2026. 60c EPS. 30% growth",
     "risk": "MODERATE", "yield": 0},
    {"ticker": "MGNI", "category": "Small-Cap Growth",
     "thesis": "CTV ad-tech leader. $1.7B mcap. Streaming tailwind. Buy consensus",
     "risk": "MODERATE-HIGH", "yield": 0},
    {"ticker": "ORN",  "category": "Infrastructure",
     "thesis": "Marine/defense construction. Infra spending tailwind. Target $15-17",
     "risk": "MODERATE", "yield": 0},
]

HIGH_YIELD_CANDIDATES = [
    {"ticker": "JEPQ", "category": "Covered Call ETF",
     "thesis": "Nasdaq-100 covered calls. 10.6% yield. Monthly. Best combo yield+growth",
     "risk": "MODERATE", "yield": 0.106},
    {"ticker": "JEPI", "category": "Covered Call ETF",
     "thesis": "S&P 500 covered calls. 7.3% yield. Monthly. Lowest volatility",
     "risk": "LOW-MODERATE", "yield": 0.073},
    {"ticker": "SVOL", "category": "Volatility Premium",
     "thesis": "Sells VIX futures. ~20% yield. Monthly. Profits from VIX contango",
     "risk": "MODERATE", "yield": 0.20},
    {"ticker": "SPHD", "category": "Dividend Low-Vol",
     "thesis": "S&P 500 high div + low vol. Just hiked div 23%. Beating S&P YTD",
     "risk": "LOW", "yield": 0.04},
    {"ticker": "SCHD", "category": "Dividend Growth",
     "thesis": "Quality div growers. 0.06% fee. Best long-term div appreciation",
     "risk": "LOW", "yield": 0.039},
]

pd.set_option("display.width", 220)


# ─────────────────────────────────────────────────────
# Fetch All Prices
# ─────────────────────────────────────────────────────
def fetch_prices():
    """Get current prices for all tickers."""
    all_tickers = set()
    for h in CURRENT:
        all_tickers.add(h["ticker"])
    for group in [SHORT_TERM_CANDIDATES, LONG_TERM_CANDIDATES, HIGH_YIELD_CANDIDATES]:
        for c in group:
            all_tickers.add(c["ticker"])

    prices = {}
    print(f"\n{'='*80}")
    print(f"  PORTFOLIO REBALANCE PLANS — MULTI-BUCKET STRATEGY")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*80}")
    print(f"\n  Fetching prices for {len(all_tickers)} tickers...")

    for t in all_tickers:
        try:
            hist = yf.Ticker(t).history(period="5d")
            if not hist.empty:
                prices[t] = hist["Close"].iloc[-1]
        except Exception:
            pass

    return prices


# ─────────────────────────────────────────────────────
# Current Portfolio Summary
# ─────────────────────────────────────────────────────
def portfolio_summary(prices):
    print(f"\n{'─'*80}")
    print(f"  CURRENT PORTFOLIO")
    print(f"{'─'*80}")

    total_inv = 0
    total_val = 0
    details = []

    for h in CURRENT:
        p = prices.get(h["ticker"], 0)
        inv = h["shares"] * h["cost"]
        val = h["shares"] * p
        pnl = val - inv
        total_inv += inv
        total_val += val
        details.append({"ticker": h["ticker"], "shares": h["shares"], "cost": h["cost"],
                         "price": p, "value": val, "pnl": pnl})
        sign = "+" if pnl >= 0 else ""
        print(f"  {h['ticker']:6s}  {h['shares']:3d} x ${h['cost']:>7.2f} → ${p:>7.2f}  "
              f"Val ${val:>6,.0f}  P&L {sign}${pnl:>7,.0f} ({pnl/inv:+.0%})")

    total_pnl = total_val - total_inv
    print(f"\n  Total: ${total_val:,.0f} invested ${total_inv:,.0f} | P&L ${total_pnl:,.0f} ({total_pnl/total_inv:+.1%})")

    return total_val, total_pnl, details


# ─────────────────────────────────────────────────────
# Step 1: Determine Sells & Frees
# ─────────────────────────────────────────────────────
def determine_sells(details, prices):
    print(f"\n{'─'*80}")
    print(f"  STEP 1: SELL UNDERPERFORMERS → FREE CAPITAL")
    print(f"{'─'*80}")

    # Always sell: FIG (down 80%), TMF (leveraged decay), DOCS (tiny, down 39%)
    # BLSH: borderline — sell to free more capital for better deployment
    sell_tickers = ["FIG", "TMF", "DOCS", "BLSH"]
    keep_tickers = ["JEPQ"]

    freed = 0
    tax_loss = 0

    print(f"\n  SELL:")
    for d in details:
        if d["ticker"] in sell_tickers:
            freed += d["value"]
            if d["pnl"] < 0:
                tax_loss += abs(d["pnl"])
            print(f"    SELL {d['ticker']:6s} → Free ${d['value']:>6,.0f}"
                  f"  (realize ${d['pnl']:>7,.0f} {'loss' if d['pnl'] < 0 else 'gain'})")

    print(f"\n  KEEP:")
    kept_value = 0
    for d in details:
        if d["ticker"] in keep_tickers:
            kept_value += d["value"]
            print(f"    KEEP {d['ticker']:6s}   ${d['value']:>6,.0f}  (income anchor, +{d['pnl']:.0f})")

    tax_savings = tax_loss * 0.30

    print(f"\n  Capital freed:     ${freed:,.0f}")
    print(f"  Tax losses:        ${tax_loss:,.0f} → ~${tax_savings:,.0f} tax savings")
    print(f"  Portfolio kept:    ${kept_value:,.0f} (JEPQ)")
    print(f"  Total deployable:  ${freed:,.0f}")

    return freed, tax_savings, kept_value


# ─────────────────────────────────────────────────────
# Step 2: Generate 3 Plans
# ─────────────────────────────────────────────────────
def generate_plans(freed, kept_value, prices, tax_savings, total_pnl):
    plans = []

    # ──────────────────────────────────────────────────
    # PLAN A: AGGRESSIVE GROWTH (Recovery in ~8-12 months)
    # 40% short-term growth | 35% long-term growth | 25% income
    # ──────────────────────────────────────────────────
    plan_a = {
        "name": "PLAN A: AGGRESSIVE GROWTH",
        "subtitle": "Max growth, higher risk. Target: recover in 8-12 months.",
        "buckets": [],
        "total_monthly": 0,
    }

    st_budget = freed * 0.40
    lt_budget = freed * 0.35
    hy_budget = freed * 0.25

    # Short-term bucket
    st_alloc = []
    remaining_st = st_budget

    # SOUN - earnings play
    p = prices.get("SOUN", 7.50)
    shares = int(remaining_st * 0.40 / p)
    if shares > 0:
        cost = shares * p
        st_alloc.append({"ticker": "SOUN", "shares": shares, "cost_total": cost,
                          "note": "Earnings Feb 26. AI voice. Target $16 (+117%)"})
        remaining_st -= cost

    # MARA - BTC leverage
    p = prices.get("MARA", 7.50)
    shares = int(remaining_st * 0.50 / p)
    if shares > 0:
        cost = shares * p
        st_alloc.append({"ticker": "MARA", "shares": shares, "cost_total": cost,
                          "note": "53K BTC holder. Target $19.60 (+161%)"})
        remaining_st -= cost

    # RIOT - AI/Crypto hybrid
    p = prices.get("RIOT", 15.60)
    shares = int(remaining_st / p)
    if shares > 0:
        cost = shares * p
        st_alloc.append({"ticker": "RIOT", "shares": shares, "cost_total": cost,
                          "note": "AI/HPC pivot + BTC. Target $26 (+75%)"})
        remaining_st -= cost

    plan_a["buckets"].append({
        "name": "SHORT-TERM GROWTH (40%)",
        "budget": st_budget,
        "allocations": st_alloc,
        "cash_left": remaining_st,
    })

    # Long-term bucket
    lt_alloc = []
    remaining_lt = lt_budget

    p = prices.get("SOFI", 19.00)
    shares = int(remaining_lt * 0.50 / p)
    if shares > 0:
        cost = shares * p
        lt_alloc.append({"ticker": "SOFI", "shares": shares, "cost_total": cost,
                          "note": "Digital bank. 30% growth. Target $26.50"})
        remaining_lt -= cost

    p = prices.get("SCHG", 30.60)
    shares = int(remaining_lt * 0.60 / p)
    if shares > 0:
        cost = shares * p
        lt_alloc.append({"ticker": "SCHG", "shares": shares, "cost_total": cost,
                          "note": "Growth ETF. 0.04% fee. 197 large-cap stocks"})
        remaining_lt -= cost

    p = prices.get("MGNI", 12.00)
    shares = int(remaining_lt / p)
    if shares > 0:
        cost = shares * p
        lt_alloc.append({"ticker": "MGNI", "shares": shares, "cost_total": cost,
                          "note": "CTV ad-tech. Buy consensus. Multibagger potential"})
        remaining_lt -= cost

    plan_a["buckets"].append({
        "name": "LONG-TERM GROWTH (35%)",
        "budget": lt_budget,
        "allocations": lt_alloc,
        "cash_left": remaining_lt,
    })

    # High yield bucket
    hy_alloc = []
    remaining_hy = hy_budget
    monthly_income = 0

    # JEPQ already kept — count its income
    jepq_shares_kept = 20
    jepq_monthly = jepq_shares_kept * 0.48
    monthly_income += jepq_monthly

    # Add SVOL for high yield
    p = prices.get("SVOL", 16.80)
    shares = int(remaining_hy * 0.50 / p)
    if shares > 0:
        cost = shares * p
        mo = cost * 0.20 / 12
        monthly_income += mo
        hy_alloc.append({"ticker": "SVOL", "shares": shares, "cost_total": cost,
                          "note": f"VIX premium. ~20% yield. ~${mo:.0f}/mo", "monthly": mo})
        remaining_hy -= cost

    # Add more JEPQ
    p = prices.get("JEPQ", 57.60)
    shares = int(remaining_hy / p)
    if shares > 0:
        cost = shares * p
        mo = cost * 0.106 / 12
        monthly_income += mo
        hy_alloc.append({"ticker": "JEPQ", "shares": shares, "cost_total": cost,
                          "note": f"Add to existing. 10.6% yield. ~${mo:.0f}/mo", "monthly": mo})
        remaining_hy -= cost

    plan_a["buckets"].append({
        "name": f"HIGH YIELD INCOME (25%) + JEPQ kept",
        "budget": hy_budget + kept_value,
        "allocations": hy_alloc,
        "cash_left": remaining_hy,
        "jepq_kept_income": jepq_monthly,
    })
    plan_a["total_monthly"] = monthly_income

    plans.append(plan_a)

    # ──────────────────────────────────────────────────
    # PLAN B: BALANCED (Recovery in ~12-15 months)
    # 20% short-term | 40% long-term | 40% income
    # ──────────────────────────────────────────────────
    plan_b = {
        "name": "PLAN B: BALANCED",
        "subtitle": "Balanced risk. Growth + steady income. Target: recover in 12-15 months.",
        "buckets": [],
        "total_monthly": 0,
    }

    st_budget = freed * 0.20
    lt_budget = freed * 0.40
    hy_budget = freed * 0.40

    # Short-term: just SOFI (best risk/reward)
    st_alloc = []
    p = prices.get("SOFI", 19.00)
    shares = int(st_budget * 0.60 / p)
    if shares > 0:
        st_alloc.append({"ticker": "SOFI", "shares": shares, "cost_total": shares * p,
                          "note": "Best risk/reward. Target $26.50 (+35%)"})

    p = prices.get("MGNI", 12.00)
    shares2 = int((st_budget - shares * prices.get("SOFI", 19)) / p) if shares > 0 else int(st_budget * 0.40 / p)
    if shares2 > 0:
        st_alloc.append({"ticker": "MGNI", "shares": shares2, "cost_total": shares2 * p,
                          "note": "CTV ad-tech. Buy consensus"})

    plan_b["buckets"].append({
        "name": "SHORT-TERM GROWTH (20%)",
        "budget": st_budget,
        "allocations": st_alloc,
    })

    # Long-term
    lt_alloc = []
    remaining_lt = lt_budget

    p = prices.get("SCHG", 30.60)
    shares = int(remaining_lt * 0.50 / p)
    if shares > 0:
        cost = shares * p
        lt_alloc.append({"ticker": "SCHG", "shares": shares, "cost_total": cost,
                          "note": "Core growth ETF. 0.04% fee"})
        remaining_lt -= cost

    p = prices.get("SOFI", 19.00)
    shares = int(remaining_lt * 0.50 / p)
    if shares > 0:
        cost = shares * p
        lt_alloc.append({"ticker": "SOFI", "shares": shares, "cost_total": cost,
                          "note": "Long-term fintech compounder"})
        remaining_lt -= cost

    p = prices.get("ORN", 13.00)
    shares = int(remaining_lt / p)
    if shares > 0:
        cost = shares * p
        lt_alloc.append({"ticker": "ORN", "shares": shares, "cost_total": cost,
                          "note": "Infrastructure. Target $15-17"})
        remaining_lt -= cost

    plan_b["buckets"].append({
        "name": "LONG-TERM GROWTH (40%)",
        "budget": lt_budget,
        "allocations": lt_alloc,
    })

    # High yield
    hy_alloc = []
    remaining_hy = hy_budget
    monthly_income = jepq_monthly  # JEPQ kept

    p = prices.get("JEPI", 59.30)
    shares = int(remaining_hy * 0.40 / p)
    if shares > 0:
        cost = shares * p
        mo = cost * 0.073 / 12
        monthly_income += mo
        hy_alloc.append({"ticker": "JEPI", "shares": shares, "cost_total": cost,
                          "note": f"Conservative income. 7.3% yield. ~${mo:.0f}/mo", "monthly": mo})
        remaining_hy -= cost

    p = prices.get("SVOL", 16.80)
    shares = int(remaining_hy * 0.40 / p)
    if shares > 0:
        cost = shares * p
        mo = cost * 0.20 / 12
        monthly_income += mo
        hy_alloc.append({"ticker": "SVOL", "shares": shares, "cost_total": cost,
                          "note": f"VIX premium. ~20% yield. ~${mo:.0f}/mo", "monthly": mo})
        remaining_hy -= cost

    p = prices.get("SPHD", 52.00)
    shares = int(remaining_hy / p)
    if shares > 0:
        cost = shares * p
        mo = cost * 0.04 / 12
        monthly_income += mo
        hy_alloc.append({"ticker": "SPHD", "shares": shares, "cost_total": cost,
                          "note": f"Low-vol dividend. Just hiked 23%. ~${mo:.0f}/mo", "monthly": mo})
        remaining_hy -= cost

    plan_b["buckets"].append({
        "name": f"HIGH YIELD INCOME (40%) + JEPQ kept",
        "budget": hy_budget + kept_value,
        "allocations": hy_alloc,
        "jepq_kept_income": jepq_monthly,
    })
    plan_b["total_monthly"] = monthly_income

    plans.append(plan_b)

    # ──────────────────────────────────────────────────
    # PLAN C: CONSERVATIVE INCOME (Recovery in ~15-18 months)
    # 10% short-term | 30% long-term | 60% income
    # ──────────────────────────────────────────────────
    plan_c = {
        "name": "PLAN C: CONSERVATIVE INCOME",
        "subtitle": "Max income, lowest risk. Steady recovery via dividends + yield.",
        "buckets": [],
        "total_monthly": 0,
    }

    st_budget = freed * 0.10
    lt_budget = freed * 0.30
    hy_budget = freed * 0.60

    # Short-term: just a small SOFI position
    st_alloc = []
    p = prices.get("SOFI", 19.00)
    shares = int(st_budget / p)
    if shares > 0:
        st_alloc.append({"ticker": "SOFI", "shares": shares, "cost_total": shares * p,
                          "note": "Small growth position. Target $26.50"})

    plan_c["buckets"].append({
        "name": "SHORT-TERM GROWTH (10%)",
        "budget": st_budget,
        "allocations": st_alloc,
    })

    # Long-term
    lt_alloc = []
    remaining_lt = lt_budget

    p = prices.get("SCHG", 30.60)
    shares = int(remaining_lt * 0.60 / p)
    if shares > 0:
        cost = shares * p
        lt_alloc.append({"ticker": "SCHG", "shares": shares, "cost_total": cost,
                          "note": "Core growth. Low-cost diversified"})
        remaining_lt -= cost

    p = prices.get("SCHD", 27.90)
    shares = int(remaining_lt / p)
    if shares > 0:
        cost = shares * p
        lt_alloc.append({"ticker": "SCHD", "shares": shares, "cost_total": cost,
                          "note": "Dividend growers. 0.06% fee. Compounding machine"})
        remaining_lt -= cost

    plan_c["buckets"].append({
        "name": "LONG-TERM GROWTH (30%)",
        "budget": lt_budget,
        "allocations": lt_alloc,
    })

    # High yield — heavy
    hy_alloc = []
    remaining_hy = hy_budget
    monthly_income = jepq_monthly

    p = prices.get("JEPQ", 57.60)
    shares = int(remaining_hy * 0.35 / p)
    if shares > 0:
        cost = shares * p
        mo = cost * 0.106 / 12
        monthly_income += mo
        hy_alloc.append({"ticker": "JEPQ", "shares": shares, "cost_total": cost,
                          "note": f"Add to existing JEPQ. ~${mo:.0f}/mo", "monthly": mo})
        remaining_hy -= cost

    p = prices.get("JEPI", 59.30)
    shares = int(remaining_hy * 0.35 / p)
    if shares > 0:
        cost = shares * p
        mo = cost * 0.073 / 12
        monthly_income += mo
        hy_alloc.append({"ticker": "JEPI", "shares": shares, "cost_total": cost,
                          "note": f"Conservative income. ~${mo:.0f}/mo", "monthly": mo})
        remaining_hy -= cost

    p = prices.get("SVOL", 16.80)
    shares = int(remaining_hy * 0.50 / p)
    if shares > 0:
        cost = shares * p
        mo = cost * 0.20 / 12
        monthly_income += mo
        hy_alloc.append({"ticker": "SVOL", "shares": shares, "cost_total": cost,
                          "note": f"VIX premium. 20% yield. ~${mo:.0f}/mo", "monthly": mo})
        remaining_hy -= cost

    p = prices.get("SPHD", 52.00)
    shares = int(remaining_hy / p)
    if shares > 0:
        cost = shares * p
        mo = cost * 0.04 / 12
        monthly_income += mo
        hy_alloc.append({"ticker": "SPHD", "shares": shares, "cost_total": cost,
                          "note": f"Low-vol defensive. ~${mo:.0f}/mo", "monthly": mo})
        remaining_hy -= cost

    plan_c["buckets"].append({
        "name": f"HIGH YIELD INCOME (60%) + JEPQ kept",
        "budget": hy_budget + kept_value,
        "allocations": hy_alloc,
        "jepq_kept_income": jepq_monthly,
    })
    plan_c["total_monthly"] = monthly_income

    plans.append(plan_c)

    return plans


# ─────────────────────────────────────────────────────
# Display Plans
# ─────────────────────────────────────────────────────
def display_plans(plans, freed, tax_savings, total_pnl, kept_value):
    effective_loss = abs(total_pnl) - tax_savings

    for plan in plans:
        print(f"\n\n{'#'*80}")
        print(f"  {plan['name']}")
        print(f"  {plan['subtitle']}")
        print(f"{'#'*80}")

        total_deployed = 0
        for bucket in plan["buckets"]:
            print(f"\n  [{bucket['name']}]")
            if "jepq_kept_income" in bucket:
                print(f"    (includes JEPQ 20 shares kept → ~${bucket['jepq_kept_income']:.0f}/mo dividends)")

            for a in bucket.get("allocations", []):
                print(f"    BUY  {a['ticker']:6s}  {a['shares']:>3d} shares  ${a['cost_total']:>7,.0f}  {a['note']}")
                total_deployed += a["cost_total"]

        cash_left = freed - total_deployed
        mo = plan["total_monthly"]
        annual = mo * 12

        print(f"\n  {'─'*60}")
        print(f"  Deployed:           ${total_deployed:,.0f} of ${freed:,.0f} freed")
        print(f"  Cash reserve:       ${max(cash_left, 0):,.0f}")
        print(f"  Monthly income:     ~${mo:,.0f} (JEPQ kept + new positions)")
        print(f"  Annual income:      ~${annual:,.0f}")
        print(f"  Tax savings:        ~${tax_savings:,.0f} (one-time)")
        print(f"  Effective loss:     ${effective_loss:,.0f}")
        if mo > 0:
            print(f"  Recovery timeline:  ~{effective_loss / mo:.0f} months via income alone")
        print(f"  Growth upside:      If growth picks hit targets, recovery is MUCH faster")


# ─────────────────────────────────────────────────────
# Comparison Table
# ─────────────────────────────────────────────────────
def comparison_table(plans, total_pnl, tax_savings, freed=2231):
    effective_loss = abs(total_pnl) - tax_savings

    print(f"\n\n{'#'*80}")
    print(f"  PLAN COMPARISON")
    print(f"{'#'*80}")

    a, b, c = plans[0], plans[1], plans[2]
    ma, mb, mc = a["total_monthly"], b["total_monthly"], c["total_monthly"]

    # Count growth vs income tickers
    def count_tickers(plan):
        growth = set()
        income = set()
        for bucket in plan["buckets"]:
            name = bucket["name"]
            for alloc in bucket.get("allocations", []):
                if "SHORT" in name or "LONG" in name:
                    growth.add(alloc["ticker"])
                else:
                    income.add(alloc["ticker"])
        return growth, income

    ga, ia = count_tickers(a)
    gb, ib = count_tickers(b)
    gc, ic = count_tickers(c)

    print(f"""
  ┌───────────────────────┬──────────────────┬──────────────────┬──────────────────┐
  │                       │ A: AGGRESSIVE    │ B: BALANCED      │ C: CONSERVATIVE  │
  ├───────────────────────┼──────────────────┼──────────────────┼──────────────────┤
  │ Growth allocation     │ 75% (40+35)      │ 60% (20+40)      │ 40% (10+30)      │
  │ Income allocation     │ 25%              │ 40%              │ 60%              │
  │ Monthly income        │ ~${ma:>5.0f}          │ ~${mb:>5.0f}          │ ~${mc:>5.0f}          │
  │ Annual income         │ ~${ma*12:>5.0f}          │ ~${mb*12:>5.0f}          │ ~${mc*12:>5.0f}          │
  │ Growth tickers        │ {', '.join(sorted(ga)):16s} │ {', '.join(sorted(gb)):16s} │ {', '.join(sorted(gc)):16s} │
  │ Income tickers        │ JEPQ+{', '.join(sorted(ia)):10s} │ JEPQ+{', '.join(sorted(ib)):10s} │ JEPQ+{', '.join(sorted(ic)):10s} │
  │ Recovery (income only)│ ~{effective_loss/max(ma,1):>3.0f} months        │ ~{effective_loss/max(mb,1):>3.0f} months        │ ~{effective_loss/max(mc,1):>3.0f} months        │
  │ Recovery (w/ growth)  │ ~8-12 months     │ ~10-14 months    │ ~14-18 months    │
  │ Risk level            │ HIGH             │ MODERATE         │ LOW-MODERATE     │
  │ Best for              │ Aggressive recov │ Balanced approach │ Sleep at night   │
  └───────────────────────┴──────────────────┴──────────────────┴──────────────────┘""")

    print(f"\n  Tax savings (all plans): ~${tax_savings:,.0f}")
    print(f"  Effective loss to recover: ${effective_loss:,.0f}")

    print(f"\n  MY SUGGESTION: PLAN B (BALANCED)")
    print(f"  {'─'*55}")
    print(f"  - Best risk/reward balance for a small portfolio")
    print(f"  - SOFI + SCHG give you solid growth exposure")
    print(f"  - JEPI + SVOL + JEPQ give steady monthly income")
    print(f"  - ~${mb:.0f}/mo income chips away at loss while growth positions work")
    print(f"  - If SOFI hits $26.50 target (+35%), that alone recovers ~${0.35 * freed * 0.20:,.0f}")


# ─────────────────────────────────────────────────────
# Visualization
# ─────────────────────────────────────────────────────
def plot_plans(plans, total_pnl, tax_savings):
    effective_loss = abs(total_pnl) - tax_savings

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("Portfolio Rebalance Plans — Side by Side", fontsize=14, fontweight="bold")

    plan_names = ["A: AGGRESSIVE", "B: BALANCED", "C: CONSERVATIVE"]
    colors_map = {
        "SHORT-TERM": "#e74c3c",
        "LONG-TERM": "#3498db",
        "HIGH YIELD": "#2ecc71",
        "Cash": "#95a5a6",
    }

    for idx, (plan, ax) in enumerate(zip(plans, axes)):
        # Collect all allocations per bucket type
        bucket_data = {}
        for bucket in plan["buckets"]:
            bname = bucket["name"].split("(")[0].strip()
            total = sum(a["cost_total"] for a in bucket.get("allocations", []))
            bucket_data[bname] = total

        # Pie chart
        labels = []
        sizes = []
        colors = []
        for bname, val in bucket_data.items():
            if val > 0:
                labels.append(bname)
                sizes.append(val)
                if "SHORT" in bname:
                    colors.append(colors_map["SHORT-TERM"])
                elif "LONG" in bname:
                    colors.append(colors_map["LONG-TERM"])
                else:
                    colors.append(colors_map["HIGH YIELD"])

        if sizes:
            wedges, texts, autotexts = ax.pie(sizes, labels=None, autopct="%1.0f%%",
                                               colors=colors, startangle=90, pctdistance=0.75)
            for t in autotexts:
                t.set_fontsize(9)

            # Custom legend
            legend_labels = [f"{l}\n${s:,.0f}" for l, s in zip(labels, sizes)]
            ax.legend(legend_labels, loc="lower center", fontsize=7,
                     bbox_to_anchor=(0.5, -0.15), ncol=1)

        mo = plan["total_monthly"]
        ax.set_title(f"{plan_names[idx]}\n~${mo:.0f}/mo income\n"
                     f"Recovery: ~{effective_loss/max(mo,1):.0f}mo (income)",
                     fontsize=10)

    plt.tight_layout()
    path = "portfolio_rebalance_plans_chart.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Chart saved to: {path}")


# ─────────────────────────────────────────────────────
# Catalyst Calendar
# ─────────────────────────────────────────────────────
def print_catalyst_calendar():
    print(f"\n\n{'#'*80}")
    print(f"  UPCOMING CATALYST CALENDAR")
    print(f"{'#'*80}")
    print(f"""
  ┌────────────────┬─────────┬──────────────────────────────────────────────┐
  │ Date           │ Ticker  │ Event                                        │
  ├────────────────┼─────────┼──────────────────────────────────────────────┤
  │ Feb 25, 2026   │ NVDA    │ Q4 earnings. Moves entire market.            │
  │ Feb 26, 2026   │ SOUN    │ Q4 earnings. Revenue est $54M (+28% QoQ).    │
  │ Feb 26, 2026   │ SG      │ Sweetgreen earnings. Near 52-week low.       │
  │ March 2026     │ NVDA    │ GTC Conference — AI inference roadmap.        │
  │ March 2026     │ SOFI    │ Potential Q1 guidance update.                 │
  │ Q1 2026        │ RIOT    │ AI/HPC revenue ramp from AMD lease.          │
  │ Q1 2026        │ MARA    │ BTC accumulation updates + AI pivot.         │
  │ Ongoing        │ JEPQ    │ Monthly dividend ~$0.48/share (ex-div ~1st). │
  │ Ongoing        │ SVOL    │ Monthly dividend ~20% annualized yield.      │
  └────────────────┴─────────┴──────────────────────────────────────────────┘

  TIP: Buy SOUN *after* Feb 26 earnings (avoid binary risk) unless you
       want to gamble on the beat. Same logic for NVDA on Feb 25.
  """)


# ─────────────────────────────────────────────────────
def main():
    prices = fetch_prices()
    total_val, total_pnl, details = portfolio_summary(prices)
    freed, tax_savings, kept_value = determine_sells(details, prices)
    plans = generate_plans(freed, kept_value, prices, tax_savings, total_pnl)
    display_plans(plans, freed, tax_savings, total_pnl, kept_value)
    comparison_table(plans, total_pnl, tax_savings, freed)
    print_catalyst_calendar()

    try:
        plot_plans(plans, total_pnl, tax_savings)
    except Exception as e:
        print(f"\n  Could not generate chart: {e}")

    print(f"\n{'='*80}")
    print(f"  DISCLAIMER: Educational purposes only. Not financial advice.")
    print(f"  All investments carry risk. Past performance != future results.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
