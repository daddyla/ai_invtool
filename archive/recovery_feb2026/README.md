# Archive: Recovery Feb 2026

One-off scripts and generated charts from the February 2026 portfolio recovery analysis,
written before the `invtool/` package existed. Preserved for reference.

Their functionality has since been folded into the package:

| Legacy script                      | Replaced by (in `invtool/`)           |
| ---------------------------------- | ------------------------------------- |
| `fig_put_analysis.py`              | `options.py` (sell-put screener)      |
| `fig_recovery_strategy.py`         | `portfolio.py` per-position strategies|
| `portfolio_recovery.py`            | `portfolio.py`                        |
| `portfolio_optimizer_v2.py`        | `optimizer.py` (Markowitz)            |
| `portfolio_rebalance_plans.py`     | `portfolio.py` rebalance plans        |
| `execution_playbook.py`            | `execution.py` + menu 6               |
| `nvda_earnings_behavior.py`        | `earnings.py`                         |
| `nvda_earnings_multidim.py`        | `earnings.py` + `earnings_ml.py`      |

Nothing here is imported by the live codebase.
