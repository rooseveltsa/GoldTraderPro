"""Detecção de padrões de candlestick multi-candle.

Padrões implementados:
- Bullish Engulfing (Engolfo de Alta)
- Bearish Engulfing (Engolfo de Baixa)
- Morning Star (Estrela da Manhã)
- Evening Star (Estrela da Noite)
"""

from __future__ import annotations

from decimal import Decimal

from packages.core.models.candle import Candle
from packages.core.models.enums import Direction, PatternType
from packages.core.patterns.single_candle import PatternDetection, _no_detection

DEFAULT_ENGULFING_MIN_RATIO = Decimal("1.0")
DEFAULT_STAR_BODY_MAX_RATIO = Decimal("0.30")
DEFAULT_STAR_MID_BODY_MAX = Decimal("0.10")


def detect_bullish_engulfing(
    prev: Candle,
    curr: Candle,
    min_ratio: Decimal = DEFAULT_ENGULFING_MIN_RATIO,
) -> PatternDetection:
    """Detecta Engolfo de Alta (Bullish Engulfing).

    Condições:
    - prev é bearish (close < open)
    - curr é bullish (close > open)
    - corpo de curr engloba totalmente o corpo de prev
    - corpo de curr > corpo de prev
    """
    if not prev.is_bearish or not curr.is_bullish:
        return _no_detection(PatternType.BULLISH_ENGULFING)

    # Corpo de curr deve englobar corpo de prev
    curr_open = curr.open
    curr_close = curr.close
    prev_open = prev.open
    prev_close = prev.close

    if curr_open > prev_close or curr_close < prev_open:
        return _no_detection(PatternType.BULLISH_ENGULFING)

    if curr.body < prev.body * min_ratio:
        return _no_detection(PatternType.BULLISH_ENGULFING)

    # Força: quanto maior o engolfo relativo, mais forte
    if prev.body > 0:
        ratio = float(curr.body / prev.body)
        strength = min(1.0, ratio / 3.0)
    else:
        strength = 0.5

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.BULLISH_ENGULFING,
        direction=Direction.BULLISH,
        strength=strength,
    )


def detect_bearish_engulfing(
    prev: Candle,
    curr: Candle,
    min_ratio: Decimal = DEFAULT_ENGULFING_MIN_RATIO,
) -> PatternDetection:
    """Detecta Engolfo de Baixa (Bearish Engulfing).

    Condições:
    - prev é bullish (close > open)
    - curr é bearish (close < open)
    - corpo de curr engloba totalmente o corpo de prev
    - corpo de curr > corpo de prev
    """
    if not prev.is_bullish or not curr.is_bearish:
        return _no_detection(PatternType.BEARISH_ENGULFING)

    curr_open = curr.open
    curr_close = curr.close
    prev_open = prev.open
    prev_close = prev.close

    if curr_open < prev_close or curr_close > prev_open:
        return _no_detection(PatternType.BEARISH_ENGULFING)

    if curr.body < prev.body * min_ratio:
        return _no_detection(PatternType.BEARISH_ENGULFING)

    if prev.body > 0:
        ratio = float(curr.body / prev.body)
        strength = min(1.0, ratio / 3.0)
    else:
        strength = 0.5

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.BEARISH_ENGULFING,
        direction=Direction.BEARISH,
        strength=strength,
    )


def detect_morning_star(
    first: Candle,
    second: Candle,
    third: Candle,
    mid_body_max: Decimal = DEFAULT_STAR_MID_BODY_MAX,
) -> PatternDetection:
    """Detecta Estrela da Manhã (Morning Star).

    Condições (3 candles):
    1. Primeiro candle: bearish com corpo longo
    2. Segundo candle: corpo pequeno (doji ou corpo <= 10% amplitude)
    3. Terceiro candle: bullish com corpo longo, fecha acima de 50% do primeiro
    """
    # Primeiro deve ser bearish com corpo significativo
    if not first.is_bearish:
        return _no_detection(PatternType.MORNING_STAR)
    if first.amplitude > 0 and first.body_ratio < Decimal("0.40"):
        return _no_detection(PatternType.MORNING_STAR)

    # Segundo deve ter corpo pequeno
    if second.amplitude > 0 and second.body_ratio > mid_body_max:
        return _no_detection(PatternType.MORNING_STAR)

    # Terceiro deve ser bullish com corpo significativo
    if not third.is_bullish:
        return _no_detection(PatternType.MORNING_STAR)
    if third.amplitude > 0 and third.body_ratio < Decimal("0.40"):
        return _no_detection(PatternType.MORNING_STAR)

    # Terceiro deve fechar acima do ponto médio do primeiro
    first_midpoint = (first.open + first.close) / 2
    if third.close < first_midpoint:
        return _no_detection(PatternType.MORNING_STAR)

    # Força baseada em quão alto o terceiro fecha em relação ao primeiro
    if first.body > 0:
        recovery = float((third.close - first.close) / first.body)
        strength = min(1.0, recovery / 1.5)
    else:
        strength = 0.5

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.MORNING_STAR,
        direction=Direction.BULLISH,
        strength=max(0.3, strength),
    )


def detect_evening_star(
    first: Candle,
    second: Candle,
    third: Candle,
    mid_body_max: Decimal = DEFAULT_STAR_MID_BODY_MAX,
) -> PatternDetection:
    """Detecta Estrela da Noite (Evening Star).

    Condições (3 candles):
    1. Primeiro candle: bullish com corpo longo
    2. Segundo candle: corpo pequeno (doji ou corpo <= 10% amplitude)
    3. Terceiro candle: bearish com corpo longo, fecha abaixo de 50% do primeiro
    """
    if not first.is_bullish:
        return _no_detection(PatternType.EVENING_STAR)
    if first.amplitude > 0 and first.body_ratio < Decimal("0.40"):
        return _no_detection(PatternType.EVENING_STAR)

    if second.amplitude > 0 and second.body_ratio > mid_body_max:
        return _no_detection(PatternType.EVENING_STAR)

    if not third.is_bearish:
        return _no_detection(PatternType.EVENING_STAR)
    if third.amplitude > 0 and third.body_ratio < Decimal("0.40"):
        return _no_detection(PatternType.EVENING_STAR)

    first_midpoint = (first.open + first.close) / 2
    if third.close > first_midpoint:
        return _no_detection(PatternType.EVENING_STAR)

    if first.body > 0:
        recovery = float((first.close - third.close) / first.body)
        strength = min(1.0, recovery / 1.5)
    else:
        strength = 0.5

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.EVENING_STAR,
        direction=Direction.BEARISH,
        strength=max(0.3, strength),
    )


def scan_multi_candle(candles: list[Candle]) -> list[PatternDetection]:
    """Escaneia uma lista de candles para padrões multi-candle.

    Analisa os últimos candles disponíveis:
    - 2-candle patterns: usa candles[-2] e candles[-1]
    - 3-candle patterns: usa candles[-3], candles[-2] e candles[-1]

    Retorna lista de padrões detectados no último candle.
    """
    detections: list[PatternDetection] = []

    if len(candles) < 2:
        return detections

    prev = candles[-2]
    curr = candles[-1]

    # 2-candle patterns
    for detector in [detect_bullish_engulfing, detect_bearish_engulfing]:
        result = detector(prev, curr)
        if result.detected:
            detections.append(result)

    # 3-candle patterns
    if len(candles) >= 3:
        first = candles[-3]
        for detector in [detect_morning_star, detect_evening_star]:
            result = detector(first, prev, curr)
            if result.detected:
                detections.append(result)

    return detections
