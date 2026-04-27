"""Índice de Força Relativa (RSI / IFR).

- Sobrecompra: RSI > 70 (potencial reversão de baixa)
- Sobrevenda: RSI < 30 (potencial reversão de alta)
- Divergências: RSI divergindo do preço = sinal forte
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from packages.core.models.candle import Candle


@dataclass(frozen=True)
class RSIResult:
    """Resultado do cálculo do RSI."""

    value: float
    is_overbought: bool
    is_oversold: bool
    zone: str  # "OVERBOUGHT" | "OVERSOLD" | "NEUTRAL"
    score: float  # 0.0 a 1.0 para confluence


def calculate_rsi(
    candles: list[Candle],
    period: int = 14,
    overbought: float = 70.0,
    oversold: float = 30.0,
) -> RSIResult:
    """Calcula o RSI (Relative Strength Index).

    Algoritmo (Wilder):
    1. Calcula variações (gains e losses)
    2. Média de gains e losses com suavização Wilder
    3. RS = avg_gain / avg_loss
    4. RSI = 100 - (100 / (1 + RS))
    """
    if len(candles) < period + 1:
        return RSIResult(
            value=50.0, is_overbought=False, is_oversold=False,
            zone="NEUTRAL", score=0.5,
        )

    closes = [float(c.close) for c in candles]

    # Variações
    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(0, change))
        losses.append(max(0, -change))

    # Primeira média (SMA)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Suavização Wilder para o restante
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    # RSI
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    rsi = round(rsi, 2)
    is_overbought = rsi > overbought
    is_oversold = rsi < oversold

    if is_overbought:
        zone = "OVERBOUGHT"
    elif is_oversold:
        zone = "OVERSOLD"
    else:
        zone = "NEUTRAL"

    score = _calculate_rsi_score(rsi, overbought, oversold)

    return RSIResult(
        value=rsi,
        is_overbought=is_overbought,
        is_oversold=is_oversold,
        zone=zone,
        score=score,
    )


def _calculate_rsi_score(rsi: float, overbought: float, oversold: float) -> float:
    """Score para confluence baseado na posição do RSI.

    Para sinais BULLISH:
    - RSI em sobrevenda (<30) = score alto (1.0)
    - RSI neutro (30-70) = score médio
    - RSI em sobrecompra (>70) = score baixo (0.0)

    Retorna score genérico — o SignalEvaluator ajusta conforme direção.
    """
    if rsi <= oversold:
        # Sobrevenda — favorável para compra
        return min(1.0, (oversold - rsi) / oversold + 0.7)
    elif rsi >= overbought:
        # Sobrecompra — favorável para venda
        return min(1.0, (rsi - overbought) / (100 - overbought) + 0.7)
    else:
        # Zona neutra — score proporcional à distância do centro
        center = (overbought + oversold) / 2
        distance = abs(rsi - center) / (center - oversold)
        return max(0.2, min(0.6, 0.5 - distance * 0.3))
