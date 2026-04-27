"""Backtesting Engine com protecao anti-repainting.

Regras fundamentais:
- Sinais sao avaliados APENAS em candles FECHADOS
- Slippage e spread sao simulados na entrada
- Posicoes sao gerenciadas com OCO (SL + TP)
- Maximo de trades simultaneos e respeitado
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from packages.core.backtest.metrics import PerformanceMetrics, calculate_metrics
from packages.core.backtest.trade import Trade
from packages.core.models.candle import Candle
from packages.core.models.enums import Direction, Timeframe
from packages.core.models.order import PositionSizing
from packages.core.signal_evaluator import SignalEvaluator

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuracao do backtesting."""

    initial_capital: float = 10000.0
    risk_per_trade: float = 0.01        # 1% por trade
    min_risk_reward: float = 1.5
    max_concurrent_trades: int = 3
    max_daily_drawdown: float = 0.03    # 3%
    slippage_pips: float = 0.5
    spread_pips: float = 2.0
    min_confluence: float = 0.65
    adx_threshold: float = 32.0
    pip_value: float = 0.01             # XAU/USD: 1 pip = $0.01


@dataclass
class BacktestResult:
    """Resultado completo de um backtest."""

    config: BacktestConfig
    metrics: PerformanceMetrics
    trades: list[Trade]
    total_candles: int = 0
    total_signals: int = 0
    signals_filtered: int = 0

    def to_dict(self) -> dict:
        return {
            "total_candles": self.total_candles,
            "total_signals": self.total_signals,
            "signals_filtered": self.signals_filtered,
            "total_trades": len(self.trades),
            "metrics": self.metrics.to_dict(),
            "trades": [t.to_dict() for t in self.trades],
        }


class BacktestEngine:
    """Motor de backtesting com anti-repainting.

    O engine itera sobre candles fechados, avalia sinais no fechamento
    de cada candle, e simula a execucao na abertura do proximo candle.
    """

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self._config = config or BacktestConfig()
        self._evaluator = SignalEvaluator(
            min_confluence=self._config.min_confluence,
            min_risk_reward=self._config.min_risk_reward,
            adx_threshold=self._config.adx_threshold,
        )

    def run(
        self,
        candles: list[Candle],
        primary_candles: Optional[list[Candle]] = None,
        macro_candles: Optional[list[Candle]] = None,
        timeframe: Timeframe = Timeframe.M15,
        warmup_bars: int = 200,
    ) -> BacktestResult:
        """Executa o backtest sobre uma serie de candles.

        Args:
            candles: Serie de candles do timeframe operacional (ordenada por tempo)
            primary_candles: Candles do timeframe primario (D1)
            macro_candles: Candles do timeframe macro (W1)
            timeframe: Timeframe operacional
            warmup_bars: Barras iniciais usadas apenas para calculo de indicadores

        Returns:
            BacktestResult com trades e metricas
        """
        if len(candles) <= warmup_bars:
            return BacktestResult(
                config=self._config,
                metrics=PerformanceMetrics(
                    equity_curve=[self._config.initial_capital],
                ),
                trades=[],
                total_candles=len(candles),
            )

        open_trades: list[Trade] = []
        closed_trades: list[Trade] = []
        total_signals = 0
        signals_filtered = 0
        equity = self._config.initial_capital
        daily_pnl = Decimal("0")
        current_day: str | None = None

        # Anti-repainting: iteramos sobre candles FECHADOS
        # O sinal e avaliado no candle[i], execucao simulada no candle[i+1]
        for i in range(warmup_bars, len(candles) - 1):
            closed_candle = candles[i]
            next_candle = candles[i + 1]

            # Reset daily drawdown tracking
            day_str = closed_candle.timestamp.strftime("%Y-%m-%d")
            if day_str != current_day:
                current_day = day_str
                daily_pnl = Decimal("0")

            # 1. Verificar SL/TP dos trades abertos no candle atual
            trades_to_close: list[tuple[Trade, Decimal]] = []
            for trade in open_trades:
                exit_price = self._check_exit(trade, next_candle)
                if exit_price is not None:
                    trades_to_close.append((trade, exit_price))

            for trade, exit_price in trades_to_close:
                trade.close(price=exit_price, time=next_candle.timestamp)
                open_trades.remove(trade)
                closed_trades.append(trade)
                daily_pnl += trade.net_pnl
                equity += float(trade.net_pnl)

            # 2. Verificar daily drawdown
            if self._config.max_daily_drawdown > 0:
                if float(daily_pnl) < -(
                    self._config.initial_capital * self._config.max_daily_drawdown
                ):
                    continue  # Nao abrir novos trades hoje

            # 3. Verificar limite de trades simultaneos
            if len(open_trades) >= self._config.max_concurrent_trades:
                continue

            # 4. Avaliar sinais no candle FECHADO (anti-repainting)
            lookback = candles[max(0, i - warmup_bars):i + 1]
            signals = self._evaluator.evaluate(
                operational_candles=lookback,
                primary_candles=primary_candles,
                macro_candles=macro_candles,
                timeframe=timeframe,
            )

            total_signals += len(signals)

            # 5. Filtrar sinais validos
            valid_signals = [s for s in signals if s.is_valid]
            signals_filtered += len(signals) - len(valid_signals)

            if not valid_signals:
                continue

            # 6. Pegar o melhor sinal (maior confluence)
            best_signal = valid_signals[0]  # Ja vem ordenado por confluence

            # 7. Verificar se ja existe trade na mesma direcao
            same_direction = any(
                t.direction == best_signal.direction for t in open_trades
            )
            if same_direction:
                continue

            # 8. Calcular position sizing
            sizing = PositionSizing(
                capital=Decimal(str(equity)),
                risk_percent=Decimal(str(self._config.risk_per_trade)),
                entry_price=best_signal.entry_price,
                stop_loss_price=best_signal.stop_loss,
            )

            if sizing.position_size <= 0:
                continue

            # 9. Simular execucao na ABERTURA do proximo candle
            slippage = Decimal(str(
                self._config.slippage_pips * self._config.pip_value,
            ))
            spread = Decimal(str(
                self._config.spread_pips * self._config.pip_value,
            ))

            if best_signal.direction == Direction.BULLISH:
                entry_price = next_candle.open + spread
            else:
                entry_price = next_candle.open - spread

            trade = Trade(
                signal_id=best_signal.id,
                direction=best_signal.direction,
                pattern_type=best_signal.pattern_type,
                entry_price=entry_price,
                stop_loss=best_signal.stop_loss,
                take_profit=best_signal.take_profit,
                entry_time=next_candle.timestamp,
                position_size=sizing.position_size,
                confluence_score=best_signal.confluence.total,
                slippage=slippage,
                spread=spread,
            )

            open_trades.append(trade)
            logger.debug(
                "Trade aberto: %s %s @ %s (confluence: %.2f)",
                trade.direction.value,
                trade.pattern_type.value,
                trade.entry_price,
                trade.confluence_score,
            )

        # Fechar trades ainda abertos no ultimo candle
        if open_trades and candles:
            last_candle = candles[-1]
            for trade in open_trades:
                trade.close(price=last_candle.close, time=last_candle.timestamp)
                closed_trades.append(trade)

        # Calcular metricas
        metrics = calculate_metrics(
            trades=closed_trades,
            initial_capital=self._config.initial_capital,
        )

        return BacktestResult(
            config=self._config,
            metrics=metrics,
            trades=closed_trades,
            total_candles=len(candles),
            total_signals=total_signals,
            signals_filtered=signals_filtered,
        )

    def _check_exit(self, trade: Trade, candle: Candle) -> Decimal | None:
        """Verifica se o candle atinge SL ou TP de um trade aberto.

        Prioridade: SL antes de TP (cenario pessimista).
        Verifica se o high/low do candle cruza os niveis.
        """
        if trade.direction == Direction.BULLISH:
            # Stop Loss: low do candle <= SL
            if candle.low <= trade.stop_loss:
                return trade.stop_loss
            # Take Profit: high do candle >= TP
            if candle.high >= trade.take_profit:
                return trade.take_profit
        elif trade.direction == Direction.BEARISH:
            # Stop Loss: high do candle >= SL
            if candle.high >= trade.stop_loss:
                return trade.stop_loss
            # Take Profit: low do candle <= TP
            if candle.low <= trade.take_profit:
                return trade.take_profit

        return None
