"""Options analysis — Black-Scholes, put/call screening, wheel strategy."""

import numpy as np
import pandas as pd
from datetime import datetime
from scipy.stats import norm
from invtool.config import RISK_FREE_RATE, MIN_OPEN_INTEREST, MIN_DTE, MAX_DTE


# ── Black-Scholes ──

def bs_delta_put(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return float(norm.cdf(d1) - 1)


def bs_delta_call(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return float(norm.cdf(d1))


def prob_otm_put(S, K, T, r, sigma):
    """Probability put expires OTM (stock stays above K)."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d2 = (np.log(S / K) + (r - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return float(norm.cdf(d2))


def prob_otm_call(S, K, T, r, sigma):
    """Probability call expires OTM (stock stays below K)."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d2 = (np.log(S / K) + (r - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return float(norm.cdf(-d2))


# ── Options Screening ──

def _fetch_chain(data_provider, ticker, direction, min_dte=MIN_DTE, max_dte=MAX_DTE):
    """Fetch and concatenate options chain across expirations."""
    expirations = data_provider.get_expirations(ticker)
    if not expirations:
        return pd.DataFrame()

    today = datetime.now().date()
    all_opts = []

    for exp_str in expirations:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        dte = (exp_date - today).days
        if dte < min_dte or dte > max_dte:
            continue
        chain = data_provider.get_options_chain(ticker, exp_str)
        if chain is None:
            continue
        opts = chain.puts.copy() if direction == "puts" else chain.calls.copy()
        if opts.empty:
            continue
        opts["expiration"] = exp_str
        opts["DTE"] = dte
        opts["T"] = dte / 365.0
        all_opts.append(opts)

    if not all_opts:
        return pd.DataFrame()

    df = pd.concat(all_opts, ignore_index=True)
    df = df[df["bid"] > 0.01].copy()
    return df


def screen_puts(ticker, data_provider, hist_vol=None, min_dte=MIN_DTE, max_dte=MAX_DTE):
    """Screen put options for sell-put strategy. Returns scored DataFrame."""
    price = data_provider.get_current_price(ticker)
    if price <= 0:
        return pd.DataFrame()

    df = _fetch_chain(data_provider, ticker, "puts", min_dte, max_dte)
    if df.empty:
        return df

    # OTM puts only
    df = df[df["strike"] < price].copy()
    df = df[df["openInterest"] >= max(MIN_OPEN_INTEREST // 3, 5)].copy()
    if df.empty:
        return df

    S, r = price, RISK_FREE_RATE
    if hist_vol is None:
        hist_vol = data_provider.get_hist_vol(ticker)

    df["iv"] = df["impliedVolatility"].fillna(hist_vol)
    df["delta"] = df.apply(lambda row: bs_delta_put(S, row["strike"], row["T"], r, row["iv"]), axis=1)
    df["prob_otm"] = df.apply(lambda row: prob_otm_put(S, row["strike"], row["T"], r, row["iv"]), axis=1)
    df["premium"] = df["bid"]
    df["return_on_capital"] = df["premium"] / df["strike"]
    df["annualized_return"] = df["return_on_capital"] * (365.0 / df["DTE"])
    df["breakeven"] = df["strike"] - df["premium"]
    df["downside_cushion"] = (S - df["breakeven"]) / S
    df["otm_pct"] = (S - df["strike"]) / S

    # Expected value
    df["expected_value"] = (
        df["prob_otm"] * df["premium"]
        - (1 - df["prob_otm"]) * (df["strike"] * 0.15)
    )

    # Scoring — balance yield, safety, and liquidity
    df["score"] = (
        df["annualized_return"] * 30
        + df["prob_otm"] * 25
        + df["downside_cushion"] * 20
        + np.log1p(df["openInterest"]) * 3
        + (df["expected_value"] > 0).astype(float) * 10
        - (df["otm_pct"] > 0.40).astype(float) * 15  # penalize strikes >40% OTM
    )

    # Prefer strikes with meaningful premium (>$0.20 bid)
    df.loc[df["premium"] >= 0.20, "score"] += 5
    df.loc[df["premium"] >= 1.00, "score"] += 5

    df = df.sort_values("score", ascending=False)
    df["current_price"] = S
    return df


def screen_calls(ticker, data_provider, cost_basis=None, hist_vol=None,
                 min_dte=MIN_DTE, max_dte=MAX_DTE):
    """Screen call options for covered-call strategy."""
    price = data_provider.get_current_price(ticker)
    if price <= 0:
        return pd.DataFrame()

    df = _fetch_chain(data_provider, ticker, "calls", min_dte, max_dte)
    if df.empty:
        return df

    # OTM calls only
    df = df[df["strike"] > price].copy()
    df = df[df["openInterest"] >= max(MIN_OPEN_INTEREST // 3, 5)].copy()
    if df.empty:
        return df

    S, r = price, RISK_FREE_RATE
    if hist_vol is None:
        hist_vol = data_provider.get_hist_vol(ticker)

    df["iv"] = df["impliedVolatility"].fillna(hist_vol)
    df["delta"] = df.apply(lambda row: bs_delta_call(S, row["strike"], row["T"], r, row["iv"]), axis=1)
    df["prob_otm"] = df.apply(lambda row: prob_otm_call(S, row["strike"], row["T"], r, row["iv"]), axis=1)
    df["premium"] = df["bid"]
    df["annualized_return"] = (df["premium"] / S) * (365.0 / df["DTE"])
    df["upside_to_strike"] = (df["strike"] - S) / S

    if cost_basis and cost_basis > 0:
        df["profit_if_called"] = (df["strike"] - cost_basis + df["premium"]) * 100

    # Scoring
    df["score"] = (
        df["annualized_return"] * 30
        + df["prob_otm"] * 20
        + df["upside_to_strike"] * 15
        + np.log1p(df["openInterest"]) * 3
    )
    df = df.sort_values("score", ascending=False)
    df["current_price"] = S
    return df


def wheel_analysis(ticker, data_provider, shares=0, cost_basis=0):
    """Full wheel strategy analysis for a ticker."""
    price = data_provider.get_current_price(ticker)
    puts = screen_puts(ticker, data_provider)
    calls = screen_calls(ticker, data_provider, cost_basis)
    can_wheel = shares >= 100

    result = {
        "ticker": ticker,
        "price": price,
        "shares": shares,
        "cost_basis": cost_basis,
        "can_wheel": can_wheel,
        "best_puts": puts.head(5).to_dict("records") if not puts.empty else [],
        "best_calls": calls.head(5).to_dict("records") if not calls.empty else [],
    }

    # Estimate monthly income
    if not puts.empty:
        best_put = puts.iloc[0]
        result["put_monthly_est"] = float(best_put["premium"] * 100 * (30 / best_put["DTE"]))
    if not calls.empty and can_wheel:
        best_call = calls.iloc[0]
        result["call_monthly_est"] = float(best_call["premium"] * 100 * (30 / best_call["DTE"]))

    return result
