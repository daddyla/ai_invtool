"""Configuration, constants, and portfolio data."""

import os
import yaml
from pathlib import Path

# ── Analysis Constants ──
RISK_FREE_RATE = 0.043
MIN_OPEN_INTEREST = 20
MIN_DTE = 14
MAX_DTE = 90
TARGET_DELTA = -0.25

# ── Paths ──
# __file__: src/invtool/config/settings.py  → parents[3] is the repo root
BASE_DIR = Path(__file__).resolve().parents[3]
CHART_DIR = BASE_DIR / "charts"
RESEARCH_LOG_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_PATH = BASE_DIR / "invtool_config.yaml"
CHART_DIR.mkdir(exist_ok=True)
RESEARCH_LOG_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ── Default Portfolio ──
DEFAULT_PORTFOLIO = [
    {"ticker": "TMF",  "shares": 36, "cost": 45.29, "type": "ETF-Leveraged"},
    {"ticker": "JEPQ", "shares": 20, "cost": 53.70, "type": "ETF-Income"},
    {"ticker": "BLSH", "shares": 11, "cost": 37.00, "type": "Stock-Crypto"},
    {"ticker": "FIG",  "shares": 11, "cost": 133.00, "type": "Stock-Tech"},
    {"ticker": "DOCS", "shares": 6,  "cost": 41.00, "type": "Stock-Health"},
]

# ── NVDA Earnings Data (built-in) ──
NVDA_EARNINGS = [
    {"date": "2023-02-22", "quarter": "Q4 FY23", "eps_est": 0.81, "eps_actual": 0.88, "rev_est": 6.01, "rev_actual": 6.05},
    {"date": "2023-05-24", "quarter": "Q1 FY24", "eps_est": 0.92, "eps_actual": 1.09, "rev_est": 6.52, "rev_actual": 7.19},
    {"date": "2023-08-23", "quarter": "Q2 FY24", "eps_est": 2.07, "eps_actual": 2.70, "rev_est": 11.22, "rev_actual": 13.51},
    {"date": "2023-11-21", "quarter": "Q3 FY24", "eps_est": 3.36, "eps_actual": 4.02, "rev_est": 16.18, "rev_actual": 18.12},
    {"date": "2024-02-21", "quarter": "Q4 FY24", "eps_est": 4.59, "eps_actual": 5.16, "rev_est": 20.62, "rev_actual": 22.10},
    {"date": "2024-05-22", "quarter": "Q1 FY25", "eps_est": 5.59, "eps_actual": 6.12, "rev_est": 24.65, "rev_actual": 26.04},
    {"date": "2024-08-28", "quarter": "Q2 FY25", "eps_est": 0.64, "eps_actual": 0.68, "rev_est": 28.72, "rev_actual": 30.04},
    {"date": "2024-11-20", "quarter": "Q3 FY25", "eps_est": 0.75, "eps_actual": 0.81, "rev_est": 33.17, "rev_actual": 35.08},
    {"date": "2025-02-26", "quarter": "Q4 FY25", "eps_est": 0.84, "eps_actual": 0.89, "rev_est": 38.05, "rev_actual": 39.33},
    {"date": "2025-05-28", "quarter": "Q1 FY26", "eps_est": 0.88, "eps_actual": 0.96, "rev_est": 43.21, "rev_actual": 44.08},
    {"date": "2025-08-27", "quarter": "Q2 FY26", "eps_est": 1.01, "eps_actual": 1.05, "rev_est": 46.20, "rev_actual": 46.70},
    {"date": "2025-11-19", "quarter": "Q3 FY26", "eps_est": 1.22, "eps_actual": 1.30, "rev_est": 55.30, "rev_actual": 57.00},
]

NVDA_UPCOMING = {"date": "2026-02-25", "quarter": "Q4 FY26", "eps_est": 1.52, "rev_est": 65.67}


def load_portfolio():
    """Load portfolio from YAML config if it exists, else use defaults."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                data = yaml.safe_load(f)
            if data and "portfolio" in data:
                return data["portfolio"]
        except Exception:
            pass
    return [dict(p) for p in DEFAULT_PORTFOLIO]


def save_portfolio(portfolio):
    """Save portfolio to YAML config."""
    with open(CONFIG_PATH, "w") as f:
        yaml.dump({"portfolio": portfolio}, f, default_flow_style=False)
