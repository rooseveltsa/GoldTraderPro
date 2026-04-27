"""Detecção de padrões de candlestick de candle único.

Padrões implementados:
- Hammer (Martelo)
- Inverted Hammer (Martelo Invertido)
- Shooting Star (Estrela Cadente)
- Hanging Man (Enforcado)
- Doji
- Dragonfly Doji
- Gravestone Doji

Cada padrão é parametrizado com regras matemáticas rigorosas
conforme especificado no PRD, evitando falsos positivos.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from packages.core.models.candle import Candle
from packages.core.models.enums import Direction, PatternType


@dataclass(frozen=True)
class PatternDetection:
    """Resultado da detecção de um padrão."""

    detected: bool
    pattern_type: PatternType
    direction: Direction
    strength: float  # 0.0 a 1.0


# Constantes padrão (configuráveis via config)
DEFAULT_BODY_MAX_RATIO = Decimal("0.30")      # corpo <= 30% amplitude
DEFAULT_WICK_MIN_RATIO = Decimal("2.0")        # pavio >= 2x corpo
DEFAULT_WICK_MAX_OPPOSITE = Decimal("0.10")    # pavio oposto <= 10% amplitude
DEFAULT_DOJI_THRESHOLD = Decimal("0.05")       # corpo <= 5% amplitude
DEFAULT_DRAGONFLY_WICK_RATIO = Decimal("3.0")  # pavio >= 3x corpo (doji variants)


def _no_detection(pattern_type: PatternType) -> PatternDetection:
    return PatternDetection(
        detected=False, pattern_type=pattern_type,
        direction=Direction.NEUTRAL, strength=0.0,
    )


def detect_hammer(
    candle: Candle,
    body_max_ratio: Decimal = DEFAULT_BODY_MAX_RATIO,
    wick_min_ratio: Decimal = DEFAULT_WICK_MIN_RATIO,
    wick_max_opposite: Decimal = DEFAULT_WICK_MAX_OPPOSITE,
) -> PatternDetection:
    """Detecta padrão Martelo (Hammer).

    Condições:
    - corpo <= 30% da amplitude
    - pavio inferior >= 2x corpo
    - pavio superior <= 10% da amplitude
    - Contexto esperado: exaustão de tendência de baixa (suporte)
    """
    if candle.amplitude == 0:
        return _no_detection(PatternType.HAMMER)

    if candle.body_ratio > body_max_ratio:
        return _no_detection(PatternType.HAMMER)

    body = candle.body
    if body == 0:
        return _no_detection(PatternType.HAMMER)

    if candle.lower_wick < wick_min_ratio * body:
        return _no_detection(PatternType.HAMMER)

    if candle.upper_wick_ratio > wick_max_opposite:
        return _no_detection(PatternType.HAMMER)

    # Força: quanto maior o pavio inferior relativo ao corpo, mais forte
    wick_body_ratio = float(candle.lower_wick / body) if body > 0 else 0
    strength = min(1.0, wick_body_ratio / 5.0)  # normaliza até 5x

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.HAMMER,
        direction=Direction.BULLISH,
        strength=strength,
    )


def detect_inverted_hammer(
    candle: Candle,
    body_max_ratio: Decimal = DEFAULT_BODY_MAX_RATIO,
    wick_min_ratio: Decimal = DEFAULT_WICK_MIN_RATIO,
    wick_max_opposite: Decimal = DEFAULT_WICK_MAX_OPPOSITE,
) -> PatternDetection:
    """Detecta padrão Martelo Invertido (Inverted Hammer).

    Condições:
    - corpo <= 30% da amplitude
    - pavio superior >= 2x corpo
    - pavio inferior <= 10% da amplitude
    """
    if candle.amplitude == 0:
        return _no_detection(PatternType.INVERTED_HAMMER)

    if candle.body_ratio > body_max_ratio:
        return _no_detection(PatternType.INVERTED_HAMMER)

    body = candle.body
    if body == 0:
        return _no_detection(PatternType.INVERTED_HAMMER)

    if candle.upper_wick < wick_min_ratio * body:
        return _no_detection(PatternType.INVERTED_HAMMER)

    if candle.lower_wick_ratio > wick_max_opposite:
        return _no_detection(PatternType.INVERTED_HAMMER)

    wick_body_ratio = float(candle.upper_wick / body) if body > 0 else 0
    strength = min(1.0, wick_body_ratio / 5.0)

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.INVERTED_HAMMER,
        direction=Direction.BULLISH,
        strength=strength,
    )


def detect_shooting_star(
    candle: Candle,
    body_max_ratio: Decimal = DEFAULT_BODY_MAX_RATIO,
    wick_min_ratio: Decimal = DEFAULT_WICK_MIN_RATIO,
    wick_max_opposite: Decimal = DEFAULT_WICK_MAX_OPPOSITE,
) -> PatternDetection:
    """Detecta padrão Estrela Cadente (Shooting Star).

    Condições:
    - corpo <= 30% da amplitude
    - pavio superior >= 2x corpo
    - fechamento próximo da mínima (pavio inferior <= 10% amplitude)
    """
    if candle.amplitude == 0:
        return _no_detection(PatternType.SHOOTING_STAR)

    if candle.body_ratio > body_max_ratio:
        return _no_detection(PatternType.SHOOTING_STAR)

    body = candle.body
    if body == 0:
        return _no_detection(PatternType.SHOOTING_STAR)

    if candle.upper_wick < wick_min_ratio * body:
        return _no_detection(PatternType.SHOOTING_STAR)

    if candle.lower_wick_ratio > wick_max_opposite:
        return _no_detection(PatternType.SHOOTING_STAR)

    wick_body_ratio = float(candle.upper_wick / body) if body > 0 else 0
    strength = min(1.0, wick_body_ratio / 5.0)

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.SHOOTING_STAR,
        direction=Direction.BEARISH,
        strength=strength,
    )


def detect_hanging_man(
    candle: Candle,
    body_max_ratio: Decimal = DEFAULT_BODY_MAX_RATIO,
    wick_min_ratio: Decimal = DEFAULT_WICK_MIN_RATIO,
    wick_max_opposite: Decimal = DEFAULT_WICK_MAX_OPPOSITE,
) -> PatternDetection:
    """Detecta padrão Enforcado (Hanging Man).

    Mesma forma do Martelo, mas em contexto de topo (BEARISH).
    A diferenciação de contexto é feita pelo chamador.
    Estruturalmente idêntico ao Hammer.
    """
    if candle.amplitude == 0:
        return _no_detection(PatternType.HANGING_MAN)

    if candle.body_ratio > body_max_ratio:
        return _no_detection(PatternType.HANGING_MAN)

    body = candle.body
    if body == 0:
        return _no_detection(PatternType.HANGING_MAN)

    if candle.lower_wick < wick_min_ratio * body:
        return _no_detection(PatternType.HANGING_MAN)

    if candle.upper_wick_ratio > wick_max_opposite:
        return _no_detection(PatternType.HANGING_MAN)

    wick_body_ratio = float(candle.lower_wick / body) if body > 0 else 0
    strength = min(1.0, wick_body_ratio / 5.0)

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.HANGING_MAN,
        direction=Direction.BEARISH,
        strength=strength,
    )


def detect_doji(
    candle: Candle,
    doji_threshold: Decimal = DEFAULT_DOJI_THRESHOLD,
) -> PatternDetection:
    """Detecta padrão Doji.

    Condições:
    - corpo <= 5% da amplitude (abertura ≈ fechamento)
    - Sinaliza indecisão / potencial reversão
    """
    if candle.amplitude == 0:
        # Candle sem movimento — tecnicamente um doji perfeito
        return PatternDetection(
            detected=True,
            pattern_type=PatternType.DOJI,
            direction=Direction.NEUTRAL,
            strength=1.0,
        )

    if candle.body_ratio > doji_threshold:
        return _no_detection(PatternType.DOJI)

    # Força inversamente proporcional ao body ratio
    strength = 1.0 - float(candle.body_ratio / doji_threshold)

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.DOJI,
        direction=Direction.NEUTRAL,
        strength=min(1.0, strength),
    )


def detect_dragonfly_doji(
    candle: Candle,
    doji_threshold: Decimal = DEFAULT_DOJI_THRESHOLD,
    wick_ratio: Decimal = DEFAULT_DRAGONFLY_WICK_RATIO,
    wick_max_opposite: Decimal = DEFAULT_WICK_MAX_OPPOSITE,
) -> PatternDetection:
    """Detecta padrão Dragonfly Doji.

    Condições:
    - É um doji (corpo <= 5% amplitude)
    - pavio inferior >= 3x corpo
    - pavio superior <= 5% amplitude
    """
    if candle.amplitude == 0:
        return _no_detection(PatternType.DRAGONFLY_DOJI)

    if candle.body_ratio > doji_threshold:
        return _no_detection(PatternType.DRAGONFLY_DOJI)

    body = candle.body
    if body > 0 and candle.lower_wick < wick_ratio * body:
        return _no_detection(PatternType.DRAGONFLY_DOJI)

    # Pavio superior deve ser mínimo
    if candle.upper_wick_ratio > wick_max_opposite:
        return _no_detection(PatternType.DRAGONFLY_DOJI)

    # Precisa ter pavio inferior significativo
    if candle.lower_wick_ratio < Decimal("0.60"):
        return _no_detection(PatternType.DRAGONFLY_DOJI)

    strength = min(1.0, float(candle.lower_wick_ratio))

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.DRAGONFLY_DOJI,
        direction=Direction.BULLISH,
        strength=strength,
    )


def detect_gravestone_doji(
    candle: Candle,
    doji_threshold: Decimal = DEFAULT_DOJI_THRESHOLD,
    wick_ratio: Decimal = DEFAULT_DRAGONFLY_WICK_RATIO,
    wick_max_opposite: Decimal = DEFAULT_WICK_MAX_OPPOSITE,
) -> PatternDetection:
    """Detecta padrão Gravestone Doji.

    Condições:
    - É um doji (corpo <= 5% amplitude)
    - pavio superior >= 3x corpo
    - pavio inferior <= 5% amplitude
    """
    if candle.amplitude == 0:
        return _no_detection(PatternType.GRAVESTONE_DOJI)

    if candle.body_ratio > doji_threshold:
        return _no_detection(PatternType.GRAVESTONE_DOJI)

    body = candle.body
    if body > 0 and candle.upper_wick < wick_ratio * body:
        return _no_detection(PatternType.GRAVESTONE_DOJI)

    if candle.lower_wick_ratio > wick_max_opposite:
        return _no_detection(PatternType.GRAVESTONE_DOJI)

    if candle.upper_wick_ratio < Decimal("0.60"):
        return _no_detection(PatternType.GRAVESTONE_DOJI)

    strength = min(1.0, float(candle.upper_wick_ratio))

    return PatternDetection(
        detected=True,
        pattern_type=PatternType.GRAVESTONE_DOJI,
        direction=Direction.BEARISH,
        strength=strength,
    )


# Registry de todos os detectores single-candle
SINGLE_CANDLE_DETECTORS = [
    detect_hammer,
    detect_inverted_hammer,
    detect_shooting_star,
    detect_hanging_man,
    detect_doji,
    detect_dragonfly_doji,
    detect_gravestone_doji,
]


def scan_single_candle(candle: Candle) -> list[PatternDetection]:
    """Escaneia um candle contra todos os padrões single-candle.

    Retorna lista de padrões detectados (pode ser vazio).
    """
    detections = []
    for detector in SINGLE_CANDLE_DETECTORS:
        result = detector(candle)
        if result.detected:
            detections.append(result)
    return detections
