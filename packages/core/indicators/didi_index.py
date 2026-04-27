"""Didi Index (Agulhada do Didi).

Desenvolvido por Odir Aguiar, identifica explosões de volatilidade
através da convergência das médias de 3, 8 e 20 períodos.

Agulhada de compra: média de 3 cruza acima da de 20, com média de 8 horizontal
Agulhada de venda: média de 3 cruza abaixo da de 20, com média de 8 horizontal

A agulhada só é válida se o ADX confirmar tendência.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from packages.core.models.candle import Candle
from packages.core.models.enums import Direction
from packages.core.indicators.moving_averages import calculate_sma


@dataclass(frozen=True)
class DidiResult:
    """Resultado do Didi Index."""

    short_ratio: float   # MA3 / MA8 (normalizado)
    long_ratio: float    # MA20 / MA8 (normalizado)
    has_needle: bool     # Agulhada detectada
    needle_direction: Direction
    mid_is_flat: bool    # MA8 está horizontal
    score: float         # 0.0 a 1.0 para confluence


def calculate_didi(
    candles: list[Candle],
    short_period: int = 3,
    mid_period: int = 8,
    long_period: int = 20,
    flatness_threshold: float = 0.001,
) -> DidiResult:
    """Calcula o Didi Index e detecta agulhadas.

    O Didi normaliza as médias dividindo pela média do meio (8):
    - Curta (3) / Média (8): se > 1, curta está acima
    - Longa (20) / Média (8): se < 1, longa está abaixo

    Agulhada ocorre quando as três linhas convergem e depois divergem.
    """
    min_candles = long_period + 2  # precisa de lookback + 2 para cruzamento
    if len(candles) < min_candles:
        return DidiResult(
            short_ratio=1.0, long_ratio=1.0,
            has_needle=False, needle_direction=Direction.NEUTRAL,
            mid_is_flat=False, score=0.0,
        )

    ma_short = calculate_sma(candles, short_period)
    ma_mid = calculate_sma(candles, mid_period)
    ma_long = calculate_sma(candles, long_period)

    # Valores atuais e anteriores
    curr_short = ma_short[-1]
    curr_mid = ma_mid[-1]
    curr_long = ma_long[-1]
    prev_short = ma_short[-2]
    prev_mid = ma_mid[-2]
    prev_long = ma_long[-2]

    if curr_mid == 0 or prev_mid == 0:
        return DidiResult(
            short_ratio=1.0, long_ratio=1.0,
            has_needle=False, needle_direction=Direction.NEUTRAL,
            mid_is_flat=False, score=0.0,
        )

    # Ratios normalizados
    short_ratio = float(curr_short / curr_mid)
    long_ratio = float(curr_long / curr_mid)

    # Verificar se MA8 está horizontal (flat)
    mid_change = abs(float(curr_mid - prev_mid) / float(prev_mid))
    mid_is_flat = mid_change < flatness_threshold

    # Detectar agulhada (cruzamento)
    has_needle = False
    needle_direction = Direction.NEUTRAL

    # Agulhada de COMPRA: curta cruza acima da longa
    prev_short_above = prev_short > prev_long
    curr_short_above = curr_short > curr_long

    if not prev_short_above and curr_short_above:
        has_needle = True
        needle_direction = Direction.BULLISH

    # Agulhada de VENDA: curta cruza abaixo da longa
    elif prev_short_above and not curr_short_above:
        has_needle = True
        needle_direction = Direction.BEARISH

    # Score
    score = _calculate_didi_score(has_needle, mid_is_flat, short_ratio, long_ratio)

    return DidiResult(
        short_ratio=round(short_ratio, 6),
        long_ratio=round(long_ratio, 6),
        has_needle=has_needle,
        needle_direction=needle_direction,
        mid_is_flat=mid_is_flat,
        score=score,
    )


def _calculate_didi_score(
    has_needle: bool,
    mid_is_flat: bool,
    short_ratio: float,
    long_ratio: float,
) -> float:
    """Score para confluence."""
    if not has_needle:
        return 0.0

    score = 0.5  # Base para agulhada detectada

    # Bônus se MA8 está horizontal (agulhada clássica)
    if mid_is_flat:
        score += 0.3

    # Bônus pela separação das linhas (divergência forte)
    spread = abs(short_ratio - long_ratio)
    score += min(0.2, spread * 10)

    return min(1.0, score)
