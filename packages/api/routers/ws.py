"""WebSocket endpoint for live market data streaming."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from packages.core.data_feed.ccxt_provider import CCXTProvider
from packages.core.models.enums import Timeframe
from packages.core.signal_evaluator import SignalEvaluator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

TIMEFRAME_MAP = {
    "M5": Timeframe.M5,
    "M15": Timeframe.M15,
    "M30": Timeframe.M30,
    "H1": Timeframe.H1,
    "H4": Timeframe.H4,
}


class ConnectionManager:
    """Gerencia conexoes WebSocket ativas."""

    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict) -> None:
        for ws in list(self.active):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_live(
    ws: WebSocket,
    symbol: str = "PAXG/USDT",
    timeframe: str = "H1",
    exchange: str = "binance",
) -> None:
    """Stream de dados de mercado ao vivo e sinais via WebSocket."""
    tf = TIMEFRAME_MAP.get(timeframe, Timeframe.H1)
    await manager.connect(ws)

    provider = CCXTProvider(exchange_id=exchange)
    evaluator = SignalEvaluator()

    try:
        await provider.connect()

        start = datetime.utcnow() - timedelta(days=30)
        candle_buffer = await provider.fetch_candles(symbol, tf, start, limit=200)

        await ws.send_json({
            "type": "init",
            "candles": [
                {
                    "timestamp": c.timestamp.isoformat(),
                    "open": str(c.open),
                    "high": str(c.high),
                    "low": str(c.low),
                    "close": str(c.close),
                    "volume": str(c.volume),
                }
                for c in candle_buffer[-50:]
            ],
        })

        last_time = candle_buffer[-1].timestamp if candle_buffer else None

        while True:
            await asyncio.sleep(30)

            candle = await provider.get_latest_candle(symbol, tf)
            if candle is None:
                continue

            if last_time and candle.timestamp <= last_time:
                await ws.send_json({
                    "type": "tick",
                    "timestamp": candle.timestamp.isoformat(),
                    "close": str(candle.close),
                    "volume": str(candle.volume),
                })
                continue

            last_time = candle.timestamp
            candle_buffer.append(candle)
            if len(candle_buffer) > 300:
                candle_buffer = candle_buffer[-300:]

            await ws.send_json({
                "type": "candle",
                "data": {
                    "timestamp": candle.timestamp.isoformat(),
                    "open": str(candle.open),
                    "high": str(candle.high),
                    "low": str(candle.low),
                    "close": str(candle.close),
                    "volume": str(candle.volume),
                },
            })

            signals = evaluator.evaluate(candle_buffer, timeframe=tf)
            valid = [s for s in signals if s.is_valid]
            if valid:
                await ws.send_json({
                    "type": "signals",
                    "data": [s.to_dict() for s in valid],
                })

    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        manager.disconnect(ws)
    finally:
        try:
            await provider.disconnect()
        except Exception:
            pass
