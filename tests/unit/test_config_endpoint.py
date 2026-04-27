"""Testes unitarios para os endpoints de configuracao."""

from __future__ import annotations

import pytest

from packages.api.routers.config import SystemConfig, TelegramSettings


class TestSystemConfig:
    def test_default_values(self):
        config = SystemConfig()
        assert config.adx_threshold == 32.0
        assert config.min_confluence == 0.65
        assert config.risk_per_trade == 0.01
        assert config.min_risk_reward == 1.5
        assert config.max_concurrent_trades == 3
        assert config.max_daily_drawdown == 0.03
        assert config.slippage_pips == 0.5
        assert config.spread_pips == 2.0
        assert config.default_timeframe == "H1"
        assert config.default_symbol == "PAXG/USDT"
        assert config.default_exchange == "binance"

    def test_custom_values(self):
        config = SystemConfig(
            adx_threshold=25.0,
            min_confluence=0.70,
            risk_per_trade=0.02,
            max_concurrent_trades=5,
        )
        assert config.adx_threshold == 25.0
        assert config.min_confluence == 0.70
        assert config.risk_per_trade == 0.02
        assert config.max_concurrent_trades == 5

    def test_model_dump(self):
        config = SystemConfig()
        d = config.model_dump()
        assert "adx_threshold" in d
        assert "min_confluence" in d
        assert d["default_symbol"] == "PAXG/USDT"


class TestTelegramSettings:
    def test_default_values(self):
        settings = TelegramSettings()
        assert settings.bot_token == ""
        assert settings.chat_id == ""
        assert settings.enabled is False

    def test_custom_values(self):
        settings = TelegramSettings(
            bot_token="123:ABC",
            chat_id="456",
            enabled=True,
        )
        assert settings.bot_token == "123:ABC"
        assert settings.chat_id == "456"
        assert settings.enabled is True
