"""Testes unitários para Volume Analyzer."""

from datetime import datetime, timedelta
from decimal import Decimal

from packages.core.models.candle import Candle
from packages.core.models.enums import Timeframe, VolumeVerdict
from packages.core.volume.analyzer import analyze_volume

BASE_TIME = datetime(2026, 1, 15, 10, 0)


def _candle_with_volume(volume, idx=0):
    return Candle(
        timestamp=BASE_TIME + timedelta(minutes=15 * idx),
        timeframe=Timeframe.M15,
        open=Decimal("2650.00"), high=Decimal("2655.00"),
        low=Decimal("2645.00"), close=Decimal("2653.00"),
        volume=Decimal(str(volume)),
    )


class TestVolumeAnalyzer:
    def test_climactic_volume(self):
        # 20 candles com volume 1000, último com 3500 (3.5x)
        candles = [_candle_with_volume(1000, i) for i in range(20)]
        candles.append(_candle_with_volume(3500, 20))
        result = analyze_volume(candles)
        assert result.verdict == VolumeVerdict.CLIMACTIC
        assert result.ratio >= 3.0
        assert result.score >= 0.8

    def test_confirmed_volume(self):
        candles = [_candle_with_volume(1000, i) for i in range(20)]
        candles.append(_candle_with_volume(1800, 20))
        result = analyze_volume(candles)
        assert result.verdict == VolumeVerdict.CONFIRMED
        assert result.ratio >= 1.5
        assert result.score >= 0.5

    def test_neutral_volume(self):
        candles = [_candle_with_volume(1000, i) for i in range(20)]
        candles.append(_candle_with_volume(1100, 20))
        result = analyze_volume(candles)
        assert result.verdict == VolumeVerdict.NEUTRAL
        assert result.ratio >= 1.0

    def test_weak_volume(self):
        candles = [_candle_with_volume(1000, i) for i in range(20)]
        candles.append(_candle_with_volume(500, 20))
        result = analyze_volume(candles)
        assert result.verdict == VolumeVerdict.WEAK
        assert result.ratio < 1.0
        assert result.score == 0.0

    def test_empty_candles(self):
        result = analyze_volume([])
        assert result.verdict == VolumeVerdict.WEAK
        assert result.score == 0.0

    def test_single_candle(self):
        result = analyze_volume([_candle_with_volume(1000)])
        assert result.verdict == VolumeVerdict.NEUTRAL
