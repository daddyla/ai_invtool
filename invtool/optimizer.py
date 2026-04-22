"""Portfolio optimization — mean-variance (Markowitz) efficient frontier."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from invtool.config import RISK_FREE_RATE


def optimize_portfolio(data_provider, tickers: list, target="sharpe") -> dict:
    """Mean-variance portfolio optimization.

    target: "sharpe" (max Sharpe), "min_vol" (minimum variance),
            or a float for target annual return.
    """
    tickers = [t.upper() for t in tickers]

    # Fetch returns
    returns_data = {}
    prices = {}
    for t in tickers:
        hist = data_provider.get_history(t, "1y")
        if hist.empty or len(hist) < 30:
            continue
        returns_data[t] = hist["Close"].pct_change().dropna()
        prices[t] = float(hist["Close"].iloc[-1])

    valid_tickers = list(returns_data.keys())
    if len(valid_tickers) < 2:
        return {"error": "Need at least 2 tickers with valid data"}

    # Align
    returns_df = pd.DataFrame(returns_data).dropna()
    if len(returns_df) < 30:
        return {"error": "Insufficient overlapping data"}

    n = len(valid_tickers)
    mean_returns = returns_df.mean().values * 252  # annualized
    cov_matrix = returns_df.cov().values * 252     # annualized

    def portfolio_return(w):
        return w @ mean_returns

    def portfolio_vol(w):
        return np.sqrt(w @ cov_matrix @ w)

    def neg_sharpe(w):
        ret = portfolio_return(w)
        vol = portfolio_vol(w)
        return -(ret - RISK_FREE_RATE) / vol if vol > 0 else 0

    # Constraints: weights sum to 1, each 0-1
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.0, 1.0)] * n
    w0 = np.ones(n) / n

    # Optimize based on target
    if target == "sharpe":
        result = minimize(neg_sharpe, w0, method="SLSQP",
                          bounds=bounds, constraints=constraints)
    elif target == "min_vol":
        result = minimize(portfolio_vol, w0, method="SLSQP",
                          bounds=bounds, constraints=constraints)
    else:
        # Target return
        target_ret = float(target)
        constraints.append({
            "type": "eq",
            "fun": lambda w: portfolio_return(w) - target_ret,
        })
        result = minimize(portfolio_vol, w0, method="SLSQP",
                          bounds=bounds, constraints=constraints)

    optimal_weights = result.x if result.success else w0
    opt_return = float(portfolio_return(optimal_weights))
    opt_vol = float(portfolio_vol(optimal_weights))
    opt_sharpe = (opt_return - RISK_FREE_RATE) / opt_vol if opt_vol > 0 else 0

    # Equal-weight benchmark
    eq_return = float(portfolio_return(w0))
    eq_vol = float(portfolio_vol(w0))
    eq_sharpe = (eq_return - RISK_FREE_RATE) / eq_vol if eq_vol > 0 else 0

    # Efficient frontier (20 points)
    frontier = []
    target_returns = np.linspace(mean_returns.min(), mean_returns.max(), 20)
    for tr in target_returns:
        cons = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w, r=tr: portfolio_return(w) - r},
        ]
        res = minimize(portfolio_vol, w0, method="SLSQP",
                       bounds=bounds, constraints=cons)
        if res.success:
            fvol = float(portfolio_vol(res.x))
            fret = float(portfolio_return(res.x))
            frontier.append({
                "return": round(fret * 100, 2),
                "volatility": round(fvol * 100, 2),
            })

    # Per-ticker stats
    ticker_stats = []
    for i, t in enumerate(valid_tickers):
        ticker_stats.append({
            "ticker": t,
            "price": round(prices.get(t, 0), 2),
            "annual_return": round(float(mean_returns[i]) * 100, 2),
            "annual_vol": round(float(np.sqrt(cov_matrix[i, i])) * 100, 2),
            "optimal_weight": round(float(optimal_weights[i]) * 100, 1),
            "equal_weight": round(100 / n, 1),
        })

    return {
        "tickers": valid_tickers,
        "target": target,
        "optimal_weights": {t: round(float(w), 4) for t, w in zip(valid_tickers, optimal_weights)},
        "optimal_return": round(opt_return * 100, 2),
        "optimal_vol": round(opt_vol * 100, 2),
        "optimal_sharpe": round(float(opt_sharpe), 3),
        "equal_return": round(eq_return * 100, 2),
        "equal_vol": round(eq_vol * 100, 2),
        "equal_sharpe": round(float(eq_sharpe), 3),
        "frontier": frontier,
        "ticker_stats": ticker_stats,
    }
