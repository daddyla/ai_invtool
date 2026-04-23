"""Web crawler for market news — RSS feeds + article content extraction."""

import re
import warnings
from datetime import datetime
from urllib.parse import quote_plus

warnings.filterwarnings("ignore")

# ── News Source Registry ──

NEWS_SOURCES = {
    "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
    "reuters_finance":  "https://feeds.reuters.com/news/wealth",
    "cnbc_top":         "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "cnbc_markets":     "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "marketwatch":      "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "marketwatch_mkts": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
    "yahoo_finance":    "https://finance.yahoo.com/news/rssindex",
    "wsj_markets":      "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "benzinga":         "https://www.benzinga.com/feed",
    "seeking_alpha":    "https://seekingalpha.com/feed.xml",
    "investing_com":    "https://www.investing.com/rss/news_301.rss",
}

DEFAULT_SOURCES = ["reuters_business", "cnbc_top", "cnbc_markets",
                   "marketwatch", "yahoo_finance", "benzinga"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# ── RSS Feed Fetcher ──

def fetch_rss_feed(feed_url: str, max_items: int = 20) -> list:
    """Fetch and parse an RSS feed. Returns list of article dicts."""
    import feedparser
    import requests

    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception:
        try:
            feed = feedparser.parse(feed_url)
        except Exception:
            return []

    if not feed.entries:
        return []

    articles = []
    for entry in feed.entries[:max_items]:
        # Parse date
        pub_date = ""
        for attr in ("published_parsed", "updated_parsed"):
            val = getattr(entry, attr, None)
            if val:
                try:
                    pub_date = datetime(*val[:6]).strftime("%Y-%m-%d %H:%M")
                    break
                except Exception:
                    pass

        # Clean summary
        summary = ""
        if hasattr(entry, "summary"):
            summary = re.sub(r"<[^>]+>", "", entry.summary or "").strip()[:400]

        source_name = ""
        try:
            source_name = feed.feed.get("title", "") or feed_url.split("/")[2]
        except Exception:
            source_name = feed_url.split("/")[2] if "/" in feed_url else feed_url

        articles.append({
            "title":   getattr(entry, "title", "").strip(),
            "url":     getattr(entry, "link", ""),
            "date":    pub_date,
            "source":  source_name,
            "summary": summary,
        })

    return articles


# ── Ticker-Specific News ──

def ticker_news_crawl(ticker: str, max_results: int = 15) -> dict:
    """Fetch recent news for a specific stock ticker.

    Sources: Yahoo Finance RSS (ticker-specific) + Google News RSS.
    Returns: {ticker, articles: [{title, url, date, source, summary}], total}
    """
    ticker = ticker.upper().strip()

    # Yahoo Finance ticker RSS (most relevant)
    yf_url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
    yf_articles = fetch_rss_feed(yf_url, max_items=max_results)

    # Google News for ticker symbol
    encoded = quote_plus(f"{ticker} stock")
    google_url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
    google_articles = fetch_rss_feed(google_url, max_items=10)

    # Merge, deduplicate by title
    all_articles = yf_articles[:]
    seen = {re.sub(r"\W+", " ", a["title"]).lower().strip() for a in yf_articles}
    for a in google_articles:
        t = re.sub(r"\W+", " ", a["title"]).lower().strip()
        if t and t not in seen:
            seen.add(t)
            all_articles.append(a)

    all_articles = all_articles[:max_results]

    return {
        "ticker":   ticker,
        "articles": all_articles,
        "total":    len(all_articles),
    }


# ── Market-Wide News Crawl ──

def crawl_market_news(sources: list = None, max_per_source: int = 8) -> dict:
    """Crawl multiple RSS news sources and return aggregated, deduplicated headlines.

    Args:
        sources: List of keys from NEWS_SOURCES (default: top 6 financial sources)
        max_per_source: Max articles per source
    Returns: {articles: [...], total, sources_fetched, errors}
    """
    if sources is None:
        sources = DEFAULT_SOURCES

    all_articles = []
    errors = []

    for src in sources:
        url = NEWS_SOURCES.get(src)
        if not url:
            errors.append(f"Unknown source: {src}")
            continue
        try:
            arts = fetch_rss_feed(url, max_items=max_per_source)
            for a in arts:
                a["feed_key"] = src
            all_articles.extend(arts)
        except Exception as e:
            errors.append(f"{src}: {e}")

    # Sort newest first
    all_articles.sort(key=lambda a: a.get("date") or "", reverse=True)

    # Deduplicate by normalized title
    seen = set()
    deduped = []
    for a in all_articles:
        t = re.sub(r"\W+", " ", a.get("title", "")).lower().strip()
        if t and t not in seen:
            seen.add(t)
            deduped.append(a)

    return {
        "articles":       deduped,
        "total":          len(deduped),
        "sources_fetched": len(sources) - len(errors),
        "errors":         errors,
    }


# ── Topic / Query Search ──

def search_financial_news(query: str, max_results: int = 15) -> dict:
    """Search financial news by topic or keyword via Google News RSS.

    Args:
        query: Search term, e.g. "Fed rate cut", "AI chip stocks", "NVDA earnings"
        max_results: Max articles to return
    Returns: {query, articles: [...], total}
    """
    encoded = quote_plus(f"{query} finance market")
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
    articles = fetch_rss_feed(url, max_items=max_results)

    return {
        "query":    query,
        "articles": articles,
        "total":    len(articles),
    }


# ── Article Content Extraction ──

def fetch_article_content(url: str, max_chars: int = 5000) -> dict:
    """Fetch and extract clean text from a news article URL.

    Uses trafilatura for best content extraction (newspaper-quality),
    falls back to BeautifulSoup paragraph extraction.

    Returns: {url, title, content, word_count, success}
    """
    import requests

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        return {"url": url, "title": "", "content": f"Fetch failed: {e}",
                "word_count": 0, "success": False}

    content = ""
    title = ""

    # 1. Try trafilatura (best quality)
    try:
        import trafilatura
        result = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
            no_fallback=False,
        )
        if result and len(result.strip()) > 150:
            content = result.strip()
    except Exception:
        pass

    # 2. Fallback: BeautifulSoup
    if not content:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Title
            t = soup.find("title")
            if t:
                title = t.get_text().strip()

            # Remove noise tags
            for tag in soup(["script", "style", "nav", "footer", "header",
                             "aside", "iframe", "noscript", "form", "button"]):
                tag.decompose()

            # Prefer <article> tag, else collect all <p>
            article_tag = soup.find("article")
            if article_tag:
                content = article_tag.get_text(separator=" ", strip=True)
            else:
                paras = soup.find_all("p")
                content = " ".join(
                    p.get_text(strip=True) for p in paras
                    if len(p.get_text(strip=True)) > 40
                )
        except Exception as e:
            return {"url": url, "title": title, "content": f"Parse failed: {e}",
                    "word_count": 0, "success": False}

    # Extract title if not yet found
    if not title:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            t = soup.find("title")
            if t:
                title = t.get_text().strip()
        except Exception:
            pass

    # Clean whitespace
    content = re.sub(r"\s+", " ", content).strip()
    word_count = len(content.split())

    # Truncate
    if len(content) > max_chars:
        content = content[:max_chars] + "..."

    return {
        "url":        url,
        "title":      title,
        "content":    content,
        "word_count": word_count,
        "success":    bool(content and word_count > 30),
    }
