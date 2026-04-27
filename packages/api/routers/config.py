"""System configuration endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/config", tags=["config"])


class SystemConfig(BaseModel):
    """Configuracao do sistema de trading."""

    adx_threshold: float = 32.0
    min_confluence: float = 0.65
    risk_per_trade: float = 0.01
    min_risk_reward: float = 1.5
    max_concurrent_trades: int = 3
    max_daily_drawdown: float = 0.03
    slippage_pips: float = 0.5
    spread_pips: float = 2.0
    default_timeframe: str = "H1"
    default_symbol: str = "PAXG/USDT"
    default_exchange: str = "binance"


class TelegramSettings(BaseModel):
    """Configuracao de alertas Telegram."""

    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = False


_current_config = SystemConfig()
_telegram_config = TelegramSettings()


@router.get("")
async def get_config():
    """Retorna configuracao atual do sistema."""
    return _current_config.model_dump()


@router.put("")
async def update_config(config: SystemConfig):
    """Atualiza configuracao do sistema."""
    global _current_config
    _current_config = config
    return {"status": "updated", "config": _current_config.model_dump()}


@router.get("/telegram")
async def get_telegram_config():
    """Retorna configuracao do Telegram."""
    return {
        "enabled": _telegram_config.enabled,
        "chat_id": _telegram_config.chat_id,
        "configured": bool(_telegram_config.bot_token),
    }


@router.put("/telegram")
async def update_telegram_config(settings: TelegramSettings):
    """Atualiza configuracao do Telegram."""
    global _telegram_config
    _telegram_config = settings
    return {"status": "updated", "enabled": settings.enabled}
