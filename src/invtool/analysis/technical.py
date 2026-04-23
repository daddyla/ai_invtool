"""Technical analysis engine — indicators, support/resistance, trend."""

import pandas as pd
import numpy as np


def compute_indicators(hist: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to a price DataFrame."""
    df = hist.copy()

    # Moving Averages
    df["SMA_20"] = df["Close"].rolling(20).mean()
    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["EMA_12"] = df["Close"].ewm(span=12).mean()
    df["EMA_26"] = df["Close"].ewm(span=26).mean()

    # MACD
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    df["MACD_Hist"] = df["MACD"] - df["Signal"]

    # RSI (14-period)
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # Bollinger Bands (20, 2)
    df["BB_Mid"] = df["Close"].rolling(20).mean()
    bb_std = df["Close"].rolling(20).std()
    df["BB_Upper"] = df["BB_Mid"] + 2 * bb_std
    df["BB_Lower"] = df["BB_Mid"] - 2 * bb_std

    # Average True Range (14-period)
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR_14"] = tr.rolling(14).mean()

    # Historical Volatility (20-day annualized)
    df["Log_Return"] = np.log(df["Close"] / df["Close"].shift(1))
    df["Hist_Vol_20d"] = df["Log_Return"].rolling(20).std() * np.sqrt(252)

    return df


def find_support_resistance(hist: pd.DataFrame, current_price: float) -> dict:
    """Detect swing lows/highs and round-number levels."""
    lookback = min(60, len(hist))
    recent = hist.tail(lookback)

    supports = []
    resistances = []

    # Swing low detection (5-day window)
    for i in range(2, len(recent) - 2):
        low = recent["Low"].iloc[i]
        high = recent["High"].iloc[i]
        if (low <= recent["Low"].iloc[i-1] and low <= recent["Low"].iloc[i-2] and
                low <= recent["Low"].iloc[i+1] and low <= recent["Low"].iloc[i+2]):
            supports.append(round(low, 2))
        if (high >= recent["High"].iloc[i-1] and high >= recent["High"].iloc[i-2] and
                high >= recent["High"].iloc[i+1] and high >= recent["High"].iloc[i+2]):
            resistances.append(round(high, 2))

    # All-time low in window
    supports.append(round(hist["Low"].min(), 2))

    # Round number levels
    for level in range(int(current_price * 0.7), int(current_price * 1.3), 1):
        if level % 5 == 0:
            if level < current_price:
                supports.append(float(level))
            elif level > current_price:
                resistances.append(float(level))

    supports = sorted(set(s for s in supports if s < current_price))
    resistances = sorted(set(r for r in resistances if r > current_price))

    return {"supports": supports[-5:], "resistances": resistances[:5]}


def assess_trend(df: pd.DataFrame, current_price: float) -> dict:
    """Evaluate trend from latest indicator values."""
    latest = df.iloc[-1]
    signals = []

    if current_price > latest["SMA_20"]:
        signals.append("+SMA20")
    else:
        signals.append("-SMA20")
    if current_price > latest["SMA_50"]:
        signals.append("+SMA50")
    else:
        signals.append("-SMA50")
    if latest["MACD_Hist"] > 0:
        signals.append("+MACD")
    else:
        signals.append("-MACD")
    if latest["RSI"] > 50:
        signals.append("+RSI")
    else:
        signals.append("-RSI")

    bullish = sum(1 for s in signals if s.startswith("+"))
    trend = "BULLISH" if bullish >= 3 else "BEARISH" if bullish <= 1 else "NEUTRAL"

    return {"trend": trend, "signals": signals, "bullish_count": bullish, "total": len(signals)}


def full_technical_analysis(ticker: str, data_provider) -> dict:
    """Run complete technical analysis for a ticker."""
    hist = data_provider.get_history(ticker, "6mo")
    if hist.empty:
        return {"error": f"No data for {ticker}"}

    current_price = float(hist["Close"].iloc[-1])
    df = compute_indicators(hist)
    sr = find_support_resistance(hist, current_price)
    trend = assess_trend(df, current_price)
    latest = df.iloc[-1]

    return {
        "ticker": ticker,
        "df": df,
        "current_price": current_price,
        "sma_20": float(latest["SMA_20"]),
        "sma_50": float(latest["SMA_50"]),
        "ema_12": float(latest["EMA_12"]),
        "ema_26": float(latest["EMA_26"]),
        "macd": float(latest["MACD"]),
        "macd_signal": float(latest["Signal"]),
        "macd_hist": float(latest["MACD_Hist"]),
        "rsi": float(latest["RSI"]),
        "bb_upper": float(latest["BB_Upper"]),
        "bb_lower": float(latest["BB_Lower"]),
        "atr": float(latest["ATR_14"]),
        "hist_vol": float(latest["Hist_Vol_20d"]) if pd.notna(latest["Hist_Vol_20d"]) else 0.5,
        "supports": sr["supports"],
        "resistances": sr["resistances"],
        "trend": trend["trend"],
        "trend_signals": trend["signals"],
        "trend_bullish": trend["bullish_count"],
        "trend_total": trend["total"],
    }
