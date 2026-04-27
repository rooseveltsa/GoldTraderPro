"""Testes unitários para Pattern Engine."""

from datetime import datetime, timedelta
from decimal import Decimal

from packages.core.models.candle import Candle
from packages.core.models.enums import Direction, PatternType, Timeframe
from packages.core.patterns.single_candle import (
    detect_doji,
    detect_dragonfly_doji,
    detect_gravestone_doji,
    detect_hammer,
    detect_inverted_hammer,
    detect_shooting_star,
    scan_single_candle,
)
from packages.core.patterns.multi_candle import (
    detect_bearish_engulfing,
    detect_bullish_engulfing,
    detect_evening_star,
    detect_morning_star,
    scan_multi_candle,
)
from packages.core.patterns.engine import PatternEngine

T = datetime(2026, 1, 15, 10, 0)


def _c(o, h, l, c, ts=None):
    """Shorthand para criar candle de teste."""
    return Candle(
        timestamp=ts or T, timeframe=Timeframe.M15,
        open=Decimal(str(o)), high=Decimal(str(h)),
        low=Decimal(str(l)), close=Decimal(str(c)),
        volume=Decimal("1000"),
    )


class TestHammer:
    def test_classic_hammer(self):
        # corpo=0.50, amplitude=10, pavio_inf=9.00, pavio_sup=0.50
        candle = _c(2654.00, 2655.00, 2645.00, 2654.50)
        result = detect_hammer(candle)
        assert result.detected is True
        assert result.direction == Direction.BULLISH

    def test_body_too_large(self):
        candle = _c(2650.00, 2660.00, 2645.00, 2657.00)
        result = detect_hammer(candle)
        assert result.detected is False

    def test_upper_wick_too_large(self):
        # corpo pequeno mas pavio superior grande
        candle = _c(2650.00, 2658.00, 2645.00, 2650.50)
        result = detect_hammer(candle)
        assert result.detected is False


class TestShootingStar:
    def test_classic_shooting_star(self):
        candle = _c(2646.00, 2655.00, 2645.00, 2645.50)
        result = detect_shooting_star(candle)
        assert result.detected is True
        assert result.direction == Direction.BEARISH

    def test_lower_wick_too_large(self):
        candle = _c(2650.00, 2658.00, 2645.00, 2650.50)
        result = detect_shooting_star(candle)
        assert result.detected is False


class TestDoji:
    def test_classic_doji(self):
        candle = _c(2650.00, 2660.00, 2640.00, 2650.10)
        result = detect_doji(candle)
        assert result.detected is True
        assert result.direction == Direction.NEUTRAL

    def test_not_doji_large_body(self):
        candle = _c(2650.00, 2660.00, 2640.00, 2658.00)
        result = detect_doji(candle)
        assert result.detected is False

    def test_dragonfly_doji(self):
        candle = _c(2650.00, 2650.20, 2640.00, 2650.10)
        result = detect_dragonfly_doji(candle)
        assert result.detected is True
        assert result.direction == Direction.BULLISH

    def test_gravestone_doji(self):
        candle = _c(2640.10, 2650.00, 2640.00, 2640.20)
        result = detect_gravestone_doji(candle)
        assert result.detected is True
        assert result.direction == Direction.BEARISH


class TestInvertedHammer:
    def test_classic(self):
        candle = _c(2645.50, 2655.00, 2645.00, 2646.00)
        result = detect_inverted_hammer(candle)
        assert result.detected is True
        assert result.direction == Direction.BULLISH


class TestScanSingleCandle:
    def test_scan_finds_patterns(self):
        hammer = _c(2654.00, 2655.00, 2645.00, 2654.50)
        results = scan_single_candle(hammer)
        assert len(results) >= 1
        assert any(r.pattern_type == PatternType.HAMMER for r in results)


class TestBullishEngulfing:
    def test_classic(self):
        prev = _c(2655.00, 2656.00, 2650.00, 2651.00)  # bearish
        curr = _c(2650.00, 2658.00, 2649.00, 2657.00)   # bullish engolfa
        result = detect_bullish_engulfing(prev, curr)
        assert result.detected is True
        assert result.direction == Direction.BULLISH

    def test_same_direction_no_engulfing(self):
        prev = _c(2650.00, 2656.00, 2649.00, 2655.00)  # bullish
        curr = _c(2655.00, 2660.00, 2654.00, 2659.00)   # bullish
        result = detect_bullish_engulfing(prev, curr)
        assert result.detected is False


class TestBearishEngulfing:
    def test_classic(self):
        prev = _c(2650.00, 2656.00, 2649.00, 2655.00)  # bullish
        curr = _c(2656.00, 2657.00, 2648.00, 2649.00)   # bearish engolfa
        result = detect_bearish_engulfing(prev, curr)
        assert result.detected is True
        assert result.direction == Direction.BEARISH


class TestMorningStar:
    def test_classic(self):
        c1 = _c(2660.00, 2661.00, 2650.00, 2651.00, T)                        # bearish longo
        c2 = _c(2651.00, 2652.00, 2650.00, 2651.10, T + timedelta(minutes=15)) # doji
        c3 = _c(2651.00, 2662.00, 2650.00, 2661.00, T + timedelta(minutes=30)) # bullish longo
        result = detect_morning_star(c1, c2, c3)
        assert result.detected is True
        assert result.direction == Direction.BULLISH


class TestEveningStar:
    def test_classic(self):
        c1 = _c(2650.00, 2661.00, 2649.00, 2660.00, T)                        # bullish longo
        c2 = _c(2660.00, 2661.00, 2659.00, 2660.10, T + timedelta(minutes=15)) # doji
        c3 = _c(2660.00, 2661.00, 2649.00, 2650.00, T + timedelta(minutes=30)) # bearish longo
        result = detect_evening_star(c1, c2, c3)
        assert result.detected is True
        assert result.direction == Direction.BEARISH


class TestScanMultiCandle:
    def test_finds_engulfing(self):
        prev = _c(2655.00, 2656.00, 2650.00, 2651.00, T)
        curr = _c(2650.00, 2658.00, 2649.00, 2657.00, T + timedelta(minutes=15))
        results = scan_multi_candle([prev, curr])
        assert len(results) >= 1
        assert any(r.pattern_type == PatternType.BULLISH_ENGULFING for r in results)


class TestPatternEngine:
    def test_scan_combined(self):
        engine = PatternEngine()
        # Cria sequência com engolfo + padrões single
        c1 = _c(2655.00, 2656.00, 2650.00, 2651.00, T)
        c2 = _c(2650.00, 2658.00, 2649.00, 2657.00, T + timedelta(minutes=15))
        results = engine.scan([c1, c2])
        assert len(results) >= 1
        # Deve estar ordenado por strength decrescente
        for i in range(len(results) - 1):
            assert results[i].strength >= results[i + 1].strength
