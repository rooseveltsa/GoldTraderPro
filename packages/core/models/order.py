"""Modelos de ordem e gestão de risco."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from packages.core.models.enums import OrderSide, OrderStatus, OrderType


@dataclass
class Order:
    """Representa uma ordem enviada ao broker."""

    id: UUID = field(default_factory=uuid4)
    signal_id: UUID | None = None
    symbol: str = "XAU/USD"
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    stop_loss: Decimal = Decimal("0")
    take_profit: Decimal = Decimal("0")
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Decimal | None = None
    filled_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    broker_order_id: str | None = None
    slippage: Decimal = Decimal("0")

    @property
    def is_active(self) -> bool:
        return self.status in (OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED)

    @property
    def is_closed(self) -> bool:
        return self.status in (
            OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED,
        )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "signal_id": str(self.signal_id) if self.signal_id else None,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": str(self.quantity),
            "price": str(self.price),
            "stop_loss": str(self.stop_loss),
            "take_profit": str(self.take_profit),
            "status": self.status.value,
            "filled_price": str(self.filled_price) if self.filled_price else None,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class OrderOCO:
    """Par de ordens OCO (One Cancels the Other): Stop Loss + Take Profit."""

    entry_order: Order
    stop_loss_order: Order
    take_profit_order: Order

    @property
    def risk(self) -> Decimal:
        """Risco em valor absoluto (distância entry → stop loss)."""
        return abs(self.entry_order.price - self.stop_loss_order.price)

    @property
    def reward(self) -> Decimal:
        """Reward em valor absoluto (distância entry → take profit)."""
        return abs(self.take_profit_order.price - self.entry_order.price)

    @property
    def risk_reward_ratio(self) -> float:
        if self.risk == 0:
            return 0.0
        return float(self.reward / self.risk)


@dataclass(frozen=True)
class PositionSizing:
    """Cálculo de dimensionamento de posição baseado em risco."""

    capital: Decimal
    risk_percent: Decimal
    entry_price: Decimal
    stop_loss_price: Decimal

    @property
    def risk_amount(self) -> Decimal:
        """Valor monetário em risco."""
        return self.capital * self.risk_percent

    @property
    def stop_distance(self) -> Decimal:
        """Distância em preço até o stop loss."""
        return abs(self.entry_price - self.stop_loss_price)

    @property
    def position_size(self) -> Decimal:
        """Tamanho da posição calculado pelo risco."""
        if self.stop_distance == 0:
            return Decimal("0")
        return self.risk_amount / self.stop_distance

    def to_dict(self) -> dict:
        return {
            "capital": str(self.capital),
            "risk_percent": str(self.risk_percent),
            "risk_amount": str(self.risk_amount),
            "entry_price": str(self.entry_price),
            "stop_loss_price": str(self.stop_loss_price),
            "stop_distance": str(self.stop_distance),
            "position_size": str(self.position_size),
        }
