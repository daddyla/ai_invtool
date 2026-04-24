"""Conversation loop — the interactive chat front-end for the Claude agent."""
import json
import os
import traceback

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner

from invtool.agent.handlers import _handle_tool, set_data_provider
from invtool.agent.tools import TOOL_DEFINITIONS

console = Console()

_SDK_AVAILABLE = False
try:
    import anthropic
    _SDK_AVAILABLE = True
except ImportError:
    pass


AGENT_SYSTEM_PROMPT = """You are an expert senior investment analyst assistant. You have access to tools for:
- Real-time stock prices and market data
- Technical analysis (SMA, RSI, MACD, Bollinger Bands, ATR, support/resistance)
- Options screening (sell puts, covered calls, wheel strategy)
- Earnings behavior analysis (pre/post patterns, sell-the-news detection)
- Portfolio tracking (P&L, allocation, per-position strategies)
- Tax-loss harvesting identification
- Chart generation

AI Analytics tools:
- Sentiment analysis (news headline scoring)
- Price forecasting (trend extrapolation with confidence bands)
- Market regime detection (trending/mean-reverting/high-volatility + strategy recommendations)
- Anomaly detection (volume spikes, price gaps, volatility changes)
- Monte Carlo risk simulation (VaR, CVaR, probability of loss)
- Earnings prediction (ML-based beat/miss probability)
- Portfolio optimization (Markowitz efficient frontier, optimal weights)
- Correlation & clustering (diversification score, K-means grouping)

Market Intelligence tools:
- Earnings calendar (which stocks report today/tomorrow/this week)
- Market movers (top gainers, losers, most active)
- Sector performance (all 11 S&P sectors via ETFs)
- Analyst ratings (consensus, price targets, upgrades/downgrades)
- Insider activity (insider buys/sells, net sentiment)
- Economic calendar (CPI, jobs, GDP, FOMC events)

Web News tools:
- crawl_market_news: Live headlines from Reuters, CNBC, MarketWatch, Yahoo Finance, Benzinga
- ticker_news_crawl: Recent news specifically about a stock ticker
- search_financial_news: Search news by topic ("Fed rate cut", "AI chip demand")
- fetch_article_content: Read the full text of any article from its URL

When answering questions:
1. Always use tools to fetch real data — never make up numbers
2. Present data in clear tables and summaries
3. Include specific numbers (prices, returns, probabilities)
4. Give actionable recommendations with rationale
5. Warn about risks when appropriate
6. Use markdown formatting for readability

The user's portfolio contains: TMF (36 shares @ $45.29), JEPQ (20 @ $53.70),
BLSH (11 @ $37.00), FIG (11 @ $133.00), DOCS (6 @ $41.00).
"""


def _run_conversation(client, messages: list) -> str:
    """Run a multi-turn conversation with tool use, return final text."""
    while True:
        with Live(Spinner("dots", text="[dim]Thinking...[/]"), console=console, transient=True):
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=AGENT_SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        if response.stop_reason == "end_turn" or not tool_calls:
            return "\n".join(text_parts)

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            console.print(f"  [dim]Calling {tc.name}({json.dumps(tc.input, default=str)[:80]})...[/]")
            try:
                result_str = _handle_tool(tc.name, tc.input)
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
                console.print(f"  [red]Tool error: {e}[/]")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})


def check_api_key() -> bool:
    """Check if ANTHROPIC_API_KEY is set (loads .env first)."""
    from dotenv import load_dotenv
    load_dotenv()
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _save_response(result_text: str):
    """Prompt user to save the last AI response to a file."""
    from datetime import datetime

    from invtool.config import REPORTS_DIR
    from invtool.ui.prompt import text as prompt_text

    filename = prompt_text("Filename (without extension):", default=f"ai_response_{datetime.now().strftime('%Y%m%d')}")
    if not filename:
        return
    filename = filename.strip().replace(" ", "_")
    for ch in '<>:"/\\|?*':
        filename = filename.replace(ch, "")

    fmt = prompt_text("Format (md/txt):", default="md")
    ext = ".txt" if fmt.strip().lower() == "txt" else ".md"
    filepath = REPORTS_DIR / f"{filename}{ext}"

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            if ext == ".txt":
                import re
                plain = result_text
                plain = re.sub(r'#{1,6}\s+', '', plain)
                plain = re.sub(r'\*\*(.+?)\*\*', r'\1', plain)
                plain = re.sub(r'\*(.+?)\*', r'\1', plain)
                plain = re.sub(r'`(.+?)`', r'\1', plain)
                f.write(plain)
            else:
                f.write(result_text)
        console.print(f"[green]Saved to: {filepath}[/]")
    except Exception as e:
        console.print(f"[red]Failed to save: {e}[/]")


def ai_chat_loop(data_provider):
    """Interactive AI chat loop."""
    if not _SDK_AVAILABLE:
        console.print(Panel(
            "[red]anthropic SDK is not installed.[/]\n\n"
            "Install with: [bold]pip install anthropic[/]",
            title="AI Agent Unavailable",
            border_style="red",
        ))
        return

    if not check_api_key():
        console.print(Panel(
            "[red]ANTHROPIC_API_KEY environment variable not set.[/]\n\n"
            "Add to .env file:\n"
            "  [bold]ANTHROPIC_API_KEY=sk-ant-...[/]",
            title="API Key Required",
            border_style="red",
        ))
        return

    set_data_provider(data_provider)
    client = anthropic.Anthropic()
    messages = []

    console.print(Panel(
        "Ask me anything about stocks, options, earnings, or your portfolio.\n"
        "Type [bold]save[/] to save the last response to a file.\n"
        "Type [bold]back[/] to return to the menu.",
        title="[bold blue]AI Investment Analyst[/]",
        border_style="blue",
    ))

    from invtool.ui.prompt import text as prompt_text

    last_result = None

    while True:
        user_input = prompt_text("You:")
        if user_input is None or user_input.lower().strip() in ("back", "quit", "exit", "q"):
            break
        if not user_input.strip():
            continue

        if user_input.strip().lower() == "save":
            if last_result:
                _save_response(last_result)
            else:
                console.print("[yellow]No response to save yet.[/]")
            continue

        messages.append({"role": "user", "content": user_input})

        console.print()
        try:
            result_text = _run_conversation(client, messages)
            if result_text:
                messages.append({"role": "assistant", "content": result_text})
                console.print(Markdown(result_text))
                console.print()
                last_result = result_text
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
            console.print(f"[dim]{traceback.format_exc()}[/]")
