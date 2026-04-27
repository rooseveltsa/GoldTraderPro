"""Testes unitários para modelos de Signal e ConfluenceScore."""

from decimal import Decimal

from packages.core.models.enums import (
    Direction,
    MarketContext,
    PatternType,
    Timeframe,
    VolumeVerdict,
)
from packages.core.models.signal import ConfluenceScore, PatternSignal


class TestConfluenceScore:
    def test_total_all_max(self):
        score = ConfluenceScore(
            pattern_score=1.0,
            volume_score=1.0,
            adx_score=1.0,
            ma_alignment_score=1.0,
            rsi_score=1.0,
            didi_score=1.0,
        )
        assert score.total == 1.0
        assert score.is_executable is True

    def test_total_all_zero(self):
        score = ConfluenceScore()
        assert score.total == 0.0
        assert score.is_executable is False

    def test_minimum_executable(self):
        # Score exatamente em 0.65
        score = ConfluenceScore(
            pattern_score=1.0,    # 0.30
            volume_score=1.0,     # 0.20
            adx_score=1.0,        # 0.15
            ma_alignment_score=0.0,
            rsi_score=0.0,
            didi_score=0.0,
        )
        # total = 0.30 + 0.20 + 0.15 = 0.65
        assert score.total == 0.65
        assert score.is_executable is True

    def test_just_below_threshold(self):
        score = ConfluenceScore(
            pattern_score=1.0,    # 0.30
            volume_score=1.0,     # 0.20
            adx_score=0.9,        # 0.135
            ma_alignment_score=0.0,
            rsi_score=0.0,
            didi_score=0.0,
        )
        # total = 0.30 + 0.20 + 0.135 = 0.635
        assert score.total < 0.65
        assert score.is_executable is False

    def test_to_dict_structure(self):
        score = ConfluenceScore(pattern_score=0.8, volume_score=0.6)
        d = score.to_dict()
        assert "total" in d
        assert "is_executable" in d
        assert "components" in d
        assert "pattern" in d["components"]


class TestPatternSignal:
    def test_valid_signal(self):
        confluence = ConfluenceScore(
            pattern_score=1.0, volume_score=1.0, adx_score=1.0,
            ma_alignment_score=1.0, rsi_score=1.0, didi_score=1.0,
        )
        signal = PatternSignal(
            pattern_type=PatternType.HAMMER,
            direction=Direction.BULLISH,
            strength=0.85,
            timeframe=Timeframe.M15,
            entry_price=Decimal("2650.00"),
            stop_loss=Decimal("2645.00"),
            take_profit=Decimal("2657.50"),
            volume_verdict=VolumeVerdict.CONFIRMED,
            context=MarketContext.SUPPORT,
            confluence=confluence,
            multi_tf_aligned=True,
        )
        assert signal.is_valid is True
        assert signal.risk_reward_ratio == 1.5

    def test_invalid_signal_low_confluence(self):
        signal = PatternSignal(
            confluence=ConfluenceScore(pattern_score=0.3),
            volume_verdict=VolumeVerdict.CONFIRMED,
            multi_tf_aligned=True,
        )
        assert signal.is_valid is False

    def test_invalid_signal_weak_volume(self):
        confluence = ConfluenceScore(
            pattern_score=1.0, volume_score=1.0, adx_score=1.0,
            ma_alignment_score=1.0, rsi_score=1.0, didi_score=1.0,
        )
        signal = PatternSignal(
            confluence=confluence,
            volume_verdict=VolumeVerdict.WEAK,
            multi_tf_aligned=True,
        )
        assert signal.is_valid is False

    def test_invalid_signal_no_tf_alignment(self):
        confluence = ConfluenceScore(
            pattern_score=1.0, volume_score=1.0, adx_score=1.0,
            ma_alignment_score=1.0, rsi_score=1.0, didi_score=1.0,
        )
        signal = PatternSignal(
            confluence=confluence,
            volume_verdict=VolumeVerdict.CONFIRMED,
            multi_tf_aligned=False,
        )
        assert signal.is_valid is False

    def test_risk_reward_ratio(self):
        signal = PatternSignal(
            entry_price=Decimal("2650.00"),
            stop_loss=Decimal("2640.00"),
            take_profit=Decimal("2680.00"),
        )
        # risk = 10, reward = 30, ratio = 3.0
        assert signal.risk_reward_ratio == 3.0

    def test_risk_reward_zero_stop(self):
        signal = PatternSignal(
            entry_price=Decimal("2650.00"),
            stop_loss=Decimal("2650.00"),
            take_profit=Decimal("2660.00"),
        )
        assert signal.risk_reward_ratio == 0.0

    def test_to_dict_structure(self):
        signal = PatternSignal()
        d = signal.to_dict()
        assert "id" in d
        assert "pattern" in d
        assert "confluence" in d
        assert "is_valid" in d
        assert "risk_reward" in d
