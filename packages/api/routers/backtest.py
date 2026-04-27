"""Endpoints de backtesting — rodar backtest on-demand via API."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from packages.core.backtest.engine import BacktestConfig, BacktestEngine
from packages.core.data_feed.ccxt_provider import CCXTProvider
from packages.core.models.enums import Timeframe

router = APIRouter(prefix="/backtest", tags=["backtest"])

TIMEFRAME_MAP = {
    "M15": Timeframe.M15, "M30": Timeframe.M30,
    "H1": Timeframe.H1, "H4": Timeframe.H4, "D1": Timeframe.D1,
}


@router.get("/run")
async def run_backtest(
    symbol: str = Query(default="PAXG/USDT"),
    timeframe: str = Query(default="H4"),
    exchange: str = Query(default="binance"),
    days: int = Query(default=90, ge=7, le=365),
    capital: float = Query(default=10000.0, ge=100.0),
    risk_per_trade: float = Query(default=0.01, ge=0.001, le=0.05),
    warmup_bars: int = Query(default=50, ge=20, le=200),
):
    """Executa um backtest com dados reais e retorna metricas."""
    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        return {"error": f"Timeframe invalido. Use: {list(TIMEFRAME_MAP.keys())}"}

    # Buscar dados
    provider = CCXTProvider(exchange_id=exchange)
    try:
        await provider.connect()
        start = datetime.utcnow() - timedelta(days=days)
        max_candles = days * (1440 // tf.minutes)
        candles = await provider.fetch_candles(
            symbol, tf, start, limit=max_candles,
        )
        await provider.disconnect()
    except Exception as e:
        return {"error": str(e)}

    if len(candles) <= warmup_bars:
        return {
            "error": f"Dados insuficientes: {len(candles)} candles (warmup={warmup_bars})",
        }

    # Rodar backtest
    config = BacktestConfig(
        initial_capital=capital,
        risk_per_trade=risk_per_trade,
        min_risk_reward=1.5,
        max_concurrent_trades=3,
        max_daily_drawdown=0.03,
        slippage_pips=0.5,
        spread_pips=2.0,
    )

    engine = BacktestEngine(config)
    result = engine.run(candles, timeframe=tf, warmup_bars=warmup_bars)
    m = result.metrics

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "period": {
            "start": candles[0].timestamp.isoformat(),
            "end": candles[-1].timestamp.isoformat(),
            "days": days,
            "candles": len(candles),
        },
        "config": {
            "initial_capital": capital,
            "risk_per_trade": risk_per_trade,
            "warmup_bars": warmup_bars,
        },
        "metrics": m.to_dict(),
        "summary": {
            "total_trades": m.total_trades,
            "win_rate": round(m.win_rate * 100, 1),
            "profit_factor": round(m.profit_factor, 2),
            "net_profit": str(m.net_profit),
            "return_pct": round((m.equity_curve[-1] - capital) / capital * 100, 2) if m.equity_curve else 0,
            "max_drawdown_pct": round(m.max_drawdown_pct * 100, 2),
        },
        "trades": [t.to_dict() for t in result.trades],
        "equity_curve": m.equity_curve,
    }
