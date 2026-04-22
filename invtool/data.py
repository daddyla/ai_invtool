"""Data provider — wraps yfinance with caching."""

import time
import yfinance as yf
import pandas as pd
import numpy as np
from rich.progress import Progress, SpinnerColumn, TextColumn


class DataProvider:
    """Centralized data fetcher with in-memory cache."""

    def __init__(self, cache_ttl=300):
        self._cache = {}
        self._ttl = cache_ttl  # seconds

    def _is_fresh(self, key):
        if key not in self._cache:
            return False
        return (time.time() - self._cache[key]["ts"]) < self._ttl

    def get_ticker(self, ticker: str) -> yf.Ticker:
        key = f"ticker_{ticker}"
        if not self._is_fresh(key):
            self._cache[key] = {"data": yf.Ticker(ticker), "ts": time.time()}
        return self._cache[key]["data"]

    def get_history(self, ticker: str, period="6mo") -> pd.DataFrame:
        key = f"hist_{ticker}_{period}"
        if not self._is_fresh(key):
            t = self.get_ticker(ticker)
            hist = t.history(period=period, interval="1d")
            if not hist.empty:
                hist.index = hist.index.tz_localize(None)
            self._cache[key] = {"data": hist, "ts": time.time()}
        return self._cache[key]["data"]

    def get_current_price(self, ticker: str) -> float:
        hist = self.get_history(ticker, "5d")
        if hist.empty:
            return 0.0
        return float(hist["Close"].iloc[-1])

    def get_info(self, ticker: str) -> dict:
        key = f"info_{ticker}"
        if not self._is_fresh(key):
            t = self.get_ticker(ticker)
            try:
                info = t.info
            except Exception:
                info = {}
            self._cache[key] = {"data": info, "ts": time.time()}
        return self._cache[key]["data"]

    def get_expirations(self, ticker: str) -> list:
        t = self.get_ticker(ticker)
        try:
            return list(t.options)
        except Exception:
            return []

    def get_options_chain(self, ticker: str, exp_date: str):
        t = self.get_ticker(ticker)
        try:
            return t.option_chain(exp_date)
        except Exception:
            return None

    def get_hist_vol(self, ticker: str, window=20) -> float:
        hist = self.get_history(ticker, "3mo")
        if len(hist) < window + 1:
            return 0.5
        log_ret = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
        return float(log_ret.rolling(window).std().iloc[-1] * np.sqrt(252))

    def bulk_fetch(self, tickers: list, period="3mo"):
        """Fetch multiple tickers with progress display."""
        results = {}
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Fetching data...", total=len(tickers))
            for t in tickers:
                progress.update(task, description=f"Fetching {t}...")
                results[t] = {
                    "price": self.get_current_price(t),
                    "hist": self.get_history(t, period),
                    "vol": self.get_hist_vol(t),
                }
                progress.advance(task)
        return results

    def clear_cache(self):
        self._cache.clear()
