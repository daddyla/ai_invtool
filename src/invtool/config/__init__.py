"""Config sub-package.

Re-exports settings at the package level so existing
`from invtool.config import RISK_FREE_RATE` calls keep working.
DataProvider is imported explicitly from `invtool.config.data_provider`.
"""
from .settings import (
    RISK_FREE_RATE,
    MIN_OPEN_INTEREST,
    MIN_DTE,
    MAX_DTE,
    TARGET_DELTA,
    BASE_DIR,
    CHART_DIR,
    RESEARCH_LOG_DIR,
    REPORTS_DIR,
    CONFIG_PATH,
    DEFAULT_PORTFOLIO,
    NVDA_EARNINGS,
    NVDA_UPCOMING,
    load_portfolio,
    save_portfolio,
)

__all__ = [
    "RISK_FREE_RATE",
    "MIN_OPEN_INTEREST",
    "MIN_DTE",
    "MAX_DTE",
    "TARGET_DELTA",
    "BASE_DIR",
    "CHART_DIR",
    "RESEARCH_LOG_DIR",
    "REPORTS_DIR",
    "CONFIG_PATH",
    "DEFAULT_PORTFOLIO",
    "NVDA_EARNINGS",
    "NVDA_UPCOMING",
    "load_portfolio",
    "save_portfolio",
]
