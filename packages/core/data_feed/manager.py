"""Gerenciador central de Data Feed — coordena providers e cache."""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime

from packages.core.data_feed.base import DataFeedProvider
from packages.core.models.candle import Candle
from packages.core.models.enums import Timeframe

logger = logging.getLogger(__name__)


class DataFeedManager:
    """Gerencia múltiplos providers e mantém buffer de candles em memória.

    Responsável por:
    - Registrar providers (CSV, CCXT, MT5)
    - Manter buffer circular dos últimos N candles
    - Validar integridade dos dados (gaps, duplicatas)
    - Fornecer candles para os engines de análise
    """

    def __init__(self, buffer_size: int = 500) -> None:
        self._providers: dict[str, DataFeedProvider] = {}
        self._active_provider: DataFeedProvider | None = None
        self._buffer_size = buffer_size
        self._buffers: dict[str, deque[Candle]] = {}

    def register_provider(self, provider: DataFeedProvider) -> None:
        """Registra um provider de dados."""
        self._providers[provider.name] = provider
        logger.info("Provider registrado: %s", provider.name)

    async def set_active_provider(self, name: str) -> None:
        """Define o provider ativo e conecta."""
        if name not in self._providers:
            raise ValueError(f"Provider não registrado: {name}")
        provider = self._providers[name]
        if not provider.is_connected:
            await provider.connect()
        self._active_provider = provider
        logger.info("Provider ativo: %s", name)

    @property
    def active_provider(self) -> DataFeedProvider:
        if self._active_provider is None:
            raise RuntimeError("Nenhum provider ativo. Use set_active_provider() primeiro.")
        return self._active_provider

    async def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]:
        """Carrega candles do provider ativo e popula o buffer."""
        candles = await self.active_provider.fetch_candles(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            limit=limit,
        )

        buffer_key = f"{symbol}_{timeframe.value}"
        if buffer_key not in self._buffers:
            self._buffers[buffer_key] = deque(maxlen=self._buffer_size)

        for candle in candles:
            self._append_to_buffer(buffer_key, candle)

        gaps = self._detect_gaps(candles, timeframe)
        if gaps:
            logger.warning(
                "%d gaps detectados em %s %s: %s",
                len(gaps), symbol, timeframe.value,
                [g.isoformat() for g in gaps[:5]],
            )

        return candles

    def get_buffer(self, symbol: str, timeframe: Timeframe) -> list[Candle]:
        """Retorna os candles no buffer para o símbolo/timeframe."""
        buffer_key = f"{symbol}_{timeframe.value}"
        if buffer_key not in self._buffers:
            return []
        return list(self._buffers[buffer_key])

    def get_last_n_candles(
        self, symbol: str, timeframe: Timeframe, n: int
    ) -> list[Candle]:
        """Retorna os últimos N candles do buffer."""
        buffer = self.get_buffer(symbol, timeframe)
        return buffer[-n:] if len(buffer) >= n else buffer

    def _append_to_buffer(self, buffer_key: str, candle: Candle) -> None:
        """Adiciona candle ao buffer evitando duplicatas."""
        buf = self._buffers[buffer_key]
        if buf and buf[-1].timestamp >= candle.timestamp:
            return
        buf.append(candle)

    @staticmethod
    def _detect_gaps(candles: list[Candle], timeframe: Timeframe) -> list[datetime]:
        """Detecta gaps temporais entre candles consecutivos."""
        if len(candles) < 2:
            return []

        from datetime import timedelta
        expected_delta = timedelta(minutes=timeframe.minutes)
        # Tolerância de 50% para mercados que fecham (fins de semana)
        max_delta = expected_delta * 3

        gaps: list[datetime] = []
        for i in range(1, len(candles)):
            delta = candles[i].timestamp - candles[i - 1].timestamp
            if delta > max_delta:
                gaps.append(candles[i - 1].timestamp)

        return gaps

    async def disconnect_all(self) -> None:
        """Desconecta todos os providers."""
        for provider in self._providers.values():
            if provider.is_connected:
                await provider.disconnect()
        self._active_provider = None
        self._buffers.clear()
        logger.info("Todos os providers desconectados")
