"""Módulo de ingestão de dados de mercado (Data Feed)."""

from packages.core.data_feed.base import DataFeedProvider
from packages.core.data_feed.csv_provider import CSVProvider
from packages.core.data_feed.manager import DataFeedManager

__all__ = ["DataFeedManager", "DataFeedProvider", "CSVProvider"]
