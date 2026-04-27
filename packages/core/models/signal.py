"""Modelos de sinal e confluência."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from packages.core.models.enums import (
    Direction,
    MarketContext,
    PatternType,
    Timeframe,
    VolumeVerdict,
)


@dataclass(frozen=True)
class ConfluenceScore:
    """Pontuação de confluência de indicadores.

    O sinal só é executável se score >= min_score (padrão 0.65).
    """

    pattern_score: float = 0.0
    volume_score: float = 0.0
    adx_score: float = 0.0
    ma_alignment_score: float = 0.0
    rsi_score: float = 0.0
    didi_score: float = 0.0

    # Pesos padrão (somam 1.0)
    pattern_weight: float = 0.30
    volume_weight: float = 0.20
    adx_weight: float = 0.15
    ma_weight: float = 0.15
    rsi_weight: float = 0.10
    didi_weight: float = 0.10

    @property
    def total(self) -> float:
        return (
            self.pattern_score * self.pattern_weight
            + self.volume_score * self.volume_weight
            + self.adx_score * self.adx_weight
            + self.ma_alignment_score * self.ma_weight
            + self.rsi_score * self.rsi_weight
            + self.didi_score * self.didi_weight
        )

    @property
    def is_executable(self) -> bool:
        return self.total >= 0.65

    def to_dict(self) -> dict:
        return {
            "total": round(self.total, 4),
            "is_executable": self.is_executable,
            "components": {
                "pattern": round(self.pattern_score * self.pattern_weight, 4),
                "volume": round(self.volume_score * self.volume_weight, 4),
                "adx": round(self.adx_score * self.adx_weight, 4),
                "ma_alignment": round(self.ma_alignment_score * self.ma_weight, 4),
                "rsi": round(self.rsi_score * self.rsi_weight, 4),
                "didi": round(self.didi_score * self.didi_weight, 4),
            },
        }


@dataclass(frozen=True)
class PatternSignal:
    """Sinal gerado pela detecção de um padrão de candlestick."""

    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    pattern_type: PatternType = PatternType.HAMMER
    direction: Direction = Direction.NEUTRAL
    strength: float = 0.0
    timeframe: Timeframe = Timeframe.M15
    candle_timestamp: datetime = field(default_factory=datetime.utcnow)
    entry_price: Decimal = Decimal("0")
    stop_loss: Decimal = Decimal("0")
    take_profit: Decimal = Decimal("0")
    confirmation_required: bool = True
    volume_verdict: VolumeVerdict = VolumeVerdict.NEUTRAL
    context: MarketContext = MarketContext.CONGESTION
    confluence: ConfluenceScore = field(default_factory=ConfluenceScore)
    multi_tf_aligned: bool = False

    @property
    def is_valid(self) -> bool:
        """Sinal é válido se tem confluência executável e volume confirmado."""
        return (
            self.confluence.is_executable
            and self.volume_verdict in (VolumeVerdict.CONFIRMED, VolumeVerdict.CLIMACTIC)
            and self.multi_tf_aligned
        )

    @property
    def risk_reward_ratio(self) -> float:
        """Razão risco/retorno."""
        if self.stop_loss == 0 or self.entry_price == 0:
            return 0.0
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        if risk == 0:
            return 0.0
        return float(reward / risk)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "pattern": self.pattern_type.value,
            "direction": self.direction.value,
            "strength": round(self.strength, 4),
            "timeframe": self.timeframe.value,
            "entry_price": str(self.entry_price),
            "stop_loss": str(self.stop_loss),
            "take_profit": str(self.take_profit),
            "volume_verdict": self.volume_verdict.value,
            "context": self.context.value,
            "confluence": self.confluence.to_dict(),
            "multi_tf_aligned": self.multi_tf_aligned,
            "is_valid": self.is_valid,
            "risk_reward": round(self.risk_reward_ratio, 2),
        }
