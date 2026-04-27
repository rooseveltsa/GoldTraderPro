"""Endpoints de Paper Trading — controle e monitoramento ao vivo."""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Query

from packages.api.dependencies import app_state
from packages.core.execution.paper_trader import PaperTrader, PaperTradingConfig
from packages.core.models.enums import Timeframe

router = APIRouter(prefix="/trading", tags=["trading"])

TIMEFRAME_MAP = {
    "M5": Timeframe.M5, "M15": Timeframe.M15, "M30": Timeframe.M30,
    "H1": Timeframe.H1, "H4": Timeframe.H4,
}

_trading_task: Optional[asyncio.Task] = None


@router.post("/paper/start")
async def start_paper_trading(
    symbol: str = Query(default="PAXG/USDT"),
    timeframe: str = Query(default="H1"),
    exchange: str = Query(default="binance"),
    capital: float = Query(default=10000.0, ge=100.0),
    risk: float = Query(default=0.01, ge=0.001, le=0.05),
    poll_interval: int = Query(default=60, ge=10, le=3600),
):
    """Inicia o paper trading ao vivo."""
    global _trading_task

    if app_state.paper_trader and app_state.paper_trader.state.is_running:
        return {"error": "Paper trading ja esta rodando. Use /trading/paper/stop primeiro."}

    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        return {"error": f"Timeframe invalido. Use: {list(TIMEFRAME_MAP.keys())}"}

    config = PaperTradingConfig(
        exchange_id=exchange,
        symbol=symbol,
        timeframe=tf,
        initial_capital=capital,
        risk_per_trade=risk,
        poll_interval_seconds=poll_interval,
    )

    app_state.paper_trader = PaperTrader(config=config)
    app_state.paper_config = config

    _trading_task = asyncio.create_task(app_state.paper_trader.start())

    return {
        "status": "started",
        "symbol": symbol,
        "timeframe": timeframe,
        "exchange": exchange,
        "capital": capital,
        "poll_interval": poll_interval,
    }


@router.post("/paper/stop")
async def stop_paper_trading():
    """Para o paper trading e retorna resumo."""
    global _trading_task

    if not app_state.paper_trader or not app_state.paper_trader.state.is_running:
        return {"error": "Paper trading nao esta rodando."}

    await app_state.paper_trader.stop()

    if _trading_task:
        _trading_task.cancel()
        try:
            await _trading_task
        except asyncio.CancelledError:
            pass
        _trading_task = None

    summary = app_state.paper_trader.summary()
    return {"status": "stopped", **summary}


@router.get("/paper/status")
async def paper_trading_status():
    """Retorna o status atual do paper trading."""
    if not app_state.paper_trader:
        return {"status": "not_initialized"}

    summary = app_state.paper_trader.summary()
    state = app_state.paper_trader.state

    # Trades abertos
    open_trades = [
        {
            "direction": t.direction.value,
            "pattern": t.pattern_type.value,
            "entry_price": str(t.entry_price),
            "stop_loss": str(t.stop_loss),
            "take_profit": str(t.take_profit),
            "entry_time": t.entry_time.isoformat(),
            "confluence": round(t.confluence_score, 4),
        }
        for t in state.open_trades
    ]

    # Ultimos trades fechados
    recent_closed = [t.to_dict() for t in state.closed_trades[-10:]]

    return {
        **summary,
        "open_trades": open_trades,
        "recent_trades": recent_closed,
    }


@router.get("/paper/metrics")
async def paper_trading_metrics():
    """Retorna metricas de performance do paper trading."""
    if not app_state.paper_trader:
        return {"error": "Paper trading nao inicializado."}

    m = app_state.paper_trader.metrics
    return m.to_dict()
