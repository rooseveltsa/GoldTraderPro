"""Pattern Engine — orquestrador de detecção de padrões."""

from __future__ import annotations

from packages.core.models.candle import Candle
from packages.core.patterns.multi_candle import scan_multi_candle
from packages.core.patterns.single_candle import PatternDetection, scan_single_candle


class PatternEngine:
    """Motor de detecção de padrões de candlestick.

    Combina detecção single-candle e multi-candle,
    retornando todos os padrões encontrados no último candle.
    """

    def scan(self, candles: list[Candle]) -> list[PatternDetection]:
        """Escaneia candles para todos os padrões disponíveis.

        Analisa o último candle (single) e a sequência recente (multi).
        Retorna lista de detecções ordenada por força (strength desc).
        """
        if not candles:
            return []

        detections: list[PatternDetection] = []

        # Single-candle: analisa o último candle
        single_results = scan_single_candle(candles[-1])
        detections.extend(single_results)

        # Multi-candle: analisa a sequência recente
        if len(candles) >= 2:
            multi_results = scan_multi_candle(candles)
            detections.extend(multi_results)

        # Ordena por força decrescente
        detections.sort(key=lambda d: d.strength, reverse=True)

        return detections
