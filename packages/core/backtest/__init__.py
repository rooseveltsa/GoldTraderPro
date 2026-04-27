"""Módulo de backtesting com proteção anti-repainting."""

from packages.core.backtest.engine import BacktestConfig, BacktestEngine, BacktestResult
from packages.core.backtest.metrics import PerformanceMetrics, calculate_metrics
from packages.core.backtest.trade import Trade

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "PerformanceMetrics",
    "Trade",
    "calculate_metrics",
]
