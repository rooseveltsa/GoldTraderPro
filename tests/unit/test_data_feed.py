"""Testes unitários para o DataFeedManager e CSVProvider."""

import csv
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from packages.core.data_feed.csv_provider import CSVProvider
from packages.core.data_feed.manager import DataFeedManager
from packages.core.models.enums import Timeframe


@pytest.fixture
def sample_csv_dir():
    """Cria um diretório temporário com CSV de teste."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "XAUUSD_M15.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            # 5 candles de teste
            writer.writerow(["2026-01-15 10:00:00", "2650.00", "2655.00", "2648.00", "2653.00", "1500"])
            writer.writerow(["2026-01-15 10:15:00", "2653.00", "2658.00", "2651.00", "2656.00", "1800"])
            writer.writerow(["2026-01-15 10:30:00", "2656.00", "2660.00", "2654.00", "2655.00", "1200"])
            writer.writerow(["2026-01-15 10:45:00", "2655.00", "2657.00", "2645.00", "2646.00", "2500"])
            writer.writerow(["2026-01-15 11:00:00", "2646.00", "2652.00", "2644.00", "2651.00", "2000"])
        yield tmpdir


class TestCSVProvider:
    @pytest.mark.asyncio
    async def test_connect(self, sample_csv_dir):
        provider = CSVProvider(sample_csv_dir)
        await provider.connect()
        assert provider.is_connected is True
        assert provider.name == "CSV"

    @pytest.mark.asyncio
    async def test_connect_invalid_dir(self):
        provider = CSVProvider("/nonexistent/path")
        with pytest.raises(FileNotFoundError):
            await provider.connect()

    @pytest.mark.asyncio
    async def test_fetch_candles(self, sample_csv_dir):
        provider = CSVProvider(sample_csv_dir)
        await provider.connect()

        candles = await provider.fetch_candles(
            symbol="XAU/USD",
            timeframe=Timeframe.M15,
            start=datetime(2026, 1, 15),
        )
        assert len(candles) == 5
        assert candles[0].open == pytest.approx(2650.00, abs=0.01)
        assert candles[0].timeframe == Timeframe.M15

    @pytest.mark.asyncio
    async def test_fetch_candles_with_range(self, sample_csv_dir):
        provider = CSVProvider(sample_csv_dir)
        await provider.connect()

        candles = await provider.fetch_candles(
            symbol="XAU/USD",
            timeframe=Timeframe.M15,
            start=datetime(2026, 1, 15, 10, 15),
            end=datetime(2026, 1, 15, 10, 45),
        )
        assert len(candles) == 3

    @pytest.mark.asyncio
    async def test_fetch_candles_with_limit(self, sample_csv_dir):
        provider = CSVProvider(sample_csv_dir)
        await provider.connect()

        candles = await provider.fetch_candles(
            symbol="XAU/USD",
            timeframe=Timeframe.M15,
            start=datetime(2026, 1, 15),
            limit=2,
        )
        assert len(candles) == 2

    @pytest.mark.asyncio
    async def test_get_latest_candle(self, sample_csv_dir):
        provider = CSVProvider(sample_csv_dir)
        await provider.connect()

        # Primeiro carregar os candles
        await provider.fetch_candles("XAU/USD", Timeframe.M15, datetime(2026, 1, 15))

        latest = await provider.get_latest_candle("XAU/USD", Timeframe.M15)
        assert latest is not None
        assert latest.timestamp == datetime(2026, 1, 15, 11, 0)

    @pytest.mark.asyncio
    async def test_disconnect(self, sample_csv_dir):
        provider = CSVProvider(sample_csv_dir)
        await provider.connect()
        await provider.disconnect()
        assert provider.is_connected is False


class TestDataFeedManager:
    @pytest.mark.asyncio
    async def test_register_and_activate(self, sample_csv_dir):
        manager = DataFeedManager()
        provider = CSVProvider(sample_csv_dir)

        manager.register_provider(provider)
        await manager.set_active_provider("CSV")

        assert manager.active_provider.name == "CSV"

    @pytest.mark.asyncio
    async def test_no_active_provider_raises(self):
        manager = DataFeedManager()
        with pytest.raises(RuntimeError, match="Nenhum provider ativo"):
            _ = manager.active_provider

    @pytest.mark.asyncio
    async def test_load_candles_populates_buffer(self, sample_csv_dir):
        manager = DataFeedManager()
        provider = CSVProvider(sample_csv_dir)
        manager.register_provider(provider)
        await manager.set_active_provider("CSV")

        candles = await manager.load_candles(
            "XAU/USD", Timeframe.M15, datetime(2026, 1, 15),
        )
        assert len(candles) == 5

        buffer = manager.get_buffer("XAU/USD", Timeframe.M15)
        assert len(buffer) == 5

    @pytest.mark.asyncio
    async def test_get_last_n_candles(self, sample_csv_dir):
        manager = DataFeedManager()
        provider = CSVProvider(sample_csv_dir)
        manager.register_provider(provider)
        await manager.set_active_provider("CSV")

        await manager.load_candles("XAU/USD", Timeframe.M15, datetime(2026, 1, 15))

        last_3 = manager.get_last_n_candles("XAU/USD", Timeframe.M15, 3)
        assert len(last_3) == 3
        assert last_3[-1].timestamp == datetime(2026, 1, 15, 11, 0)

    @pytest.mark.asyncio
    async def test_empty_buffer(self):
        manager = DataFeedManager()
        buffer = manager.get_buffer("XAU/USD", Timeframe.M15)
        assert buffer == []

    @pytest.mark.asyncio
    async def test_disconnect_all(self, sample_csv_dir):
        manager = DataFeedManager()
        provider = CSVProvider(sample_csv_dir)
        manager.register_provider(provider)
        await manager.set_active_provider("CSV")

        await manager.disconnect_all()
        assert provider.is_connected is False
