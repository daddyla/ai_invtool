"""Menu 12: Web News."""
from invtool.cli.common import ask_ticker
from invtool.ui.display import console
from invtool.ui.prompt import select, text


def run(data):
    from invtool.market.webcrawler import (
        crawl_market_news,
        fetch_article_content,
        search_financial_news,
        ticker_news_crawl,
    )
    from invtool.ui.display import print_article_content, print_news_headlines

    choice = select("Web News", [
        ("Market Headlines (Reuters, CNBC, MarketWatch, Yahoo, Benzinga)", "headlines"),
        ("Stock News (by ticker)", "ticker"),
        ("Topic Search (e.g. 'Fed rate cut', 'AI stocks')", "search"),
        ("Read Full Article (paste URL)", "article"),
        ("Back", "back"),
    ])
    if not choice or choice == "back":
        return

    if choice == "headlines":
        console.print("[dim]Crawling news sources...[/]")
        result = crawl_market_news()
        print_news_headlines(result)

    elif choice == "ticker":
        ticker = ask_ticker()
        console.print(f"[dim]Fetching news for {ticker}...[/]")
        result = ticker_news_crawl(ticker)
        print_news_headlines(result)

    elif choice == "search":
        query = text("Search query:", default="Federal Reserve interest rates")
        if query:
            console.print(f"[dim]Searching: {query}...[/]")
            result = search_financial_news(query)
            print_news_headlines(result)

    elif choice == "article":
        url = text("Article URL:")
        if url and url.startswith("http"):
            console.print("[dim]Fetching article...[/]")
            result = fetch_article_content(url)
            print_article_content(result)
