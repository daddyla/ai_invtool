"""Sentiment analysis — financial news scoring via keyword lexicon."""

import re
from datetime import datetime, timezone

# Financial sentiment lexicon: word -> score (-1.0 to +1.0)
POSITIVE_TERMS = {
    "surge": 0.8, "surges": 0.8, "soar": 0.9, "soars": 0.9, "rally": 0.7,
    "rallies": 0.7, "jump": 0.6, "jumps": 0.6, "gain": 0.5, "gains": 0.5,
    "rise": 0.4, "rises": 0.4, "climb": 0.5, "climbs": 0.5, "up": 0.2,
    "bull": 0.6, "bullish": 0.7, "upgrade": 0.7, "upgraded": 0.7,
    "outperform": 0.6, "overweight": 0.5, "buy": 0.5,
    "beat": 0.6, "beats": 0.6, "exceed": 0.6, "exceeds": 0.6,
    "record": 0.5, "high": 0.3, "profit": 0.5, "profitable": 0.5,
    "growth": 0.5, "growing": 0.4, "expand": 0.4, "expansion": 0.4,
    "strong": 0.5, "strength": 0.4, "momentum": 0.4, "breakout": 0.7,
    "boom": 0.7, "recover": 0.5, "recovery": 0.5, "rebound": 0.6,
    "optimistic": 0.5, "positive": 0.4, "upside": 0.5, "opportunity": 0.3,
    "dividend": 0.3, "innovation": 0.4, "breakthrough": 0.6,
    "outpace": 0.5, "accelerate": 0.5, "accelerating": 0.5,
    "revenue": 0.2, "earnings": 0.2, "beat": 0.6,
}

NEGATIVE_TERMS = {
    "crash": -0.9, "crashes": -0.9, "plunge": -0.8, "plunges": -0.8,
    "tank": -0.7, "tanks": -0.7, "tumble": -0.7, "tumbles": -0.7,
    "drop": -0.5, "drops": -0.5, "fall": -0.5, "falls": -0.5,
    "decline": -0.5, "declines": -0.5, "slide": -0.5, "slides": -0.5,
    "slip": -0.4, "slips": -0.4, "down": -0.2, "low": -0.3,
    "bear": -0.6, "bearish": -0.7, "downgrade": -0.7, "downgraded": -0.7,
    "underperform": -0.6, "underweight": -0.5, "sell": -0.5,
    "miss": -0.6, "misses": -0.6, "missed": -0.6,
    "loss": -0.5, "losses": -0.5, "losing": -0.4, "lose": -0.4,
    "weak": -0.5, "weakness": -0.4, "risk": -0.3, "risky": -0.4,
    "recession": -0.7, "downturn": -0.6, "slowdown": -0.5,
    "layoff": -0.5, "layoffs": -0.5, "cut": -0.3, "cuts": -0.3,
    "warning": -0.5, "warn": -0.4, "warns": -0.4, "concern": -0.3,
    "volatile": -0.3, "volatility": -0.2, "uncertainty": -0.4,
    "debt": -0.3, "lawsuit": -0.4, "fraud": -0.8, "scandal": -0.7,
    "bankruptcy": -0.9, "default": -0.7, "overvalued": -0.5,
    "selloff": -0.6, "sell-off": -0.6, "correction": -0.4,
    "inflation": -0.3, "tariff": -0.4, "tariffs": -0.4,
}

LEXICON = {**POSITIVE_TERMS, **NEGATIVE_TERMS}


def _score_text(text: str) -> float:
    """Score a headline using the financial lexicon. Returns -1.0 to +1.0."""
    words = re.findall(r'\b[a-z]+\b', text.lower())
    if not words:
        return 0.0
    scores = [LEXICON[w] for w in words if w in LEXICON]
    if not scores:
        return 0.0
    return max(-1.0, min(1.0, sum(scores) / max(len(scores), 1)))


def analyze_sentiment(ticker: str, data_provider) -> dict:
    """Analyze news sentiment for a ticker using yfinance news + keyword lexicon."""
    ticker = ticker.upper()
    t = data_provider.get_ticker(ticker)

    headlines = []
    try:
        news = t.news or []
    except Exception:
        news = []

    for item in news[:20]:
        # Handle both old and new yfinance news formats
        content = item.get("content", item)  # new format nests under "content"
        title = content.get("title", item.get("title", ""))
        if not title:
            continue
        score = _score_text(title)

        # Parse date
        pub_date = ""
        if "pubDate" in content:
            try:
                pub_date = content["pubDate"][:16].replace("T", " ")
            except Exception:
                pass
        elif "providerPublishTime" in item:
            try:
                pub_date = datetime.fromtimestamp(
                    item["providerPublishTime"], tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        # Parse source
        provider = content.get("provider", {})
        source = (provider.get("displayName", "") if isinstance(provider, dict)
                  else item.get("publisher", item.get("source", "")))

        # Parse URL
        url_obj = content.get("canonicalUrl", content.get("clickThroughUrl", {}))
        url = url_obj.get("url", "") if isinstance(url_obj, dict) else item.get("link", "")

        headlines.append({
            "title": title,
            "score": round(score, 3),
            "source": source,
            "date": pub_date,
            "url": url,
        })

    bullish = [h for h in headlines if h["score"] > 0.1]
    bearish = [h for h in headlines if h["score"] < -0.1]
    neutral = [h for h in headlines if -0.1 <= h["score"] <= 0.1]

    if headlines:
        overall = sum(h["score"] for h in headlines) / len(headlines)
    else:
        overall = 0.0

    if overall > 0.15:
        label = "BULLISH"
    elif overall < -0.15:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    return {
        "ticker": ticker,
        "overall_score": round(overall, 3),
        "label": label,
        "bullish_count": len(bullish),
        "bearish_count": len(bearish),
        "neutral_count": len(neutral),
        "total_articles": len(headlines),
        "headlines": headlines,
    }
