"""Monte Carlo simulation — portfolio risk analysis with VaR and CVaR."""

import numpy as np
import pandas as pd
from invtool.config import load_portfolio


def monte_carlo_simulation(data_provider, holdings=None, n_sims=10000,
                           horizons=None) -> dict:
    """Run Monte Carlo simulation on portfolio."""
    if holdings is None:
        holdings = load_portfolio()
    if horizons is None:
        horizons = [7, 30, 90]

    tickers = [h["ticker"] for h in holdings]
    shares = {h["ticker"]: h["shares"] for h in holdings}
    costs = {h["ticker"]: h["cost"] for h in holdings}

    # Fetch historical data
    returns_data = {}
    prices = {}
    for t in tickers:
        hist = data_provider.get_history(t, "1y")
        if hist.empty or len(hist) < 30:
            continue
        ret = hist["Close"].pct_change().dropna()
        returns_data[t] = ret
        prices[t] = float(hist["Close"].iloc[-1])

    if not returns_data:
        return {"error": "No valid price data for portfolio"}

    valid_tickers = list(returns_data.keys())

    # Align returns to common dates
    returns_df = pd.DataFrame(returns_data)
    returns_df = returns_df.dropna()

    if len(returns_df) < 20:
        return {"error": "Insufficient overlapping data"}

    # Calculate portfolio value
    portfolio_value = sum(shares.get(t, 0) * prices.get(t, 0) for t in valid_tickers)
    weights = np.array([
        shares.get(t, 0) * prices.get(t, 0) / portfolio_value
        for t in valid_tickers
    ]) if portfolio_value > 0 else np.ones(len(valid_tickers)) / len(valid_tickers)

    # Portfolio return statistics
    mean_returns = returns_df[valid_tickers].mean().values
    cov_matrix = returns_df[valid_tickers].cov().values

    # Run simulations for each horizon
    horizon_results = []
    np.random.seed(42)

    for days in horizons:
        # Simulate correlated returns using Cholesky decomposition
        try:
            L = np.linalg.cholesky(cov_matrix)
        except np.linalg.LinAlgError:
            # Add small diagonal if not positive definite
            cov_adj = cov_matrix + np.eye(len(valid_tickers)) * 1e-6
            L = np.linalg.cholesky(cov_adj)

        # Generate random returns: (n_sims, days, n_assets)
        z = np.random.standard_normal((n_sims, days, len(valid_tickers)))
        correlated_returns = z @ L.T + mean_returns

        # Cumulative portfolio returns
        cumulative = np.prod(1 + correlated_returns, axis=1)  # (n_sims, n_assets)
        portfolio_returns = (cumulative * weights).sum(axis=1) - 1  # (n_sims,)

        # Dollar P&L
        pnl = portfolio_returns * portfolio_value

        # VaR and CVaR
        var_95 = float(np.percentile(pnl, 5))
        var_99 = float(np.percentile(pnl, 1))
        cvar_95 = float(pnl[pnl <= np.percentile(pnl, 5)].mean())

        # Probabilities
        prob_loss = float((pnl < 0).mean())
        prob_loss_10pct = float((portfolio_returns < -0.10).mean())

        # Max drawdown simulation (simplified: worst single-day across path)
        # Track running cumulative for drawdown
        cum_paths = np.cumprod(1 + correlated_returns @ weights.reshape(-1, 1),
                               axis=1).squeeze()  # (n_sims, days)
        if cum_paths.ndim == 1:
            cum_paths = cum_paths.reshape(1, -1)
        running_max = np.maximum.accumulate(cum_paths, axis=1)
        drawdowns = (cum_paths - running_max) / running_max
        max_drawdowns = drawdowns.min(axis=1)
        avg_max_dd = float(max_drawdowns.mean())

        horizon_results.append({
            "days": days,
            "var_95": round(var_95, 2),
            "var_99": round(var_99, 2),
            "cvar_95": round(cvar_95, 2),
            "prob_loss": round(prob_loss, 3),
            "prob_loss_10pct": round(prob_loss_10pct, 3),
            "median_return": round(float(np.median(portfolio_returns)) * 100, 2),
            "mean_return": round(float(np.mean(portfolio_returns)) * 100, 2),
            "best_case": round(float(np.percentile(pnl, 95)), 2),
            "worst_case": round(float(np.percentile(pnl, 5)), 2),
            "avg_max_drawdown": round(avg_max_dd * 100, 2),
            "simulations": pnl.tolist(),  # for histogram charting
        })

    return {
        "portfolio_value": round(portfolio_value, 2),
        "tickers": valid_tickers,
        "weights": {t: round(float(w), 4) for t, w in zip(valid_tickers, weights)},
        "n_sims": n_sims,
        "horizons": horizon_results,
    }
