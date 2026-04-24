"""Shared CLI helpers used across menu modules."""
from invtool.ui.prompt import text


def ask_ticker(default: str = "NVDA") -> str:
    result = text("Enter stock ticker:", default=default)
    return result.upper().strip() if result else default
