#!/usr/bin/env python3
"""
Portfolio Recovery Optimizer V2 — No New Capital
=================================================
Constraints:
  - NO additional money
  - Can sell ANY existing holding and swap into anything
  - ANY options strategy allowed (spreads, PMCC, wheel, etc.)
  - Goal: Recover $1,427 loss as fast as possible

Current portfolio (~$3,393 total value):
  TMF  36 @ $45.29  |  JEPQ 20 @ $53.70  |  BLSH 11 @ $37.00
  FIG  11 @ $133.00 |  DOCS  6 @ $41.00

Requirements: pip install yfinance pandas numpy matplotlib scipy
"""

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────
# Portfolio & Candidates
# ─────────────────────────────────────────────────────
CURRENT_HOLDINGS = [
    {"ticker": "TMF",  "shares": 36, "cost": 45.29},
    {"ticker": "JEPQ", "shares": 20, "cost": 53.70},
    {"ticker": "BLSH", "shares": 11, "cost": 37.00},
    {"ticker": "FIG",  "shares": 11, "cost": 133.00},
    {"ticker": "DOCS", "shares": 6,  "cost": 41.00},
]

# Candidates to swap into (researched: high IV, liquid options, affordable)
SWAP_CANDIDATES = [
    "SOFI",   # $19.54, IV 72-82%, wheel-friendly, strong fundamentals
    "F",      # $13.87, IV 33%, low-cost wheel, dividend
    "QYLD",   # $17.50, 11.6% yield, monthly dividends
    "RIOT",   # $15.63, IV 70-90%, crypto-correlated, aggressive
    "JEPQ",   # Already own — might add more
    "MSTR",   # $128, IV 80-100%, for bull put spreads only
    "PLTR",   # $138, IV 50-65%, for bull put spreads only
    "SVOL",   # $16.94, ~20% yield, VIX premium selling
]

pd.set_option("display.width", 220)


# ─────────────────────────────────────────────────────
# Fetch Data
# ─────────────────────────────────────────────────────
def fetch_all_data():
    """Fetch prices, IV, and options data for all tickers."""
    all_tickers = list(set(
        [h["ticker"] for h in CURRENT_HOLDINGS] + SWAP_CANDIDATES
    ))

    data = {}
    print(f"\n{'='*80}")
    print(f"  PORTFOLIO OPTIMIZER V2 — NO NEW CAPITAL")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*80}")
    print(f"\n  Fetching data for {len(all_tickers)} tickers...")

    for ticker in all_tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="3mo")
            if hist.empty:
                continue
            price = hist["Close"].iloc[-1]

            # Historical volatility
            log_ret = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
            hv = log_ret.std() * np.sqrt(252) if len(log_ret) > 10 else 0.5

            # Options availability and IV
            has_options = False
            avg_iv = hv  # fallback
            best_put = None
            best_call = None
            best_spread = None

            try:
                exps = t.options
                if exps:
                    has_options = True
                    today = datetime.now().date()

                    # Find 30-45 DTE expiration
                    target_exp = None
                    for exp_str in exps:
                        dte = (datetime.strptime(exp_str, "%Y-%m-%d").date() - today).days
                        if 20 <= dte <= 50:
                            target_exp = exp_str
                            target_dte = dte
                            break

                    if target_exp:
                        chain = t.option_chain(target_exp)

                        # Best OTM put to sell (for wheel / CSP)
                        puts = chain.puts
                        otm_puts = puts[(puts["strike"] <= price * 0.95) &
                                        (puts["bid"] > 0.03) &
                                        (puts["openInterest"] >= 5)].copy()
                        if not otm_puts.empty:
                            otm_puts["ann_yield"] = (otm_puts["bid"] / otm_puts["strike"]) * (365 / target_dte)
                            best_put_row = otm_puts.sort_values("ann_yield", ascending=False).iloc[0]
                            best_put = {
                                "exp": target_exp,
                                "dte": target_dte,
                                "strike": best_put_row["strike"],
                                "bid": best_put_row["bid"],
                                "ann_yield": best_put_row["ann_yield"],
                                "collateral": best_put_row["strike"] * 100,
                                "premium": best_put_row["bid"] * 100,
                                "iv": best_put_row.get("impliedVolatility", hv),
                            }

                        # Best OTM call to sell (for covered calls)
                        calls = chain.calls
                        otm_calls = calls[(calls["strike"] >= price * 1.03) &
                                          (calls["bid"] > 0.03) &
                                          (calls["openInterest"] >= 5)].copy()
                        if not otm_calls.empty:
                            otm_calls["ann_yield"] = (otm_calls["bid"] / price) * (365 / target_dte)
                            best_call_row = otm_calls.sort_values("ann_yield", ascending=False).iloc[0]
                            best_call = {
                                "exp": target_exp,
                                "dte": target_dte,
                                "strike": best_call_row["strike"],
                                "bid": best_call_row["bid"],
                                "ann_yield": best_call_row["ann_yield"],
                                "premium": best_call_row["bid"] * 100,
                                "iv": best_call_row.get("impliedVolatility", hv),
                            }

                        # Best bull put spread ($5 wide)
                        if not otm_puts.empty:
                            for _, sell_row in otm_puts.head(5).iterrows():
                                sell_strike = sell_row["strike"]
                                buy_strike_target = sell_strike - 5
                                buy_candidates = puts[(puts["strike"] >= buy_strike_target - 1) &
                                                      (puts["strike"] <= buy_strike_target + 1) &
                                                      (puts["strike"] < sell_strike)]
                                if not buy_candidates.empty:
                                    buy_row = buy_candidates.iloc[-1]  # closest to target
                                    width = sell_strike - buy_row["strike"]
                                    credit = sell_row["bid"] - buy_row["ask"]
                                    if credit > 0.05 and width > 0:
                                        max_risk = (width - credit) * 100
                                        best_spread = {
                                            "exp": target_exp,
                                            "dte": target_dte,
                                            "sell_strike": sell_strike,
                                            "buy_strike": buy_row["strike"],
                                            "width": width,
                                            "credit": credit * 100,
                                            "max_risk": max_risk,
                                            "roi": credit / width if width > 0 else 0,
                                            "ann_roi": (credit / width) * (365 / target_dte) if width > 0 else 0,
                                        }
                                        break

                        # Average IV from puts
                        if not otm_puts.empty:
                            avg_iv = otm_puts["impliedVolatility"].mean()

            except Exception:
                pass

            data[ticker] = {
                "price": price,
                "hv": hv,
                "avg_iv": avg_iv,
                "has_options": has_options,
                "best_put": best_put,
                "best_call": best_call,
                "best_spread": best_spread,
                "obj": t,
            }
        except Exception as e:
            print(f"  WARNING: {ticker}: {e}")

    return data


# ─────────────────────────────────────────────────────
# Step 1: Current Portfolio Analysis
# ─────────────────────────────────────────────────────
def current_portfolio_analysis(data):
    print(f"\n{'─'*80}")
    print(f"  STEP 1: CURRENT PORTFOLIO — WHAT YOU HAVE")
    print(f"{'─'*80}")

    total_invested = 0
    total_value = 0
    tax_losses = 0
    holdings_detail = []

    for h in CURRENT_HOLDINGS:
        t = h["ticker"]
        d = data.get(t)
        if not d:
            continue
        price = d["price"]
        invested = h["shares"] * h["cost"]
        value = h["shares"] * price
        pnl = value - invested
        total_invested += invested
        total_value += value
        if pnl < 0:
            tax_losses += abs(pnl)

        holdings_detail.append({
            "ticker": t, "shares": h["shares"], "cost": h["cost"],
            "price": price, "invested": invested, "value": value, "pnl": pnl,
        })

    total_pnl = total_value - total_invested

    for hd in holdings_detail:
        status = "+" if hd["pnl"] >= 0 else ""
        print(f"  {hd['ticker']:6s}  {hd['shares']:3d} shares  "
              f"Cost ${hd['cost']:>7.2f}  Now ${hd['price']:>7.2f}  "
              f"Value ${hd['value']:>7,.0f}  P&L {status}${hd['pnl']:>7,.0f}"
              f"  ({hd['pnl']/hd['invested']:+.0%})")

    print(f"\n  Total Value:    ${total_value:,.0f}")
    print(f"  Total Invested: ${total_invested:,.0f}")
    print(f"  Total P&L:      ${total_pnl:,.0f} ({total_pnl/total_invested:+.1%})")
    print(f"  Harvestable Tax Losses: ${tax_losses:,.0f}")

    return total_value, total_pnl, tax_losses, holdings_detail


# ─────────────────────────────────────────────────────
# Step 2: Evaluate What to Sell
# ─────────────────────────────────────────────────────
def evaluate_sells(data, holdings_detail):
    print(f"\n{'─'*80}")
    print(f"  STEP 2: WHAT TO SELL — SCORING EACH HOLDING")
    print(f"{'─'*80}")
    print(f"  Scoring: Higher = stronger case to SELL\n")

    sell_scores = []

    for hd in holdings_detail:
        t = hd["ticker"]
        d = data.get(t, {})
        price = hd["price"]
        cost = hd["cost"]
        pnl_pct = hd["pnl"] / hd["invested"]
        value = hd["value"]

        score = 0
        reasons = []

        # Tax loss harvestable?
        if hd["pnl"] < 0:
            tax_benefit = abs(hd["pnl"]) * 0.30
            score += min(tax_benefit / value * 100, 30)  # up to 30 points
            reasons.append(f"Tax-loss harvest: save ~${tax_benefit:.0f}")

        # How far from cost basis? (unlikely to recover)
        if pnl_pct < -0.50:
            score += 25
            reasons.append(f"Down {pnl_pct:.0%} — recovery to cost is unlikely")
        elif pnl_pct < -0.20:
            score += 10
            reasons.append(f"Down {pnl_pct:.0%}")

        # Leveraged ETF penalty (TMF compounding decay)
        if t == "TMF":
            score += 15
            reasons.append("3x leveraged ETF — compounding decay destroys long-term value")

        # Small position (< $300) — not worth the attention
        if value < 300:
            score += 10
            reasons.append(f"Tiny position (${value:.0f}) — not worth managing")

        # No options or illiquid options?
        if not d.get("has_options") or not d.get("best_put"):
            score += 5
            reasons.append("Limited/no options — can't generate income")

        # Already profitable? Penalty for selling winners
        if hd["pnl"] > 0:
            score -= 20
            reasons.append(f"PROFITABLE (+${hd['pnl']:.0f}) — penalize selling winners")

        # Income-generating (JEPQ)?
        if t == "JEPQ":
            score -= 25
            reasons.append("~10% yield income ETF — strong reason to keep")

        sell_scores.append({
            "ticker": t, "value": value, "pnl": hd["pnl"],
            "score": score, "reasons": reasons,
        })

    sell_scores.sort(key=lambda x: x["score"], reverse=True)

    for ss in sell_scores:
        indicator = ">> SELL" if ss["score"] > 15 else "   HOLD" if ss["score"] < 0 else "?  MAYBE"
        print(f"  {indicator}  {ss['ticker']:6s}  Score: {ss['score']:>5.0f}  "
              f"Value: ${ss['value']:>6,.0f}  P&L: ${ss['pnl']:>7,.0f}")
        for r in ss["reasons"]:
            print(f"           - {r}")
        print()

    return sell_scores


# ─────────────────────────────────────────────────────
# Step 3: Evaluate What to Buy / Deploy Into
# ─────────────────────────────────────────────────────
def evaluate_buys(data, available_capital):
    print(f"\n{'─'*80}")
    print(f"  STEP 3: WHAT TO BUY — RANKING CANDIDATES")
    print(f"{'─'*80}")
    print(f"  Available capital after sells: ~${available_capital:,.0f}\n")

    candidates = []

    for ticker in SWAP_CANDIDATES:
        d = data.get(ticker)
        if not d:
            continue

        price = d["price"]
        iv = d.get("avg_iv", 0)
        best_put = d.get("best_put")
        best_call = d.get("best_call")
        best_spread = d.get("best_spread")

        # Score: higher = better candidate to deploy capital into
        score = 0
        strategies = []
        monthly_income_est = 0

        # Can run the wheel? (need 100 shares affordable)
        shares_for_100 = price * 100
        if shares_for_100 <= available_capital:
            # Wheel: sell puts → get assigned → sell calls
            if best_put:
                monthly_put = best_put["premium"] * (30 / best_put["dte"])
                score += 30 + iv * 20  # high IV = more premium
                strategies.append({
                    "name": "WHEEL (CSP + CC)",
                    "detail": f"Sell {best_put['exp']} ${best_put['strike']:.0f}P @ ${best_put['bid']:.2f}"
                              f" → ${best_put['premium']:.0f}/cycle, ~${monthly_put:.0f}/mo",
                    "capital": best_put["collateral"],
                    "monthly": monthly_put,
                })
                monthly_income_est += monthly_put

        # Bull put spread? (much less capital needed)
        if best_spread:
            monthly_spread = best_spread["credit"] * (30 / best_spread["dte"])
            score += 20 + best_spread["roi"] * 30
            strategies.append({
                "name": "BULL PUT SPREAD",
                "detail": f"Sell ${best_spread['sell_strike']:.0f}P / Buy ${best_spread['buy_strike']:.0f}P"
                          f" ({best_spread['exp']}) → Credit ${best_spread['credit']:.0f}"
                          f" | Risk ${best_spread['max_risk']:.0f}"
                          f" | ROI {best_spread['roi']:.0%}",
                "capital": best_spread["max_risk"],
                "monthly": monthly_spread,
            })
            monthly_income_est += monthly_spread

        # Buy shares + sell CC?
        if price * 100 <= available_capital and best_call:
            monthly_cc = best_call["premium"] * (30 / best_call["dte"])
            strategies.append({
                "name": "BUY 100 + SELL COVERED CALL",
                "detail": f"Buy 100 @ ${price:.2f}, sell {best_call['exp']} ${best_call['strike']:.0f}C"
                          f" @ ${best_call['bid']:.2f} → ${best_call['premium']:.0f}/cycle",
                "capital": price * 100,
                "monthly": monthly_cc,
            })

        # PMCC? (buy LEAPS, sell monthly calls)
        # Estimate LEAPS cost as ~40-60% of 100 shares for deep ITM
        pmcc_cost_est = price * 100 * 0.50  # rough estimate
        if pmcc_cost_est <= available_capital and best_call and price > 10:
            monthly_pmcc = best_call["premium"] * (30 / best_call["dte"]) * 0.8  # slightly less than CC
            score += 15
            strategies.append({
                "name": "POOR MAN'S COVERED CALL (PMCC)",
                "detail": f"Buy deep ITM LEAPS ~${pmcc_cost_est:.0f}, sell monthly"
                          f" ${best_call['strike']:.0f}C @ ${best_call['bid']:.2f}"
                          f" → ~${monthly_pmcc:.0f}/mo on ~${pmcc_cost_est:.0f} capital",
                "capital": pmcc_cost_est,
                "monthly": monthly_pmcc,
            })

        # Passive income? (for income ETFs)
        div_yield = 0
        if ticker == "JEPQ":
            div_yield = 0.106
        elif ticker == "QYLD":
            div_yield = 0.116
        elif ticker == "SVOL":
            div_yield = 0.20

        if div_yield > 0:
            max_shares = int(available_capital / price)
            annual_div = max_shares * price * div_yield
            monthly_div = annual_div / 12
            score += div_yield * 100  # reward yield
            strategies.append({
                "name": "BUY & HOLD FOR DIVIDENDS",
                "detail": f"Buy {max_shares} shares @ ${price:.2f}"
                          f" → ${monthly_div:.0f}/mo dividends ({div_yield:.1%} yield)",
                "capital": max_shares * price,
                "monthly": monthly_div,
            })
            monthly_income_est += monthly_div

        if strategies:
            candidates.append({
                "ticker": ticker,
                "price": price,
                "iv": iv,
                "score": score,
                "strategies": strategies,
                "monthly_income_est": monthly_income_est,
            })

    candidates.sort(key=lambda x: x["score"], reverse=True)

    for c in candidates:
        print(f"  {c['ticker']:6s}  ${c['price']:>7.2f}  IV:{c['iv']:.0%}  "
              f"Score: {c['score']:>5.1f}  Est. income: ~${c['monthly_income_est']:.0f}/mo")
        for s in c["strategies"]:
            print(f"    [{s['name']}]")
            print(f"      {s['detail']}")
            print(f"      Capital: ${s['capital']:,.0f}  |  ~${s['monthly']:.0f}/mo")
        print()

    return candidates


# ─────────────────────────────────────────────────────
# Step 4: Generate Optimal Plan
# ─────────────────────────────────────────────────────
def generate_optimal_plan(data, sell_scores, candidates, total_value, total_pnl, tax_losses):
    print(f"\n{'#'*80}")
    print(f"  OPTIMAL REALLOCATION PLAN — NO NEW CAPITAL")
    print(f"{'#'*80}")

    # Determine what to sell
    to_sell = [s for s in sell_scores if s["score"] > 15]
    to_keep = [s for s in sell_scores if s["score"] <= 15]

    freed_capital = sum(s["value"] for s in to_sell)
    kept_value = sum(s["value"] for s in to_keep)
    total_tax_harvest = sum(abs(s["pnl"]) for s in to_sell if s["pnl"] < 0)
    tax_savings = total_tax_harvest * 0.30

    print(f"\n  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │  SELL THESE (free up capital + harvest tax losses):         │")
    print(f"  └─────────────────────────────────────────────────────────────┘")
    for s in to_sell:
        print(f"    SELL ALL {s['ticker']:6s}  →  Free ${s['value']:>6,.0f}"
              f"  (Tax loss: ${abs(s['pnl']):>6,.0f})" if s["pnl"] < 0 else
              f"    SELL ALL {s['ticker']:6s}  →  Free ${s['value']:>6,.0f}")

    print(f"\n    Total freed:       ${freed_capital:,.0f}")
    print(f"    Tax losses:        ${total_tax_harvest:,.0f}")
    print(f"    Est. tax savings:  ${tax_savings:,.0f}")

    print(f"\n  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │  KEEP THESE:                                                │")
    print(f"  └─────────────────────────────────────────────────────────────┘")
    for s in to_keep:
        print(f"    KEEP {s['ticker']:6s}  (${s['value']:>6,.0f})")

    # Allocate freed capital into best candidates
    print(f"\n  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │  DEPLOY FREED CAPITAL (${freed_capital:,.0f}):                        │")
    print(f"  └─────────────────────────────────────────────────────────────┘")

    remaining = freed_capital
    deployments = []
    total_monthly = 0

    # Add income from kept positions
    for s in to_keep:
        if s["ticker"] == "JEPQ":
            jepq_monthly = 0.48 * next(h["shares"] for h in CURRENT_HOLDINGS if h["ticker"] == "JEPQ")
            total_monthly += jepq_monthly
            deployments.append({
                "ticker": "JEPQ (EXISTING)",
                "strategy": "Hold & collect dividends",
                "capital": 0,
                "monthly": jepq_monthly,
            })

    # Strategy 1: SOFI Wheel (if affordable)
    sofi = data.get("SOFI", {})
    if sofi and sofi["price"] * 100 <= remaining and sofi.get("best_put"):
        capital = sofi["best_put"]["collateral"]
        monthly = sofi["best_put"]["premium"] * (30 / sofi["best_put"]["dte"])
        deployments.append({
            "ticker": "SOFI",
            "strategy": f"WHEEL: Sell {sofi['best_put']['exp']} ${sofi['best_put']['strike']:.0f}P"
                        f" @ ${sofi['best_put']['bid']:.2f}",
            "capital": capital,
            "monthly": monthly,
        })
        remaining -= capital
        total_monthly += monthly

    # Strategy 2: Bull put spreads on high-IV names
    for ticker in ["MSTR", "PLTR", "SOFI", "RIOT"]:
        d = data.get(ticker, {})
        spread = d.get("best_spread")
        if spread and spread["max_risk"] <= remaining and spread["max_risk"] > 0:
            monthly = spread["credit"] * (30 / spread["dte"])
            # Can run multiple contracts
            contracts = min(int(remaining * 0.25 / spread["max_risk"]), 3)
            if contracts >= 1:
                cap = spread["max_risk"] * contracts
                mo = monthly * contracts
                deployments.append({
                    "ticker": ticker,
                    "strategy": f"BULL PUT SPREAD x{contracts}: "
                                f"Sell ${spread['sell_strike']:.0f}P / Buy ${spread['buy_strike']:.0f}P"
                                f" → ${spread['credit']*contracts:.0f} credit"
                                f" | ${cap:.0f} max risk",
                    "capital": cap,
                    "monthly": mo,
                })
                remaining -= cap
                total_monthly += mo

    # Strategy 3: Income ETFs with remaining capital
    for etf, div_yield in [("QYLD", 0.116), ("SVOL", 0.20)]:
        d = data.get(etf, {})
        if d and remaining >= d["price"] * 5:  # at least 5 shares
            shares = int(remaining * 0.5 / d["price"])  # use half remaining
            if shares >= 1:
                capital = shares * d["price"]
                monthly = capital * div_yield / 12
                deployments.append({
                    "ticker": etf,
                    "strategy": f"BUY {shares} shares @ ${d['price']:.2f} — {div_yield:.1%} yield",
                    "capital": capital,
                    "monthly": monthly,
                })
                remaining -= capital
                total_monthly += monthly

    # Display deployments
    print()
    for dep in deployments:
        print(f"    {dep['ticker']:20s}  {dep['strategy']}")
        print(f"    {'':20s}  Capital: ${dep['capital']:>6,.0f}  |  ~${dep['monthly']:>5.0f}/mo")
        print()

    print(f"    Cash reserve: ${remaining:,.0f}")

    # ── Final Summary ──
    print(f"\n  {'='*70}")
    print(f"  RECOVERY SUMMARY")
    print(f"  {'='*70}")
    print(f"  Total monthly income:     ~${total_monthly:,.0f}")
    print(f"  Total annual income:      ~${total_monthly * 12:,.0f}")
    print(f"  Tax savings (one-time):   ~${tax_savings:,.0f}")
    effective_loss = abs(total_pnl) - tax_savings
    print(f"  Effective loss after tax:  ${effective_loss:,.0f}")

    if total_monthly > 0:
        months = effective_loss / total_monthly
        print(f"  Months to full recovery:  ~{months:.1f} months")
    print(f"  Cash reserve remaining:   ${remaining:,.0f}")

    return deployments, total_monthly, remaining, tax_savings


# ─────────────────────────────────────────────────────
# Step 5: Before/After Comparison
# ─────────────────────────────────────────────────────
def before_after_comparison(holdings_detail, deployments, total_monthly_before, total_monthly_after,
                            total_pnl, tax_savings):
    print(f"\n\n{'#'*80}")
    print(f"  BEFORE vs AFTER COMPARISON")
    print(f"{'#'*80}")

    print(f"""
  ┌─────────────────────────────────┬─────────────────────────────────┐
  │  BEFORE (Current Portfolio)     │  AFTER (Optimized Portfolio)    │
  ├─────────────────────────────────┼─────────────────────────────────┤
  │  5 positions, mostly losses     │  Concentrated, income-focused   │
  │  Monthly income: ~${total_monthly_before:>3.0f}         │  Monthly income: ~${total_monthly_after:>5.0f}         │
  │  Annual income:  ~${total_monthly_before*12:>5.0f}       │  Annual income:  ~${total_monthly_after*12:>5.0f}       │
  │  Tax savings:    $0             │  Tax savings:    ~${tax_savings:>5.0f}       │
  │  Recovery path:  unclear        │  Recovery: ~{abs(total_pnl)/max(total_monthly_after,1):.0f} months           │
  │  Options income: $0             │  Options + dividends active     │
  │  TMF decay risk: HIGH           │  TMF decay risk: ELIMINATED     │
  │  FIG -80% anchor: dragging      │  FIG: harvested, redeployed     │
  └─────────────────────────────────┴─────────────────────────────────┘""")

    # ── Risk comparison ──
    print(f"\n  RISK CHANGES:")
    print(f"  {'─'*55}")
    print(f"  [-] Eliminated TMF 3x leverage decay risk")
    print(f"  [-] Eliminated FIG concentration risk (-80% position)")
    print(f"  [-] Eliminated DOCS tiny illiquid position")
    print(f"  [+] Added SOFI wheel: moderate risk, high IV premium")
    print(f"  [+] Added bull put spreads: DEFINED risk, capped losses")
    print(f"  [+] Added income ETFs: steady monthly distributions")
    print(f"  [=] Kept JEPQ: stable income anchor")


# ─────────────────────────────────────────────────────
# Visualization
# ─────────────────────────────────────────────────────
def plot_comparison(holdings_detail, deployments, total_pnl, total_monthly_after, tax_savings):
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle("Portfolio Optimization — Before vs After", fontsize=14, fontweight="bold")

    # ── 1. Before: P&L bars ──
    ax1 = axes[0][0]
    tickers = [h["ticker"] for h in holdings_detail]
    pnls = [h["pnl"] for h in holdings_detail]
    colors = ["#2ecc71" if x >= 0 else "#e74c3c" for x in pnls]
    ax1.barh(tickers, pnls, color=colors, edgecolor="black", linewidth=0.5)
    for i, (t, v) in enumerate(zip(tickers, pnls)):
        ax1.text(v + (10 if v >= 0 else -10), i, f"${v:,.0f}",
                 ha="left" if v >= 0 else "right", va="center", fontsize=9)
    ax1.axvline(0, color="black", linewidth=0.8)
    ax1.set_title("BEFORE: P&L by Position")
    ax1.set_xlabel("Unrealized P&L ($)")
    ax1.grid(axis="x", alpha=0.3)

    # ── 2. After: Capital allocation ──
    ax2 = axes[0][1]
    dep_labels = [d["ticker"] for d in deployments if d["capital"] > 0]
    dep_values = [d["capital"] for d in deployments if d["capital"] > 0]
    dep_labels.append("Cash Reserve")
    cash_reserve = sum(h["value"] for h in holdings_detail) - sum(dep_values)
    dep_values.append(max(cash_reserve, 0))
    colors2 = plt.cm.Set3(np.linspace(0, 1, len(dep_labels)))
    wedges, texts, autotexts = ax2.pie(dep_values, labels=dep_labels, autopct="%1.0f%%",
                                        colors=colors2, startangle=90)
    for t in texts + autotexts:
        t.set_fontsize(8)
    ax2.set_title("AFTER: Capital Allocation")

    # ── 3. Monthly income comparison ──
    ax3 = axes[1][0]
    income_labels = [d["ticker"] for d in deployments]
    income_values = [d["monthly"] for d in deployments]
    colors3 = plt.cm.Paired(np.linspace(0, 1, len(income_labels)))
    ax3.bar(income_labels, income_values, color=colors3, edgecolor="black", linewidth=0.5)
    for i, v in enumerate(income_values):
        ax3.text(i, v + 1, f"${v:.0f}", ha="center", fontsize=9)
    ax3.set_ylabel("Monthly Income ($)")
    ax3.set_title("AFTER: Estimated Monthly Income by Strategy")
    ax3.grid(axis="y", alpha=0.3)
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=20, ha="right", fontsize=8)

    # ── 4. Recovery timeline ──
    ax4 = axes[1][1]
    effective_loss = abs(total_pnl) - tax_savings
    months = range(0, 19)
    remaining_loss = [effective_loss - m * total_monthly_after for m in months]

    ax4.plot(months, remaining_loss, "b-", linewidth=2, label="Remaining Loss")
    ax4.axhline(0, color="green", linewidth=1.5, linestyle="--", label="Break Even")
    ax4.fill_between(months, remaining_loss, 0,
                     where=[r > 0 for r in remaining_loss], alpha=0.1, color="red")
    ax4.fill_between(months, remaining_loss, 0,
                     where=[r <= 0 for r in remaining_loss], alpha=0.1, color="green")

    # Mark tax savings as immediate offset
    ax4.annotate(f"Tax savings\n-${tax_savings:.0f}", xy=(0, effective_loss),
                 xytext=(2, effective_loss + 100),
                 arrowprops=dict(arrowstyle="->"), fontsize=8)

    ax4.set_xlabel("Months")
    ax4.set_ylabel("Remaining Loss ($)")
    ax4.set_title(f"Recovery Timeline (~${total_monthly_after:.0f}/mo income)")
    ax4.legend(fontsize=8)
    ax4.grid(alpha=0.3)

    plt.tight_layout()
    path = "portfolio_optimizer_v2_chart.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Chart saved to: {path}")


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────
def main():
    data = fetch_all_data()

    # Step 1: Current analysis
    total_value, total_pnl, tax_losses, holdings_detail = current_portfolio_analysis(data)

    # Step 2: Score sells
    sell_scores = evaluate_sells(data, holdings_detail)

    # Step 3: Score buys
    freed = sum(s["value"] for s in sell_scores if s["score"] > 15)
    candidates = evaluate_buys(data, freed)

    # Step 4: Optimal plan
    deployments, total_monthly, remaining, tax_savings = generate_optimal_plan(
        data, sell_scores, candidates, total_value, total_pnl, tax_losses
    )

    # Step 5: Before/After
    # Current monthly income = JEPQ dividends only
    jepq_monthly = 0.48 * 20  # ~$9.60
    before_after_comparison(holdings_detail, deployments, jepq_monthly,
                            total_monthly, total_pnl, tax_savings)

    # Charts
    try:
        plot_comparison(holdings_detail, deployments, total_pnl, total_monthly, tax_savings)
    except Exception as e:
        print(f"\n  Could not generate chart: {e}")

    # Wash sale reminder
    print(f"\n\n  {'!'*60}")
    print(f"  WASH SALE REMINDER")
    print(f"  {'!'*60}")
    print(f"  If you sell FIG, BLSH, TMF, or DOCS at a loss:")
    print(f"  - Do NOT buy them back within 30 days")
    print(f"  - Do NOT buy substantially identical securities")
    print(f"  - Mark your calendar: 30 days from sell date")
    print(f"  - After 30 days, you can re-enter if desired")

    print(f"\n{'='*80}")
    print(f"  DISCLAIMER: Educational purposes only. Not financial advice.")
    print(f"  Options involve significant risk. Do your own due diligence.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
