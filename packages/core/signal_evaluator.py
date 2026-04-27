"""Signal Evaluator — orquestrador central que combina todos os módulos.

Fluxo de avaliação:
1. Pattern Engine detecta padrões no candle atual
2. Volume Analyzer valida o volume
3. Indicator Engine calcula ADX, RSI, Didi, MAs
4. Multi-TF Validator confirma alinhamento
5. Confluence Score é calculado
6. Sinal é emitido se score >= 0.65
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from packages.core.indicators.adx import calculate_adx
from packages.core.indicators.didi_index import calculate_didi
from packages.core.indicators.moving_averages import analyze_ma_alignment
from packages.core.indicators.rsi import calculate_rsi
from packages.core.models.candle import Candle
from packages.core.models.enums import (
    Direction,
    MarketContext,
    SystemState,
    Timeframe,
    VolumeVerdict,
)
from packages.core.models.signal import ConfluenceScore, PatternSignal
from packages.core.multi_tf.validator import validate_multi_timeframe
from packages.core.patterns.engine import PatternEngine
from packages.core.patterns.single_candle import PatternDetection
from packages.core.volume.analyzer import analyze_volume


class SignalEvaluator:
    """Avaliador central de sinais.

    Combina Pattern Engine, Indicators, Volume e Multi-TF
    para gerar sinais com Confluence Score.
    """

    def __init__(
        self,
        min_confluence: float = 0.65,
        min_risk_reward: float = 1.5,
        adx_threshold: float = 32.0,
    ) -> None:
        self._pattern_engine = PatternEngine()
        self._min_confluence = min_confluence
        self._min_risk_reward = min_risk_reward
        self._adx_threshold = adx_threshold

    def evaluate(
        self,
        operational_candles: list[Candle],
        primary_candles: Optional[list[Candle]] = None,
        macro_candles: Optional[list[Candle]] = None,
        timeframe: Timeframe = Timeframe.M15,
    ) -> list[PatternSignal]:
        """Avalia os candles e retorna sinais qualificados.

        Args:
            operational_candles: Candles do timeframe operacional (M15)
            primary_candles: Candles do timeframe primário (D1) para multi-TF
            macro_candles: Candles do timeframe macro (W1) para multi-TF
            timeframe: Timeframe operacional

        Returns:
            Lista de PatternSignal qualificados (pode ser vazia)
        """
        if not operational_candles:
            return []

        # 1. ADX Gate — se não há tendência, retornar vazio
        adx_result = calculate_adx(
            operational_candles, trend_threshold=self._adx_threshold,
        )
        if adx_result.system_state == SystemState.WAIT:
            return []  # Mercado congestionado — modo WAIT

        # 2. Detectar padrões
        detections = self._pattern_engine.scan(operational_candles)
        if not detections:
            return []

        # 3. Calcular indicadores
        rsi_result = calculate_rsi(operational_candles)
        didi_result = calculate_didi(operational_candles)
        ma_result = analyze_ma_alignment(operational_candles)

        # 4. Analisar volume
        volume_analysis = analyze_volume(operational_candles)

        # 5. Para cada padrão detectado, construir sinal
        signals: list[PatternSignal] = []

        for detection in detections:
            signal = self._build_signal(
                detection=detection,
                candles=operational_candles,
                timeframe=timeframe,
                adx_score=adx_result.score,
                rsi_score=rsi_result.score,
                didi_score=didi_result.score,
                ma_score=ma_result.score,
                volume_verdict=volume_analysis.verdict,
                volume_score=volume_analysis.score,
                primary_candles=primary_candles,
                macro_candles=macro_candles,
            )
            if signal is not None:
                signals.append(signal)

        # Ordenar por confluence score
        signals.sort(key=lambda s: s.confluence.total, reverse=True)

        return signals

    def _build_signal(
        self,
        detection: PatternDetection,
        candles: list[Candle],
        timeframe: Timeframe,
        adx_score: float,
        rsi_score: float,
        didi_score: float,
        ma_score: float,
        volume_verdict: VolumeVerdict,
        volume_score: float,
        primary_candles: Optional[list[Candle]],
        macro_candles: Optional[list[Candle]],
    ) -> Optional[PatternSignal]:
        """Constrói um PatternSignal completo a partir de uma detecção."""
        current_candle = candles[-1]

        # Multi-TF validation
        multi_tf_aligned = False
        bonus = 0.0

        if primary_candles and macro_candles:
            mtf = validate_multi_timeframe(
                signal_direction=detection.direction,
                primary_candles=primary_candles,
                macro_candles=macro_candles,
            )
            multi_tf_aligned = mtf.is_aligned
            bonus = mtf.bonus
        else:
            # Sem dados multi-TF, assume alinhado (para backtesting single-TF)
            multi_tf_aligned = True

        # Calcular preços de entrada, stop loss e take profit
        entry_price, stop_loss, take_profit = self._calculate_order_levels(
            detection.direction, current_candle,
        )

        # Confluence Score
        confluence = ConfluenceScore(
            pattern_score=detection.strength,
            volume_score=volume_score,
            adx_score=adx_score,
            ma_alignment_score=ma_score + bonus,
            rsi_score=rsi_score,
            didi_score=didi_score,
        )

        # Contexto de mercado
        context = self._determine_context(detection.direction, candles)

        return PatternSignal(
            timestamp=datetime.utcnow(),
            pattern_type=detection.pattern_type,
            direction=detection.direction,
            strength=detection.strength,
            timeframe=timeframe,
            candle_timestamp=current_candle.timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confirmation_required=True,
            volume_verdict=volume_verdict,
            context=context,
            confluence=confluence,
            multi_tf_aligned=multi_tf_aligned,
        )

    def _calculate_order_levels(
        self,
        direction: Direction,
        candle: Candle,
    ) -> tuple:
        """Calcula entry, stop loss e take profit.

        COMPRA: entry = close, SL = low do candle, TP = 1.5x risco
        VENDA: entry = close, SL = high do candle, TP = 1.5x risco
        """
        entry = candle.close

        if direction == Direction.BULLISH:
            stop_loss = candle.low
            risk = entry - stop_loss
            take_profit = entry + risk * Decimal(str(self._min_risk_reward))
        elif direction == Direction.BEARISH:
            stop_loss = candle.high
            risk = stop_loss - entry
            take_profit = entry - risk * Decimal(str(self._min_risk_reward))
        else:
            stop_loss = candle.low
            take_profit = candle.high

        return (entry, stop_loss, take_profit)

    @staticmethod
    def _determine_context(
        direction: Direction,
        candles: list[Candle],
    ) -> MarketContext:
        """Determina o contexto de mercado baseado na posição do preço."""
        if len(candles) < 20:
            return MarketContext.CONGESTION

        recent_highs = [c.high for c in candles[-20:]]
        recent_lows = [c.low for c in candles[-20:]]
        current = candles[-1].close

        highest = max(recent_highs)
        lowest = min(recent_lows)
        range_size = highest - lowest

        if range_size == 0:
            return MarketContext.CONGESTION

        position = (current - lowest) / range_size

        if position < Decimal("0.20"):
            return MarketContext.SUPPORT
        elif position > Decimal("0.80"):
            return MarketContext.RESISTANCE
        elif direction == Direction.BULLISH:
            return MarketContext.TREND_UP
        elif direction == Direction.BEARISH:
            return MarketContext.TREND_DOWN
        else:
            return MarketContext.CONGESTION
