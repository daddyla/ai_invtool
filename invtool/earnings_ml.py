"""Earnings prediction — ML-based beat/miss and sell-the-news probability."""

import numpy as np
from invtool.earnings import get_earnings_dates, analyze_earnings_windows


def predict_earnings(ticker: str, data_provider) -> dict:
    """Predict earnings outcomes using statistical features + logistic regression."""
    ticker = ticker.upper()

    # Get earnings history
    earnings = get_earnings_dates(ticker, data_provider)
    if not earnings or len(earnings) < 4:
        return {"ticker": ticker, "error": "Need at least 4 quarters of earnings data"}

    hist = data_provider.get_history(ticker, "3y")
    if hist.empty:
        return {"ticker": ticker, "error": "No price history available"}

    # Analyze historical windows
    windows_df = analyze_earnings_windows(hist, earnings)
    if windows_df.empty or len(windows_df) < 4:
        return {"ticker": ticker, "error": "Insufficient earnings window data"}

    # Feature engineering
    eps_surprises = windows_df["eps_surprise"].dropna()
    rev_surprises = windows_df["rev_surprise"].dropna() if "rev_surprise" in windows_df.columns else None

    # Historical beat rate
    beat_rate = float((eps_surprises > 0).mean()) if len(eps_surprises) > 0 else 0.5

    # Average surprise magnitude
    avg_surprise = float(eps_surprises.mean()) if len(eps_surprises) > 0 else 0

    # Consecutive beats (streak)
    streak = 0
    for s in reversed(eps_surprises.values):
        if s > 0:
            streak += 1
        else:
            break

    # Pre-earnings runup (average 10d pre-earnings return)
    pre_10d = windows_df.get("pre_10d", None)
    avg_pre_runup = float(pre_10d.mean()) if pre_10d is not None and len(pre_10d) > 0 else 0

    # Post-earnings 1d moves
    post_1d = windows_df.get("post_1d", None)
    if post_1d is not None and len(post_1d) > 0:
        avg_post_1d = float(post_1d.mean())
        sell_the_news_rate = float(
            ((eps_surprises > 0) & (post_1d < 0)).sum() / max((eps_surprises > 0).sum(), 1)
        )
    else:
        avg_post_1d = 0
        sell_the_news_rate = 0

    # Current IV rank (proxy: current 20d vol vs 6-month range)
    vol = data_provider.get_hist_vol(ticker, 20)
    hist_6m = data_provider.get_history(ticker, "6mo")
    if len(hist_6m) > 40:
        log_ret = np.log(hist_6m["Close"] / hist_6m["Close"].shift(1)).dropna()
        vol_series = log_ret.rolling(20).std() * np.sqrt(252)
        vol_series = vol_series.dropna()
        if len(vol_series) > 0:
            iv_rank = float((vol_series < vol).mean())
        else:
            iv_rank = 0.5
    else:
        iv_rank = 0.5

    # Try ML prediction with logistic regression
    p_beat = beat_rate  # default to historical rate
    p_sell_news = sell_the_news_rate
    ml_used = False

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        # Build training data from historical quarters
        if len(windows_df) >= 6:
            X_list, y_beat_list, y_stn_list = [], [], []

            for i in range(1, len(windows_df)):
                row = windows_df.iloc[i]
                prev = windows_df.iloc[:i]

                feat = [
                    float(prev["eps_surprise"].mean()),      # historical avg surprise
                    float((prev["eps_surprise"] > 0).mean()), # historical beat rate
                    float(row.get("pre_10d", 0) or 0),       # pre-earnings runup
                    iv_rank,                                   # vol rank
                    float(len(prev)),                          # quarters of history
                ]
                X_list.append(feat)
                y_beat_list.append(1 if row["eps_surprise"] > 0 else 0)
                post = row.get("post_1d", 0)
                y_stn_list.append(1 if (row["eps_surprise"] > 0 and (post or 0) < 0) else 0)

            X = np.array(X_list)
            y_beat = np.array(y_beat_list)
            y_stn = np.array(y_stn_list)

            if len(set(y_beat)) > 1:
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)

                # Train beat predictor
                lr_beat = LogisticRegression(random_state=42, max_iter=200)
                lr_beat.fit(X_scaled, y_beat)

                # Predict next quarter
                next_feat = np.array([[
                    float(eps_surprises.mean()),
                    beat_rate,
                    avg_pre_runup,
                    iv_rank,
                    float(len(windows_df)),
                ]])
                next_scaled = scaler.transform(next_feat)
                p_beat = float(lr_beat.predict_proba(next_scaled)[0, 1])
                ml_used = True

            if len(set(y_stn)) > 1 and ml_used:
                lr_stn = LogisticRegression(random_state=42, max_iter=200)
                lr_stn.fit(X_scaled, y_stn)
                p_sell_news = float(lr_stn.predict_proba(next_scaled)[0, 1])
    except ImportError:
        pass
    except Exception:
        pass

    # Expected post-earnings move
    if post_1d is not None and len(post_1d) > 0:
        recent_moves = post_1d.tail(6)
        expected_move = float(recent_moves.mean())
        move_std = float(recent_moves.std())
    else:
        expected_move = 0
        move_std = 0

    # Recommendation
    if p_beat > 0.7 and p_sell_news < 0.4:
        recommendation = "HOLD THROUGH — High beat probability, low sell-the-news risk"
    elif p_beat > 0.7 and p_sell_news > 0.5:
        recommendation = "TRIM PRE-EARNINGS — Likely beat but sell-the-news pattern expected"
    elif p_beat < 0.4:
        recommendation = "HEDGE / REDUCE — Elevated miss risk; consider protective puts"
    else:
        recommendation = "NEUTRAL — Hold current position; consider hedging with options"

    confidence = "HIGH" if ml_used and len(windows_df) >= 8 else "MEDIUM" if len(windows_df) >= 5 else "LOW"

    return {
        "ticker": ticker,
        "p_beat": round(p_beat, 3),
        "p_sell_the_news": round(p_sell_news, 3),
        "expected_move": round(expected_move * 100, 2),
        "move_std": round(move_std * 100, 2),
        "confidence": confidence,
        "ml_used": ml_used,
        "recommendation": recommendation,
        "features": {
            "historical_beat_rate": round(beat_rate, 3),
            "avg_eps_surprise": round(avg_surprise * 100, 2),
            "consecutive_beats": streak,
            "avg_pre_10d_runup": round(avg_pre_runup * 100, 2),
            "avg_post_1d_move": round(avg_post_1d * 100, 2),
            "iv_rank": round(iv_rank, 2),
            "quarters_analyzed": len(windows_df),
        },
    }
