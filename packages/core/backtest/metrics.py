"""Metricas de performance para backtesting."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal

from packages.core.backtest.trade import Trade


@dataclass(frozen=True)
class PerformanceMetrics:
    """Metricas consolidadas de um backtest."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0

    gross_profit: Decimal = Decimal("0")
    gross_loss: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")

    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    avg_win: Decimal = Decimal("0")
    avg_loss: Decimal = Decimal("0")
    avg_r_multiple: float = 0.0

    equity_curve: list[float] = field(default_factory=list)

    @property
    def net_profit(self) -> Decimal:
        return self.gross_profit + self.gross_loss - self.total_fees

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    @property
    def loss_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.losing_trades / self.total_trades

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0:
            return float("inf") if self.gross_profit > 0 else 0.0
        return float(abs(self.gross_profit / self.gross_loss))

    @property
    def expectancy(self) -> float:
        """Expectancia por trade (win_rate * avg_win - loss_rate * avg_loss)."""
        if self.total_trades == 0:
            return 0.0
        return float(
            self.win_rate * float(self.avg_win)
            + self.loss_rate * float(self.avg_loss)  # avg_loss ja e negativo
        )

    @property
    def sharpe_ratio(self) -> float:
        """Sharpe ratio simplificado (retornos dos trades)."""
        if len(self.equity_curve) < 2:
            return 0.0
        returns = [
            self.equity_curve[i] - self.equity_curve[i - 1]
            for i in range(1, len(self.equity_curve))
        ]
        if not returns:
            return 0.0
        avg = sum(returns) / len(returns)
        variance = sum((r - avg) ** 2 for r in returns) / len(returns)
        std = math.sqrt(variance)
        if std == 0:
            return 0.0
        return avg / std

    @property
    def recovery_factor(self) -> float:
        """Net profit / Max drawdown."""
        if self.max_drawdown == 0:
            return 0.0
        return float(self.net_profit) / self.max_drawdown

    def to_dict(self) -> dict:
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 4),
            "net_profit": str(self.net_profit),
            "gross_profit": str(self.gross_profit),
            "gross_loss": str(self.gross_loss),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy": round(self.expectancy, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "avg_win": str(self.avg_win),
            "avg_loss": str(self.avg_loss),
            "avg_r_multiple": round(self.avg_r_multiple, 2),
            "recovery_factor": round(self.recovery_factor, 2),
        }


def calculate_metrics(
    trades: list[Trade],
    initial_capital: float = 10000.0,
) -> PerformanceMetrics:
    """Calcula metricas a partir de uma lista de trades fechados."""
    closed = [t for t in trades if t.is_closed]
    if not closed:
        return PerformanceMetrics(equity_curve=[initial_capital])

    winners = [t for t in closed if t.is_winner]
    losers = [t for t in closed if t.is_loser]
    breakeven = [t for t in closed if t.net_pnl == 0]

    gross_profit = sum((t.net_pnl for t in winners), Decimal("0"))
    gross_loss = sum((t.net_pnl for t in losers), Decimal("0"))
    total_fees = sum(
        ((t.slippage + t.spread) * t.position_size for t in closed),
        Decimal("0"),
    )

    avg_win = gross_profit / len(winners) if winners else Decimal("0")
    avg_loss = gross_loss / len(losers) if losers else Decimal("0")
    avg_r = sum(t.r_multiple for t in closed) / len(closed) if closed else 0.0

    # Equity curve
    equity_curve = [initial_capital]
    equity = initial_capital
    for t in closed:
        equity += float(t.net_pnl)
        equity_curve.append(equity)

    # Max drawdown
    peak = initial_capital
    max_dd = 0.0
    max_dd_pct = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = dd / peak if peak > 0 else 0.0

    # Consecutive wins/losses
    max_consec_wins = 0
    max_consec_losses = 0
    current_wins = 0
    current_losses = 0
    for t in closed:
        if t.is_winner:
            current_wins += 1
            current_losses = 0
            max_consec_wins = max(max_consec_wins, current_wins)
        elif t.is_loser:
            current_losses += 1
            current_wins = 0
            max_consec_losses = max(max_consec_losses, current_losses)
        else:
            current_wins = 0
            current_losses = 0

    return PerformanceMetrics(
        total_trades=len(closed),
        winning_trades=len(winners),
        losing_trades=len(losers),
        breakeven_trades=len(breakeven),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        total_fees=total_fees,
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd_pct,
        max_consecutive_wins=max_consec_wins,
        max_consecutive_losses=max_consec_losses,
        avg_win=avg_win,
        avg_loss=avg_loss,
        avg_r_multiple=avg_r,
        equity_curve=equity_curve,
    )
