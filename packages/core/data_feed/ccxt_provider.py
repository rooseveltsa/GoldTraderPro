"""Provider de dados via CCXT — acesso a exchanges reais e dados ao vivo.

Fontes suportadas (sem necessidade de API key para dados publicos):
- Binance: XAU/USDT (ou pares gold via futures)
- Bybit: XAUUSDT perpetual
- OKX: XAU/USDT

Para XAU/USD real (forex), considere:
- OANDA (requer API key)
- Qualquer exchange que liste gold tokens

O CCXT unifica a interface para 100+ exchanges.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from packages.core.data_feed.base import DataFeedProvider
from packages.core.models.candle import Candle
from packages.core.models.enums import Timeframe

logger = logging.getLogger(__name__)

# Mapeamento de Timeframe interno para formato CCXT
_TIMEFRAME_MAP = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1d",
    Timeframe.W1: "1w",
    Timeframe.MN: "1M",
}


class CCXTProvider(DataFeedProvider):
    """Provider que busca dados OHLCV de exchanges via CCXT.

    Suporta dados historicos e o ultimo candle fechado (near real-time).
    Nao requer API key para dados publicos de mercado.

    Uso:
        provider = CCXTProvider(exchange_id="binance")
        await provider.connect()
        candles = await provider.fetch_candles("XAU/USDT", Timeframe.M15, start)
    """

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False,
    ) -> None:
        self._exchange_id = exchange_id
        self._api_key = api_key
        self._api_secret = api_secret
        self._sandbox = sandbox
        self._exchange = None
        self._connected = False

    @property
    def name(self) -> str:
        return f"CCXT:{self._exchange_id}"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Inicializa a conexao com a exchange via CCXT."""
        import ccxt

        exchange_class = getattr(ccxt, self._exchange_id, None)
        if exchange_class is None:
            raise ValueError(
                f"Exchange '{self._exchange_id}' nao encontrada no CCXT. "
                f"Disponiveis: binance, bybit, okx, kraken, oanda, etc."
            )

        config = {
            "enableRateLimit": True,
            "timeout": 30000,
        }

        if self._api_key:
            config["apiKey"] = self._api_key
        if self._api_secret:
            config["secret"] = self._api_secret

        self._exchange = exchange_class(config)

        if self._sandbox:
            self._exchange.set_sandbox_mode(True)

        # Carregar mercados disponiveis
        self._exchange.load_markets()
        self._connected = True

        available = len(self._exchange.symbols)
        logger.info(
            "CCXTProvider conectado: %s (%d mercados disponiveis)",
            self._exchange_id, available,
        )

    async def disconnect(self) -> None:
        """Encerra conexao com a exchange."""
        if self._exchange:
            self._exchange = None
        self._connected = False
        logger.info("CCXTProvider desconectado: %s", self._exchange_id)

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[Candle]:
        """Busca candles historicos da exchange.

        A maioria das exchanges retorna ate 500-1000 candles por request.
        Para periodos maiores, faz paginacao automatica.
        """
        if not self._exchange:
            raise RuntimeError("Provider nao conectado. Chame connect() primeiro.")

        ccxt_tf = _TIMEFRAME_MAP.get(timeframe)
        if ccxt_tf is None:
            raise ValueError(f"Timeframe {timeframe} nao suportado pelo CCXT")

        # Resolver simbolo (tentar variantes se necessario)
        resolved_symbol = self._resolve_symbol(symbol)
        if resolved_symbol is None:
            logger.warning(
                "Simbolo %s nao encontrado em %s. Disponiveis com 'XAU': %s",
                symbol,
                self._exchange_id,
                [s for s in self._exchange.symbols if "XAU" in s.upper()][:10],
            )
            return []

        since_ms = int(start.replace(tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = (
            int(end.replace(tzinfo=timezone.utc).timestamp() * 1000)
            if end else None
        )

        all_candles: list[Candle] = []
        current_since = since_ms
        batch_size = min(limit, 500)  # Maioria das exchanges limita a 500

        while len(all_candles) < limit:
            remaining = limit - len(all_candles)
            fetch_limit = min(batch_size, remaining)

            try:
                ohlcv = self._exchange.fetch_ohlcv(
                    resolved_symbol,
                    timeframe=ccxt_tf,
                    since=current_since,
                    limit=fetch_limit,
                )
            except Exception as e:
                logger.error(
                    "Erro ao buscar candles de %s: %s", self._exchange_id, e,
                )
                break

            if not ohlcv:
                break

            for row in ohlcv:
                ts_ms, o, h, l, c, v = row[:6]
                ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

                # Filtrar por end se especificado
                if end_ms and ts_ms > end_ms:
                    return all_candles

                candle = Candle(
                    timestamp=ts.replace(tzinfo=None),
                    timeframe=timeframe,
                    open=Decimal(str(o)),
                    high=Decimal(str(h)),
                    low=Decimal(str(l)),
                    close=Decimal(str(c)),
                    volume=Decimal(str(v)) if v else Decimal("0"),
                )
                all_candles.append(candle)

            # Avancar para proximo batch
            last_ts = ohlcv[-1][0]
            if last_ts == current_since:
                break  # Evitar loop infinito
            current_since = last_ts + 1

            # Se retornou menos que o solicitado, nao ha mais dados
            if len(ohlcv) < fetch_limit:
                break

        logger.info(
            "Carregados %d candles de %s (%s %s)",
            len(all_candles), self._exchange_id, resolved_symbol, ccxt_tf,
        )
        return all_candles

    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Optional[Candle]:
        """Retorna o ultimo candle fechado."""
        if not self._exchange:
            return None

        ccxt_tf = _TIMEFRAME_MAP.get(timeframe)
        if ccxt_tf is None:
            return None

        resolved_symbol = self._resolve_symbol(symbol)
        if resolved_symbol is None:
            return None

        try:
            # Busca os 2 ultimos — o ultimo pode estar aberto
            ohlcv = self._exchange.fetch_ohlcv(
                resolved_symbol, timeframe=ccxt_tf, limit=2,
            )
        except Exception as e:
            logger.error("Erro ao buscar ultimo candle: %s", e)
            return None

        if not ohlcv:
            return None

        # Pega o penultimo (garantidamente fechado)
        row = ohlcv[-2] if len(ohlcv) >= 2 else ohlcv[-1]
        ts_ms, o, h, l, c, v = row[:6]

        return Candle(
            timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).replace(tzinfo=None),
            timeframe=timeframe,
            open=Decimal(str(o)),
            high=Decimal(str(h)),
            low=Decimal(str(l)),
            close=Decimal(str(c)),
            volume=Decimal(str(v)) if v else Decimal("0"),
        )

    def _resolve_symbol(self, symbol: str) -> Optional[str]:
        """Resolve o simbolo para o formato aceito pela exchange.

        Tenta variantes comuns:
        - XAU/USD -> XAU/USDT -> XAUUSD -> PAXG/USDT
        """
        if not self._exchange:
            return None

        # Tentar direto
        if symbol in self._exchange.symbols:
            return symbol

        # Variantes
        variants = [
            symbol.replace("/USD", "/USDT"),
            symbol.replace("/", ""),
            symbol.replace("XAU", "PAXG"),  # PAX Gold e proxy do ouro
            symbol.replace("XAU/USD", "PAXG/USDT"),
        ]

        for variant in variants:
            if variant in self._exchange.symbols:
                logger.info("Simbolo resolvido: %s -> %s", symbol, variant)
                return variant

        return None

    def list_gold_symbols(self) -> list[str]:
        """Lista simbolos relacionados a ouro disponiveis na exchange."""
        if not self._exchange:
            return []
        gold_keywords = ["XAU", "PAXG", "XAUT"]
        return [
            s for s in self._exchange.symbols
            if any(s.upper().startswith(k) for k in gold_keywords)
        ]
