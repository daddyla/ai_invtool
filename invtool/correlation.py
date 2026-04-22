"""Correlation analysis & K-means clustering."""

import numpy as np
import pandas as pd


def analyze_correlations(data_provider, tickers: list) -> dict:
    """Compute correlation matrix and cluster tickers by return patterns."""
    tickers = [t.upper() for t in tickers]

    # Fetch returns
    returns_data = {}
    for t in tickers:
        hist = data_provider.get_history(t, "6mo")
        if hist.empty or len(hist) < 20:
            continue
        returns_data[t] = hist["Close"].pct_change().dropna()

    valid_tickers = list(returns_data.keys())
    if len(valid_tickers) < 2:
        return {"error": "Need at least 2 tickers with valid data",
                "tickers": valid_tickers}

    # Align to common dates
    returns_df = pd.DataFrame(returns_data).dropna()
    if len(returns_df) < 10:
        return {"error": "Insufficient overlapping data", "tickers": valid_tickers}

    # Correlation matrix
    corr_matrix = returns_df.corr()

    # High correlation pairs
    high_corr_pairs = []
    for i, t1 in enumerate(valid_tickers):
        for j, t2 in enumerate(valid_tickers):
            if i < j:
                corr = float(corr_matrix.loc[t1, t2])
                if abs(corr) > 0.5:
                    high_corr_pairs.append({
                        "ticker1": t1, "ticker2": t2,
                        "correlation": round(corr, 3),
                    })
    high_corr_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    # K-means clustering
    clusters = []
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import silhouette_score

        # Feature matrix: use return statistics per ticker
        features = []
        for t in valid_tickers:
            r = returns_df[t]
            features.append([
                r.mean(), r.std(), r.skew(), r.kurt(),
                r.min(), r.max(), (r > 0).mean(),
            ])
        X = StandardScaler().fit_transform(features)

        # Find optimal k (2 to min(5, n-1))
        max_k = min(5, len(valid_tickers) - 1)
        if max_k >= 2:
            best_k, best_score = 2, -1
            for k in range(2, max_k + 1):
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = km.fit_predict(X)
                score = silhouette_score(X, labels) if len(set(labels)) > 1 else -1
                if score > best_score:
                    best_k, best_score = k, score

            km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            labels = km.fit_predict(X)

            for c_id in range(best_k):
                members = [valid_tickers[i] for i, l in enumerate(labels) if l == c_id]
                if len(members) > 1:
                    sub_corr = corr_matrix.loc[members, members]
                    mask = np.triu(np.ones_like(sub_corr, dtype=bool), k=1)
                    avg_corr = float(sub_corr.where(mask).mean().mean())
                else:
                    avg_corr = 1.0
                clusters.append({
                    "id": c_id,
                    "tickers": members,
                    "avg_internal_corr": round(avg_corr, 3) if not np.isnan(avg_corr) else 1.0,
                })
        else:
            clusters = [{"id": 0, "tickers": valid_tickers, "avg_internal_corr": 1.0}]
    except ImportError:
        # Fallback: no clustering if scikit-learn missing
        clusters = [{"id": 0, "tickers": valid_tickers, "avg_internal_corr": 1.0}]

    # Diversification score (1 - avg absolute pairwise correlation)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    avg_corr_all = float(corr_matrix.abs().where(mask).mean().mean())
    diversification_score = round(1 - avg_corr_all, 3) if not np.isnan(avg_corr_all) else 0.5

    return {
        "tickers": valid_tickers,
        "corr_matrix": corr_matrix.round(3).to_dict(),
        "corr_matrix_list": corr_matrix.round(3).values.tolist(),
        "high_corr_pairs": high_corr_pairs,
        "clusters": clusters,
        "diversification_score": diversification_score,
        "n_observations": len(returns_df),
    }
