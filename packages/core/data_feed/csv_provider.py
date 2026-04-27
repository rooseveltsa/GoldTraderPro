"""Provider de dados via arquivos CSV — ideal para backtesting e desenvolvimento."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from packages.core.data_feed.base import DataFeedProvider
from packages.core.models.candle import Candle
from packages.core.models.enums import Timeframe

logger = logging.getLogger(__name__)


class CSVProvider(DataFeedProvider):
    """Carrega dados OHLCV de arquivos CSV.

    Formatos suportados:
    - Padrão: timestamp,open,high,low,close,volume
    - MetaTrader: Date,Time,Open,High,Low,Close,Volume
    - TradingView: time,open,high,low,close,Volume
    """

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = Path(data_dir)
        self._connected = False
        self._candles_cache: dict[str, list[Candle]] = {}

    @property
    def name(self) -> str:
        return "CSV"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        if not self._data_dir.exists():
            raise FileNotFoundError(f"Diretório de dados não encontrado: {self._data_dir}")
        self._connected = True
        logger.info("CSVProvider conectado: %s", self._data_dir)

    async def disconnect(self) -> None:
        self._candles_cache.clear()
        self._connected = False
        logger.info("CSVProvider desconectado")

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]:
        cache_key = f"{symbol}_{timeframe.value}"

        if cache_key not in self._candles_cache:
            file_path = self._resolve_file(symbol, timeframe)
            if file_path is None:
                logger.warning("Arquivo CSV não encontrado para %s %s", symbol, timeframe)
                return []
            self._candles_cache[cache_key] = self._load_csv(file_path, timeframe)

        candles = self._candles_cache[cache_key]

        filtered = [c for c in candles if c.timestamp >= start]
        if end:
            filtered = [c for c in filtered if c.timestamp <= end]

        return filtered[:limit]

    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Candle | None:
        cache_key = f"{symbol}_{timeframe.value}"
        if cache_key in self._candles_cache and self._candles_cache[cache_key]:
            return self._candles_cache[cache_key][-1]
        return None

    def _resolve_file(self, symbol: str, timeframe: Timeframe) -> Path | None:
        """Encontra o arquivo CSV correspondente ao símbolo e timeframe."""
        safe_symbol = symbol.replace("/", "").replace("\\", "")
        patterns = [
            f"{safe_symbol}_{timeframe.value}.csv",
            f"{safe_symbol}_{timeframe.value.lower()}.csv",
            f"{safe_symbol}.csv",
            f"{symbol.replace('/', '_')}_{timeframe.value}.csv",
        ]
        for pattern in patterns:
            path = self._data_dir / pattern
            if path.exists():
                return path
        return None

    def _load_csv(self, file_path: Path, timeframe: Timeframe) -> list[Candle]:
        """Carrega e normaliza um CSV em lista de Candles."""
        candles: list[Candle] = []

        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return candles

            headers = [h.strip().lower() for h in reader.fieldnames]
            col_map = self._detect_columns(headers)

            for row_num, row in enumerate(reader, start=2):
                try:
                    candle = self._parse_row(row, col_map, timeframe, headers)
                    candles.append(candle)
                except (ValueError, KeyError) as e:
                    logger.warning("Erro na linha %d de %s: %s", row_num, file_path.name, e)
                    continue

        candles.sort(key=lambda c: c.timestamp)
        logger.info("Carregados %d candles de %s", len(candles), file_path.name)
        return candles

    def _detect_columns(self, headers: list[str]) -> dict[str, str]:
        """Detecta automaticamente o mapeamento de colunas."""
        col_map: dict[str, str] = {}

        time_aliases = ["timestamp", "time", "date", "datetime", "date_time"]
        for alias in time_aliases:
            if alias in headers:
                col_map["timestamp"] = alias
                break

        for field in ["open", "high", "low", "close", "volume"]:
            for h in headers:
                if h == field or h == field[0]:
                    col_map[field] = h
                    break

        required = ["timestamp", "open", "high", "low", "close"]
        missing = [k for k in required if k not in col_map]
        if missing:
            raise ValueError(f"Colunas obrigatórias não encontradas: {missing}")

        return col_map

    def _parse_row(
        self,
        row: dict[str, str],
        col_map: dict[str, str],
        timeframe: Timeframe,
        headers: list[str],
    ) -> Candle:
        """Converte uma linha do CSV em Candle."""
        # Normalizar keys para lowercase
        normalized = {k.strip().lower(): v.strip() for k, v in row.items()}

        ts_raw = normalized[col_map["timestamp"]]
        timestamp = self._parse_timestamp(ts_raw)

        volume_str = normalized.get(col_map.get("volume", ""), "0")
        volume = Decimal(volume_str) if volume_str else Decimal("0")

        return Candle(
            timestamp=timestamp,
            timeframe=timeframe,
            open=Decimal(normalized[col_map["open"]]),
            high=Decimal(normalized[col_map["high"]]),
            low=Decimal(normalized[col_map["low"]]),
            close=Decimal(normalized[col_map["close"]]),
            volume=volume,
        )

    @staticmethod
    def _parse_timestamp(raw: str) -> datetime:
        """Tenta múltiplos formatos de timestamp."""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%Y.%m.%d %H:%M:%S",
            "%Y.%m.%d %H:%M",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        raise ValueError(f"Formato de timestamp não reconhecido: {raw}")
