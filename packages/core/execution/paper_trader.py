"""Paper Trading — execucao simulada em tempo real.

Monitora o mercado ao vivo via CCXT, gera sinais com o SignalEvaluator,
e registra trades virtuais sem arriscar dinheiro real.

Uso:
    trader = PaperTrader(config)
    await trader.start()  # Loop continuo
    await trader.stop()   # Para o loop
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional

from packages.core.backtest.metrics import PerformanceMetrics, calculate_metrics
from packages.core.backtest.trade import Trade
from packages.core.data_feed.ccxt_provider import CCXTProvider
from packages.core.models.candle import Candle
from packages.core.models.enums import Direction, Timeframe
from packages.core.models.order import PositionSizing
from packages.core.signal_evaluator import SignalEvaluator

logger = logging.getLogger(__name__)


@dataclass
class PaperTradingConfig:
    """Configuracao do paper trading."""

    exchange_id: str = "binance"
    symbol: str = "PAXG/USDT"
    timeframe: Timeframe = Timeframe.M15
    initial_capital: float = 10000.0
    risk_per_trade: float = 0.01
    min_risk_reward: float = 1.5
    max_concurrent_trades: int = 3
    min_confluence: float = 0.65
    adx_threshold: float = 32.0
    slippage_pips: float = 0.5
    spread_pips: float = 2.0
    pip_value: float = 0.01
    warmup_bars: int = 200
    poll_interval_seconds: int = 60


@dataclass
class PaperTradingState:
    """Estado atual do paper trader."""

    equity: float = 0.0
    open_trades: list = field(default_factory=list)
    closed_trades: list = field(default_factory=list)
    candle_buffer: list = field(default_factory=list)
    last_candle_time: Optional[datetime] = None
    signals_generated: int = 0
    is_running: bool = False


class PaperTrader:
    """Motor de paper trading ao vivo."""

    def __init__(
        self,
        config: Optional[PaperTradingConfig] = None,
        on_signal: Optional[Callable] = None,
        on_trade_open: Optional[Callable] = None,
        on_trade_close: Optional[Callable] = None,
    ) -> None:
        self._config = config or PaperTradingConfig()
        self._state = PaperTradingState(equity=self._config.initial_capital)
        self._provider = CCXTProvider(exchange_id=self._config.exchange_id)
        self._evaluator = SignalEvaluator(
            min_confluence=self._config.min_confluence,
            min_risk_reward=self._config.min_risk_reward,
            adx_threshold=self._config.adx_threshold,
        )
        # Callbacks opcionais
        self._on_signal = on_signal
        self._on_trade_open = on_trade_open
        self._on_trade_close = on_trade_close

    @property
    def state(self) -> PaperTradingState:
        return self._state

    @property
    def metrics(self) -> PerformanceMetrics:
        return calculate_metrics(
            self._state.closed_trades,
            initial_capital=self._config.initial_capital,
        )

    async def start(self) -> None:
        """Inicia o loop de paper trading."""
        await self._provider.connect()
        self._state.is_running = True

        logger.info(
            "Paper Trading iniciado: %s %s em %s (capital: $%.2f)",
            self._config.symbol, self._config.timeframe.value,
            self._config.exchange_id, self._config.initial_capital,
        )

        # Carregar warmup
        await self._load_warmup()

        # Loop principal
        try:
            while self._state.is_running:
                await self._tick()
                await asyncio.sleep(self._config.poll_interval_seconds)
        except asyncio.CancelledError:
            logger.info("Paper Trading cancelado")
        finally:
            await self._provider.disconnect()

    async def stop(self) -> None:
        """Para o loop de paper trading."""
        self._state.is_running = False
        logger.info("Paper Trading parado")

    async def _load_warmup(self) -> None:
        """Carrega candles historicos para warmup dos indicadores."""
        from datetime import timedelta

        tf_minutes = self._config.timeframe.minutes
        lookback = timedelta(minutes=tf_minutes * (self._config.warmup_bars + 50))
        start = datetime.utcnow() - lookback

        candles = await self._provider.fetch_candles(
            symbol=self._config.symbol,
            timeframe=self._config.timeframe,
            start=start,
            limit=self._config.warmup_bars + 50,
        )

        self._state.candle_buffer = candles
        if candles:
            self._state.last_candle_time = candles[-1].timestamp

        logger.info("Warmup carregado: %d candles", len(candles))

    async def _tick(self) -> None:
        """Executa um ciclo de verificacao."""
        # Buscar ultimo candle fechado
        candle = await self._provider.get_latest_candle(
            self._config.symbol, self._config.timeframe,
        )

        if candle is None:
            return

        # Verificar se e um candle novo (anti-repainting)
        if (
            self._state.last_candle_time is not None
            and candle.timestamp <= self._state.last_candle_time
        ):
            # Mesmo candle — apenas verificar SL/TP dos trades abertos
            await self._check_exits_live()
            return

        # Novo candle fechado
        self._state.last_candle_time = candle.timestamp
        self._state.candle_buffer.append(candle)

        # Manter buffer gerenciavel
        max_buffer = self._config.warmup_bars + 100
        if len(self._state.candle_buffer) > max_buffer:
            self._state.candle_buffer = self._state.candle_buffer[-max_buffer:]

        logger.info(
            "Novo candle: %s | O:%.2f H:%.2f L:%.2f C:%.2f V:%.0f",
            candle.timestamp, float(candle.open), float(candle.high),
            float(candle.low), float(candle.close), float(candle.volume),
        )

        # Verificar exits primeiro
        await self._check_exits(candle)

        # Avaliar sinais
        if len(self._state.open_trades) < self._config.max_concurrent_trades:
            await self._evaluate_signals()

    async def _check_exits(self, candle: Candle) -> None:
        """Verifica SL/TP nos trades abertos."""
        trades_to_close = []
        for trade in self._state.open_trades:
            exit_price = self._check_exit(trade, candle)
            if exit_price is not None:
                trades_to_close.append((trade, exit_price))

        for trade, exit_price in trades_to_close:
            trade.close(price=exit_price, time=candle.timestamp)
            self._state.open_trades.remove(trade)
            self._state.closed_trades.append(trade)
            self._state.equity += float(trade.net_pnl)

            logger.info(
                "Trade fechado: %s %s @ $%.2f -> $%.2f | PnL: $%.2f (%s)",
                trade.direction.value, trade.pattern_type.value,
                float(trade.entry_price), float(exit_price),
                float(trade.net_pnl), trade.exit_reason,
            )

            if self._on_trade_close:
                self._on_trade_close(trade)

    async def _check_exits_live(self) -> None:
        """Verifica exits usando ticker ao vivo (entre candles)."""
        # Usar o ultimo candle do buffer como proxy
        if not self._state.candle_buffer:
            return
        last = self._state.candle_buffer[-1]
        await self._check_exits(last)

    async def _evaluate_signals(self) -> None:
        """Avalia sinais no buffer de candles."""
        if len(self._state.candle_buffer) < self._config.warmup_bars:
            return

        signals = self._evaluator.evaluate(
            operational_candles=self._state.candle_buffer,
            timeframe=self._config.timeframe,
        )

        self._state.signals_generated += len(signals)

        valid = [s for s in signals if s.is_valid]

        for signal in valid:
            if self._on_signal:
                self._on_signal(signal)

            # Verificar se ja existe trade na mesma direcao
            same_dir = any(
                t.direction == signal.direction
                for t in self._state.open_trades
            )
            if same_dir:
                continue

            # Position sizing
            sizing = PositionSizing(
                capital=Decimal(str(self._state.equity)),
                risk_percent=Decimal(str(self._config.risk_per_trade)),
                entry_price=signal.entry_price,
                stop_loss_price=signal.stop_loss,
            )

            if sizing.position_size <= 0:
                continue

            slippage = Decimal(str(
                self._config.slippage_pips * self._config.pip_value,
            ))
            spread = Decimal(str(
                self._config.spread_pips * self._config.pip_value,
            ))

            entry_price = signal.entry_price + spread if signal.direction == Direction.BULLISH else signal.entry_price - spread

            trade = Trade(
                signal_id=signal.id,
                direction=signal.direction,
                pattern_type=signal.pattern_type,
                entry_price=entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                entry_time=datetime.utcnow(),
                position_size=sizing.position_size,
                confluence_score=signal.confluence.total,
                slippage=slippage,
                spread=spread,
            )

            self._state.open_trades.append(trade)

            logger.info(
                "Trade aberto: %s %s @ $%.2f (SL: $%.2f, TP: $%.2f, Conf: %.2f)",
                trade.direction.value, trade.pattern_type.value,
                float(trade.entry_price), float(trade.stop_loss),
                float(trade.take_profit), trade.confluence_score,
            )

            if self._on_trade_open:
                self._on_trade_open(trade)

            # Respeitar max concurrent
            if len(self._state.open_trades) >= self._config.max_concurrent_trades:
                break

    @staticmethod
    def _check_exit(trade: Trade, candle: Candle) -> Optional[Decimal]:
        """Verifica se candle atinge SL ou TP."""
        if trade.direction == Direction.BULLISH:
            if candle.low <= trade.stop_loss:
                return trade.stop_loss
            if candle.high >= trade.take_profit:
                return trade.take_profit
        elif trade.direction == Direction.BEARISH:
            if candle.high >= trade.stop_loss:
                return trade.stop_loss
            if candle.low <= trade.take_profit:
                return trade.take_profit
        return None

    def summary(self) -> dict:
        """Retorna resumo do estado atual."""
        m = self.metrics
        return {
            "status": "running" if self._state.is_running else "stopped",
            "equity": round(self._state.equity, 2),
            "open_trades": len(self._state.open_trades),
            "closed_trades": len(self._state.closed_trades),
            "signals_generated": self._state.signals_generated,
            "win_rate": round(m.win_rate, 4),
            "net_profit": str(m.net_profit),
            "profit_factor": round(m.profit_factor, 2),
            "max_drawdown_pct": round(m.max_drawdown_pct, 4),
            "candles_in_buffer": len(self._state.candle_buffer),
        }
