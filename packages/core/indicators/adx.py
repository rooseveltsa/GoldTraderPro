"""Average Directional Index (ADX) — filtro de tendência.

O ADX mede a FORÇA da tendência, não a direção.
- ADX > 32: tendência válida → sistema em modo TRADING
- ADX < 32: congestionamento → sistema em modo WAIT

DI+ e DI- determinam a direção:
- DI+ > DI-: tendência de alta
- DI- > DI+: tendência de baixa
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List

from packages.core.models.candle import Candle
from packages.core.models.enums import SystemState, TrendDirection


@dataclass(frozen=True)
class ADXResult:
    """Resultado do cálculo do ADX."""

    adx: float
    di_plus: float
    di_minus: float
    trend_direction: TrendDirection
    system_state: SystemState
    score: float  # 0.0 a 1.0 para confluence


def calculate_adx(
    candles: list[Candle],
    period: int = 14,
    trend_threshold: float = 32.0,
) -> ADXResult:
    """Calcula o ADX (Average Directional Index).

    Algoritmo:
    1. Calcula True Range (TR)
    2. Calcula +DM e -DM (Directional Movement)
    3. Suaviza TR, +DM, -DM com período
    4. Calcula +DI e -DI
    5. Calcula DX
    6. Suaviza DX → ADX
    """
    if len(candles) < period * 2 + 1:
        return ADXResult(
            adx=0.0, di_plus=0.0, di_minus=0.0,
            trend_direction=TrendDirection.LATERAL,
            system_state=SystemState.WAIT, score=0.0,
        )

    # True Range, +DM, -DM
    tr_list: List[float] = []
    plus_dm_list: List[float] = []
    minus_dm_list: List[float] = []

    for i in range(1, len(candles)):
        high = float(candles[i].high)
        low = float(candles[i].low)
        prev_close = float(candles[i - 1].close)
        prev_high = float(candles[i - 1].high)
        prev_low = float(candles[i - 1].low)

        # True Range
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)

        # +DM e -DM
        up_move = high - prev_high
        down_move = prev_low - low

        if up_move > down_move and up_move > 0:
            plus_dm_list.append(up_move)
        else:
            plus_dm_list.append(0.0)

        if down_move > up_move and down_move > 0:
            minus_dm_list.append(down_move)
        else:
            minus_dm_list.append(0.0)

    # Suavização Wilder (primeira = soma, depois = prev - prev/period + current)
    smoothed_tr = _wilder_smooth(tr_list, period)
    smoothed_plus_dm = _wilder_smooth(plus_dm_list, period)
    smoothed_minus_dm = _wilder_smooth(minus_dm_list, period)

    if not smoothed_tr:
        return ADXResult(
            adx=0.0, di_plus=0.0, di_minus=0.0,
            trend_direction=TrendDirection.LATERAL,
            system_state=SystemState.WAIT, score=0.0,
        )

    # +DI e -DI
    di_plus_list: List[float] = []
    di_minus_list: List[float] = []
    dx_list: List[float] = []

    for i in range(len(smoothed_tr)):
        if smoothed_tr[i] == 0:
            di_plus_list.append(0.0)
            di_minus_list.append(0.0)
            dx_list.append(0.0)
            continue

        di_plus = (smoothed_plus_dm[i] / smoothed_tr[i]) * 100
        di_minus = (smoothed_minus_dm[i] / smoothed_tr[i]) * 100
        di_plus_list.append(di_plus)
        di_minus_list.append(di_minus)

        di_sum = di_plus + di_minus
        if di_sum == 0:
            dx_list.append(0.0)
        else:
            dx = abs(di_plus - di_minus) / di_sum * 100
            dx_list.append(dx)

    # ADX = suavização de DX
    adx_values = _wilder_smooth(dx_list, period)

    if not adx_values:
        return ADXResult(
            adx=0.0, di_plus=0.0, di_minus=0.0,
            trend_direction=TrendDirection.LATERAL,
            system_state=SystemState.WAIT, score=0.0,
        )

    adx = adx_values[-1]
    di_plus = di_plus_list[-1] if di_plus_list else 0.0
    di_minus = di_minus_list[-1] if di_minus_list else 0.0

    # Direção da tendência
    if di_plus > di_minus:
        trend = TrendDirection.UP
    elif di_minus > di_plus:
        trend = TrendDirection.DOWN
    else:
        trend = TrendDirection.LATERAL

    # Estado do sistema
    state = SystemState.TRADING if adx >= trend_threshold else SystemState.WAIT

    # Score para confluence
    score = _calculate_adx_score(adx, trend_threshold)

    return ADXResult(
        adx=round(adx, 2),
        di_plus=round(di_plus, 2),
        di_minus=round(di_minus, 2),
        trend_direction=trend,
        system_state=state,
        score=score,
    )


def _wilder_smooth(data: list[float], period: int) -> list[float]:
    """Suavização de Wilder (usada em TR, DM, DX)."""
    if len(data) < period:
        return []

    result: list[float] = []
    # Primeira valor = soma dos primeiros N
    first = sum(data[:period])
    result.append(first)

    for i in range(period, len(data)):
        smoothed = result[-1] - (result[-1] / period) + data[i]
        result.append(smoothed)

    return result


def _calculate_adx_score(adx: float, threshold: float) -> float:
    """Score de 0.0 a 1.0 baseado no ADX para o confluence."""
    if adx < threshold:
        return 0.0
    # Score linear de threshold até 60
    normalized = (adx - threshold) / (60 - threshold)
    return min(1.0, max(0.0, normalized))
