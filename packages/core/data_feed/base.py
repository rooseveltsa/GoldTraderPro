"""Interface base para providers de dados de mercado."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from packages.core.models.candle import Candle
from packages.core.models.enums import Timeframe


class DataFeedProvider(ABC):
    """Interface abstrata para fontes de dados OHLCV."""

    @abstractmethod
    async def fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]:
        """Busca candles históricos."""
        ...

    @abstractmethod
    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Candle | None:
        """Retorna o último candle fechado."""
        ...

    @abstractmethod
    async def connect(self) -> None:
        """Estabelece conexão com a fonte de dados."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Encerra conexão com a fonte de dados."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do provider."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Estado da conexão."""
        ...
