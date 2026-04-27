"""Testes unitários para o modelo Candle."""

from datetime import datetime
from decimal import Decimal

import pytest

from packages.core.models.candle import Candle
from packages.core.models.enums import Timeframe


def _make_candle(**overrides) -> Candle:
    """Helper para criar candles de teste."""
    defaults = {
        "timestamp": datetime(2026, 1, 15, 10, 0),
        "timeframe": Timeframe.M15,
        "open": Decimal("2650.50"),
        "high": Decimal("2655.00"),
        "low": Decimal("2648.00"),
        "close": Decimal("2653.00"),
        "volume": Decimal("1500"),
    }
    defaults.update(overrides)
    return Candle(**defaults)


class TestCandleCreation:
    def test_valid_bullish_candle(self):
        candle = _make_candle()
        assert candle.is_bullish is True
        assert candle.is_bearish is False

    def test_valid_bearish_candle(self):
        candle = _make_candle(
            open=Decimal("2655.00"),
            close=Decimal("2650.00"),
        )
        assert candle.is_bearish is True
        assert candle.is_bullish is False

    def test_high_less_than_low_raises(self):
        with pytest.raises(ValueError, match="High.*não pode ser menor que Low"):
            _make_candle(high=Decimal("2645.00"), low=Decimal("2650.00"))

    def test_high_less_than_open_raises(self):
        with pytest.raises(ValueError, match="High deve ser"):
            _make_candle(high=Decimal("2649.00"))

    def test_low_greater_than_close_raises(self):
        with pytest.raises(ValueError, match="Low deve ser"):
            _make_candle(low=Decimal("2654.00"))

    def test_negative_volume_raises(self):
        with pytest.raises(ValueError, match="Volume não pode ser negativo"):
            _make_candle(volume=Decimal("-100"))

    def test_candle_is_immutable(self):
        candle = _make_candle()
        with pytest.raises(AttributeError):
            candle.close = Decimal("9999")  # type: ignore


class TestCandleProperties:
    def test_body(self):
        candle = _make_candle(open=Decimal("2650.00"), close=Decimal("2653.00"))
        assert candle.body == Decimal("3.00")

    def test_amplitude(self):
        candle = _make_candle(high=Decimal("2660.00"), low=Decimal("2645.00"))
        assert candle.amplitude == Decimal("15.00")

    def test_upper_wick_bullish(self):
        # Bullish: upper_wick = high - close
        candle = _make_candle(
            open=Decimal("2650.00"), high=Decimal("2660.00"),
            low=Decimal("2648.00"), close=Decimal("2655.00"),
        )
        assert candle.upper_wick == Decimal("5.00")

    def test_lower_wick_bullish(self):
        # Bullish: lower_wick = open - low
        candle = _make_candle(
            open=Decimal("2650.00"), high=Decimal("2660.00"),
            low=Decimal("2645.00"), close=Decimal("2655.00"),
        )
        assert candle.lower_wick == Decimal("5.00")

    def test_upper_wick_bearish(self):
        # Bearish: upper_wick = high - open
        candle = _make_candle(
            open=Decimal("2655.00"), high=Decimal("2660.00"),
            low=Decimal("2648.00"), close=Decimal("2650.00"),
        )
        assert candle.upper_wick == Decimal("5.00")

    def test_lower_wick_bearish(self):
        # Bearish: lower_wick = close - low
        candle = _make_candle(
            open=Decimal("2655.00"), high=Decimal("2660.00"),
            low=Decimal("2645.00"), close=Decimal("2650.00"),
        )
        assert candle.lower_wick == Decimal("5.00")

    def test_body_ratio(self):
        # body=3, amplitude=7
        candle = _make_candle(
            open=Decimal("2650.00"), high=Decimal("2655.00"),
            low=Decimal("2648.00"), close=Decimal("2653.00"),
        )
        expected = Decimal("3") / Decimal("7")
        assert candle.body_ratio == expected

    def test_is_doji(self):
        # Corpo muito pequeno relativo à amplitude
        candle = _make_candle(
            open=Decimal("2650.00"), high=Decimal("2660.00"),
            low=Decimal("2640.00"), close=Decimal("2650.10"),
        )
        # body = 0.10, amplitude = 20.00, ratio = 0.005 <= 0.05
        assert candle.is_doji is True

    def test_is_not_doji(self):
        candle = _make_candle(
            open=Decimal("2650.00"), high=Decimal("2660.00"),
            low=Decimal("2640.00"), close=Decimal("2658.00"),
        )
        # body = 8.00, amplitude = 20.00, ratio = 0.40 > 0.05
        assert candle.is_doji is False

    def test_zero_amplitude_doji(self):
        candle = _make_candle(
            open=Decimal("2650.00"), high=Decimal("2650.00"),
            low=Decimal("2650.00"), close=Decimal("2650.00"),
        )
        assert candle.is_doji is True
        assert candle.body_ratio == Decimal("0")

    def test_midpoint(self):
        candle = _make_candle(high=Decimal("2660.00"), low=Decimal("2640.00"))
        assert candle.midpoint == Decimal("2650.00")

    def test_to_dict(self):
        candle = _make_candle()
        d = candle.to_dict()
        assert d["timeframe"] == "M15"
        assert "timestamp" in d
        assert d["open"] == "2650.50"


class TestCandlePatternPreConditions:
    """Testa as pré-condições para detecção de padrões no candle."""

    def test_hammer_preconditions(self):
        """Martelo: corpo <= 30% amplitude, pavio inferior >= 2x corpo."""
        candle = _make_candle(
            open=Decimal("2654.00"), high=Decimal("2655.00"),
            low=Decimal("2645.00"), close=Decimal("2654.50"),
        )
        # amplitude = 10, body = 0.50, lower_wick = 9.00
        # body_ratio = 0.05, lower_wick >= 2 * 0.50
        assert candle.body_ratio <= Decimal("0.30")
        assert candle.lower_wick >= 2 * candle.body

    def test_shooting_star_preconditions(self):
        """Estrela Cadente: corpo <= 30% amplitude, pavio superior >= 2x corpo."""
        candle = _make_candle(
            open=Decimal("2646.00"), high=Decimal("2655.00"),
            low=Decimal("2645.00"), close=Decimal("2645.50"),
        )
        # amplitude = 10, body = 0.50, upper_wick = 9.00
        assert candle.body_ratio <= Decimal("0.30")
        assert candle.upper_wick >= 2 * candle.body
