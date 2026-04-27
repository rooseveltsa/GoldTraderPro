"""Volume Analyzer — validação de sinais por volume institucional.

Regras:
- Volume >= 3.0x média = CLIMACTIC (confirmação muito forte)
- Volume >= 1.5x média = CONFIRMED (confirmação padrão)
- Volume >= 1.0x média = NEUTRAL (sem confirmação)
- Volume < 1.0x média = WEAK (ruído — sinal filtrado)

Padrão gráfico sem volume correspondente = RUÍDO.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from packages.core.models.candle import Candle
from packages.core.models.enums import VolumeVerdict


@dataclass(frozen=True)
class VolumeAnalysis:
    """Resultado da análise de volume."""

    current_volume: Decimal
    average_volume: Decimal
    ratio: float
    verdict: VolumeVerdict
    score: float  # 0.0 a 1.0 para confluence


def analyze_volume(
    candles: list[Candle],
    lookback: int = 20,
    confirmation_ratio: float = 1.5,
    climactic_ratio: float = 3.0,
) -> VolumeAnalysis:
    """Analisa o volume do último candle em relação à média recente.

    Args:
        candles: Lista de candles (último é o analisado)
        lookback: Período para cálculo da média de volume
        confirmation_ratio: Multiplicador para confirmação (padrão 1.5x)
        climactic_ratio: Multiplicador para volume climático (padrão 3.0x)
    """
    if not candles:
        return VolumeAnalysis(
            current_volume=Decimal("0"),
            average_volume=Decimal("0"),
            ratio=0.0,
            verdict=VolumeVerdict.WEAK,
            score=0.0,
        )

    current = candles[-1]
    current_volume = current.volume

    # Calcular média dos candles anteriores (exclui o atual)
    history = candles[-(lookback + 1):-1] if len(candles) > 1 else []

    if not history:
        return VolumeAnalysis(
            current_volume=current_volume,
            average_volume=Decimal("0"),
            ratio=0.0,
            verdict=VolumeVerdict.NEUTRAL,
            score=0.5,
        )

    avg_volume = sum(c.volume for c in history) / len(history)

    if avg_volume == 0:
        return VolumeAnalysis(
            current_volume=current_volume,
            average_volume=avg_volume,
            ratio=0.0,
            verdict=VolumeVerdict.NEUTRAL,
            score=0.5,
        )

    ratio = float(current_volume / avg_volume)

    # Classificar
    if ratio >= climactic_ratio:
        verdict = VolumeVerdict.CLIMACTIC
    elif ratio >= confirmation_ratio:
        verdict = VolumeVerdict.CONFIRMED
    elif ratio >= 1.0:
        verdict = VolumeVerdict.NEUTRAL
    else:
        verdict = VolumeVerdict.WEAK

    score = _calculate_volume_score(ratio, confirmation_ratio, climactic_ratio)

    return VolumeAnalysis(
        current_volume=current_volume,
        average_volume=avg_volume,
        ratio=round(ratio, 2),
        verdict=verdict,
        score=score,
    )


def _calculate_volume_score(
    ratio: float,
    confirmation_ratio: float,
    climactic_ratio: float,
) -> float:
    """Score de 0.0 a 1.0 para o confluence."""
    if ratio < 1.0:
        return 0.0  # Volume fraco
    elif ratio < confirmation_ratio:
        # Linear de 0.2 a 0.5
        return 0.2 + 0.3 * (ratio - 1.0) / (confirmation_ratio - 1.0)
    elif ratio < climactic_ratio:
        # Linear de 0.5 a 0.8
        return 0.5 + 0.3 * (ratio - confirmation_ratio) / (climactic_ratio - confirmation_ratio)
    else:
        # Climático: 0.8 a 1.0
        return min(1.0, 0.8 + 0.2 * min(1.0, (ratio - climactic_ratio) / climactic_ratio))
