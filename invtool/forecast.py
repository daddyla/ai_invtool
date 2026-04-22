"""Price forecasting — trend extrapolation with confidence intervals."""

import numpy as np
import pandas as pd
from scipy import stats


def price_forecast(ticker: str, data_provider, days_forward=90) -> dict:
    """Forecast price using log-linear regression with confidence bands."""
    ticker = ticker.upper()
    hist = data_provider.get_history(ticker, "1y")

    if hist.empty or len(hist) < 30:
        return {"ticker": ticker, "error": "Insufficient price history"}

    df = hist.copy()
    prices = df["Close"].values
    log_prices = np.log(prices)
    n = len(log_prices)
    x = np.arange(n)

    # Fit log-linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, log_prices)
    r_squared = r_value ** 2

    # Residual standard error
    fitted = intercept + slope * x
    residuals = log_prices - fitted
    residual_std = np.std(residuals, ddof=2)

    # Daily trend as annualized %
    daily_trend = np.exp(slope) - 1
    annual_trend = (1 + daily_trend) ** 252 - 1

    current_price = float(prices[-1])

    # Forecast at 30, 60, 90 day horizons
    horizons = [30, 60, 90] if days_forward >= 90 else [days_forward]
    if days_forward >= 60 and 60 not in horizons:
        horizons = [30, 60, days_forward]
    if days_forward >= 30 and 30 not in horizons:
        horizons = [30, days_forward]
    horizons = sorted(set([30, 60, 90]))

    forecasts = []
    for d in horizons:
        x_future = n - 1 + d
        log_forecast = intercept + slope * x_future

        # Prediction interval: wider as we extrapolate further
        se_pred = residual_std * np.sqrt(
            1 + 1 / n + (x_future - np.mean(x)) ** 2 / np.sum((x - np.mean(x)) ** 2)
        )

        price_mid = np.exp(log_forecast)
        low_1s = np.exp(log_forecast - se_pred)
        high_1s = np.exp(log_forecast + se_pred)
        low_2s = np.exp(log_forecast - 2 * se_pred)
        high_2s = np.exp(log_forecast + 2 * se_pred)

        forecasts.append({
            "days": d,
            "price": round(float(price_mid), 2),
            "low_1s": round(float(low_1s), 2),
            "high_1s": round(float(high_1s), 2),
            "low_2s": round(float(low_2s), 2),
            "high_2s": round(float(high_2s), 2),
            "change_pct": round(float((price_mid / current_price - 1) * 100), 1),
        })

    # Build projection DataFrame for charting
    future_x = np.arange(n, n + 91)
    future_dates = pd.bdate_range(start=df.index[-1], periods=92)[1:]
    future_log = intercept + slope * future_x
    future_se = residual_std * np.sqrt(
        1 + 1 / n + (future_x - np.mean(x)) ** 2 / np.sum((x - np.mean(x)) ** 2)
    )

    proj_df = pd.DataFrame({
        "price": np.exp(future_log),
        "low_1s": np.exp(future_log - future_se),
        "high_1s": np.exp(future_log + future_se),
        "low_2s": np.exp(future_log - 2 * future_se),
        "high_2s": np.exp(future_log + 2 * future_se),
    }, index=future_dates[:len(future_x)])

    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "forecasts": forecasts,
        "trend_slope_daily": round(float(daily_trend) * 100, 4),
        "trend_annual": round(float(annual_trend) * 100, 1),
        "r_squared": round(float(r_squared), 4),
        "p_value": round(float(p_value), 6),
        "residual_std": round(float(residual_std), 4),
        "hist_df": df,
        "proj_df": proj_df,
    }
