# Investment Dashboard

Rich CLI + AI Agent for stock analysis, options screening, earnings patterns, and portfolio tracking.

## Quick Start

**PowerShell:**
```powershell
.\run.ps1
```

**Git Bash:**
```bash
PYTHONIOENCODING=utf-8 python -m invtool
```

## Setup

```bash
# Activate conda environment
conda activate invt

# Install dependencies (first time only)
pip install rich questionary pyyaml claude-agent-sdk yfinance matplotlib scipy
```

## Menu Options

```
1. Technical Analysis    — SMA, RSI, MACD, Bollinger Bands, ATR, support/resistance
2. Options Screening     — Sell puts, covered calls, wheel strategy with scoring
3. Earnings Analysis     — Pre/post earnings patterns, sell-the-news detection
4. Portfolio Tracker     — Live P&L, per-position strategies, rebalance plans
5. Recovery Strategies   — Tax-loss harvest candidates, wheel sim, recovery timeline
6. Execution Planning    — Wash sale calendar, dividend calendar
7. Ask AI               — Natural language queries powered by Claude
8. Settings             — Edit portfolio holdings, clear cache
```

## Usage Examples

### Technical Analysis
Pick option `1`, enter a ticker (e.g. `NVDA`), get a full technical breakdown with trend assessment and chart.

### Options Screening
Pick option `2`, enter a ticker, choose a strategy:
- **Sell Put** — ranks OTM puts by annualized return, probability of profit, and cushion
- **Covered Call** — ranks OTM calls for income generation
- **Wheel Strategy** — combined put + call analysis with monthly income estimates

### Earnings Analysis
Pick option `3`, enter a ticker. NVDA has 12 quarters of built-in data. Other tickers pull from yfinance.
Shows sell-the-news rate, pre-earnings run-up patterns, and forecast scenarios.

### Portfolio Tracker
Pick option `4` to see live P&L for all holdings, get per-position strategy recommendations (sell puts, covered calls, tax-loss harvest, buy-to-100), or compare 3 rebalance plans.

### AI Mode
Pick option `7` to chat with an AI investment analyst. Requires `ANTHROPIC_API_KEY`:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
.\run.ps1
```

Example questions:
- "What's the best way to generate $200/mo income from my portfolio?"
- "Compare NVDA vs AMD options premiums"
- "Should I sell puts on SOFI right now?"
- "Show me NVDA earnings patterns"

The AI has access to all analysis tools plus web search.

## Portfolio Configuration

Your portfolio is stored in `invtool_config.yaml`. Edit it via Settings (option `8`) or directly:

```yaml
portfolio:
- ticker: JEPQ
  shares: 20
  cost: 53.7
  type: ETF-Income
- ticker: NVDA
  shares: 10
  cost: 120.0
  type: Stock-Tech
```

## Charts

All charts save to the `charts/` directory as PNG files. The file path is printed after generation.

## Project Structure

```
invtool/
  main.py         — App entry point and menu loop
  config.py       — Portfolio data and constants
  data.py         — yfinance data provider with caching
  technical.py    — Technical indicators engine
  options.py      — Black-Scholes, put/call screening
  earnings.py     — Earnings window analysis
  portfolio.py    — Portfolio P&L and strategies
  execution.py    — Wash sale and dividend calendars
  charts.py       — Matplotlib chart generation
  display.py      — Rich terminal formatting
  agent.py        — Claude AI agent integration
  prompt.py       — Cross-platform input (PowerShell/Bash/cmd)
```
