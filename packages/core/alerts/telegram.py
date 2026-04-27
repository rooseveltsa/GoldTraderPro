"""Telegram alert notifications for trading signals."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class TelegramConfig:
    """Configuracao do bot Telegram."""

    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = False


class TelegramAlerter:
    """Envia alertas de trading via Telegram bot."""

    def __init__(self, config: Optional[TelegramConfig] = None) -> None:
        self._config = config or TelegramConfig()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_configured(self) -> bool:
        return bool(
            self._config.bot_token
            and self._config.chat_id
            and self._config.enabled
        )

    async def send(self, message: str) -> bool:
        """Envia mensagem para o chat configurado."""
        if not self.is_configured:
            return False

        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)

        url = f"https://api.telegram.org/bot{self._config.bot_token}/sendMessage"
        try:
            resp = await self._client.post(url, json={
                "chat_id": self._config.chat_id,
                "text": message,
                "parse_mode": "HTML",
            })
            return resp.status_code == 200
        except Exception as e:
            logger.error("Telegram send failed: %s", e)
            return False

    async def send_signal_alert(self, signal_data: dict) -> bool:
        """Formata e envia alerta de sinal de trading."""
        direction = signal_data.get("direction", "?")
        pattern = signal_data.get("pattern", "?")
        entry = signal_data.get("entry_price", "?")
        sl = signal_data.get("stop_loss", "?")
        tp = signal_data.get("take_profit", "?")
        confluence = signal_data.get("confluence", 0)

        arrow = "\U0001f7e2" if direction == "BULLISH" else "\U0001f534"
        msg = (
            f"{arrow} <b>GoldTrader Pro - Sinal Detectado</b>\n\n"
            f"<b>Padrao:</b> {pattern}\n"
            f"<b>Direcao:</b> {direction}\n"
            f"<b>Entry:</b> ${entry}\n"
            f"<b>Stop Loss:</b> ${sl}\n"
            f"<b>Take Profit:</b> ${tp}\n"
            f"<b>Confluencia:</b> {confluence:.1%}\n"
        )
        return await self.send(msg)

    async def send_trade_alert(self, trade_data: dict, event: str = "open") -> bool:
        """Envia alerta de abertura/fechamento de trade."""
        direction = trade_data.get("direction", "?")
        pattern = trade_data.get("pattern", "?")

        if event == "open":
            entry = trade_data.get("entry_price", "?")
            msg = (
                f"\U0001f4c8 <b>Trade Aberto</b>\n\n"
                f"<b>{direction}</b> - {pattern}\n"
                f"<b>Entry:</b> ${entry}\n"
            )
        else:
            pnl = trade_data.get("pnl", 0)
            reason = trade_data.get("exit_reason", "?")
            icon = "\u2705" if float(str(pnl)) >= 0 else "\u274c"
            msg = (
                f"{icon} <b>Trade Fechado</b>\n\n"
                f"<b>{direction}</b> - {pattern}\n"
                f"<b>PnL:</b> ${pnl}\n"
                f"<b>Motivo:</b> {reason}\n"
            )
        return await self.send(msg)

    async def close(self) -> None:
        """Fecha o cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None
