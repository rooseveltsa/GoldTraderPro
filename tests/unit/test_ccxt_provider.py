"""Testes do CCXTProvider com mocks (sem dependencia de rede)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from packages.core.data_feed.ccxt_provider import CCXTProvider
from packages.core.models.enums import Timeframe


@pytest.fixture
def mock_exchange():
    """Cria um mock do objeto exchange ccxt."""
    exchange = MagicMock()
    exchange.symbols = ["XAU/USDT", "PAXG/USDT", "BTC/USDT"]
    exchange.load_markets.return_value = {}
    return exchange


@pytest.fixture
def sample_ohlcv():
    """Dados OHLCV no formato ccxt: [timestamp_ms, open, high, low, close, volume]."""
    base_ts = int(datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    return [
        [base_ts, 2000.0, 2005.0, 1998.0, 2003.0, 150.5],
        [base_ts + 900_000, 2003.0, 2008.0, 2001.0, 2006.0, 200.0],
        [base_ts + 1_800_000, 2006.0, 2010.0, 2004.0, 2009.0, 175.0],
    ]


class TestCCXTProviderConnect:
    @pytest.mark.asyncio
    async def test_connect_valid_exchange(self, mock_exchange):
        with patch("ccxt.binance", return_value=mock_exchange, create=True):
            provider = CCXTProvider(exchange_id="binance")
            await provider.connect()
            assert provider.is_connected
            assert provider.name == "CCXT:binance"

    @pytest.mark.asyncio
    async def test_connect_invalid_exchange(self):
        provider = CCXTProvider(exchange_id="exchange_que_nao_existe")
        with pytest.raises(ValueError, match="nao encontrada"):
            await provider.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_exchange):
        with patch("ccxt.binance", return_value=mock_exchange, create=True):
            provider = CCXTProvider(exchange_id="binance")
            await provider.connect()
            await provider.disconnect()
            assert not provider.is_connected


class TestCCXTProviderFetch:
    @pytest.mark.asyncio
    async def test_fetch_candles(self, mock_exchange, sample_ohlcv):
        mock_exchange.fetch_ohlcv.return_value = sample_ohlcv
        with patch("ccxt.binance", return_value=mock_exchange, create=True):
            provider = CCXTProvider(exchange_id="binance")
            await provider.connect()

            candles = await provider.fetch_candles(
                symbol="XAU/USDT",
                timeframe=Timeframe.M15,
                start=datetime(2025, 1, 1),
                limit=10,
            )

            assert len(candles) == 3
            assert candles[0].open == Decimal("2000.0")
            assert candles[0].close == Decimal("2003.0")
            assert candles[0].volume == Decimal("150.5")
            assert candles[0].timeframe == Timeframe.M15

    @pytest.mark.asyncio
    async def test_fetch_candles_with_end(self, mock_exchange, sample_ohlcv):
        # Retornar apenas os 2 primeiros candles (simulando filtragem por end)
        mock_exchange.fetch_ohlcv.return_value = sample_ohlcv[:2]
        with patch("ccxt.binance", return_value=mock_exchange, create=True):
            provider = CCXTProvider(exchange_id="binance")
            await provider.connect()

            candles = await provider.fetch_candles(
                symbol="XAU/USDT",
                timeframe=Timeframe.M15,
                start=datetime(2025, 1, 1),
                end=datetime(2025, 1, 1, 0, 20),
                limit=10,
            )

            assert len(candles) == 2

    @pytest.mark.asyncio
    async def test_fetch_candles_empty(self, mock_exchange):
        mock_exchange.fetch_ohlcv.return_value = []
        with patch("ccxt.binance", return_value=mock_exchange, create=True):
            provider = CCXTProvider(exchange_id="binance")
            await provider.connect()

            candles = await provider.fetch_candles(
                symbol="XAU/USDT",
                timeframe=Timeframe.M15,
                start=datetime(2025, 1, 1),
            )
            assert candles == []

    @pytest.mark.asyncio
    async def test_fetch_not_connected(self):
        provider = CCXTProvider(exchange_id="binance")
        with pytest.raises(RuntimeError, match="nao conectado"):
            await provider.fetch_candles(
                symbol="XAU/USDT",
                timeframe=Timeframe.M15,
                start=datetime(2025, 1, 1),
            )


class TestCCXTProviderLatestCandle:
    @pytest.mark.asyncio
    async def test_get_latest_candle(self, mock_exchange, sample_ohlcv):
        mock_exchange.fetch_ohlcv.return_value = sample_ohlcv[-2:]
        with patch("ccxt.binance", return_value=mock_exchange, create=True):
            provider = CCXTProvider(exchange_id="binance")
            await provider.connect()

            candle = await provider.get_latest_candle("XAU/USDT", Timeframe.M15)
            assert candle is not None
            # Penultimo candle (garantidamente fechado)
            assert candle.open == Decimal("2003.0")

    @pytest.mark.asyncio
    async def test_get_latest_candle_not_connected(self):
        provider = CCXTProvider(exchange_id="binance")
        result = await provider.get_latest_candle("XAU/USDT", Timeframe.M15)
        assert result is None


class TestCCXTProviderSymbolResolution:
    @pytest.mark.asyncio
    async def test_resolve_direct_symbol(self, mock_exchange):
        mock_exchange.fetch_ohlcv.return_value = []
        with patch("ccxt.binance", return_value=mock_exchange, create=True):
            provider = CCXTProvider(exchange_id="binance")
            await provider.connect()
            # XAU/USDT esta nos symbols, entao resolve direto
            result = provider._resolve_symbol("XAU/USDT")
            assert result == "XAU/USDT"

    @pytest.mark.asyncio
    async def test_resolve_xau_usd_to_usdt(self, mock_exchange):
        with patch("ccxt.binance", return_value=mock_exchange, create=True):
            provider = CCXTProvider(exchange_id="binance")
            await provider.connect()
            result = provider._resolve_symbol("XAU/USD")
            assert result == "XAU/USDT"

    @pytest.mark.asyncio
    async def test_resolve_unknown_symbol(self, mock_exchange):
        with patch("ccxt.binance", return_value=mock_exchange, create=True):
            provider = CCXTProvider(exchange_id="binance")
            await provider.connect()
            result = provider._resolve_symbol("INEXISTENTE/PAR")
            assert result is None

    @pytest.mark.asyncio
    async def test_list_gold_symbols(self, mock_exchange):
        mock_exchange.symbols = ["XAU/USDT", "PAXG/USDT", "BTC/USDT", "XAUT/USDT"]
        with patch("ccxt.binance", return_value=mock_exchange, create=True):
            provider = CCXTProvider(exchange_id="binance")
            await provider.connect()
            gold = provider.list_gold_symbols()
            assert "XAU/USDT" in gold
            assert "PAXG/USDT" in gold
            assert "XAUT/USDT" in gold
            assert "BTC/USDT" not in gold
