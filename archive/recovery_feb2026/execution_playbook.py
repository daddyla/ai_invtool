#!/usr/bin/env python3
"""
Execution Playbook — Day-by-Day Trading Guide
===============================================
Exact timing for when to sell, when to buy, in what order.
Accounts for: earnings dates, ex-dividend dates, settlement,
wash sale rules, and optimal execution windows.

Today: February 19, 2026 (Thursday)

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
# Key Dates
# ─────────────────────────────────────────────────────
KEY_DATES = {
    "today":            "2026-02-19",
    "nvda_earnings":    "2026-02-25",  # After close, Wed
    "soun_earnings":    "2026-02-26",  # After close, Thu
    "sphd_exdiv":       "2026-02-24",  # Estimated, Tue
    "svol_exdiv_feb":   "2026-02-25",  # Estimated, Wed
    "jepq_exdiv":       "2026-03-02",  # Confirmed, Mon
    "jepi_exdiv":       "2026-03-02",  # Confirmed, Mon
    "sphd_exdiv_mar":   "2026-03-24",  # Estimated
    "svol_exdiv_mar":   "2026-03-26",  # Estimated
    "schd_exdiv":       "2026-03-26",  # Confirmed, quarterly
    # Wash sale: 30 days after sell = cannot rebuy same stock
    "wash_sale_end":    "2026-03-22",  # 30 days from ~Feb 20
}


def fetch_live_prices():
    """Fetch current prices for execution planning."""
    tickers = ["TMF", "JEPQ", "BLSH", "FIG", "DOCS",
               "SOFI", "SCHG", "MGNI", "ORN", "SOUN",
               "MARA", "RIOT", "JEPI", "SVOL", "SPHD", "SCHD"]
    prices = {}
    for t in tickers:
        try:
            h = yf.Ticker(t).history(period="2d")
            if not h.empty:
                prices[t] = round(h["Close"].iloc[-1], 2)
        except Exception:
            pass
    return prices


def print_header():
    print(f"\n{'='*80}")
    print(f"  EXECUTION PLAYBOOK — DAY-BY-DAY TRADING GUIDE")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*80}")


def print_rules():
    print(f"""
  ┌────────────────────────────────────────────────────────────────────┐
  │  EXECUTION RULES                                                   │
  ├────────────────────────────────────────────────────────────────────┤
  │  1. Execute ALL trades between 10:00-11:30 AM ET (best fills)     │
  │  2. Use LIMIT orders, not market orders (small positions)         │
  │  3. Settlement is T+1 (buy today → settled tomorrow)              │
  │  4. Must own BEFORE ex-div date to get dividend                   │
  │  5. Wash sale: don't rebuy sold stocks within 30 days             │
  │  6. SELL losers FIRST, then buy new positions with freed cash     │
  │  7. Don't buy before earnings unless you want binary risk         │
  └────────────────────────────────────────────────────────────────────┘""")


def phase1_immediate_sells(prices):
    print(f"\n\n{'#'*80}")
    print(f"  PHASE 1: IMMEDIATE SELLS — Do This TOMORROW (Feb 20, Thu)")
    print(f"  Time: 10:00-11:00 AM ET")
    print(f"{'#'*80}")

    sells = [
        {"ticker": "FIG",  "shares": 11, "cost": 133.00, "reason": "Down 81%. Dead money. Harvest $1,180 tax loss."},
        {"ticker": "DOCS", "shares": 6,  "cost": 41.00,  "reason": "Down 39%. Tiny position ($150). Harvest $96 loss."},
        {"ticker": "TMF",  "shares": 36, "cost": 45.29,  "reason": "3x leveraged decay. Harvest $181 loss. Free $1,450."},
        {"ticker": "BLSH", "shares": 11, "cost": 37.00,  "reason": "Down 14%. Small position. Free $348."},
    ]

    total_freed = 0
    total_tax_loss = 0

    print(f"\n  ORDER OF EXECUTION (do in this order):\n")
    for i, s in enumerate(sells, 1):
        p = prices.get(s["ticker"], 0)
        value = s["shares"] * p
        loss = value - (s["shares"] * s["cost"])
        total_freed += value
        if loss < 0:
            total_tax_loss += abs(loss)

        print(f"  {i}. SELL ALL {s['ticker']}  —  {s['shares']} shares @ ~${p:.2f} = ~${value:,.0f}")
        print(f"     Order type: LIMIT order at ${p:.2f} (or slightly below ask)")
        print(f"     Why: {s['reason']}")
        if loss < 0:
            print(f"     Tax loss: ${abs(loss):,.0f}")
        print()

    print(f"  {'─'*60}")
    print(f"  Total cash freed:       ~${total_freed:,.0f}")
    print(f"  Total tax losses:       ~${total_tax_loss:,.0f}")
    print(f"  Est. tax savings:       ~${total_tax_loss * 0.30:,.0f}")
    print(f"  Cash available (T+1):   Feb 21 (Friday)")

    print(f"\n  WASH SALE WARNING:")
    print(f"  Do NOT buy FIG, DOCS, TMF, or BLSH until after March 22, 2026")
    print(f"  (30 calendar days from sell date)")

    return total_freed, total_tax_loss


def phase2_pre_earnings_buys(prices, freed):
    print(f"\n\n{'#'*80}")
    print(f"  PHASE 2: SAFE BUYS — Feb 21 (Fri) after cash settles")
    print(f"  Time: 10:00-11:30 AM ET")
    print(f"  These are NOT earnings-dependent picks")
    print(f"{'#'*80}")

    print(f"""
  WHY BUY FRIDAY FEB 21:
  - Cash from Phase 1 sells is settled (T+1)
  - SPHD ex-div is Feb 24 → buy before to capture dividend
  - SVOL ex-div is Feb 25 → buy before to capture dividend
  - JEPQ/JEPI ex-div is Mar 2 → still time, but buy early to settle
  - Buy income & long-term positions BEFORE earnings volatility (Feb 25-26)
  """)

    # Plan B (Balanced) allocations
    buys = []
    remaining = freed

    # Income bucket FIRST (capture dividends)
    print(f"  ── INCOME POSITIONS (buy first to capture dividends) ──\n")

    # SPHD - ex div Feb 24
    p = prices.get("SPHD", 52.00)
    shares = 6
    cost = shares * p
    buys.append({"ticker": "SPHD", "shares": shares, "price": p, "total": cost,
                 "urgency": "URGENT", "reason": "Ex-div Feb 24 (Tue). Buy Fri to settle Mon."})
    remaining -= cost

    # SVOL - ex div Feb 25
    p = prices.get("SVOL", 16.80)
    shares = 12
    cost = shares * p
    buys.append({"ticker": "SVOL", "shares": shares, "price": p, "total": cost,
                 "urgency": "URGENT", "reason": "Ex-div Feb 25 (Wed). Buy Fri to settle Mon."})
    remaining -= cost

    # JEPI
    p = prices.get("JEPI", 59.30)
    shares = 6
    cost = shares * p
    buys.append({"ticker": "JEPI", "shares": shares, "price": p, "total": cost,
                 "urgency": "MODERATE", "reason": "Ex-div Mar 2. Buy anytime before Feb 27."})
    remaining -= cost

    for b in buys:
        print(f"  BUY {b['shares']:>3d} {b['ticker']:6s} @ ~${b['price']:>7.2f} = ${b['total']:>7,.0f}"
              f"  [{b['urgency']}]")
        print(f"       {b['reason']}")
        print(f"       Order: LIMIT @ ${b['price']:.2f}")
        print()

    # Long-term positions (not time-sensitive for dividends)
    print(f"  ── LONG-TERM GROWTH POSITIONS (same day, after income buys) ──\n")

    lt_buys = []

    p = prices.get("SCHG", 30.60)
    shares = 14
    cost = shares * p
    lt_buys.append({"ticker": "SCHG", "shares": shares, "price": p, "total": cost,
                    "reason": "Core growth ETF. 0.04% fee. No catalyst urgency."})
    remaining -= cost

    p = prices.get("ORN", 13.00)
    shares = 17
    cost = shares * p
    lt_buys.append({"ticker": "ORN", "shares": shares, "price": p, "total": cost,
                    "reason": "Infrastructure play. Target $15-17. Steady compounder."})
    remaining -= cost

    for b in lt_buys:
        print(f"  BUY {b['shares']:>3d} {b['ticker']:6s} @ ~${b['price']:>7.2f} = ${b['total']:>7,.0f}")
        print(f"       {b['reason']}")
        print(f"       Order: LIMIT @ ${b['price']:.2f}")
        print()

    total_phase2 = sum(b["total"] for b in buys + lt_buys)
    print(f"  {'─'*60}")
    print(f"  Phase 2 total deployed: ~${total_phase2:,.0f}")
    print(f"  Cash remaining:         ~${remaining:,.0f}")

    return remaining


def phase3_post_earnings_buys(prices, remaining):
    print(f"\n\n{'#'*80}")
    print(f"  PHASE 3: POST-EARNINGS BUYS — Feb 27 (Fri) or Mar 2 (Mon)")
    print(f"  Time: 10:00-11:30 AM ET")
    print(f"  WAIT for NVDA (Feb 25) and SOUN (Feb 26) earnings to settle")
    print(f"{'#'*80}")

    print(f"""
  WHY WAIT UNTIL FEB 27 OR LATER:
  - NVDA reports after close Feb 25 → market-wide impact Feb 26
  - SOUN reports after close Feb 26 → if you want SOUN, buy Feb 27
  - Feb 26 will be volatile → let dust settle 1 day
  - You avoid binary earnings risk
  - If NVDA beats: market rallies → buy the dip in growth names
  - If NVDA misses: growth names drop → buy at lower prices

  DECISION TREE FOR FEB 27 MORNING:
  ┌──────────────────────────────────────────────────────┐
  │ NVDA beat + SOUN beat?                               │
  │   → Market bullish. Buy SOFI + MGNI at open.        │
  │   → Consider adding SOUN if it gaps up but stays     │
  │     below analyst target ($16).                      │
  │                                                      │
  │ NVDA beat + SOUN miss?                               │
  │   → Buy SOFI + MGNI. Skip SOUN.                     │
  │   → Use SOUN money for more SCHG or SOFI.            │
  │                                                      │
  │ NVDA miss?                                           │
  │   → WAIT 1-2 more days for market to stabilize.      │
  │   → Buy SOFI + MGNI on the dip (Mar 2-3).           │
  │   → Prices will likely be LOWER = better entry.      │
  └──────────────────────────────────────────────────────┘
  """)

    print(f"  ── GROWTH POSITIONS TO BUY (use remaining ~${remaining:,.0f}) ──\n")

    growth_buys = []

    # SOFI — core growth pick (26 shares total across buckets in Plan B)
    p = prices.get("SOFI", 19.00)
    shares = int(remaining * 0.55 / p)
    cost = shares * p
    growth_buys.append({
        "ticker": "SOFI", "shares": shares, "price": p, "total": cost,
        "reason": "Best risk/reward. Target $26.50 (+35%). Digital bank compounder.",
        "timing": "Buy Feb 27 if NVDA beat, or Mar 2-3 if NVDA missed (buy the dip).",
    })
    remaining -= cost

    # MGNI — CTV ad-tech
    p = prices.get("MGNI", 12.00)
    shares = int(remaining / p)
    cost = shares * p
    growth_buys.append({
        "ticker": "MGNI", "shares": shares, "price": p, "total": cost,
        "reason": "CTV ad-tech. Buy consensus. Streaming ad spend boom.",
        "timing": "Buy Feb 27 same session as SOFI.",
    })
    remaining -= cost

    for b in growth_buys:
        print(f"  BUY {b['shares']:>3d} {b['ticker']:6s} @ ~${b['price']:>7.2f} = ${b['total']:>7,.0f}")
        print(f"       {b['reason']}")
        print(f"       Timing: {b['timing']}")
        print(f"       Order: LIMIT @ ${b['price']:.2f} (adjust to actual price that day)")
        print()

    total_phase3 = sum(b["total"] for b in growth_buys)
    print(f"  {'─'*60}")
    print(f"  Phase 3 total deployed: ~${total_phase3:,.0f}")
    print(f"  Final cash remaining:   ~${remaining:,.0f}")

    return remaining, growth_buys


def phase4_plan_a_aggressive_addon(prices):
    print(f"\n\n{'#'*80}")
    print(f"  PHASE 3-ALT: IF YOU CHOOSE PLAN A (AGGRESSIVE)")
    print(f"  Replace growth buys above with these")
    print(f"{'#'*80}")

    print(f"""
  Instead of SOFI + MGNI, buy these momentum names AFTER earnings:

  ── CRYPTO/AI PLAYS (only if Bitcoin recovering + NVDA beat) ──

  SOUN  — Buy Feb 27 ONLY if earnings beat (revenue > $54M)
           Skip if miss. Target $16 from ~$7.50.
           Order: LIMIT at post-earnings price.

  MARA  — Buy Feb 27-28. Bitcoin leverage play.
           Only if BTC holding above $80K. Target $19.60.
           Order: LIMIT at market price.

  RIOT  — Buy Feb 27-28. AI/HPC pivot + crypto.
           Least risky of the three. Target $26.
           Order: LIMIT at market price.

  WARNING: These are HIGH RISK. Only do this if you're comfortable
  potentially losing 30-50% on these positions. They can also 2-3x.
  """)


def print_weekly_calendar(prices, freed):
    print(f"\n\n{'#'*80}")
    print(f"  WEEK-BY-WEEK EXECUTION CALENDAR")
    print(f"{'#'*80}")

    print(f"""
  ┌─────────────┬──────────────────────────────────────────────────────────────┐
  │    DATE     │  ACTION                                                      │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │             │  WEEK 1: SELL + SAFE BUYS                                    │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Feb 20 Thu  │  10AM: SELL ALL FIG, DOCS, TMF, BLSH (4 sell orders)        │
  │             │  → Free ~${freed:,.0f}. Cash settles Feb 21.                     │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Feb 21 Fri  │  10AM: BUY income ETFs: SPHD(6), SVOL(12), JEPI(6)         │
  │             │  10:30: BUY long-term: SCHG(14), ORN(17)                    │
  │             │  → Capture SPHD div (ex 2/24), SVOL div (ex 2/25)           │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Feb 22-23   │  WEEKEND — no action. Positions settling.                    │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │             │  WEEK 2: EARNINGS WEEK — WAIT & WATCH                        │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Feb 24 Mon  │  SPHD ex-dividend date (you're eligible, bought Fri)        │
  │             │  No trades. Watch market.                                     │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Feb 25 Wed  │  SVOL ex-dividend date (eligible)                            │
  │             │  *** NVDA EARNINGS AFTER CLOSE ***                           │
  │             │  No trades. Wait for NVDA report.                            │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Feb 26 Thu  │  Market reacts to NVDA. Could be +/-3% on indexes.          │
  │             │  *** SOUN EARNINGS AFTER CLOSE ***                           │
  │             │  No trades. Watch. Prepare buy orders for tomorrow.          │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Feb 27 Fri  │  10AM: BUY growth positions: SOFI + MGNI                    │
  │             │  (Or SOUN/MARA/RIOT if Plan A and earnings were good)        │
  │             │  Use LIMIT orders. Adjust prices to post-earnings levels.    │
  │             │  → Must settle before JEPQ/JEPI ex-div Mar 2                │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Feb 28-Mar1 │  WEEKEND — positions settling.                               │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │             │  WEEK 3: DIVIDEND COLLECTION                                 │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Mar 2  Mon  │  JEPQ + JEPI ex-dividend date.                              │
  │             │  You collect: ~$12 JEPQ (25 shares x $0.48)                 │
  │             │              ~$2 JEPI (6 shares x $0.33)                    │
  │             │  If NVDA missed and you waited: buy growth today.            │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Mar 4  Wed  │  JEPI dividend payment received.                             │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Mar 6  Fri  │  JEPQ dividend payment received.                             │
  │             │  Review all positions. Rebalance if needed.                  │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │             │  ONGOING: MONTHLY RHYTHM                                     │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Monthly     │  Collect JEPQ + JEPI + SVOL + SPHD dividends                │
  │             │  Review growth positions (SOFI, MGNI, SCHG, ORN)            │
  │             │  Reinvest dividends into best-performing position            │
  │ Mar 22      │  WASH SALE ENDS — can re-buy FIG/TMF/DOCS/BLSH if wanted   │
  │ Mar 24      │  SPHD March ex-dividend                                      │
  │ Mar 26      │  SVOL + SCHD ex-dividend                                     │
  └─────────────┴──────────────────────────────────────────────────────────────┘""")


def print_order_cheatsheet(prices, freed):
    print(f"\n\n{'#'*80}")
    print(f"  ORDER ENTRY CHEAT SHEET — Copy & Execute")
    print(f"{'#'*80}")

    print(f"\n  ── FEB 20 (THURSDAY) — SELLS ──")
    print(f"  All orders: LIMIT, GTC (Good-Til-Cancelled)")
    print(f"  Execute at 10:00 AM ET\n")

    sells = [
        ("FIG",  11, prices.get("FIG",  25.71)),
        ("DOCS",  6, prices.get("DOCS", 25.08)),
        ("TMF",  36, prices.get("TMF",  40.26)),
        ("BLSH", 11, prices.get("BLSH", 31.67)),
    ]

    for ticker, shares, price in sells:
        # Set limit slightly below bid for quick fill
        limit = round(price * 0.998, 2)
        total = shares * limit
        print(f"  SELL  {shares:>3d}  {ticker:6s}  LIMIT  ${limit:>7.2f}  (~${total:>7,.0f})")

    print(f"\n  ── FEB 21 (FRIDAY) — BUYS ROUND 1 ──")
    print(f"  All orders: LIMIT, DAY")
    print(f"  Execute at 10:00 AM ET\n")

    buys_r1 = [
        ("SPHD",  6, prices.get("SPHD", 52.00), "Capture Feb 24 ex-div"),
        ("SVOL", 12, prices.get("SVOL", 16.80), "Capture Feb 25 ex-div"),
        ("JEPI",  6, prices.get("JEPI", 59.30), "Income, ex-div Mar 2"),
        ("SCHG", 14, prices.get("SCHG", 30.60), "Core growth ETF"),
        ("ORN",  17, prices.get("ORN",  13.00), "Infrastructure growth"),
    ]

    total_r1 = 0
    for ticker, shares, price, note in buys_r1:
        limit = round(price * 1.002, 2)  # slightly above ask for quick fill
        total = shares * limit
        total_r1 += total
        print(f"  BUY   {shares:>3d}  {ticker:6s}  LIMIT  ${limit:>7.2f}  (~${total:>7,.0f})  {note}")

    print(f"\n  Round 1 total: ~${total_r1:,.0f}")

    print(f"\n  ── FEB 27 (FRIDAY) — BUYS ROUND 2 ──")
    print(f"  All orders: LIMIT, DAY")
    print(f"  Execute at 10:00 AM ET (after NVDA + SOUN earnings settle)")
    print(f"  ** ADJUST PRICES to actual market prices that morning **\n")

    remaining = freed - total_r1
    p_sofi = prices.get("SOFI", 19.00)
    sofi_shares = int(remaining * 0.55 / p_sofi)
    p_mgni = prices.get("MGNI", 12.00)
    mgni_shares = int((remaining - sofi_shares * p_sofi) / p_mgni)

    buys_r2 = [
        ("SOFI", sofi_shares, p_sofi, "Growth. Adjust to post-earnings price"),
        ("MGNI", mgni_shares, p_mgni, "CTV ad-tech. Adjust to market"),
    ]

    total_r2 = 0
    for ticker, shares, price, note in buys_r2:
        limit = round(price * 1.002, 2)
        total = shares * limit
        total_r2 += total
        print(f"  BUY   {shares:>3d}  {ticker:6s}  LIMIT  ${limit:>7.2f}  (~${total:>7,.0f})  {note}")

    print(f"\n  Round 2 total: ~${total_r2:,.0f}")
    print(f"  Grand total deployed: ~${total_r1 + total_r2:,.0f}")
    print(f"  Cash reserve: ~${freed - total_r1 - total_r2:,.0f}")


def print_monitoring_guide():
    print(f"\n\n{'#'*80}")
    print(f"  POST-EXECUTION MONITORING GUIDE")
    print(f"{'#'*80}")

    print(f"""
  CHECK WEEKLY (every Friday close):
  ┌──────────────────────────────────────────────────────────────────┐
  │  1. Total portfolio value vs cost basis → are we recovering?    │
  │  2. Each position: is it within ±10% of buy price?              │
  │  3. Dividends received this month → track cumulative income     │
  │  4. Any upcoming earnings for held positions?                    │
  └──────────────────────────────────────────────────────────────────┘

  STOP-LOSS RULES (protect capital):
  ┌────────────────────┬──────────────────────────────────────────────┐
  │ Position           │ Action if drops below                        │
  ├────────────────────┼──────────────────────────────────────────────┤
  │ SOFI               │ Set mental stop at -20% ($15.20). Review.   │
  │ MGNI               │ Set mental stop at -25% ($9.00). Review.    │
  │ ORN                │ Set mental stop at -20% ($10.40). Review.   │
  │ SCHG               │ No stop. Core holding. Buy more on dips.    │
  │ Income ETFs        │ No stop. Hold for dividends.                │
  └────────────────────┴──────────────────────────────────────────────┘

  TAKE-PROFIT TARGETS:
  ┌────────────────────┬──────────┬──────────────────────────────────┐
  │ Position           │ Target   │ Action when hit                   │
  ├────────────────────┼──────────┼──────────────────────────────────┤
  │ SOFI               │ $26.50   │ Sell half, let rest ride         │
  │ MGNI               │ $16.00   │ Sell half, let rest ride         │
  │ ORN                │ $16.00   │ Sell half, let rest ride         │
  │ SCHG               │ None     │ Hold forever. Core growth.       │
  │ Income ETFs        │ None     │ Hold forever. Collect dividends. │
  └────────────────────┴──────────┴──────────────────────────────────┘

  MONTHLY DIVIDEND CALENDAR:
  ┌─────────────────┬──────────┬────────────────────────────────────┐
  │ ETF             │ ~Amount  │ Schedule                            │
  ├─────────────────┼──────────┼────────────────────────────────────┤
  │ JEPQ (25 sh)    │ ~$12/mo  │ Ex-div ~1st of month               │
  │ JEPI (6 sh)     │ ~$2/mo   │ Ex-div ~1st of month               │
  │ SVOL (12 sh)    │ ~$3/mo   │ Ex-div ~25th of month              │
  │ SPHD (6 sh)     │ ~$1/mo   │ Ex-div ~24th of month              │
  │ TOTAL           │ ~$18/mo  │ Plus growth from SOFI/MGNI/ORN/SCHG│
  └─────────────────┴──────────┴────────────────────────────────────┘

  REINVESTMENT RULE:
  Each month when dividends accumulate to >$50, reinvest into:
  - SCHG (if market dipping) — buy the dip on growth
  - JEPQ (if market flat) — compound the income
  """)


def plot_timeline():
    fig, ax = plt.subplots(figsize=(16, 7))
    ax.set_title("Execution Timeline — February-March 2026", fontsize=14, fontweight="bold")

    # Timeline
    dates = pd.date_range("2026-02-19", "2026-03-08")
    y = 0

    events = [
        ("2026-02-19", 0, "TODAY", "#95a5a6", ""),
        ("2026-02-20", 1, "SELL ALL\nFIG, DOCS,\nTMF, BLSH", "#e74c3c", "Phase 1: Sell"),
        ("2026-02-21", 2, "BUY SPHD,\nSVOL, JEPI,\nSCHG, ORN", "#2ecc71", "Phase 2: Safe Buys"),
        ("2026-02-24", 3, "SPHD\nex-div", "#f39c12", "Dividend"),
        ("2026-02-25", 4, "SVOL ex-div\n+ NVDA\nearnings", "#f39c12", "Catalyst"),
        ("2026-02-26", 5, "SOUN\nearnings", "#f39c12", "Catalyst"),
        ("2026-02-27", 6, "BUY SOFI\n+ MGNI", "#2ecc71", "Phase 3: Growth Buys"),
        ("2026-03-02", 7, "JEPQ + JEPI\nex-div", "#f39c12", "Dividend"),
        ("2026-03-06", 8, "JEPQ div\npaid", "#3498db", "Cash In"),
    ]

    for date_str, idx, label, color, category in events:
        date = pd.Timestamp(date_str)
        day_offset = (date - pd.Timestamp("2026-02-19")).days

        ax.scatter(day_offset, 0, s=200, c=color, zorder=5, edgecolors="black", linewidth=0.5)
        y_offset = 1.5 if idx % 2 == 0 else -1.5
        ax.annotate(label, (day_offset, 0), xytext=(day_offset, y_offset),
                    fontsize=8, ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.3),
                    arrowprops=dict(arrowstyle="->", color="gray"))

    ax.axhline(0, color="black", linewidth=1)
    ax.set_xlim(-1, 18)
    ax.set_ylim(-3, 3)

    # X labels
    day_labels = [(i, (pd.Timestamp("2026-02-19") + timedelta(days=i)).strftime("%b %d\n%a"))
                  for i in range(18)]
    ax.set_xticks([d[0] for d in day_labels])
    ax.set_xticklabels([d[1] for d in day_labels], fontsize=7)
    ax.set_yticks([])

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#e74c3c', markersize=10, label='Sell'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#2ecc71', markersize=10, label='Buy'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#f39c12', markersize=10, label='Catalyst/Ex-Div'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#3498db', markersize=10, label='Cash In'),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9)

    plt.tight_layout()
    path = "execution_timeline_chart.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Chart saved to: {path}")


# ─────────────────────────────────────────────────────
def main():
    prices = fetch_live_prices()
    print_header()
    print_rules()
    freed, tax_loss = phase1_immediate_sells(prices)
    remaining = phase2_pre_earnings_buys(prices, freed)
    remaining, _ = phase3_post_earnings_buys(prices, remaining)
    phase4_plan_a_aggressive_addon(prices)
    print_weekly_calendar(prices, freed)
    print_order_cheatsheet(prices, freed)
    print_monitoring_guide()

    try:
        plot_timeline()
    except Exception as e:
        print(f"\n  Could not generate chart: {e}")

    print(f"\n{'='*80}")
    print(f"  DISCLAIMER: Educational purposes only. Not financial advice.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
