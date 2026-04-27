"""Testes unitarios para o modulo de alertas Telegram."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.alerts.telegram import TelegramAlerter, TelegramConfig


class TestTelegramConfig:
    def test_default_config(self):
        config = TelegramConfig()
        assert config.bot_token == ""
        assert config.chat_id == ""
        assert config.enabled is False

    def test_custom_config(self):
        config = TelegramConfig(bot_token="123:ABC", chat_id="456", enabled=True)
        assert config.bot_token == "123:ABC"
        assert config.chat_id == "456"
        assert config.enabled is True


class TestTelegramAlerter:
    def test_not_configured_by_default(self):
        alerter = TelegramAlerter()
        assert alerter.is_configured is False

    def test_configured_when_all_set(self):
        config = TelegramConfig(bot_token="123:ABC", chat_id="456", enabled=True)
        alerter = TelegramAlerter(config)
        assert alerter.is_configured is True

    def test_not_configured_without_token(self):
        config = TelegramConfig(chat_id="456", enabled=True)
        alerter = TelegramAlerter(config)
        assert alerter.is_configured is False

    def test_not_configured_when_disabled(self):
        config = TelegramConfig(bot_token="123:ABC", chat_id="456", enabled=False)
        alerter = TelegramAlerter(config)
        assert alerter.is_configured is False

    @pytest.mark.asyncio
    async def test_send_returns_false_when_not_configured(self):
        alerter = TelegramAlerter()
        result = await alerter.send("test")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_success(self):
        config = TelegramConfig(bot_token="123:ABC", chat_id="456", enabled=True)
        alerter = TelegramAlerter(config)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        alerter._client = mock_client

        result = await alerter.send("Hello")
        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_failure(self):
        config = TelegramConfig(bot_token="123:ABC", chat_id="456", enabled=True)
        alerter = TelegramAlerter(config)

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        alerter._client = mock_client

        result = await alerter.send("Hello")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_exception(self):
        config = TelegramConfig(bot_token="123:ABC", chat_id="456", enabled=True)
        alerter = TelegramAlerter(config)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("network error"))
        alerter._client = mock_client

        result = await alerter.send("Hello")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_signal_alert(self):
        config = TelegramConfig(bot_token="123:ABC", chat_id="456", enabled=True)
        alerter = TelegramAlerter(config)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        alerter._client = mock_client

        result = await alerter.send_signal_alert({
            "direction": "BULLISH",
            "pattern": "hammer",
            "entry_price": "2450.00",
            "stop_loss": "2440.00",
            "take_profit": "2465.00",
            "confluence": 0.75,
        })
        assert result is True

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "hammer" in body["text"]
        assert "BULLISH" in body["text"]

    @pytest.mark.asyncio
    async def test_send_trade_alert_open(self):
        config = TelegramConfig(bot_token="123:ABC", chat_id="456", enabled=True)
        alerter = TelegramAlerter(config)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        alerter._client = mock_client

        result = await alerter.send_trade_alert(
            {"direction": "BULLISH", "pattern": "engulfing", "entry_price": "2450.00"},
            event="open",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_trade_alert_close(self):
        config = TelegramConfig(bot_token="123:ABC", chat_id="456", enabled=True)
        alerter = TelegramAlerter(config)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        alerter._client = mock_client

        result = await alerter.send_trade_alert(
            {"direction": "BEARISH", "pattern": "doji", "pnl": "150.00", "exit_reason": "take_profit"},
            event="close",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_close(self):
        alerter = TelegramAlerter()
        mock_client = AsyncMock()
        alerter._client = mock_client

        await alerter.close()
        mock_client.aclose.assert_called_once()
        assert alerter._client is None
