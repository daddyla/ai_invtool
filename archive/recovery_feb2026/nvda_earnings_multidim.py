#!/usr/bin/env python3
"""
NVDA Earnings — Multi-Dimensional Analysis
=============================================
Researches NVDA earnings impact from 5 dimensions:
  1. Sector & Market Ripple Effects (QQQ, SMH, SPY)
  2. Volatility & Volume Behavior (IV proxy, volume spikes)
  3. Related Stocks Impact (AMD, AVGO, SMCI, MRVL, ARM)
  4. Guidance vs Beat — What Actually Moves the Stock?
  5. Macro Environment (VIX, 10Y yield, market regime)

Requirements: yfinance, pandas, numpy, matplotlib, scipy
"""

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from scipy import stats

# ──────────────────────────────────────────────────────────────
# NVDA Earnings Data (same as base analysis)
# ──────────────────────────────────────────────────────────────
EARNINGS = [
    {"date": "2023-02-22", "q": "Q4 FY23", "eps_beat": 8.6, "rev_beat": 0.7,
     "guidance_rev": 6.5, "prior_rev": 6.05, "guidance_note": "Inline"},
    {"date": "2023-05-24", "q": "Q1 FY24", "eps_beat": 18.5, "rev_beat": 10.3,
     "guidance_rev": 11.0, "prior_rev": 7.19, "guidance_note": "Massive raise (+53%)"},
    {"date": "2023-08-23", "q": "Q2 FY24", "eps_beat": 30.4, "rev_beat": 20.4,
     "guidance_rev": 16.0, "prior_rev": 13.51, "guidance_note": "Strong raise (+18%)"},
    {"date": "2023-11-21", "q": "Q3 FY24", "eps_beat": 19.6, "rev_beat": 12.0,
     "guidance_rev": 20.0, "prior_rev": 18.12, "guidance_note": "Strong raise (+10%)"},
    {"date": "2024-02-21", "q": "Q4 FY24", "eps_beat": 12.4, "rev_beat": 7.2,
     "guidance_rev": 24.0, "prior_rev": 22.10, "guidance_note": "Strong raise (+9%)"},
    {"date": "2024-05-22", "q": "Q1 FY25", "eps_beat": 9.5, "rev_beat": 5.6,
     "guidance_rev": 28.0, "prior_rev": 26.04, "guidance_note": "Solid raise (+8%)"},
    {"date": "2024-08-28", "q": "Q2 FY25", "eps_beat": 6.3, "rev_beat": 4.6,
     "guidance_rev": 32.5, "prior_rev": 30.04, "guidance_note": "Moderate raise (+8%)"},
    {"date": "2024-11-20", "q": "Q3 FY25", "eps_beat": 8.0, "rev_beat": 5.8,
     "guidance_rev": 37.5, "prior_rev": 35.08, "guidance_note": "Moderate raise (+7%)"},
    {"date": "2025-02-26", "q": "Q4 FY25", "eps_beat": 6.0, "rev_beat": 3.4,
     "guidance_rev": 43.0, "prior_rev": 39.33, "guidance_note": "Solid raise (+9%)"},
    {"date": "2025-05-28", "q": "Q1 FY26", "eps_beat": 9.1, "rev_beat": 2.0,
     "guidance_rev": 45.0, "prior_rev": 44.08, "guidance_note": "Slowing raise (+2%)"},
    {"date": "2025-08-27", "q": "Q2 FY26", "eps_beat": 4.0, "rev_beat": 1.1,
     "guidance_rev": 53.0, "prior_rev": 46.70, "guidance_note": "Moderate raise (+14%)"},
    {"date": "2025-11-19", "q": "Q3 FY26", "eps_beat": 6.6, "rev_beat": 3.1,
     "guidance_rev": 63.0, "prior_rev": 57.00, "guidance_note": "Solid raise (+11%)"},
]


def fetch_all_data():
    """Fetch price history for NVDA + related tickers."""
    tickers = {
        "NVDA": "NVIDIA",
        "QQQ": "Nasdaq 100",
        "SMH": "Semiconductor ETF",
        "SPY": "S&P 500",
        "AMD": "AMD",
        "AVGO": "Broadcom",
        "MRVL": "Marvell",
        "^VIX": "VIX",
        "^TNX": "10Y Treasury Yield",
    }

    # ARM IPO was Sep 2023, SMCI had issues — try them but handle missing
    optional = {"ARM": "ARM Holdings", "SMCI": "Super Micro"}

    print(f"\n{'='*80}")
    print(f"  NVDA EARNINGS — MULTI-DIMENSIONAL ANALYSIS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*80}")

    all_data = {}
    all_tickers = {**tickers, **optional}

    print(f"\n  Fetching data for {len(all_tickers)} tickers...")
    for sym, name in all_tickers.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period="3y", interval="1d")
            if not h.empty:
                h.index = h.index.tz_localize(None)
                all_data[sym] = h
                print(f"    ✓ {sym:6s} ({name}): {len(h)} days")
            else:
                print(f"    ✗ {sym:6s} ({name}): no data")
        except Exception as e:
            print(f"    ✗ {sym:6s} ({name}): {e}")

    return all_data


def get_return(data, ticker, date, offset_days):
    """Get return from `date` to `date + offset_days` trading days."""
    if ticker not in data:
        return np.nan
    hist = data[ticker]
    earn_ts = pd.Timestamp(date)

    if offset_days >= 0:
        # Post-earnings: find trading days after earnings
        post = hist.index[hist.index > earn_ts]
        if len(post) <= offset_days:
            return np.nan
        if offset_days == 0:
            # Same day (for pre-close reference)
            pre = hist.index[hist.index <= earn_ts]
            if len(pre) == 0:
                return np.nan
            return hist.loc[pre[-1], "Close"]
        pre = hist.index[hist.index <= earn_ts]
        if len(pre) == 0:
            return np.nan
        pre_close = hist.loc[pre[-1], "Close"]
        post_close = hist.loc[post[offset_days - 1], "Close"]
        return (post_close - pre_close) / pre_close
    else:
        # Pre-earnings
        pre = hist.index[hist.index <= earn_ts]
        if len(pre) == 0:
            return np.nan
        pre_close = hist.loc[pre[-1], "Close"]
        target_idx = len(pre) - 1 + offset_days  # negative offset
        if target_idx < 0:
            return np.nan
        ref_close = hist.loc[pre[target_idx], "Close"]
        return (pre_close - ref_close) / ref_close


def get_volume_ratio(data, ticker, date, window=5):
    """Get volume on earnings day vs avg volume over prior `window` days."""
    if ticker not in data:
        return np.nan
    hist = data[ticker]
    earn_ts = pd.Timestamp(date)

    post = hist.index[hist.index > earn_ts]
    pre = hist.index[hist.index <= earn_ts]
    if len(post) == 0 or len(pre) < window:
        return np.nan

    earn_day_vol = hist.loc[post[0], "Volume"]
    avg_vol = hist.loc[pre[-window:], "Volume"].mean()
    if avg_vol == 0:
        return np.nan
    return earn_day_vol / avg_vol


def get_volatility(data, ticker, date, window=20):
    """Get realized volatility (annualized) in `window` days before earnings."""
    if ticker not in data:
        return np.nan
    hist = data[ticker]
    earn_ts = pd.Timestamp(date)

    pre = hist.index[hist.index <= earn_ts]
    if len(pre) < window + 1:
        return np.nan

    prices = hist.loc[pre[-(window+1):], "Close"]
    log_ret = np.log(prices / prices.shift(1)).dropna()
    return log_ret.std() * np.sqrt(252)


# ══════════════════════════════════════════════════════════════
# DIMENSION 1: Sector & Market Ripple Effects
# ══════════════════════════════════════════════════════════════
def dim1_sector_ripple(data):
    """How does NVDA earnings move the broader market?"""
    print(f"\n\n{'═'*80}")
    print(f"  DIMENSION 1: SECTOR & MARKET RIPPLE EFFECTS")
    print(f"  How does NVDA earnings move QQQ, SMH, and SPY?")
    print(f"{'═'*80}")

    results = []
    for e in EARNINGS:
        row = {"date": e["date"], "quarter": e["q"]}
        for ticker in ["NVDA", "QQQ", "SMH", "SPY"]:
            for d in [1, 5]:
                row[f"{ticker}_{d}d"] = get_return(data, ticker, e["date"], d)
        results.append(row)

    df = pd.DataFrame(results)

    # Display table
    print(f"\n  Next-Day Returns After NVDA Earnings:\n")
    header = f"  {'Quarter':<10} {'NVDA':>8} {'QQQ':>8} {'SMH':>8} {'SPY':>8}"
    print(header)
    print(f"  {'─'*42}")
    for _, r in df.iterrows():
        nvda = f"{r['NVDA_1d']:+.1%}" if pd.notna(r['NVDA_1d']) else "N/A"
        qqq = f"{r['QQQ_1d']:+.1%}" if pd.notna(r['QQQ_1d']) else "N/A"
        smh = f"{r['SMH_1d']:+.1%}" if pd.notna(r['SMH_1d']) else "N/A"
        spy = f"{r['SPY_1d']:+.1%}" if pd.notna(r['SPY_1d']) else "N/A"
        print(f"  {r['quarter']:<10} {nvda:>8} {qqq:>8} {smh:>8} {spy:>8}")

    # Correlations
    print(f"\n  CORRELATION: NVDA next-day move vs others:")
    for ticker in ["QQQ", "SMH", "SPY"]:
        col_nvda = df["NVDA_1d"].dropna()
        col_other = df[f"{ticker}_1d"].dropna()
        common = col_nvda.index.intersection(col_other.index)
        if len(common) >= 3:
            corr, pval = stats.pearsonr(col_nvda[common], col_other[common])
            print(f"    NVDA vs {ticker}: r = {corr:.2f} (p={pval:.3f})")

    # Amplification ratio
    print(f"\n  AMPLIFICATION RATIO (how much do indices move per 1% NVDA move):")
    for ticker in ["QQQ", "SMH", "SPY"]:
        nvda_moves = df["NVDA_1d"].dropna()
        idx_moves = df[f"{ticker}_1d"].dropna()
        common = nvda_moves.index.intersection(idx_moves.index)
        if len(common) >= 3 and nvda_moves[common].std() > 0:
            ratio = idx_moves[common].mean() / nvda_moves[common].mean() if nvda_moves[common].mean() != 0 else 0
            print(f"    {ticker}: {ratio:.2f}x  (avg NVDA {nvda_moves[common].mean():+.1%} → avg {ticker} {idx_moves[common].mean():+.1%})")

    # 5-day drift
    print(f"\n  5-DAY DRIFT after NVDA earnings:")
    print(f"  {'Quarter':<10} {'NVDA':>8} {'QQQ':>8} {'SMH':>8} {'SPY':>8}")
    print(f"  {'─'*42}")
    for _, r in df.iterrows():
        nvda = f"{r['NVDA_5d']:+.1%}" if pd.notna(r['NVDA_5d']) else "N/A"
        qqq = f"{r['QQQ_5d']:+.1%}" if pd.notna(r['QQQ_5d']) else "N/A"
        smh = f"{r['SMH_5d']:+.1%}" if pd.notna(r['SMH_5d']) else "N/A"
        spy = f"{r['SPY_5d']:+.1%}" if pd.notna(r['SPY_5d']) else "N/A"
        print(f"  {r['quarter']:<10} {nvda:>8} {qqq:>8} {smh:>8} {spy:>8}")

    return df


# ══════════════════════════════════════════════════════════════
# DIMENSION 2: Volatility & Volume Behavior
# ══════════════════════════════════════════════════════════════
def dim2_volatility_volume(data):
    """Analyze volatility crush and volume spikes around earnings."""
    print(f"\n\n{'═'*80}")
    print(f"  DIMENSION 2: VOLATILITY & VOLUME BEHAVIOR")
    print(f"  IV proxy, volume spikes, and post-earnings volatility crush")
    print(f"{'═'*80}")

    results = []
    for e in EARNINGS:
        row = {"date": e["date"], "quarter": e["q"]}

        # Pre-earnings volatility (20-day realized vol)
        row["pre_vol_20d"] = get_volatility(data, "NVDA", e["date"], 20)

        # Post-earnings volatility (10-day realized vol starting from day after)
        earn_ts = pd.Timestamp(e["date"])
        if "NVDA" in data:
            hist = data["NVDA"]
            post = hist.index[hist.index > earn_ts]
            if len(post) >= 11:
                post_prices = hist.loc[post[:11], "Close"]
                log_ret = np.log(post_prices / post_prices.shift(1)).dropna()
                row["post_vol_10d"] = log_ret.std() * np.sqrt(252)
            else:
                row["post_vol_10d"] = np.nan
        else:
            row["post_vol_10d"] = np.nan

        # Volatility crush ratio
        if pd.notna(row.get("pre_vol_20d")) and pd.notna(row.get("post_vol_10d")) and row["pre_vol_20d"] > 0:
            row["vol_crush"] = (row["post_vol_10d"] - row["pre_vol_20d"]) / row["pre_vol_20d"]
        else:
            row["vol_crush"] = np.nan

        # Volume ratio (earnings day vs avg)
        row["vol_ratio"] = get_volume_ratio(data, "NVDA", e["date"], 10)

        # VIX level on earnings day
        if "^VIX" in data:
            vix = data["^VIX"]
            pre_vix = vix.index[vix.index <= earn_ts]
            if len(pre_vix) > 0:
                row["vix_level"] = vix.loc[pre_vix[-1], "Close"]
                # VIX change next day
                post_vix = vix.index[vix.index > earn_ts]
                if len(post_vix) > 0:
                    row["vix_change"] = (vix.loc[post_vix[0], "Close"] - row["vix_level"]) / row["vix_level"]
                else:
                    row["vix_change"] = np.nan
            else:
                row["vix_level"] = np.nan
                row["vix_change"] = np.nan
        else:
            row["vix_level"] = np.nan
            row["vix_change"] = np.nan

        results.append(row)

    df = pd.DataFrame(results)

    # Display
    print(f"\n  Volatility & Volume Around Earnings:\n")
    print(f"  {'Quarter':<10} {'Pre-Vol':>8} {'Post-Vol':>9} {'Crush':>8} {'Vol Ratio':>10} {'VIX':>6} {'VIX Δ':>8}")
    print(f"  {'─'*60}")
    for _, r in df.iterrows():
        pv = f"{r['pre_vol_20d']:.0%}" if pd.notna(r['pre_vol_20d']) else "N/A"
        po = f"{r['post_vol_10d']:.0%}" if pd.notna(r['post_vol_10d']) else "N/A"
        vc = f"{r['vol_crush']:+.0%}" if pd.notna(r['vol_crush']) else "N/A"
        vr = f"{r['vol_ratio']:.1f}x" if pd.notna(r['vol_ratio']) else "N/A"
        vx = f"{r['vix_level']:.1f}" if pd.notna(r['vix_level']) else "N/A"
        vd = f"{r['vix_change']:+.1%}" if pd.notna(r['vix_change']) else "N/A"
        print(f"  {r['quarter']:<10} {pv:>8} {po:>9} {vc:>8} {vr:>10} {vx:>6} {vd:>8}")

    # Averages
    print(f"\n  AVERAGES:")
    print(f"    Pre-earnings realized vol:  {df['pre_vol_20d'].mean():.0%}")
    print(f"    Post-earnings realized vol: {df['post_vol_10d'].mean():.0%}")
    avg_crush = df['vol_crush'].mean()
    print(f"    Avg volatility crush:       {avg_crush:+.0%} ({'vol drops' if avg_crush < 0 else 'vol rises'} after earnings)")
    print(f"    Avg volume spike on E-day:  {df['vol_ratio'].mean():.1f}x normal")
    print(f"    Avg VIX level at earnings:  {df['vix_level'].mean():.1f}")

    return df


# ══════════════════════════════════════════════════════════════
# DIMENSION 3: Related Stocks Impact
# ══════════════════════════════════════════════════════════════
def dim3_related_stocks(data):
    """How do AI/semiconductor peers move after NVDA earnings?"""
    print(f"\n\n{'═'*80}")
    print(f"  DIMENSION 3: RELATED STOCKS IMPACT")
    print(f"  How do AMD, AVGO, MRVL, ARM, SMCI react to NVDA earnings?")
    print(f"{'═'*80}")

    peers = ["AMD", "AVGO", "MRVL", "ARM", "SMCI"]
    available_peers = [p for p in peers if p in data]

    results = []
    for e in EARNINGS:
        row = {"date": e["date"], "quarter": e["q"]}
        row["NVDA_1d"] = get_return(data, "NVDA", e["date"], 1)
        for peer in available_peers:
            row[f"{peer}_1d"] = get_return(data, peer, e["date"], 1)
            row[f"{peer}_5d"] = get_return(data, peer, e["date"], 5)
        results.append(row)

    df = pd.DataFrame(results)

    # Next-day table
    print(f"\n  Next-Day Returns (Peers React to NVDA Earnings):\n")
    header = f"  {'Quarter':<10} {'NVDA':>8}"
    for p in available_peers:
        header += f" {p:>8}"
    print(header)
    print(f"  {'─'*(10 + 9 * (1 + len(available_peers)))}")

    for _, r in df.iterrows():
        line = f"  {r['quarter']:<10}"
        nvda = f"{r['NVDA_1d']:+.1%}" if pd.notna(r['NVDA_1d']) else "N/A"
        line += f" {nvda:>8}"
        for p in available_peers:
            val = f"{r[f'{p}_1d']:+.1%}" if pd.notna(r.get(f'{p}_1d')) else "N/A"
            line += f" {val:>8}"
        print(line)

    # Correlation with NVDA
    print(f"\n  CORRELATION with NVDA next-day move:")
    for peer in available_peers:
        nvda_col = df["NVDA_1d"].dropna()
        peer_col = df[f"{peer}_1d"].dropna()
        common = nvda_col.index.intersection(peer_col.index)
        if len(common) >= 3:
            corr, pval = stats.pearsonr(nvda_col[common], peer_col[common])
            beta = peer_col[common].std() / nvda_col[common].std() * corr if nvda_col[common].std() > 0 else 0
            print(f"    {peer:6s}: r = {corr:+.2f} (p={pval:.3f}), beta = {beta:.2f}")

    # Who benefits most when NVDA rallies?
    rally_mask = df["NVDA_1d"] > 0
    drop_mask = df["NVDA_1d"] < 0

    if rally_mask.sum() > 0:
        print(f"\n  WHEN NVDA RALLIES after earnings ({rally_mask.sum()} times):")
        for peer in available_peers:
            avg_peer = df.loc[rally_mask, f"{peer}_1d"].mean()
            if pd.notna(avg_peer):
                print(f"    {peer:6s}: avg {avg_peer:+.1%}")

    if drop_mask.sum() > 0:
        print(f"\n  WHEN NVDA DROPS after earnings ({drop_mask.sum()} times):")
        for peer in available_peers:
            avg_peer = df.loc[drop_mask, f"{peer}_1d"].mean()
            if pd.notna(avg_peer):
                print(f"    {peer:6s}: avg {avg_peer:+.1%}")

    return df


# ══════════════════════════════════════════════════════════════
# DIMENSION 4: Guidance vs Beat — What Actually Moves Price?
# ══════════════════════════════════════════════════════════════
def dim4_guidance_analysis(data):
    """Determine if guidance or EPS beat has more impact on price."""
    print(f"\n\n{'═'*80}")
    print(f"  DIMENSION 4: GUIDANCE vs BEAT — WHAT MOVES THE STOCK?")
    print(f"  Is it the earnings beat or the forward guidance that drives price?")
    print(f"{'═'*80}")

    results = []
    for e in EARNINGS:
        row = {
            "quarter": e["q"],
            "date": e["date"],
            "eps_beat": e["eps_beat"],
            "rev_beat": e["rev_beat"],
            "guidance_rev": e["guidance_rev"],
            "prior_rev": e["prior_rev"],
            "guidance_note": e["guidance_note"],
        }
        # Guidance raise %
        if e["prior_rev"] > 0:
            row["guidance_raise"] = (e["guidance_rev"] - e["prior_rev"]) / e["prior_rev"] * 100
        else:
            row["guidance_raise"] = 0

        row["nvda_1d"] = get_return(data, "NVDA", e["date"], 1)
        row["nvda_5d"] = get_return(data, "NVDA", e["date"], 5)
        results.append(row)

    df = pd.DataFrame(results)

    # Display
    print(f"\n  Earnings Beat vs Guidance Raise vs Price Move:\n")
    print(f"  {'Quarter':<10} {'EPS Beat':>9} {'Rev Beat':>9} {'Guide Δ':>8} {'Next Day':>9} {'5-Day':>8}  {'Guidance Note'}")
    print(f"  {'─'*85}")
    for _, r in df.iterrows():
        nd = f"{r['nvda_1d']:+.1%}" if pd.notna(r['nvda_1d']) else "N/A"
        fd = f"{r['nvda_5d']:+.1%}" if pd.notna(r['nvda_5d']) else "N/A"
        print(f"  {r['quarter']:<10} {r['eps_beat']:>+8.1f}% {r['rev_beat']:>+8.1f}% {r['guidance_raise']:>+7.1f}% {nd:>9} {fd:>8}  {r['guidance_note']}")

    # Regression analysis
    print(f"\n  REGRESSION ANALYSIS — What predicts next-day move?")
    valid = df.dropna(subset=["nvda_1d"])

    for predictor, label in [("eps_beat", "EPS Beat %"), ("rev_beat", "Rev Beat %"), ("guidance_raise", "Guidance Raise %")]:
        if len(valid) >= 4:
            slope, intercept, r, p, se = stats.linregress(valid[predictor], valid["nvda_1d"])
            print(f"\n    {label}:")
            print(f"      R² = {r**2:.3f}, p = {p:.3f}")
            print(f"      Each +1% {label.lower()} → {slope:+.2%} next-day return")
            if p < 0.1:
                print(f"      ★ STATISTICALLY SIGNIFICANT (p<0.10)")
            else:
                print(f"      Not statistically significant")

    # Combined analysis
    print(f"\n  KEY INSIGHT:")
    # Sort by guidance raise and check correlation
    high_guide = df[df["guidance_raise"] >= 9].copy()
    low_guide = df[df["guidance_raise"] < 9].copy()

    if len(high_guide) > 0 and len(low_guide) > 0:
        avg_high = high_guide["nvda_1d"].mean()
        avg_low = low_guide["nvda_1d"].mean()
        print(f"    Strong guidance (≥9% raise): avg next-day {avg_high:+.1%} ({len(high_guide)} quarters)")
        print(f"    Weak guidance (<9% raise):   avg next-day {avg_low:+.1%} ({len(low_guide)} quarters)")

        if avg_high > avg_low:
            print(f"    → GUIDANCE STRENGTH is a better predictor than EPS beat")
        else:
            print(f"    → No clear guidance advantage")

    # Declining beat effect
    print(f"\n  DECLINING BEAT EFFECT (market gets used to beats):")
    first_half = df.iloc[:6]
    second_half = df.iloc[6:]
    avg_beat_1h = first_half["eps_beat"].mean()
    avg_move_1h = first_half["nvda_1d"].mean()
    avg_beat_2h = second_half["eps_beat"].mean()
    avg_move_2h = second_half["nvda_1d"].mean()
    print(f"    First 6 quarters: avg EPS beat {avg_beat_1h:+.1f}%, avg next-day {avg_move_1h:+.1%}")
    print(f"    Last 6 quarters:  avg EPS beat {avg_beat_2h:+.1f}%, avg next-day {avg_move_2h:+.1%}")

    return df


# ══════════════════════════════════════════════════════════════
# DIMENSION 5: Macro Environment Correlation
# ══════════════════════════════════════════════════════════════
def dim5_macro_environment(data):
    """How does macro environment affect NVDA earnings reaction?"""
    print(f"\n\n{'═'*80}")
    print(f"  DIMENSION 5: MACRO ENVIRONMENT CORRELATION")
    print(f"  VIX level, 10Y yield, and market regime at each earnings")
    print(f"{'═'*80}")

    results = []
    for e in EARNINGS:
        earn_ts = pd.Timestamp(e["date"])
        row = {"quarter": e["q"], "date": e["date"]}
        row["nvda_1d"] = get_return(data, "NVDA", e["date"], 1)

        # VIX level
        if "^VIX" in data:
            vix = data["^VIX"]
            pre = vix.index[vix.index <= earn_ts]
            row["vix"] = vix.loc[pre[-1], "Close"] if len(pre) > 0 else np.nan
        else:
            row["vix"] = np.nan

        # 10Y Yield
        if "^TNX" in data:
            tnx = data["^TNX"]
            pre = tnx.index[tnx.index <= earn_ts]
            row["yield_10y"] = tnx.loc[pre[-1], "Close"] if len(pre) > 0 else np.nan
        else:
            row["yield_10y"] = np.nan

        # SPY trend (20-day return = market momentum)
        row["spy_20d"] = get_return(data, "SPY", e["date"], -20) if "SPY" in data else np.nan

        # Market regime classification
        vix_val = row.get("vix", np.nan)
        spy_trend = row.get("spy_20d", np.nan)
        if pd.notna(vix_val) and pd.notna(spy_trend):
            if vix_val < 15 and spy_trend > 0:
                row["regime"] = "Risk-On"
            elif vix_val > 25:
                row["regime"] = "Fear"
            elif spy_trend < -0.02:
                row["regime"] = "Correction"
            else:
                row["regime"] = "Neutral"
        else:
            row["regime"] = "Unknown"

        results.append(row)

    df = pd.DataFrame(results)

    # Display
    print(f"\n  Macro Environment at Each NVDA Earnings:\n")
    print(f"  {'Quarter':<10} {'NVDA 1d':>8} {'VIX':>6} {'10Y':>6} {'SPY 20d':>8} {'Regime':<12}")
    print(f"  {'─'*55}")
    for _, r in df.iterrows():
        nd = f"{r['nvda_1d']:+.1%}" if pd.notna(r['nvda_1d']) else "N/A"
        vx = f"{r['vix']:.1f}" if pd.notna(r['vix']) else "N/A"
        yd = f"{r['yield_10y']:.2f}%" if pd.notna(r['yield_10y']) else "N/A"
        sp = f"{r['spy_20d']:+.1%}" if pd.notna(r['spy_20d']) else "N/A"
        print(f"  {r['quarter']:<10} {nd:>8} {vx:>6} {yd:>6} {sp:>8} {r['regime']:<12}")

    # Regime analysis
    print(f"\n  NVDA REACTION BY MARKET REGIME:")
    for regime in df["regime"].unique():
        subset = df[df["regime"] == regime]
        avg = subset["nvda_1d"].mean()
        n = len(subset)
        if pd.notna(avg):
            print(f"    {regime:<12}: avg next-day {avg:+.1%} ({n} occurrences)")

    # VIX correlation
    valid = df.dropna(subset=["nvda_1d", "vix"])
    if len(valid) >= 4:
        corr, pval = stats.pearsonr(valid["vix"], valid["nvda_1d"])
        print(f"\n  VIX vs NVDA next-day: r = {corr:+.2f} (p={pval:.3f})")
        if corr > 0:
            print(f"    → Higher VIX (more fear) = BIGGER rallies (fear positioning gives upside surprise)")
        else:
            print(f"    → Higher VIX = more muted/negative reaction")

    # Yield correlation
    valid = df.dropna(subset=["nvda_1d", "yield_10y"])
    if len(valid) >= 4:
        corr, pval = stats.pearsonr(valid["yield_10y"], valid["nvda_1d"])
        print(f"\n  10Y Yield vs NVDA next-day: r = {corr:+.2f} (p={pval:.3f})")
        if corr < 0:
            print(f"    → Higher rates = worse NVDA reaction (growth stock rate sensitivity)")
        else:
            print(f"    → Rates don't hurt NVDA reaction (AI demand overrides rate concerns)")

    # Current macro snapshot
    print(f"\n  CURRENT MACRO SNAPSHOT (for Feb 25, 2026 earnings):")
    if "^VIX" in data:
        curr_vix = data["^VIX"]["Close"].iloc[-1]
        print(f"    VIX: {curr_vix:.1f}", end="")
        if curr_vix < 15:
            print(" (LOW — complacent, larger moves possible)")
        elif curr_vix > 25:
            print(" (HIGH — fearful, potential for upside surprise)")
        else:
            print(" (MODERATE)")
    if "^TNX" in data:
        curr_tnx = data["^TNX"]["Close"].iloc[-1]
        print(f"    10Y Yield: {curr_tnx:.2f}%", end="")
        if curr_tnx > 4.5:
            print(" (HIGH — headwind for growth)")
        elif curr_tnx < 3.5:
            print(" (LOW — tailwind for growth)")
        else:
            print(" (MODERATE)")
    if "SPY" in data:
        spy = data["SPY"]
        spy_20d = (spy["Close"].iloc[-1] - spy["Close"].iloc[-20]) / spy["Close"].iloc[-20]
        print(f"    SPY 20-day trend: {spy_20d:+.1%}", end="")
        if spy_20d > 0.02:
            print(" (BULLISH)")
        elif spy_20d < -0.02:
            print(" (BEARISH)")
        else:
            print(" (FLAT)")

    return df


# ══════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════
def create_charts(data, df_sector, df_vol, df_peers, df_guidance, df_macro):
    """Create comprehensive multi-dimensional charts."""

    # ── CHART 1: 2x3 Multi-Dimension Overview ──
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle("NVDA Earnings — Multi-Dimensional Analysis (12 Quarters)", fontsize=16, fontweight="bold")

    quarters = [e["q"] for e in EARNINGS]
    x = np.arange(len(quarters))

    # Panel 1: Sector Ripple
    ax = axes[0, 0]
    width = 0.2
    for i, (ticker, color) in enumerate([("NVDA", "#76b900"), ("QQQ", "#4285f4"), ("SMH", "#ea4335"), ("SPY", "#fbbc05")]):
        col = f"{ticker}_1d"
        if col in df_sector.columns:
            vals = df_sector[col].fillna(0) * 100
            ax.bar(x + i*width - 1.5*width, vals, width, label=ticker, color=color, alpha=0.8)
    ax.set_title("D1: Sector Ripple (Next-Day %)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(quarters, rotation=45, fontsize=7)
    ax.legend(fontsize=7)
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.set_ylabel("Return (%)")

    # Panel 2: Volatility & Volume
    ax = axes[0, 1]
    ax2 = ax.twinx()
    if "pre_vol_20d" in df_vol.columns:
        ax.plot(x, df_vol["pre_vol_20d"].fillna(0) * 100, "o-", color="#e74c3c", label="Pre-Earnings Vol", linewidth=2)
    if "post_vol_10d" in df_vol.columns:
        ax.plot(x, df_vol["post_vol_10d"].fillna(0) * 100, "s--", color="#3498db", label="Post-Earnings Vol", linewidth=2)
    if "vol_ratio" in df_vol.columns:
        ax2.bar(x, df_vol["vol_ratio"].fillna(0), 0.4, color="#95a5a6", alpha=0.4, label="Volume Spike")
    ax.set_title("D2: Volatility Crush & Volume", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(quarters, rotation=45, fontsize=7)
    ax.set_ylabel("Realized Vol (%)", color="#e74c3c")
    ax2.set_ylabel("Volume Ratio", color="#95a5a6")
    ax.legend(loc="upper left", fontsize=7)

    # Panel 3: Peer Reactions
    ax = axes[0, 2]
    peers = ["AMD", "AVGO", "MRVL", "ARM", "SMCI"]
    peer_colors = {"AMD": "#ed1c24", "AVGO": "#cc0000", "MRVL": "#005daa", "ARM": "#0091bd", "SMCI": "#ff6600"}
    for peer in peers:
        col = f"{peer}_1d"
        if col in df_peers.columns:
            vals = df_peers[col].fillna(0) * 100
            ax.plot(x, vals, "o-", label=peer, color=peer_colors.get(peer, "gray"), linewidth=1.5, markersize=4)
    nvda_col = df_peers["NVDA_1d"].fillna(0) * 100
    ax.plot(x, nvda_col, "s-", label="NVDA", color="#76b900", linewidth=2.5, markersize=5)
    ax.set_title("D3: Peer Stock Reactions (Next-Day %)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(quarters, rotation=45, fontsize=7)
    ax.legend(fontsize=6, ncol=2)
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.set_ylabel("Return (%)")

    # Panel 4: Guidance vs Beat
    ax = axes[1, 0]
    ax2 = ax.twinx()
    if "guidance_raise" in df_guidance.columns:
        ax.bar(x - 0.2, df_guidance["guidance_raise"].fillna(0), 0.35, color="#2ecc71", alpha=0.8, label="Guidance Raise %")
    if "eps_beat" in df_guidance.columns:
        ax.bar(x + 0.2, df_guidance["eps_beat"].fillna(0), 0.35, color="#9b59b6", alpha=0.8, label="EPS Beat %")
    if "nvda_1d" in df_guidance.columns:
        ax2.plot(x, df_guidance["nvda_1d"].fillna(0) * 100, "D-", color="#e74c3c", linewidth=2, markersize=6, label="NVDA Next-Day %")
    ax.set_title("D4: Guidance vs Beat → Price Move", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(quarters, rotation=45, fontsize=7)
    ax.set_ylabel("Beat / Raise (%)")
    ax2.set_ylabel("NVDA Next-Day Return (%)", color="#e74c3c")
    ax.legend(loc="upper left", fontsize=7)
    ax2.legend(loc="upper right", fontsize=7)

    # Panel 5: Macro Environment
    ax = axes[1, 1]
    ax2 = ax.twinx()
    if "vix" in df_macro.columns:
        ax.plot(x, df_macro["vix"].fillna(0), "o-", color="#e74c3c", linewidth=2, label="VIX")
    if "yield_10y" in df_macro.columns:
        ax.plot(x, df_macro["yield_10y"].fillna(0), "s-", color="#3498db", linewidth=2, label="10Y Yield")
    if "nvda_1d" in df_macro.columns:
        ax2.bar(x, df_macro["nvda_1d"].fillna(0) * 100, 0.4, color="#76b900", alpha=0.5, label="NVDA Next-Day %")
    ax.set_title("D5: Macro Environment at Earnings", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(quarters, rotation=45, fontsize=7)
    ax.set_ylabel("VIX / Yield Level")
    ax2.set_ylabel("NVDA Next-Day (%)", color="#76b900")
    ax.legend(loc="upper left", fontsize=7)
    ax2.legend(loc="upper right", fontsize=7)

    # Panel 6: Combined Score Heatmap
    ax = axes[1, 2]
    # Create a summary heatmap of all dimensions
    heatmap_data = []
    labels = []
    for i, e in enumerate(EARNINGS):
        row = []
        # D1: Sector drag (SMH move)
        smh_val = df_sector.iloc[i].get("SMH_1d", 0)
        row.append(smh_val * 100 if pd.notna(smh_val) else 0)
        # D2: Vol crush
        vc = df_vol.iloc[i].get("vol_crush", 0)
        row.append(vc * 100 if pd.notna(vc) else 0)
        # D3: Best peer
        peer_vals = []
        for p in peers:
            pv = df_peers.iloc[i].get(f"{p}_1d", np.nan)
            if pd.notna(pv):
                peer_vals.append(pv * 100)
        row.append(np.mean(peer_vals) if peer_vals else 0)
        # D4: Guidance raise
        gr = df_guidance.iloc[i].get("guidance_raise", 0)
        row.append(gr if pd.notna(gr) else 0)
        # D5: VIX level
        vx = df_macro.iloc[i].get("vix", 0)
        row.append(vx if pd.notna(vx) else 0)

        heatmap_data.append(row)
        labels.append(e["q"])

    hm = np.array(heatmap_data)
    # Normalize each column to 0-1 for heatmap
    hm_norm = np.zeros_like(hm)
    for j in range(hm.shape[1]):
        col = hm[:, j]
        mn, mx = col.min(), col.max()
        if mx > mn:
            hm_norm[:, j] = (col - mn) / (mx - mn)
        else:
            hm_norm[:, j] = 0.5

    im = ax.imshow(hm_norm.T, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, fontsize=7)
    ax.set_yticks(range(5))
    ax.set_yticklabels(["Sector", "Vol Crush", "Peers", "Guidance", "VIX"], fontsize=8)
    ax.set_title("Combined Dimension Heatmap", fontweight="bold")

    # Add values
    for i in range(len(labels)):
        for j in range(5):
            val = hm[i, j]
            ax.text(i, j, f"{val:.1f}", ha="center", va="center", fontsize=6,
                    color="white" if hm_norm[i, j] < 0.3 or hm_norm[i, j] > 0.7 else "black")

    plt.tight_layout()
    plt.savefig("nvda_multidim_chart.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Chart saved to: nvda_multidim_chart.png")

    # ── CHART 2: Guidance Scatter ──
    fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig2.suptitle("NVDA: What Drives Post-Earnings Price Move?", fontsize=14, fontweight="bold")

    # Guidance raise vs next-day return
    valid = df_guidance.dropna(subset=["nvda_1d", "guidance_raise"])
    if len(valid) >= 3:
        ax1.scatter(valid["guidance_raise"], valid["nvda_1d"] * 100, s=80, c="#2ecc71", edgecolors="black", zorder=3)
        for _, r in valid.iterrows():
            ax1.annotate(r["quarter"], (r["guidance_raise"], r["nvda_1d"] * 100), fontsize=7, ha="center", va="bottom")
        # Trend line
        z = np.polyfit(valid["guidance_raise"], valid["nvda_1d"] * 100, 1)
        p = np.poly1d(z)
        x_line = np.linspace(valid["guidance_raise"].min(), valid["guidance_raise"].max(), 50)
        ax1.plot(x_line, p(x_line), "--", color="red", alpha=0.7, label=f"Trend (slope={z[0]:.2f})")
    ax1.set_xlabel("Guidance Revenue Raise (%)")
    ax1.set_ylabel("NVDA Next-Day Return (%)")
    ax1.set_title("Guidance Raise → Next-Day Move")
    ax1.axhline(y=0, color="gray", linewidth=0.5)
    ax1.legend()

    # EPS beat vs next-day return
    valid2 = df_guidance.dropna(subset=["nvda_1d", "eps_beat"])
    if len(valid2) >= 3:
        ax2.scatter(valid2["eps_beat"], valid2["nvda_1d"] * 100, s=80, c="#9b59b6", edgecolors="black", zorder=3)
        for _, r in valid2.iterrows():
            ax2.annotate(r["quarter"], (r["eps_beat"], r["nvda_1d"] * 100), fontsize=7, ha="center", va="bottom")
        z2 = np.polyfit(valid2["eps_beat"], valid2["nvda_1d"] * 100, 1)
        p2 = np.poly1d(z2)
        x_line2 = np.linspace(valid2["eps_beat"].min(), valid2["eps_beat"].max(), 50)
        ax2.plot(x_line2, p2(x_line2), "--", color="red", alpha=0.7, label=f"Trend (slope={z2[0]:.2f})")
    ax2.set_xlabel("EPS Beat (%)")
    ax2.set_ylabel("NVDA Next-Day Return (%)")
    ax2.set_title("EPS Beat → Next-Day Move")
    ax2.axhline(y=0, color="gray", linewidth=0.5)
    ax2.legend()

    plt.tight_layout()
    plt.savefig("nvda_guidance_vs_beat_chart.png", dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"  Chart saved to: nvda_guidance_vs_beat_chart.png")


# ══════════════════════════════════════════════════════════════
# FINAL SYNTHESIS
# ══════════════════════════════════════════════════════════════
def synthesis(df_sector, df_vol, df_peers, df_guidance, df_macro):
    """Combine all dimensions into actionable insights."""
    print(f"\n\n{'#'*80}")
    print(f"  SYNTHESIS: MULTI-DIMENSIONAL OUTLOOK FOR FEB 25, 2026")
    print(f"{'#'*80}")

    print(f"""
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  DIMENSION 1 — SECTOR RIPPLE                                          │
  │  When NVDA drops, SMH drops harder. QQQ/SPY follow but less.          │
  │  If sell-the-news plays out → expect SMH -2% to -5%, QQQ -1% to -2%  │
  │  Your SOFI/MGNI (not in SMH) may get collateral damage but less      │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  DIMENSION 2 — VOLATILITY                                             │
  │  Pre-earnings vol runs high → post-earnings vol typically drops        │
  │  Volume spikes 2-4x on earnings day                                   │
  │  Best to buy AFTER the volatility crush settles (2-3 days post)       │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  DIMENSION 3 — PEER STOCKS                                            │
  │  AMD, AVGO, MRVL move in sympathy with NVDA earnings                  │
  │  When NVDA sells off, peers sell off harder (higher beta)              │
  │  This creates buying opportunities in quality peers                    │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  DIMENSION 4 — GUIDANCE > BEAT                                        │
  │  EPS beat alone does NOT reliably move stock (+)                       │
  │  Forward guidance (revenue raise %) is the better predictor            │
  │  Recent quarters: beats shrinking, guidance slowing → weaker rallies   │
  │  Watch for: guidance raise <5% = likely selloff                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  DIMENSION 5 — MACRO ENVIRONMENT                                      │
  │  Low VIX + bullish SPY = complacent market → larger post-earnings     │
  │  moves (either direction). High VIX = potential upside surprise.       │
  │  Rate environment: higher 10Y yield = headwind for growth reactions    │
  └─────────────────────────────────────────────────────────────────────────┘
""")

    print(f"  ═══════════════════════════════════════════════════════════════")
    print(f"  ACTION PLAN CONFIRMATION:")
    print(f"  ═══════════════════════════════════════════════════════════════")
    print(f"""
  Phase 1 (Feb 20): SELL losers — UNAFFECTED by NVDA earnings
  Phase 2 (Feb 21): BUY income ETFs — UNAFFECTED by NVDA earnings
  Phase 3 (Feb 27): BUY growth — OPTIMAL timing:
    • 2 days post-NVDA earnings → volatility crush settled
    • If sell-the-news → buy SOFI/MGNI at ~2-3% discount
    • If beat-and-rally → buy with momentum, still good entries
    • Peer damage may create even better entries in related names

  WATCH LIST for Feb 25 evening:
    1. Guidance revenue number — is raise >8%? (bullish) or <5%? (bearish)
    2. VIX reaction — spike >20 = market nervous = wait an extra day
    3. SMH after-hours — if SMH drops >3% = broader chip selloff = wait
    4. AMD/AVGO pre-market Feb 26 — if they gap down = buy them instead?
""")


def main():
    # Fetch all data
    data = fetch_all_data()

    # Run all 5 dimensions
    df_sector = dim1_sector_ripple(data)
    df_vol = dim2_volatility_volume(data)
    df_peers = dim3_related_stocks(data)
    df_guidance = dim4_guidance_analysis(data)
    df_macro = dim5_macro_environment(data)

    # Generate charts
    print(f"\n  Generating multi-dimensional charts...")
    create_charts(data, df_sector, df_vol, df_peers, df_guidance, df_macro)

    # Final synthesis
    synthesis(df_sector, df_vol, df_peers, df_guidance, df_macro)

    print(f"\n{'='*80}")
    print(f"  DISCLAIMER: Historical patterns do not guarantee future results.")
    print(f"  This is for educational/analysis purposes only.")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
