"""Endpoints de sinais — avaliar candles e gerar sinais de trading."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from packages.core.data_feed.ccxt_provider import CCXTProvider
from packages.core.models.enums import Timeframe
from packages.core.signal_evaluator import SignalEvaluator

router = APIRouter(prefix="/signals", tags=["signals"])

TIMEFRAME_MAP = {
    "M5": Timeframe.M5, "M15": Timeframe.M15, "M30": Timeframe.M30,
    "H1": Timeframe.H1, "H4": Timeframe.H4, "D1": Timeframe.D1,
}


@router.get("/evaluate")
async def evaluate_signals(
    symbol: str = Query(default="PAXG/USDT"),
    timeframe: str = Query(default="H1"),
    exchange: str = Query(default="binance"),
    lookback_bars: int = Query(default=200, ge=50, le=500),
    min_confluence: float = Query(default=0.65, ge=0.0, le=1.0),
    adx_threshold: float = Query(default=32.0, ge=10.0, le=50.0),
):
    """Avalia sinais no mercado atual com base nos indicadores."""
    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        return {"error": f"Timeframe invalido. Use: {list(TIMEFRAME_MAP.keys())}"}

    provider = CCXTProvider(exchange_id=exchange)
    try:
        await provider.connect()

        tf_minutes = tf.minutes
        lookback_delta = timedelta(minutes=tf_minutes * (lookback_bars + 10))
        start = datetime.utcnow() - lookback_delta

        candles = await provider.fetch_candles(
            symbol, tf, start, limit=lookback_bars + 10,
        )
        await provider.disconnect()
    except Exception as e:
        return {"error": str(e)}

    if len(candles) < 50:
        return {
            "signals": [],
            "message": f"Dados insuficientes: {len(candles)} candles (minimo 50)",
        }

    evaluator = SignalEvaluator(
        min_confluence=min_confluence,
        adx_threshold=adx_threshold,
    )

    signals = evaluator.evaluate(candles, timeframe=tf)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles_analyzed": len(candles),
        "last_candle": candles[-1].timestamp.isoformat() if candles else None,
        "last_price": str(candles[-1].close) if candles else None,
        "total_signals": len(signals),
        "valid_signals": len([s for s in signals if s.is_valid]),
        "signals": [s.to_dict() for s in signals],
    }
