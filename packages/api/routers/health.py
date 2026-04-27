"""Health check e status do sistema."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "GoldTrader Pro",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }
