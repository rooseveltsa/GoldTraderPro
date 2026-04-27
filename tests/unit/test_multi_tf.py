"""Testes unitários para Multi-Timeframe Validator."""

from datetime import datetime, timedelta
from decimal import Decimal

from packages.core.models.candle import Candle
from packages.core.models.enums import Direction, Timeframe, TrendDirection
from packages.core.multi_tf.validator import validate_multi_timeframe, _detect_trend

BASE = datetime(2026, 1, 1)


def _make_trend_candles(direction, n=60, tf=Timeframe.D1):
    """Cria candles em tendência clara."""
    candles = []
    base = 2650.0
    step = 3.0 if direction == "up" else -3.0
    for i in range(n):
        close = base + i * step
        candles.append(Candle(
            timestamp=BASE + timedelta(days=i),
            timeframe=tf,
            open=Decimal(str(close - 1)),
            high=Decimal(str(close + 2)),
            low=Decimal(str(close - 2)),
            close=Decimal(str(close)),
            volume=Decimal("1000"),
        ))
    return candles


def _make_lateral_candles(n=60, tf=Timeframe.D1):
    """Cria candles laterais."""
    import math
    candles = []
    for i in range(n):
        close = 2650.0 + 2.0 * math.sin(i * 0.3)
        candles.append(Candle(
            timestamp=BASE + timedelta(days=i),
            timeframe=tf,
            open=Decimal(str(close - 0.5)),
            high=Decimal(str(close + 1)),
            low=Decimal(str(close - 1)),
            close=Decimal(str(close)),
            volume=Decimal("1000"),
        ))
    return candles


class TestDetectTrend:
    def test_uptrend(self):
        candles = _make_trend_candles("up")
        trend = _detect_trend(candles)
        assert trend == TrendDirection.UP

    def test_downtrend(self):
        candles = _make_trend_candles("down")
        trend = _detect_trend(candles)
        assert trend == TrendDirection.DOWN

    def test_insufficient_data(self):
        candles = _make_trend_candles("up", n=5)
        trend = _detect_trend(candles)
        assert trend == TrendDirection.LATERAL


class TestMultiTFValidation:
    def test_buy_aligned_all_up(self):
        primary = _make_trend_candles("up", tf=Timeframe.D1)
        macro = _make_trend_candles("up", tf=Timeframe.W1)
        result = validate_multi_timeframe(
            Direction.BULLISH, primary, macro,
        )
        assert result.is_aligned is True
        assert result.bonus == 0.10  # bonus por alinhamento total

    def test_buy_rejected_primary_down(self):
        primary = _make_trend_candles("down", tf=Timeframe.D1)
        macro = _make_trend_candles("up", tf=Timeframe.W1)
        result = validate_multi_timeframe(
            Direction.BULLISH, primary, macro,
        )
        assert result.is_aligned is False
        assert "contra-fluxo" in result.rejection_reason.lower() or "D1" in result.rejection_reason

    def test_sell_aligned_all_down(self):
        primary = _make_trend_candles("down", tf=Timeframe.D1)
        macro = _make_trend_candles("down", tf=Timeframe.W1)
        result = validate_multi_timeframe(
            Direction.BEARISH, primary, macro,
        )
        assert result.is_aligned is True
        assert result.bonus == 0.10

    def test_neutral_signal(self):
        primary = _make_trend_candles("up", tf=Timeframe.D1)
        macro = _make_trend_candles("up", tf=Timeframe.W1)
        result = validate_multi_timeframe(
            Direction.NEUTRAL, primary, macro,
        )
        assert result.is_aligned is False

    def test_buy_lateral_primary_rejected(self):
        primary = _make_lateral_candles(tf=Timeframe.D1)
        macro = _make_trend_candles("up", tf=Timeframe.W1)
        result = validate_multi_timeframe(
            Direction.BULLISH, primary, macro,
        )
        # Em mercado lateral/contra-fluxo, sinal de compra é rejeitado
        assert result.is_aligned is False
        assert result.rejection_reason != ""
