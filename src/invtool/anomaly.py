"""Anomaly detection — z-score based alerts for price, volume, and volatility."""

import numpy as np
import pandas as pd


def detect_anomalies(ticker: str, data_provider, lookback=60, z_threshold=2.0) -> dict:
    """Detect anomalies in price, volume, and volatility for a ticker."""
    ticker = ticker.upper()
    hist = data_provider.get_history(ticker, "6mo")

    if hist.empty or len(hist) < 20:
        return {"ticker": ticker, "anomalies": [], "has_active_alerts": False,
                "summary": "Insufficient data"}

    df = hist.copy()
    df["returns"] = df["Close"].pct_change()
    df["log_returns"] = np.log(df["Close"] / df["Close"].shift(1))
    df["intraday_range"] = (df["High"] - df["Low"]) / df["Close"]
    df["vol_20d"] = df["log_returns"].rolling(20).std() * np.sqrt(252)

    anomalies = []

    # 1. Volume anomalies — z-score on log-volume
    if "Volume" in df.columns:
        log_vol = np.log1p(df["Volume"].astype(float))
        vol_mean = log_vol.rolling(lookback, min_periods=20).mean()
        vol_std = log_vol.rolling(lookback, min_periods=20).std()
        df["vol_z"] = (log_vol - vol_mean) / vol_std.replace(0, np.nan)

        recent = df.dropna(subset=["vol_z"]).tail(5)
        for idx, row in recent.iterrows():
            if abs(row["vol_z"]) >= z_threshold:
                direction = "spike" if row["vol_z"] > 0 else "dry-up"
                anomalies.append({
                    "type": f"VOLUME_{direction.upper().replace('-', '_')}",
                    "date": idx.strftime("%Y-%m-%d"),
                    "z_score": round(float(row["vol_z"]), 2),
                    "value": int(row["Volume"]),
                    "description": f"Volume {direction}: {int(row['Volume']):,} "
                                   f"(z={row['vol_z']:.1f})",
                })

    # 2. Price gap anomalies — overnight gaps
    df["gap"] = (df["Open"] - df["Close"].shift(1)) / df["Close"].shift(1)
    gap_std = df["gap"].rolling(lookback, min_periods=20).std()
    gap_mean = df["gap"].rolling(lookback, min_periods=20).mean()
    df["gap_z"] = (df["gap"] - gap_mean) / gap_std.replace(0, np.nan)

    recent = df.dropna(subset=["gap_z"]).tail(5)
    for idx, row in recent.iterrows():
        if abs(row["gap_z"]) >= z_threshold:
            direction = "up" if row["gap"] > 0 else "down"
            anomalies.append({
                "type": f"PRICE_GAP_{direction.upper()}",
                "date": idx.strftime("%Y-%m-%d"),
                "z_score": round(float(row["gap_z"]), 2),
                "value": round(float(row["gap"]) * 100, 2),
                "description": f"Price gap {direction}: {row['gap']:+.2%} "
                               f"(z={row['gap_z']:.1f})",
            })

    # 3. Return anomalies — extreme daily moves
    ret_mean = df["returns"].rolling(lookback, min_periods=20).mean()
    ret_std = df["returns"].rolling(lookback, min_periods=20).std()
    df["ret_z"] = (df["returns"] - ret_mean) / ret_std.replace(0, np.nan)

    recent = df.dropna(subset=["ret_z"]).tail(5)
    for idx, row in recent.iterrows():
        if abs(row["ret_z"]) >= z_threshold:
            direction = "surge" if row["returns"] > 0 else "plunge"
            anomalies.append({
                "type": f"EXTREME_MOVE_{direction.upper()}",
                "date": idx.strftime("%Y-%m-%d"),
                "z_score": round(float(row["ret_z"]), 2),
                "value": round(float(row["returns"]) * 100, 2),
                "description": f"Extreme {direction}: {row['returns']:+.2%} "
                               f"(z={row['ret_z']:.1f})",
            })

    # 4. Volatility regime change — sudden vol expansion or crush
    if df["vol_20d"].notna().sum() > 10:
        vol_mean = df["vol_20d"].rolling(lookback, min_periods=10).mean()
        vol_std_r = df["vol_20d"].rolling(lookback, min_periods=10).std()
        df["vol_regime_z"] = (df["vol_20d"] - vol_mean) / vol_std_r.replace(0, np.nan)

        recent = df.dropna(subset=["vol_regime_z"]).tail(3)
        for idx, row in recent.iterrows():
            if abs(row["vol_regime_z"]) >= z_threshold:
                direction = "expansion" if row["vol_regime_z"] > 0 else "crush"
                anomalies.append({
                    "type": f"VOLATILITY_{direction.upper()}",
                    "date": idx.strftime("%Y-%m-%d"),
                    "z_score": round(float(row["vol_regime_z"]), 2),
                    "value": round(float(row["vol_20d"]) * 100, 1),
                    "description": f"Vol {direction}: {row['vol_20d']:.1%} annualized "
                                   f"(z={row['vol_regime_z']:.1f})",
                })

    # Deduplicate by date+type
    seen = set()
    unique = []
    for a in anomalies:
        key = (a["date"], a["type"])
        if key not in seen:
            seen.add(key)
            unique.append(a)
    anomalies = sorted(unique, key=lambda x: x["date"], reverse=True)

    # Summary
    current_price = float(df["Close"].iloc[-1])
    if anomalies:
        summary = f"{len(anomalies)} anomalies detected in last 5 days"
    else:
        summary = "No anomalies — normal trading activity"

    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "anomalies": anomalies,
        "has_active_alerts": len(anomalies) > 0,
        "summary": summary,
        "df": df,  # for charting
    }


def scan_portfolio_anomalies(data_provider, holdings: list) -> list:
    """Scan all portfolio holdings for anomalies."""
    results = []
    for h in holdings:
        result = detect_anomalies(h["ticker"], data_provider)
        if result["anomalies"]:
            results.append({
                "ticker": result["ticker"],
                "alert_count": len(result["anomalies"]),
                "anomalies": result["anomalies"],
            })
    return results
