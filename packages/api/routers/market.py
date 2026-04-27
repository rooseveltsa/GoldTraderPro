"""Endpoints de dados de mercado — candles e simbolos ao vivo."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from packages.core.data_feed.ccxt_provider import CCXTProvider
from packages.core.models.enums import Timeframe

router = APIRouter(prefix="/market", tags=["market"])

TIMEFRAME_MAP = {
    "M5": Timeframe.M5, "M15": Timeframe.M15, "M30": Timeframe.M30,
    "H1": Timeframe.H1, "H4": Timeframe.H4, "D1": Timeframe.D1,
    "W1": Timeframe.W1,
}


@router.get("/candles")
async def get_candles(
    symbol: str = Query(default="PAXG/USDT", description="Simbolo do ativo"),
    timeframe: str = Query(default="H1", description="Timeframe"),
    days: int = Query(default=7, ge=1, le=365, description="Dias de historico"),
    exchange: str = Query(default="binance", description="Exchange"),
    limit: int = Query(default=500, ge=1, le=5000),
):
    """Busca candles historicos de uma exchange."""
    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        return {"error": f"Timeframe invalido. Use: {list(TIMEFRAME_MAP.keys())}"}

    provider = CCXTProvider(exchange_id=exchange)
    try:
        await provider.connect()
        start = datetime.utcnow() - timedelta(days=days)
        candles = await provider.fetch_candles(symbol, tf, start, limit=limit)
        await provider.disconnect()
    except Exception as e:
        return {"error": str(e)}

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "exchange": exchange,
        "count": len(candles),
        "candles": [
            {
                "timestamp": c.timestamp.isoformat(),
                "open": str(c.open),
                "high": str(c.high),
                "low": str(c.low),
                "close": str(c.close),
                "volume": str(c.volume),
            }
            for c in candles
        ],
    }


@router.get("/symbols")
async def get_gold_symbols(
    exchange: str = Query(default="binance"),
):
    """Lista simbolos de ouro disponiveis na exchange."""
    provider = CCXTProvider(exchange_id=exchange)
    try:
        await provider.connect()
        symbols = provider.list_gold_symbols()
        await provider.disconnect()
    except Exception as e:
        return {"error": str(e)}

    return {"exchange": exchange, "symbols": symbols}


@router.get("/latest")
async def get_latest_price(
    symbol: str = Query(default="PAXG/USDT"),
    timeframe: str = Query(default="M15"),
    exchange: str = Query(default="binance"),
):
    """Retorna o ultimo candle fechado (preco mais recente)."""
    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        return {"error": "Timeframe invalido"}

    provider = CCXTProvider(exchange_id=exchange)
    try:
        await provider.connect()
        candle = await provider.get_latest_candle(symbol, tf)
        await provider.disconnect()
    except Exception as e:
        return {"error": str(e)}

    if candle is None:
        return {"error": "Nenhum candle encontrado"}

    return {
        "symbol": symbol,
        "timestamp": candle.timestamp.isoformat(),
        "open": str(candle.open),
        "high": str(candle.high),
        "low": str(candle.low),
        "close": str(candle.close),
        "volume": str(candle.volume),
    }
