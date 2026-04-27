"""Multi-Timeframe Validator — regra do "Passo Atrás".

Sinal em M15 → Validar em D1 → Confirmar em W1

Matriz de validação:
| Sinal M15 | D1     | W1      | Decisão              |
|-----------|--------|---------|----------------------|
| COMPRA    | ALTA   | ALTA    | EXECUTAR (+bonus)    |
| COMPRA    | ALTA   | LATERAL | EXECUTAR             |
| COMPRA    | ALTA   | BAIXA   | REJEITAR             |
| COMPRA    | LATERAL| -       | REJEITAR (sem inércia)|
| COMPRA    | BAIXA  | -       | REJEITAR (contra-fluxo)|
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from packages.core.models.candle import Candle
from packages.core.models.enums import Direction, TrendDirection
from packages.core.indicators.moving_averages import calculate_ema, calculate_sma


@dataclass(frozen=True)
class MultiTFValidation:
    """Resultado da validação multi-timeframe."""

    is_aligned: bool
    primary_trend: TrendDirection    # D1
    macro_trend: TrendDirection      # W1
    signal_direction: Direction
    rejection_reason: str            # "" se aprovado
    bonus: float                     # bonus ao confluence (0.0 ou 0.10)


def validate_multi_timeframe(
    signal_direction: Direction,
    primary_candles: list[Candle],
    macro_candles: list[Candle],
    ema_period: int = 21,
    sma_period: int = 50,
) -> MultiTFValidation:
    """Valida se o sinal está alinhado com os timeframes superiores.

    Args:
        signal_direction: Direção do sinal no timeframe operacional (M15)
        primary_candles: Candles do timeframe primário (D1)
        macro_candles: Candles do timeframe macro (W1)
        ema_period: Período da EMA para detecção de tendência
        sma_period: Período da SMA para detecção de tendência
    """
    primary_trend = _detect_trend(primary_candles, ema_period, sma_period)
    macro_trend = _detect_trend(macro_candles, ema_period, sma_period)

    if signal_direction == Direction.NEUTRAL:
        return MultiTFValidation(
            is_aligned=False,
            primary_trend=primary_trend,
            macro_trend=macro_trend,
            signal_direction=signal_direction,
            rejection_reason="Sinal neutro não requer validação multi-TF",
            bonus=0.0,
        )

    is_aligned, rejection_reason, bonus = _apply_validation_matrix(
        signal_direction, primary_trend, macro_trend,
    )

    return MultiTFValidation(
        is_aligned=is_aligned,
        primary_trend=primary_trend,
        macro_trend=macro_trend,
        signal_direction=signal_direction,
        rejection_reason=rejection_reason,
        bonus=bonus,
    )


def _detect_trend(
    candles: list[Candle],
    ema_period: int = 21,
    sma_period: int = 50,
) -> TrendDirection:
    """Detecta a tendência de uma série de candles.

    Usa EMA e SMA + direção do preço em relação às médias.
    """
    if len(candles) < sma_period + 1:
        return TrendDirection.LATERAL

    ema = calculate_ema(candles, ema_period)
    sma = calculate_sma(candles, sma_period)

    current_price = candles[-1].close
    current_ema = ema[-1]
    current_sma = sma[-1]

    if current_ema == 0 or current_sma == 0:
        return TrendDirection.LATERAL

    price_above_ema = current_price > current_ema
    price_above_sma = current_price > current_sma
    ema_above_sma = current_ema > current_sma

    # EMA crescente nos últimos 5 períodos
    ema_rising = False
    ema_falling = False
    if len(ema) >= 6:
        recent_ema = ema[-5:]
        if all(recent_ema[i] > 0 for i in range(len(recent_ema))):
            ema_rising = all(recent_ema[i] >= recent_ema[i - 1] for i in range(1, len(recent_ema)))
            ema_falling = all(recent_ema[i] <= recent_ema[i - 1] for i in range(1, len(recent_ema)))

    if price_above_ema and price_above_sma and ema_above_sma and ema_rising:
        return TrendDirection.UP
    elif not price_above_ema and not price_above_sma and not ema_above_sma and ema_falling:
        return TrendDirection.DOWN
    else:
        return TrendDirection.LATERAL


def _apply_validation_matrix(
    signal: Direction,
    primary: TrendDirection,
    macro: TrendDirection,
) -> tuple:
    """Aplica a matriz de validação multi-timeframe.

    Returns:
        (is_aligned, rejection_reason, bonus)
    """
    if signal == Direction.BULLISH:
        if primary == TrendDirection.UP:
            if macro == TrendDirection.UP:
                return (True, "", 0.10)  # Alinhamento total + bonus
            elif macro == TrendDirection.LATERAL:
                return (True, "", 0.0)   # Alinhado sem bonus
            else:  # DOWN
                return (False, "Contra-fluxo macro: W1 em baixa", 0.0)
        elif primary == TrendDirection.LATERAL:
            return (False, "Sem inércia: D1 lateral", 0.0)
        else:  # DOWN
            return (False, "Contra-fluxo: D1 em baixa", 0.0)

    elif signal == Direction.BEARISH:
        if primary == TrendDirection.DOWN:
            if macro == TrendDirection.DOWN:
                return (True, "", 0.10)
            elif macro == TrendDirection.LATERAL:
                return (True, "", 0.0)
            else:  # UP
                return (False, "Contra-fluxo macro: W1 em alta", 0.0)
        elif primary == TrendDirection.LATERAL:
            return (False, "Sem inércia: D1 lateral", 0.0)
        else:  # UP
            return (False, "Contra-fluxo: D1 em alta", 0.0)

    return (False, "Direção não reconhecida", 0.0)
