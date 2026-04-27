"""GoldTrader Pro — API REST.

Servidor FastAPI que expoe:
- /health         — status do sistema
- /market/*       — dados de mercado ao vivo (candles, precos, simbolos)
- /signals/*      — avaliacao de sinais em tempo real
- /backtest/*     — backtesting on-demand
- /trading/*      — controle do paper trading

Uso:
    uvicorn packages.api.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.api.routers import backtest, config, health, market, risk, signals, trading, ws

app = FastAPI(
    title="GoldTrader Pro",
    description="API de trading algoritmico para XAU/USD",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — permitir acesso do dashboard (Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos para dev/demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(market.router)
app.include_router(signals.router)
app.include_router(backtest.router)
app.include_router(trading.router)
app.include_router(risk.router)
app.include_router(config.router)
app.include_router(ws.router)


@app.get("/")
async def root():
    return {
        "service": "GoldTrader Pro",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/market/candles",
            "/market/symbols",
            "/market/latest",
            "/signals/evaluate",
            "/backtest/run",
            "/trading/paper/start",
            "/trading/paper/stop",
            "/trading/paper/status",
            "/trading/paper/metrics",
            "/risk/summary",
            "/config",
            "/config/telegram",
            "/ws/live",
        ],
    }
