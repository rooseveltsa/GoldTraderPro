"""Repository para persistência de candles no TimescaleDB."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from packages.core.models.candle import Candle
from packages.core.models.enums import Timeframe

logger = logging.getLogger(__name__)


class CandleRepository:
    """Repositório de candles usando SQLAlchemy async."""

    def __init__(self, connection_url: str) -> None:
        self._connection_url = connection_url
        self._engine = None

    async def connect(self) -> None:
        """Inicializa o engine SQLAlchemy async."""
        from sqlalchemy.ext.asyncio import create_async_engine

        self._engine = create_async_engine(
            self._connection_url,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )
        logger.info("CandleRepository conectado")

    async def disconnect(self) -> None:
        """Fecha o engine."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
        logger.info("CandleRepository desconectado")

    async def upsert_candles(self, candles: list[Candle]) -> int:
        """Insere ou atualiza candles (upsert por timestamp+symbol+timeframe)."""
        if not candles or not self._engine:
            return 0

        from sqlalchemy import text

        query = text("""
            INSERT INTO candles (timestamp, symbol, timeframe, open, high, low, close, volume, tick_volume, spread)
            VALUES (:timestamp, :symbol, :timeframe, :open, :high, :low, :close, :volume, :tick_volume, :spread)
            ON CONFLICT (timestamp, symbol, timeframe)
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """)

        async with self._engine.begin() as conn:
            for candle in candles:
                await conn.execute(query, {
                    "timestamp": candle.timestamp,
                    "symbol": "XAU/USD",
                    "timeframe": candle.timeframe.value,
                    "open": float(candle.open),
                    "high": float(candle.high),
                    "low": float(candle.low),
                    "close": float(candle.close),
                    "volume": float(candle.volume),
                    "tick_volume": candle.tick_volume,
                    "spread": candle.spread,
                })

        logger.info("Upsert de %d candles concluído", len(candles))
        return len(candles)

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]:
        """Busca candles do banco de dados."""
        if not self._engine:
            return []

        from sqlalchemy import text

        query_str = """
            SELECT timestamp, timeframe, open, high, low, close, volume, tick_volume, spread
            FROM candles
            WHERE symbol = :symbol
              AND timeframe = :timeframe
              AND timestamp >= :start
        """
        params: dict = {
            "symbol": symbol,
            "timeframe": timeframe.value,
            "start": start,
        }

        if end:
            query_str += " AND timestamp <= :end"
            params["end"] = end

        query_str += " ORDER BY timestamp ASC LIMIT :limit"
        params["limit"] = limit

        async with self._engine.connect() as conn:
            result = await conn.execute(text(query_str), params)
            rows = result.fetchall()

        return [
            Candle(
                timestamp=row[0],
                timeframe=Timeframe(row[1]),
                open=Decimal(str(row[2])),
                high=Decimal(str(row[3])),
                low=Decimal(str(row[4])),
                close=Decimal(str(row[5])),
                volume=Decimal(str(row[6])),
                tick_volume=row[7],
                spread=row[8],
            )
            for row in rows
        ]

    async def get_candle_count(self, symbol: str, timeframe: Timeframe) -> int:
        """Retorna a contagem de candles armazenados."""
        if not self._engine:
            return 0

        from sqlalchemy import text

        async with self._engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM candles WHERE symbol = :symbol AND timeframe = :tf"),
                {"symbol": symbol, "tf": timeframe.value},
            )
            row = result.fetchone()
            return row[0] if row else 0
