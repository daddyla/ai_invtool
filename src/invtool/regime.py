"""Market regime detection — classify regime and recommend strategies."""

import numpy as np
from invtool.technical import compute_indicators


# Regime → strategy mapping
STRATEGY_MAP = {
    "TRENDING_UP": [
        {"name": "SELL COVERED CALLS", "rationale": "Capture premium while riding uptrend; set strikes above resistance"},
        {"name": "BUY CALL SPREADS", "rationale": "Leverage uptrend with defined risk; use debit spreads"},
        {"name": "SELL OTM PUTS", "rationale": "High prob OTM in uptrend; collect premium on pullbacks"},
    ],
    "TRENDING_DOWN": [
        {"name": "SELL PUT SPREADS", "rationale": "Defined risk bearish play; credit spread below support"},
        {"name": "BUY PROTECTIVE PUTS", "rationale": "Hedge existing long positions against further decline"},
        {"name": "AVOID SELLING NAKED PUTS", "rationale": "High risk of assignment in downtrend"},
    ],
    "MEAN_REVERTING": [
        {"name": "IRON CONDORS", "rationale": "Range-bound = ideal for selling both sides; collect premium"},
        {"name": "SELL STRANGLES", "rationale": "Profit from time decay in sideways market"},
        {"name": "WHEEL STRATEGY", "rationale": "Sell puts at support, calls at resistance; repeat"},
    ],
    "HIGH_VOLATILITY": [
        {"name": "SELL PREMIUM (PUTS)", "rationale": "Elevated IV = fat premiums; sell puts for income"},
        {"name": "IRON BUTTERFLIES", "rationale": "Profit from vol crush; defined risk neutral strategy"},
        {"name": "WAIT / REDUCE SIZE", "rationale": "High vol = big swings; smaller positions reduce risk"},
    ],
}


def detect_regime(ticker: str, data_provider) -> dict:
    """Detect market regime for a ticker."""
    ticker = ticker.upper()
    hist = data_provider.get_history(ticker, "6mo")

    if hist.empty or len(hist) < 50:
        return {"ticker": ticker, "error": "Insufficient data (need 50+ trading days)"}

    df = compute_indicators(hist)
    last = df.iloc[-1]
    current_price = float(last["Close"])

    signals = []
    scores = {"TRENDING_UP": 0, "TRENDING_DOWN": 0, "MEAN_REVERTING": 0, "HIGH_VOLATILITY": 0}

    # 1. SMA crossover
    sma_20 = float(last["SMA_20"]) if "SMA_20" in df.columns else current_price
    sma_50 = float(last["SMA_50"]) if "SMA_50" in df.columns else current_price

    if current_price > sma_20 > sma_50:
        signals.append("+SMA_BULLISH_STACK")
        scores["TRENDING_UP"] += 2
    elif current_price < sma_20 < sma_50:
        signals.append("-SMA_BEARISH_STACK")
        scores["TRENDING_DOWN"] += 2
    else:
        signals.append("~SMA_MIXED")
        scores["MEAN_REVERTING"] += 1

    # 2. RSI positioning
    rsi = float(last["RSI"]) if "RSI" in df.columns else 50
    if rsi > 60:
        signals.append(f"+RSI_HIGH({rsi:.0f})")
        scores["TRENDING_UP"] += 1
    elif rsi < 40:
        signals.append(f"-RSI_LOW({rsi:.0f})")
        scores["TRENDING_DOWN"] += 1
    else:
        signals.append(f"~RSI_NEUTRAL({rsi:.0f})")
        scores["MEAN_REVERTING"] += 1

    # 3. MACD direction
    macd = float(last.get("MACD", 0))
    macd_signal = float(last.get("Signal", 0))
    if macd > macd_signal and macd > 0:
        signals.append("+MACD_BULLISH")
        scores["TRENDING_UP"] += 1
    elif macd < macd_signal and macd < 0:
        signals.append("-MACD_BEARISH")
        scores["TRENDING_DOWN"] += 1
    else:
        signals.append("~MACD_TRANSITIONING")
        scores["MEAN_REVERTING"] += 1

    # 4. Volatility percentile
    hist_vol = float(last.get("Hist_Vol_20d", 0.3)) if "Hist_Vol_20d" in df.columns else 0.3
    vol_series = df["Hist_Vol_20d"].dropna() if "Hist_Vol_20d" in df.columns else None
    if vol_series is not None and len(vol_series) > 20:
        vol_pctile = float((vol_series < hist_vol).mean())
    else:
        vol_pctile = 0.5

    if vol_pctile > 0.80:
        signals.append(f"+VOL_HIGH(p{vol_pctile:.0%})")
        scores["HIGH_VOLATILITY"] += 2
    elif vol_pctile < 0.20:
        signals.append(f"-VOL_LOW(p{vol_pctile:.0%})")
        scores["MEAN_REVERTING"] += 1
    else:
        signals.append(f"~VOL_NORMAL(p{vol_pctile:.0%})")

    # 5. Trend strength — price distance from SMA50
    distance = (current_price - sma_50) / sma_50 if sma_50 > 0 else 0
    if abs(distance) > 0.10:
        if distance > 0:
            signals.append(f"+STRONG_TREND_UP({distance:+.1%})")
            scores["TRENDING_UP"] += 1
        else:
            signals.append(f"-STRONG_TREND_DOWN({distance:+.1%})")
            scores["TRENDING_DOWN"] += 1
    else:
        signals.append(f"~RANGE_BOUND({distance:+.1%})")
        scores["MEAN_REVERTING"] += 1

    # 6. Bollinger Band position
    bb_upper = float(last.get("BB_Upper", current_price * 1.05))
    bb_lower = float(last.get("BB_Lower", current_price * 0.95))
    bb_width = (bb_upper - bb_lower) / current_price if current_price > 0 else 0
    bb_pct = (current_price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5

    if bb_pct > 0.8:
        signals.append("+BB_UPPER_BAND")
        scores["TRENDING_UP"] += 1
    elif bb_pct < 0.2:
        signals.append("-BB_LOWER_BAND")
        scores["TRENDING_DOWN"] += 1

    # Determine winning regime
    regime = max(scores, key=scores.get)
    total_score = sum(scores.values())
    confidence = scores[regime] / total_score if total_score > 0 else 0

    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "regime": regime,
        "confidence": round(confidence, 2),
        "scores": scores,
        "signals": signals,
        "recommended_strategies": STRATEGY_MAP.get(regime, []),
        "vol_percentile": round(vol_pctile, 2),
        "hist_vol": round(hist_vol, 4),
        "rsi": round(rsi, 1),
        "sma_20": round(sma_20, 2),
        "sma_50": round(sma_50, 2),
    }
