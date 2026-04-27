"""Modelo de Trade para backtesting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from packages.core.models.enums import Direction, PatternType


@dataclass
class Trade:
    """Representa um trade completo (entrada + saida)."""

    id: UUID = field(default_factory=uuid4)
    signal_id: Optional[UUID] = None
    direction: Direction = Direction.BULLISH
    pattern_type: PatternType = PatternType.HAMMER

    # Precos
    entry_price: Decimal = Decimal("0")
    stop_loss: Decimal = Decimal("0")
    take_profit: Decimal = Decimal("0")
    exit_price: Optional[Decimal] = None

    # Timestamps
    entry_time: datetime = field(default_factory=datetime.utcnow)
    exit_time: Optional[datetime] = None

    # Sizing
    position_size: Decimal = Decimal("1")
    confluence_score: float = 0.0

    # Custos
    slippage: Decimal = Decimal("0")
    spread: Decimal = Decimal("0")

    @property
    def is_open(self) -> bool:
        return self.exit_price is None

    @property
    def is_closed(self) -> bool:
        return self.exit_price is not None

    @property
    def pnl(self) -> Decimal:
        """Lucro/prejuizo bruto em pontos."""
        if self.exit_price is None:
            return Decimal("0")
        if self.direction == Direction.BULLISH:
            return (self.exit_price - self.entry_price) * self.position_size
        elif self.direction == Direction.BEARISH:
            return (self.entry_price - self.exit_price) * self.position_size
        return Decimal("0")

    @property
    def net_pnl(self) -> Decimal:
        """PnL liquido (descontando slippage e spread)."""
        cost = (self.slippage + self.spread) * self.position_size
        return self.pnl - cost

    @property
    def is_winner(self) -> bool:
        return self.net_pnl > 0

    @property
    def is_loser(self) -> bool:
        return self.net_pnl < 0

    @property
    def duration_bars(self) -> Optional[int]:
        """Duracao em barras (calculada externamente)."""
        return self._duration_bars if hasattr(self, "_duration_bars") else None

    @duration_bars.setter
    def duration_bars(self, value: int) -> None:
        self._duration_bars = value

    @property
    def risk(self) -> Decimal:
        """Risco em pontos (distancia entry -> SL)."""
        return abs(self.entry_price - self.stop_loss)

    @property
    def reward(self) -> Decimal:
        """Reward em pontos (distancia entry -> TP)."""
        return abs(self.take_profit - self.entry_price)

    @property
    def r_multiple(self) -> float:
        """Resultado em multiplos de R (risco)."""
        if self.risk == 0 or self.exit_price is None:
            return 0.0
        if self.direction == Direction.BULLISH:
            return float((self.exit_price - self.entry_price) / self.risk)
        elif self.direction == Direction.BEARISH:
            return float((self.entry_price - self.exit_price) / self.risk)
        return 0.0

    @property
    def exit_reason(self) -> str:
        """Motivo do fechamento."""
        if self.exit_price is None:
            return "OPEN"
        if self.direction == Direction.BULLISH:
            if self.exit_price <= self.stop_loss:
                return "STOP_LOSS"
            elif self.exit_price >= self.take_profit:
                return "TAKE_PROFIT"
        elif self.direction == Direction.BEARISH:
            if self.exit_price >= self.stop_loss:
                return "STOP_LOSS"
            elif self.exit_price <= self.take_profit:
                return "TAKE_PROFIT"
        return "MANUAL"

    def close(self, price: Decimal, time: datetime) -> None:
        """Fecha o trade com preco e timestamp."""
        self.exit_price = price
        self.exit_time = time

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "direction": self.direction.value,
            "pattern": self.pattern_type.value,
            "entry_price": str(self.entry_price),
            "exit_price": str(self.exit_price) if self.exit_price else None,
            "stop_loss": str(self.stop_loss),
            "take_profit": str(self.take_profit),
            "position_size": str(self.position_size),
            "pnl": str(self.net_pnl),
            "r_multiple": round(self.r_multiple, 2),
            "exit_reason": self.exit_reason,
            "confluence": round(self.confluence_score, 4),
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
        }
