"""Dependencias compartilhadas da API — singletons e estado global."""

from __future__ import annotations

from typing import Optional

from packages.core.execution.paper_trader import PaperTrader, PaperTradingConfig


class AppState:
    """Estado global da aplicacao."""

    def __init__(self) -> None:
        self.paper_trader: Optional[PaperTrader] = None
        self.paper_config: Optional[PaperTradingConfig] = None


app_state = AppState()


def get_paper_trader() -> Optional[PaperTrader]:
    return app_state.paper_trader
