"""Deep Research Agent — Dexter-inspired iterative research with skills, validation, and logging."""

import os
import json
import traceback
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich import box

console = Console()

# Lazy-import
_SDK_AVAILABLE = False
try:
    import anthropic
    _SDK_AVAILABLE = True
except ImportError:
    pass


# ── Skills Registry ──

SKILLS = {
    "full_stock_analysis": {
        "name": "Full Stock Analysis",
        "description": "Comprehensive analysis: technicals + sentiment + regime + analysts + insiders + forecast",
        "required_inputs": ["ticker"],
        "steps": [
            "Get current price and basic info for {ticker}",
            "Run full technical analysis for {ticker}",
            "Analyze news sentiment for {ticker}",
            "Detect market regime and recommended strategies for {ticker}",
            "Get analyst ratings, consensus, and price targets for {ticker}",
            "Check insider trading activity for {ticker}",
            "Generate price forecast with confidence intervals for {ticker}",
            "Check for anomalies (volume spikes, price gaps) in {ticker}",
        ],
        "synthesis": (
            "Provide a comprehensive investment thesis for {ticker} covering:\n"
            "1) Technical outlook (trend, key levels, signals)\n"
            "2) News sentiment (bullish/bearish/neutral)\n"
            "3) Analyst consensus and price targets\n"
            "4) Insider signals (net buying/selling)\n"
            "5) Risk factors and anomalies\n"
            "6) Price target and actionable recommendation"
        ),
    },
    "portfolio_health_check": {
        "name": "Portfolio Health Check",
        "description": "Full portfolio risk assessment: P&L + Monte Carlo + anomalies + correlation + optimization",
        "required_inputs": [],
        "steps": [
            "Get current portfolio summary with P&L for all holdings",
            "Run Monte Carlo risk simulation (VaR, CVaR at 7/30/90 day horizons)",
            "Scan all portfolio holdings for anomalies (volume spikes, gaps, extreme moves)",
            "Analyze correlations between all portfolio holdings",
            "Run portfolio optimization to find optimal weights vs current allocation",
            "Identify tax-loss harvesting opportunities",
        ],
        "synthesis": (
            "Provide a portfolio health report covering:\n"
            "1) Current P&L and allocation breakdown\n"
            "2) Risk exposure (VaR/CVaR at each horizon)\n"
            "3) Diversification score and correlation clusters\n"
            "4) Any anomalies flagged in holdings\n"
            "5) Optimization suggestions (current vs optimal weights)\n"
            "6) Tax-loss harvesting opportunities"
        ),
    },
    "earnings_research": {
        "name": "Earnings Research",
        "description": "Earnings season prep: calendar + ML predictions + historical patterns",
        "required_inputs": ["ticker"],
        "steps": [
            "Get this week's earnings calendar to see upcoming reports",
            "Run ML earnings prediction (beat/miss probability) for {ticker}",
            "Analyze historical earnings behavior and patterns for {ticker}",
            "Get analyst ratings and recent upgrades/downgrades for {ticker}",
            "Detect market regime for {ticker} to assess post-earnings move context",
        ],
        "synthesis": (
            "Provide an earnings research report for {ticker} covering:\n"
            "1) Upcoming earnings date and estimates\n"
            "2) ML-predicted beat probability and sell-the-news probability\n"
            "3) Historical earnings patterns (avg move, beat rate)\n"
            "4) Analyst consensus heading into earnings\n"
            "5) Current market regime context\n"
            "6) Recommended pre-earnings strategy (hold/trade/hedge)"
        ),
    },
    "market_overview": {
        "name": "Market Overview",
        "description": "Daily market briefing: sectors + movers + economic events",
        "required_inputs": [],
        "steps": [
            "Get sector performance for all 11 S&P sectors",
            "Get today's top gainers",
            "Get today's top losers",
            "Get most actively traded stocks today",
            "Get upcoming economic calendar events",
            "Get today's and tomorrow's earnings calendar",
        ],
        "synthesis": (
            "Provide a daily market briefing covering:\n"
            "1) Sector rotation and trends (which sectors lead/lag)\n"
            "2) Notable movers and potential reasons\n"
            "3) Upcoming catalysts (earnings reports, economic data)\n"
            "4) Risk events ahead\n"
            "5) Opportunities to watch"
        ),
    },
    "options_strategy": {
        "name": "Options Strategy Finder",
        "description": "Find optimal options strategy: regime + forecast + puts/calls + wheel",
        "required_inputs": ["ticker"],
        "steps": [
            "Get current price and basic info for {ticker}",
            "Detect market regime for {ticker} to know what strategies work best",
            "Generate price forecast for {ticker} to assess directional bias",
            "Check for anomalies in {ticker} that might affect options pricing",
            "Screen best put options for selling on {ticker}",
            "Screen best call options for selling on {ticker}",
            "Run full wheel strategy analysis for {ticker}",
        ],
        "synthesis": (
            "Recommend an options strategy for {ticker} covering:\n"
            "1) Current regime and what strategy types it favors\n"
            "2) Price forecast direction and magnitude\n"
            "3) Best put to sell (strike, premium, probability OTM)\n"
            "4) Best call to sell (strike, premium, probability OTM)\n"
            "5) Wheel strategy projected monthly income\n"
            "6) Key risks and position sizing guidance"
        ),
    },
    "market_news_deep_dive": {
        "name": "Market News Deep Dive",
        "description": "Crawl live news for a ticker + read full articles + sentiment analysis + impact assessment",
        "required_inputs": ["ticker"],
        "steps": [
            "Crawl recent news articles specifically about {ticker} from Yahoo Finance and Google News",
            "Fetch the full content of the top 3 most relevant articles found",
            "Search for broader market/sector news related to {ticker}'s industry",
            "Run sentiment analysis on {ticker} using financial keyword scoring",
            "Get analyst ratings and any recent upgrades/downgrades for {ticker}",
        ],
        "synthesis": (
            "Provide a news intelligence report for {ticker} covering:\n"
            "1) Top news stories — what happened and when\n"
            "2) Key quotes and facts from full article content\n"
            "3) Sentiment trend (improving/deteriorating/neutral)\n"
            "4) Analyst reaction and rating changes\n"
            "5) Sector-level tailwinds or headwinds\n"
            "6) Potential market impact — bullish, bearish, or neutral catalyst assessment"
        ),
    },
    "market_news_briefing": {
        "name": "Market News Briefing",
        "description": "Crawl today's top market headlines from all major sources and summarize key themes",
        "required_inputs": [],
        "steps": [
            "Crawl live market news from Reuters, CNBC, MarketWatch, Yahoo Finance, and Benzinga",
            "Search for news on 'stock market today' to capture broad market movements",
            "Search for news on 'Federal Reserve interest rates' for macro context",
            "Search for news on 'earnings results this week' for earnings catalysts",
        ],
        "synthesis": (
            "Provide a market news briefing covering:\n"
            "1) Top 5 market-moving stories today\n"
            "2) Macro themes (Fed, rates, inflation, geopolitics)\n"
            "3) Sector highlights (which sectors are in the news)\n"
            "4) Earnings surprises or misses\n"
            "5) Stocks to watch based on today's news\n"
            "6) Overall market narrative — risk-on or risk-off tone"
        ),
    },
}


# ── Session Logger ──

class ResearchLog:
    """JSONL session logger for deep research sessions."""

    def __init__(self):
        from invtool.config import RESEARCH_LOG_DIR
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = RESEARCH_LOG_DIR / f"research_{ts}.jsonl"
        self._file = None

    def log(self, event_type: str, data: dict):
        """Append a log entry."""
        entry = {
            "ts": datetime.now().isoformat(),
            "type": event_type,
            "data": data,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass


# ── Context Management ──

def _estimate_tokens(messages: list) -> int:
    """Estimate token count from messages (~4 chars per token)."""
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total_chars += len(json.dumps(block, default=str))
                else:
                    total_chars += len(str(block))
        else:
            total_chars += len(str(content))
    return total_chars // 4


def _manage_context(messages: list, max_tokens: int = 80000) -> list:
    """Trim old tool results when conversation exceeds token budget.

    Keeps: first message (user query), last 5 tool-result exchanges.
    Replaces trimmed results with a note.
    """
    estimated = _estimate_tokens(messages)
    if estimated <= max_tokens:
        return messages

    # Find all tool_result message indices
    tool_result_indices = []
    for i, msg in enumerate(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                    tool_result_indices.append(i)

    if len(tool_result_indices) <= 5:
        return messages  # Not enough to trim

    # Keep first message and last 5 tool exchanges
    trim_count = len(tool_result_indices) - 5
    indices_to_trim = set()
    for idx in tool_result_indices[:trim_count]:
        indices_to_trim.add(idx)
        # Also trim the assistant message before it (contains tool_use)
        if idx > 0 and messages[idx - 1].get("role") == "assistant":
            indices_to_trim.add(idx - 1)

    trimmed = []
    inserted_note = False
    for i, msg in enumerate(messages):
        if i in indices_to_trim:
            if not inserted_note:
                trimmed.append({
                    "role": "user",
                    "content": "[System: Earlier research steps were trimmed to manage context. Key findings are retained in the assistant's reasoning above.]",
                })
                inserted_note = True
        else:
            trimmed.append(msg)

    return trimmed


# ── Progress Display ──

def _build_progress_panel(title: str, steps: list, step_status: list, current_step: int) -> Panel:
    """Build a Rich Panel showing research progress."""
    lines = []
    for i, step in enumerate(steps):
        if step_status[i] == "done":
            lines.append(f"  [green]v[/] {step}")
        elif i == current_step:
            lines.append(f"  [yellow]>[/] [bold]{step}[/] [dim]...[/]")
        else:
            lines.append(f"  [dim]o {step}[/]")

    progress_text = "\n".join(lines)
    step_label = f"Step {current_step + 1}/{len(steps)}" if current_step < len(steps) else "Synthesizing..."

    return Panel(
        progress_text,
        title=f"[bold blue]{title}[/]",
        subtitle=f"[dim]{step_label}[/]",
        border_style="blue",
        box=box.ROUNDED,
        padding=(1, 2),
    )


# ── Enhanced System Prompts ──

DEEP_RESEARCH_SYSTEM = """You are a senior investment research analyst conducting deep, multi-step research.

## Your Research Process
You follow a structured approach:

1. **PLAN**: Before calling tools, briefly state your research plan — which tools you'll use and what you're looking for.
2. **EXECUTE**: Call tools to gather data. Use multiple tools to build a complete picture.
3. **VALIDATE**: After gathering data, check for:
   - Missing data (did any tool fail or return empty?)
   - Conflicting signals (e.g., bullish technicals but bearish sentiment)
   - Data quality issues (stale prices, missing fields)
   If you find gaps, call additional tools to fill them.
4. **SYNTHESIZE**: Produce a comprehensive, well-structured report with:
   - Clear sections with headers
   - Specific numbers and data points
   - Actionable recommendations with rationale
   - Risk warnings where appropriate

## Available Tools
Stock: get_stock_price, technical_analysis
Options: screen_puts, screen_calls, wheel_analysis
Earnings: earnings_analysis, predict_earnings
Portfolio: portfolio_summary, portfolio_strategies, tax_loss_candidates, monte_carlo_risk, optimize_portfolio, correlation_analysis
AI Analytics: sentiment_analysis, price_forecast, market_regime, detect_anomalies
Market Intel: earnings_calendar, market_movers, sector_performance, analyst_ratings, insider_activity, economic_calendar
Web News: crawl_market_news, ticker_news_crawl, search_financial_news, fetch_article_content
Charts: generate_chart

## Rules
- Always use tools for data — never fabricate numbers
- Cross-reference conflicting data points and explain discrepancies
- Include confidence levels in your recommendations
- Warn about risks and limitations
- Use markdown formatting with headers, tables, and bullet points

The user's portfolio: TMF (36 shares @ $45.29), JEPQ (20 @ $53.70), BLSH (11 @ $37.00), FIG (11 @ $133.00), DOCS (6 @ $41.00).
"""

SKILL_SYSTEM_TEMPLATE = """You are a senior investment research analyst executing a structured research skill.

## Skill: {skill_name}
{skill_description}

## Research Steps (follow in order)
{steps_formatted}

## Instructions
- Execute each step by calling the appropriate tool(s)
- For news steps, use ticker_news_crawl or crawl_market_news, then fetch_article_content on the top articles
- After completing all steps, VALIDATE your findings:
  - Check for missing or failed data
  - Note any conflicting signals
  - Identify gaps that need additional research
- Then SYNTHESIZE your findings into a comprehensive report:
{synthesis}

## Rules
- Always use tools for data — never fabricate numbers
- Cross-reference conflicting data points
- Include specific numbers, prices, and percentages
- Give actionable recommendations with rationale
- Use markdown formatting for readability

The user's portfolio: TMF (36 shares @ $45.29), JEPQ (20 @ $53.70), BLSH (11 @ $37.00), FIG (11 @ $133.00), DOCS (6 @ $41.00).
"""


def _build_skill_prompt(skill: dict, inputs: dict) -> str:
    """Build the system prompt for a skill execution."""
    steps_formatted = "\n".join(
        f"{i+1}. {step.format(**inputs)}" for i, step in enumerate(skill["steps"])
    )
    synthesis = skill["synthesis"].format(**inputs)

    return SKILL_SYSTEM_TEMPLATE.format(
        skill_name=skill["name"],
        skill_description=skill["description"],
        steps_formatted=steps_formatted,
        synthesis=synthesis,
    )


# ── Core Research Loop ──

def _run_deep_research(client, system_prompt: str, user_query: str,
                       max_iterations: int = 15, log: ResearchLog = None,
                       skill_steps: list = None, title: str = "Deep Research") -> str:
    """Enhanced agent loop with iteration limit, context management, and logging."""
    from invtool.agent import TOOL_DEFINITIONS, _handle_tool, _ensure_provider

    _ensure_provider()
    messages = [{"role": "user", "content": user_query}]

    if log:
        log.log("query", {"query": user_query, "title": title})

    # Track progress for skills
    step_status = ["pending"] * len(skill_steps) if skill_steps else []
    current_step = [0]  # mutable for closure

    iteration = 0
    while iteration < max_iterations:
        iteration += 1

        # Context management
        messages = _manage_context(messages)

        # Show progress
        if skill_steps:
            panel = _build_progress_panel(title, skill_steps, step_status, current_step[0])
            console.print(panel)

        # Call LLM
        with Live(Spinner("dots", text=f"[dim]Iteration {iteration}/{max_iterations} — Thinking...[/]"),
                  console=console, transient=True):
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=8192,
                    system=system_prompt,
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                )
            except Exception as e:
                console.print(f"[red]API Error: {e}[/]")
                if log:
                    log.log("error", {"error": str(e), "iteration": iteration})
                break

        # Collect text and tool calls
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        # Log thinking
        if text_parts and log:
            log.log("thinking", {"text": "\n".join(text_parts), "iteration": iteration})

        # If no tool calls, we're done
        if response.stop_reason == "end_turn" or not tool_calls:
            final_text = "\n".join(text_parts)
            if log:
                log.log("done", {"text": final_text, "iterations": iteration})

            # Mark remaining steps as done
            if skill_steps:
                for i in range(len(step_status)):
                    step_status[i] = "done"
                panel = _build_progress_panel(title, skill_steps, step_status, len(skill_steps))
                console.print(panel)

            return final_text

        # Process tool calls
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            tool_desc = f"{tc.name}({json.dumps(tc.input, default=str)[:60]})"
            console.print(f"  [dim]  -> {tool_desc}[/]")

            if log:
                log.log("tool_call", {"name": tc.name, "input": tc.input, "iteration": iteration})

            try:
                result_str = _handle_tool(tc.name, tc.input)
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
                console.print(f"  [red]  Tool error: {e}[/]")

            if log:
                # Truncate large results for logging
                log_result = result_str[:2000] if len(result_str) > 2000 else result_str
                log.log("tool_result", {"name": tc.name, "result": log_result, "iteration": iteration})

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result_str,
            })

            # Update skill progress tracking
            if skill_steps and current_step[0] < len(skill_steps):
                step_status[current_step[0]] = "done"
                current_step[0] = min(current_step[0] + 1, len(skill_steps) - 1)

        messages.append({"role": "user", "content": tool_results})

    # Max iterations reached
    console.print(f"[yellow]Reached max iterations ({max_iterations}). Generating final response...[/]")
    messages.append({
        "role": "user",
        "content": "You've reached the iteration limit. Please synthesize all findings gathered so far into a final comprehensive report.",
    })

    with Live(Spinner("dots", text="[dim]Synthesizing final report...[/]"), console=console, transient=True):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=_manage_context(messages),
            )
            final_text = "\n".join(b.text for b in response.content if b.type == "text")
        except Exception as e:
            final_text = f"Error generating final report: {e}"

    if log:
        log.log("done", {"text": final_text[:1000], "iterations": iteration, "hit_limit": True})

    return final_text


# ── Save Report ──

def _save_report(result_text: str, default_name: str = "") -> str:
    """Prompt user to save research result to a file. Returns path or None."""
    from invtool.ui.prompt import text as prompt_text, confirm
    from invtool.config import REPORTS_DIR

    if not confirm("Save report to file?", default=True):
        return None

    # Ask for filename
    default_name = default_name.replace(" ", "_").replace("/", "-")
    ts = datetime.now().strftime("%Y%m%d")
    suggestion = f"{default_name}_{ts}" if default_name else f"research_{ts}"
    filename = prompt_text("Filename (without extension):", default=suggestion)
    if not filename:
        return None

    # Clean the filename
    filename = filename.strip().replace(" ", "_")
    for ch in '<>:"/\\|?*':
        filename = filename.replace(ch, "")

    # Ask for format
    fmt = prompt_text("Format (md/txt):", default="md")
    ext = ".txt" if fmt.strip().lower() == "txt" else ".md"

    filepath = REPORTS_DIR / f"{filename}{ext}"

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            if ext == ".md":
                f.write(result_text)
            else:
                # Strip markdown formatting for plain text
                import re
                plain = result_text
                plain = re.sub(r'#{1,6}\s+', '', plain)  # headers
                plain = re.sub(r'\*\*(.+?)\*\*', r'\1', plain)  # bold
                plain = re.sub(r'\*(.+?)\*', r'\1', plain)  # italic
                plain = re.sub(r'`(.+?)`', r'\1', plain)  # inline code
                f.write(plain)
        console.print(f"[green]Report saved to: {filepath}[/]")
        return str(filepath)
    except Exception as e:
        console.print(f"[red]Failed to save: {e}[/]")
        return None


# ── Entry Points ──

def run_skill(client, skill_key: str, inputs: dict, log: ResearchLog = None) -> str:
    """Execute a pre-defined research skill."""
    skill = SKILLS[skill_key]
    system_prompt = _build_skill_prompt(skill, inputs)

    # Format user query from skill
    input_desc = ", ".join(f"{k}={v}" for k, v in inputs.items())
    user_query = f"Execute the '{skill['name']}' research workflow. Inputs: {input_desc}. Follow all steps in order, then validate and synthesize."

    # Format steps for progress display
    skill_steps = [step.format(**inputs) for step in skill["steps"]]
    title = f"{skill['name']}"
    if inputs.get("ticker"):
        title += f" -- {inputs['ticker']}"

    return _run_deep_research(
        client, system_prompt, user_query,
        max_iterations=15, log=log,
        skill_steps=skill_steps, title=title,
    )


def deep_research_chat(client, log: ResearchLog = None) -> str:
    """Free-form deep research (single query)."""
    from invtool.ui.prompt import text as prompt_text

    user_query = prompt_text("Research query:")
    if not user_query or user_query.strip().lower() in ("back", "quit", "exit", "q"):
        return None

    return _run_deep_research(
        client, DEEP_RESEARCH_SYSTEM, user_query,
        max_iterations=15, log=log,
        title="Deep Research",
    )


def deep_research_menu(data_provider):
    """Interactive menu for deep research agent."""
    if not _SDK_AVAILABLE:
        console.print(Panel(
            "[red]anthropic SDK is not installed.[/]\n\n"
            "Install with: [bold]pip install anthropic[/]",
            title="Deep Research Unavailable",
            border_style="red",
        ))
        return

    from invtool.agent import check_api_key, set_data_provider
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

    from invtool.ui.prompt import select, text as prompt_text

    while True:
        # Build skill choices
        choices = []
        for key, skill in SKILLS.items():
            choices.append((f"{skill['name']} — {skill['description']}", key))
        choices.append(("Free Research (ask anything)", "free"))
        choices.append(("Back", "back"))

        console.print()
        choice = select("Deep Research Agent", choices)
        if choice is None or choice == "back":
            break

        log = ResearchLog()

        if choice == "free":
            # Free-form deep research
            console.print(Panel(
                "Ask any investment research question.\n"
                "The agent will plan, research, validate, and synthesize a report.\n"
                "Type [bold]back[/] to return.",
                title="[bold blue]Deep Research Mode[/]",
                border_style="blue",
            ))
            result = deep_research_chat(client, log)
            if result:
                console.print()
                console.print(Markdown(result))
                console.print()
                console.print(f"[dim]Session log: {log.log_path}[/]")
                _save_report(result, "research")
        else:
            # Run a skill
            skill = SKILLS[choice]
            inputs = {}
            for inp in skill["required_inputs"]:
                val = prompt_text(f"Enter {inp}:", default="NVDA" if inp == "ticker" else "")
                if not val:
                    break
                inputs[inp] = val.upper() if inp == "ticker" else val

            if len(inputs) == len(skill["required_inputs"]):
                console.print()
                try:
                    result = run_skill(client, choice, inputs, log)
                    if result:
                        console.print()
                        console.print(Markdown(result))
                        console.print()
                        console.print(f"[dim]Session log: {log.log_path}[/]")
                        # Suggest filename from skill + ticker
                        save_name = skill["name"].replace(" ", "_")
                        if inputs.get("ticker"):
                            save_name += f"_{inputs['ticker']}"
                        _save_report(result, save_name)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Research interrupted.[/]")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/]")
                    console.print(f"[dim]{traceback.format_exc()}[/]")
