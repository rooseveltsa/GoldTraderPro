"""Modelo de dados do Candle (OHLCV)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from packages.core.models.enums import Timeframe


@dataclass(frozen=True)
class Candle:
    """Representa um candle OHLCV completo.

    Imutável por design — uma vez criado, não pode ser alterado.
    Isso garante integridade dos dados no pipeline de análise.
    """

    timestamp: datetime
    timeframe: Timeframe
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    tick_volume: int = 0
    spread: int = 0
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(f"High ({self.high}) não pode ser menor que Low ({self.low})")
        if self.high < self.open or self.high < self.close:
            raise ValueError("High deve ser >= Open e Close")
        if self.low > self.open or self.low > self.close:
            raise ValueError("Low deve ser <= Open e Close")
        if self.volume < 0:
            raise ValueError("Volume não pode ser negativo")

    @property
    def body(self) -> Decimal:
        """Tamanho absoluto do corpo (|Close - Open|)."""
        return abs(self.close - self.open)

    @property
    def amplitude(self) -> Decimal:
        """Amplitude total do candle (High - Low)."""
        return self.high - self.low

    @property
    def upper_wick(self) -> Decimal:
        """Pavio superior."""
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> Decimal:
        """Pavio inferior."""
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        """Candle de alta (close > open)."""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Candle de baixa (close < open)."""
        return self.close < self.open

    @property
    def is_doji(self) -> bool:
        """Candle doji (corpo <= 5% da amplitude)."""
        if self.amplitude == 0:
            return True
        return self.body / self.amplitude <= Decimal("0.05")

    @property
    def body_ratio(self) -> Decimal:
        """Razão corpo/amplitude."""
        if self.amplitude == 0:
            return Decimal("0")
        return self.body / self.amplitude

    @property
    def upper_wick_ratio(self) -> Decimal:
        """Razão pavio superior/amplitude."""
        if self.amplitude == 0:
            return Decimal("0")
        return self.upper_wick / self.amplitude

    @property
    def lower_wick_ratio(self) -> Decimal:
        """Razão pavio inferior/amplitude."""
        if self.amplitude == 0:
            return Decimal("0")
        return self.lower_wick / self.amplitude

    @property
    def midpoint(self) -> Decimal:
        """Ponto médio do candle."""
        return (self.high + self.low) / 2

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe.value,
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "volume": str(self.volume),
            "tick_volume": self.tick_volume,
            "spread": self.spread,
        }
