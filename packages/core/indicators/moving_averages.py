"""Indicadores de Médias Móveis (MMA e MME).

- MMA (Média Móvel Aritmética / SMA): períodos 20, 50, 100, 200
- MME (Média Móvel Exponencial / EMA): períodos 9, 21, 50
- Cruzamentos: Golden Cross, Death Cross
- Proximidade à MMA200 como suporte macro
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List

from packages.core.models.candle import Candle


@dataclass(frozen=True)
class MAResult:
    """Resultado do cálculo de uma média móvel."""

    period: int
    ma_type: str  # "SMA" ou "EMA"
    values: List[Decimal]


@dataclass(frozen=True)
class CrossoverSignal:
    """Sinal de cruzamento de médias."""

    cross_type: str  # "GOLDEN_CROSS" | "DEATH_CROSS"
    fast_period: int
    slow_period: int
    fast_value: Decimal
    slow_value: Decimal


@dataclass(frozen=True)
class MAAlignment:
    """Resultado da análise de alinhamento de médias."""

    bullish_aligned: bool  # Todas as médias em ordem crescente (curta > longa)
    bearish_aligned: bool  # Todas as médias em ordem decrescente
    price_above_ma200: bool
    ma200_distance_pct: float  # Distância % do preço à MA200
    crossovers: List[CrossoverSignal]
    score: float  # 0.0 a 1.0 — pontuação para confluence


def calculate_sma(candles: list[Candle], period: int) -> list[Decimal]:
    """Calcula a Média Móvel Simples (SMA/MMA).

    Retorna lista de valores com mesmo tamanho dos candles.
    Posições sem dados suficientes recebem Decimal("0").
    """
    closes = [c.close for c in candles]
    result: list[Decimal] = []

    for i in range(len(closes)):
        if i < period - 1:
            result.append(Decimal("0"))
        else:
            window = closes[i - period + 1: i + 1]
            avg = sum(window) / len(window)
            result.append(avg)

    return result


def calculate_ema(candles: list[Candle], period: int) -> list[Decimal]:
    """Calcula a Média Móvel Exponencial (EMA/MME).

    Usa SMA do primeiro período como seed.
    Multiplier = 2 / (period + 1)
    """
    closes = [c.close for c in candles]
    result: list[Decimal] = []
    multiplier = Decimal(str(2 / (period + 1)))

    for i in range(len(closes)):
        if i < period - 1:
            result.append(Decimal("0"))
        elif i == period - 1:
            # Seed com SMA
            sma = sum(closes[:period]) / period
            result.append(sma)
        else:
            prev_ema = result[-1]
            ema = (closes[i] - prev_ema) * multiplier + prev_ema
            result.append(ema)

    return result


def detect_crossovers(
    fast_ma: list[Decimal],
    slow_ma: list[Decimal],
    fast_period: int,
    slow_period: int,
) -> list[CrossoverSignal]:
    """Detecta cruzamentos entre duas médias móveis.

    Golden Cross: média rápida cruza ACIMA da lenta
    Death Cross: média rápida cruza ABAIXO da lenta
    """
    crossovers: list[CrossoverSignal] = []

    for i in range(1, len(fast_ma)):
        if fast_ma[i] == 0 or slow_ma[i] == 0:
            continue
        if fast_ma[i - 1] == 0 or slow_ma[i - 1] == 0:
            continue

        prev_above = fast_ma[i - 1] > slow_ma[i - 1]
        curr_above = fast_ma[i] > slow_ma[i]

        if not prev_above and curr_above:
            crossovers.append(CrossoverSignal(
                cross_type="GOLDEN_CROSS",
                fast_period=fast_period,
                slow_period=slow_period,
                fast_value=fast_ma[i],
                slow_value=slow_ma[i],
            ))
        elif prev_above and not curr_above:
            crossovers.append(CrossoverSignal(
                cross_type="DEATH_CROSS",
                fast_period=fast_period,
                slow_period=slow_period,
                fast_value=fast_ma[i],
                slow_value=slow_ma[i],
            ))

    return crossovers


def analyze_ma_alignment(
    candles: list[Candle],
    sma_periods: list[int] = None,
    ema_periods: list[int] = None,
) -> MAAlignment:
    """Analisa o alinhamento das médias móveis com o preço atual.

    Calcula:
    - Se as médias estão alinhadas (bullish ou bearish)
    - Distância do preço à MMA200
    - Cruzamentos recentes (Golden/Death Cross)
    - Score de alinhamento para confluence (0.0 a 1.0)
    """
    if sma_periods is None:
        sma_periods = [20, 50, 100, 200]
    if ema_periods is None:
        ema_periods = [9, 21, 50]

    if not candles:
        return MAAlignment(
            bullish_aligned=False, bearish_aligned=False,
            price_above_ma200=False, ma200_distance_pct=0.0,
            crossovers=[], score=0.0,
        )

    current_price = candles[-1].close

    # Calcular SMAs
    sma_values: dict[int, Decimal] = {}
    for period in sma_periods:
        sma = calculate_sma(candles, period)
        if sma and sma[-1] != 0:
            sma_values[period] = sma[-1]

    # Calcular EMAs
    ema_values: dict[int, Decimal] = {}
    for period in ema_periods:
        ema = calculate_ema(candles, period)
        if ema and ema[-1] != 0:
            ema_values[period] = ema[-1]

    # MMA200 — suporte macro
    ma200 = sma_values.get(200, Decimal("0"))
    price_above_ma200 = current_price > ma200 if ma200 > 0 else False
    ma200_distance_pct = 0.0
    if ma200 > 0:
        ma200_distance_pct = float((current_price - ma200) / ma200 * 100)

    # Verificar alinhamento bullish: preço > EMA9 > EMA21 > SMA50 > SMA200
    all_ma_values = []
    for p in sorted(ema_periods):
        if p in ema_values:
            all_ma_values.append(ema_values[p])
    for p in sorted(sma_periods):
        if p in sma_values and p not in ema_periods:
            all_ma_values.append(sma_values[p])

    bullish_aligned = False
    bearish_aligned = False

    if len(all_ma_values) >= 2:
        bullish_aligned = all(
            all_ma_values[i] >= all_ma_values[i + 1]
            for i in range(len(all_ma_values) - 1)
        ) and current_price > all_ma_values[0]

        bearish_aligned = all(
            all_ma_values[i] <= all_ma_values[i + 1]
            for i in range(len(all_ma_values) - 1)
        ) and current_price < all_ma_values[0]

    # Detectar Golden/Death Cross (SMA50 vs SMA200)
    crossovers: list[CrossoverSignal] = []
    if 50 in sma_periods and 200 in sma_periods:
        sma50_full = calculate_sma(candles, 50)
        sma200_full = calculate_sma(candles, 200)
        crossovers = detect_crossovers(sma50_full, sma200_full, 50, 200)

    # Score de alinhamento
    score = _calculate_alignment_score(
        current_price, sma_values, ema_values,
        bullish_aligned, bearish_aligned, price_above_ma200,
    )

    return MAAlignment(
        bullish_aligned=bullish_aligned,
        bearish_aligned=bearish_aligned,
        price_above_ma200=price_above_ma200,
        ma200_distance_pct=ma200_distance_pct,
        crossovers=crossovers,
        score=score,
    )


def _calculate_alignment_score(
    price: Decimal,
    sma_values: dict[int, Decimal],
    ema_values: dict[int, Decimal],
    bullish_aligned: bool,
    bearish_aligned: bool,
    price_above_ma200: bool,
) -> float:
    """Calcula score de 0.0 a 1.0 para o confluence."""
    score = 0.0

    # Alinhamento completo: +0.40
    if bullish_aligned or bearish_aligned:
        score += 0.40

    # Preço acima da MA200: +0.25
    if price_above_ma200:
        score += 0.25

    # Preço acima da EMA9 e EMA21: +0.20
    ema9 = ema_values.get(9, Decimal("0"))
    ema21 = ema_values.get(21, Decimal("0"))
    if ema9 > 0 and price > ema9:
        score += 0.10
    if ema21 > 0 and price > ema21:
        score += 0.10

    # EMA9 > EMA21: +0.15
    if ema9 > 0 and ema21 > 0 and ema9 > ema21:
        score += 0.15

    return min(1.0, score)
