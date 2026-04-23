"""Portfolio tracker — P&L, strategies, rebalancing."""

from invtool.config import load_portfolio, save_portfolio
from invtool.analysis.options import screen_puts, screen_calls


class Portfolio:
    """Portfolio manager with live data."""

    def __init__(self, data_provider, holdings=None):
        self.data = data_provider
        self.holdings = holdings or load_portfolio()
        self._prices = {}

    def refresh_prices(self):
        for h in self.holdings:
            h["price"] = self.data.get_current_price(h["ticker"])

    def summary(self) -> dict:
        self.refresh_prices()
        positions = []
        total_invested = 0
        total_value = 0

        for h in self.holdings:
            invested = h["shares"] * h["cost"]
            value = h["shares"] * h["price"]
            pnl = value - invested
            total_invested += invested
            total_value += value
            positions.append({
                **h,
                "invested": invested,
                "value": value,
                "pnl": pnl,
                "pnl_pct": pnl / invested if invested > 0 else 0,
            })

        return {
            "positions": positions,
            "total_invested": total_invested,
            "total_value": total_value,
            "total_pnl": total_value - total_invested,
            "total_pnl_pct": (total_value - total_invested) / total_invested if total_invested > 0 else 0,
        }

    def per_position_strategies(self) -> list:
        """Determine strategies for each position."""
        self.refresh_prices()
        results = []

        for h in self.holdings:
            ticker = h["ticker"]
            shares = h["shares"]
            cost = h["cost"]
            price = h["price"]
            pnl = shares * (price - cost)
            strategies = []

            # Covered calls (if 100+ shares)
            if shares >= 100:
                calls = screen_calls(ticker, self.data, cost_basis=cost)
                if not calls.empty:
                    best = calls.iloc[0]
                    strategies.append({
                        "name": "SELL COVERED CALL",
                        "action": f"SELL {best['expiration']} ${best['strike']:.2f}C @ ${best['premium']:.2f}",
                        "premium": float(best["premium"] * 100),
                        "ann_yield": float(best["annualized_return"]),
                    })

            # Sell puts
            puts = screen_puts(ticker, self.data)
            if not puts.empty:
                best = puts.iloc[0]
                eff_buy = best["strike"] - best["premium"]
                strategies.append({
                    "name": "SELL PUT",
                    "action": f"SELL {best['expiration']} ${best['strike']:.2f}P @ ${best['premium']:.2f}",
                    "premium": float(best["premium"] * 100),
                    "ann_yield": float(best["annualized_return"]),
                    "effective_buy": float(eff_buy),
                    "capital_needed": float(best["strike"] * 100),
                })

            # Buy to 100 shares
            if 0 < shares < 100:
                needs = 100 - shares
                add_cost = needs * price
                blended = (shares * cost + needs * price) / 100
                strategies.append({
                    "name": "BUY TO 100 SHARES",
                    "action": f"Buy {needs} shares @ ${price:.2f}",
                    "capital_needed": float(add_cost),
                    "blended_basis": float(blended),
                })

            # Tax-loss harvest
            if pnl < 0:
                tax_benefit = abs(pnl) * 0.30
                strategies.append({
                    "name": "TAX-LOSS HARVEST",
                    "action": f"Sell all {shares} shares @ ${price:.2f}",
                    "realized_loss": float(pnl),
                    "tax_benefit": float(tax_benefit),
                })

            # Hold dividends (special tickers)
            if ticker == "JEPQ":
                monthly_div = 0.48 * shares
                strategies.append({
                    "name": "HOLD + REINVEST DIVIDENDS",
                    "action": f"~${monthly_div:.0f}/month (~10% yield)",
                    "annual_income": float(monthly_div * 12),
                })

            results.append({
                "ticker": ticker,
                "shares": shares,
                "cost": cost,
                "price": price,
                "pnl": pnl,
                "strategies": strategies,
            })

        return results

    def tax_loss_candidates(self) -> list:
        """Identify positions eligible for tax-loss harvesting."""
        self.refresh_prices()
        candidates = []
        for h in self.holdings:
            pnl = h["shares"] * (h["price"] - h["cost"])
            if pnl < 0:
                candidates.append({
                    "ticker": h["ticker"],
                    "shares": h["shares"],
                    "loss": pnl,
                    "tax_benefit": abs(pnl) * 0.30,
                })
        candidates.sort(key=lambda x: x["loss"])
        return candidates

    def rebalance_plans(self) -> list:
        """Generate 3 rebalance plans."""
        self.refresh_prices()
        total_value = sum(h["shares"] * h["price"] for h in self.holdings)

        plans = [
            {
                "name": "Plan A: Aggressive",
                "mix": "75% growth / 25% income",
                "growth_pct": 0.75,
                "income_pct": 0.25,
                "recovery": "8-12 months",
                "risk": "High",
            },
            {
                "name": "Plan B: Balanced (Recommended)",
                "mix": "60% growth / 40% income",
                "growth_pct": 0.60,
                "income_pct": 0.40,
                "recovery": "10-14 months",
                "risk": "Medium",
            },
            {
                "name": "Plan C: Conservative",
                "mix": "40% growth / 60% income",
                "growth_pct": 0.40,
                "income_pct": 0.60,
                "recovery": "14-18 months",
                "risk": "Low",
            },
        ]

        for plan in plans:
            plan["total_capital"] = total_value
            plan["growth_allocation"] = total_value * plan["growth_pct"]
            plan["income_allocation"] = total_value * plan["income_pct"]

        return plans

    def add_holding(self, ticker: str, shares: int, cost: float, htype: str = ""):
        self.holdings.append({"ticker": ticker, "shares": shares, "cost": cost, "type": htype})
        save_portfolio(self.holdings)

    def remove_holding(self, ticker: str):
        self.holdings = [h for h in self.holdings if h["ticker"] != ticker]
        save_portfolio(self.holdings)
