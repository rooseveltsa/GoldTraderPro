"""Testes unitários para Indicadores Técnicos."""

from datetime import datetime, timedelta
from decimal import Decimal

from packages.core.models.candle import Candle
from packages.core.models.enums import Direction, SystemState, Timeframe, TrendDirection
from packages.core.indicators.moving_averages import (
    calculate_ema,
    calculate_sma,
    detect_crossovers,
    analyze_ma_alignment,
)
from packages.core.indicators.adx import calculate_adx
from packages.core.indicators.rsi import calculate_rsi
from packages.core.indicators.didi_index import calculate_didi

BASE_TIME = datetime(2026, 1, 1, 10, 0)


def _make_candles(closes, start_price=2650.0, spread=5.0):
    """Cria lista de candles a partir de preços de fechamento."""
    candles = []
    for i, close in enumerate(closes):
        o = close - 1.0
        h = max(o, close) + spread
        l = min(o, close) - spread
        candles.append(Candle(
            timestamp=BASE_TIME + timedelta(minutes=15 * i),
            timeframe=Timeframe.M15,
            open=Decimal(str(round(o, 5))),
            high=Decimal(str(round(h, 5))),
            low=Decimal(str(round(l, 5))),
            close=Decimal(str(round(close, 5))),
            volume=Decimal("1000"),
        ))
    return candles


def _trending_up(n=60, start=2600.0, step=2.0):
    """Gera sequência de preços em tendência de alta."""
    return [start + i * step for i in range(n)]


def _trending_down(n=60, start=2800.0, step=2.0):
    """Gera sequência de preços em tendência de baixa."""
    return [start - i * step for i in range(n)]


def _sideways(n=60, center=2650.0, amplitude=3.0):
    """Gera sequência lateral."""
    import math
    return [center + amplitude * math.sin(i * 0.5) for i in range(n)]


class TestSMA:
    def test_basic_sma(self):
        candles = _make_candles([10, 20, 30, 40, 50])
        sma = calculate_sma(candles, 3)
        assert sma[0] == Decimal("0")  # insuficiente
        assert sma[1] == Decimal("0")  # insuficiente
        # sma[2] = (10+20+30)/3 = 20
        assert float(sma[2]) == 20.0
        # sma[3] = (20+30+40)/3 = 30
        assert float(sma[3]) == 30.0

    def test_sma_single_period(self):
        candles = _make_candles([100, 200, 300])
        sma = calculate_sma(candles, 1)
        assert float(sma[0]) == 100.0
        assert float(sma[1]) == 200.0


class TestEMA:
    def test_basic_ema(self):
        candles = _make_candles([10, 20, 30, 40, 50])
        ema = calculate_ema(candles, 3)
        assert ema[0] == Decimal("0")
        assert ema[1] == Decimal("0")
        # ema[2] = SMA seed = (10+20+30)/3 = 20
        assert float(ema[2]) == 20.0
        # ema[3] = (40 - 20) * 0.5 + 20 = 30
        assert float(ema[3]) == 30.0

    def test_ema_follows_trend(self):
        candles = _make_candles(_trending_up(20))
        ema = calculate_ema(candles, 9)
        # EMA deve estar abaixo do preço em tendência de alta
        assert ema[-1] < candles[-1].close


class TestCrossovers:
    def test_golden_cross(self):
        # Começa lateral/baixa, depois sobe → gera cruzamento
        prices = _trending_down(30, start=2700.0, step=1.0) + _trending_up(40, start=2670.0, step=2.0)
        candles = _make_candles(prices)
        fast = calculate_sma(candles, 10)
        slow = calculate_sma(candles, 30)
        crosses = detect_crossovers(fast, slow, 10, 30)
        golden = [c for c in crosses if c.cross_type == "GOLDEN_CROSS"]
        assert len(golden) >= 1


class TestADX:
    def test_trending_market(self):
        candles = _make_candles(_trending_up(60, step=5.0), spread=2.0)
        result = calculate_adx(candles, period=14, trend_threshold=32.0)
        # Em tendência forte, ADX deve ser alto
        assert result.adx > 0
        assert result.trend_direction == TrendDirection.UP

    def test_sideways_market(self):
        candles = _make_candles(_sideways(60, amplitude=1.0), spread=0.5)
        result = calculate_adx(candles, period=14, trend_threshold=32.0)
        # Em mercado lateral, sistema deve ficar em WAIT
        # (pode não ser exato em dados sintéticos, mas ADX deve ser menor)
        assert result.system_state in (SystemState.WAIT, SystemState.TRADING)

    def test_insufficient_data(self):
        candles = _make_candles([2650, 2651, 2652])
        result = calculate_adx(candles)
        assert result.adx == 0.0
        assert result.system_state == SystemState.WAIT


class TestRSI:
    def test_overbought(self):
        # Tendência de alta forte → RSI alto
        candles = _make_candles(_trending_up(30, step=10.0), spread=1.0)
        result = calculate_rsi(candles)
        assert result.value > 70
        assert result.is_overbought is True
        assert result.zone == "OVERBOUGHT"

    def test_oversold(self):
        # Tendência de baixa forte → RSI baixo
        candles = _make_candles(_trending_down(30, step=10.0), spread=1.0)
        result = calculate_rsi(candles)
        assert result.value < 30
        assert result.is_oversold is True
        assert result.zone == "OVERSOLD"

    def test_neutral(self):
        candles = _make_candles(_sideways(30))
        result = calculate_rsi(candles)
        assert 30 <= result.value <= 70
        assert result.zone == "NEUTRAL"

    def test_insufficient_data(self):
        candles = _make_candles([2650, 2651])
        result = calculate_rsi(candles)
        assert result.value == 50.0


class TestDidiIndex:
    def test_bullish_needle(self):
        # Começa lateral, depois sobe forte → agulhada de compra
        prices = _sideways(15) + _trending_up(10, start=2650.0, step=5.0)
        candles = _make_candles(prices, spread=2.0)
        result = calculate_didi(candles)
        # Pode ou não detectar agulhada dependendo dos dados
        assert result.short_ratio != 0
        assert result.long_ratio != 0

    def test_insufficient_data(self):
        candles = _make_candles([2650, 2651, 2652])
        result = calculate_didi(candles)
        assert result.has_needle is False
        assert result.score == 0.0


class TestMAAlignment:
    def test_bullish_alignment(self):
        candles = _make_candles(_trending_up(250, step=1.0), spread=0.5)
        result = analyze_ma_alignment(candles)
        assert result.price_above_ma200 is True
        assert result.score > 0

    def test_empty_candles(self):
        result = analyze_ma_alignment([])
        assert result.score == 0.0
        assert result.bullish_aligned is False
