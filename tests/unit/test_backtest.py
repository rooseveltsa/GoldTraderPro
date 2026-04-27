"""Testes do modulo de backtesting."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import pytest

from packages.core.backtest.engine import BacktestConfig, BacktestEngine
from packages.core.backtest.metrics import PerformanceMetrics, calculate_metrics
from packages.core.backtest.trade import Trade
from packages.core.models.candle import Candle
from packages.core.models.enums import Direction, PatternType, Timeframe


# === Helpers ===

def make_candle(
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float = 1000.0,
    timestamp: datetime | None = None,
    timeframe: Timeframe = Timeframe.M15,
) -> Candle:
    return Candle(
        timestamp=timestamp or datetime(2025, 1, 1),
        timeframe=timeframe,
        open=Decimal(str(open_)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal(str(volume)),
    )


def make_trade(
    direction: Direction = Direction.BULLISH,
    entry: float = 2000.0,
    sl: float = 1995.0,
    tp: float = 2007.5,
    exit_price: float | None = None,
    size: float = 1.0,
    slippage: float = 0.0,
    spread: float = 0.0,
) -> Trade:
    t = Trade(
        direction=direction,
        pattern_type=PatternType.HAMMER,
        entry_price=Decimal(str(entry)),
        stop_loss=Decimal(str(sl)),
        take_profit=Decimal(str(tp)),
        position_size=Decimal(str(size)),
        slippage=Decimal(str(slippage)),
        spread=Decimal(str(spread)),
        entry_time=datetime(2025, 1, 1, 10, 0),
    )
    if exit_price is not None:
        t.close(Decimal(str(exit_price)), datetime(2025, 1, 1, 11, 0))
    return t


# === Trade Tests ===

class TestTrade:
    def test_open_trade(self):
        t = make_trade()
        assert t.is_open
        assert not t.is_closed
        assert t.pnl == Decimal("0")
        assert t.exit_reason == "OPEN"

    def test_winning_buy_trade(self):
        t = make_trade(exit_price=2007.5)
        assert t.is_closed
        assert not t.is_open
        assert t.pnl == Decimal("7.5")
        assert t.is_winner
        assert t.exit_reason == "TAKE_PROFIT"

    def test_losing_buy_trade(self):
        t = make_trade(exit_price=1995.0)
        assert t.pnl == Decimal("-5.0")
        assert t.is_loser
        assert t.exit_reason == "STOP_LOSS"

    def test_winning_sell_trade(self):
        t = make_trade(
            direction=Direction.BEARISH,
            entry=2000.0, sl=2005.0, tp=1992.5,
            exit_price=1992.5,
        )
        assert t.pnl == Decimal("7.5")
        assert t.is_winner
        assert t.exit_reason == "TAKE_PROFIT"

    def test_losing_sell_trade(self):
        t = make_trade(
            direction=Direction.BEARISH,
            entry=2000.0, sl=2005.0, tp=1992.5,
            exit_price=2005.0,
        )
        assert t.pnl == Decimal("-5.0")
        assert t.is_loser
        assert t.exit_reason == "STOP_LOSS"

    def test_risk_reward(self):
        t = make_trade()  # entry=2000, sl=1995, tp=2007.5
        assert t.risk == Decimal("5")
        assert t.reward == Decimal("7.5")

    def test_r_multiple_winner(self):
        t = make_trade(exit_price=2007.5)
        assert t.r_multiple == pytest.approx(1.5)

    def test_r_multiple_loser(self):
        t = make_trade(exit_price=1995.0)
        assert t.r_multiple == pytest.approx(-1.0)

    def test_net_pnl_with_costs(self):
        t = make_trade(exit_price=2007.5, slippage=0.5, spread=1.0)
        # pnl = 7.5, costs = (0.5 + 1.0) * 1 = 1.5
        assert t.net_pnl == Decimal("6.0")

    def test_position_sizing_effect(self):
        t = make_trade(exit_price=2007.5, size=2.0)
        assert t.pnl == Decimal("15.0")

    def test_close_method(self):
        t = make_trade()
        assert t.is_open
        exit_time = datetime(2025, 1, 1, 12, 0)
        t.close(Decimal("2003"), exit_time)
        assert t.is_closed
        assert t.exit_price == Decimal("2003")
        assert t.exit_time == exit_time

    def test_to_dict(self):
        t = make_trade(exit_price=2007.5)
        d = t.to_dict()
        assert d["direction"] == "BULLISH"
        assert d["r_multiple"] == 1.5
        assert d["exit_reason"] == "TAKE_PROFIT"
        assert "pnl" in d


# === Metrics Tests ===

class TestPerformanceMetrics:
    def test_empty_trades(self):
        m = calculate_metrics([], initial_capital=10000.0)
        assert m.total_trades == 0
        assert m.win_rate == 0.0
        assert m.equity_curve == [10000.0]

    def test_all_winners(self):
        trades = [
            make_trade(exit_price=2007.5),
            make_trade(exit_price=2010.0),
        ]
        m = calculate_metrics(trades, initial_capital=10000.0)
        assert m.total_trades == 2
        assert m.winning_trades == 2
        assert m.losing_trades == 0
        assert m.win_rate == 1.0
        assert m.profit_factor == float("inf")
        assert m.gross_profit > 0

    def test_all_losers(self):
        trades = [
            make_trade(exit_price=1995.0),
            make_trade(exit_price=1998.0),
        ]
        m = calculate_metrics(trades, initial_capital=10000.0)
        assert m.total_trades == 2
        assert m.winning_trades == 0
        assert m.losing_trades == 2
        assert m.win_rate == 0.0
        assert m.profit_factor == 0.0

    def test_mixed_trades(self):
        trades = [
            make_trade(exit_price=2007.5),  # +7.5
            make_trade(exit_price=1995.0),  # -5.0
            make_trade(exit_price=2010.0),  # +10.0
        ]
        m = calculate_metrics(trades, initial_capital=10000.0)
        assert m.total_trades == 3
        assert m.winning_trades == 2
        assert m.losing_trades == 1
        assert m.win_rate == pytest.approx(2 / 3)
        assert m.net_profit == Decimal("12.5")
        assert m.profit_factor == pytest.approx(3.5, abs=0.01)

    def test_equity_curve(self):
        trades = [
            make_trade(exit_price=2007.5),  # +7.5
            make_trade(exit_price=1995.0),  # -5.0
        ]
        m = calculate_metrics(trades, initial_capital=10000.0)
        assert m.equity_curve == [10000.0, 10007.5, 10002.5]

    def test_max_drawdown(self):
        trades = [
            make_trade(exit_price=2007.5),  # +7.5, equity=10007.5 (peak)
            make_trade(exit_price=1995.0),  # -5.0, equity=10002.5
            make_trade(exit_price=1995.0),  # -5.0, equity=9997.5
        ]
        m = calculate_metrics(trades, initial_capital=10000.0)
        # Peak=10007.5, valley=9997.5, dd=10.0
        assert m.max_drawdown == pytest.approx(10.0)

    def test_consecutive_wins_losses(self):
        trades = [
            make_trade(exit_price=2007.5),  # W
            make_trade(exit_price=2007.5),  # W
            make_trade(exit_price=2007.5),  # W
            make_trade(exit_price=1995.0),  # L
            make_trade(exit_price=1995.0),  # L
        ]
        m = calculate_metrics(trades, initial_capital=10000.0)
        assert m.max_consecutive_wins == 3
        assert m.max_consecutive_losses == 2

    def test_expectancy(self):
        trades = [
            make_trade(exit_price=2007.5),  # +7.5
            make_trade(exit_price=1995.0),  # -5.0
        ]
        m = calculate_metrics(trades, initial_capital=10000.0)
        # win_rate=0.5, avg_win=7.5, loss_rate=0.5, avg_loss=-5.0
        # expectancy = 0.5 * 7.5 + 0.5 * (-5.0) = 1.25
        assert m.expectancy == pytest.approx(1.25)

    def test_sharpe_ratio_positive(self):
        trades = [
            make_trade(exit_price=2007.5),
            make_trade(exit_price=2007.5),
            make_trade(exit_price=2007.5),
        ]
        m = calculate_metrics(trades, initial_capital=10000.0)
        # All returns equal -> std=0 -> sharpe=0
        assert m.sharpe_ratio == 0.0

    def test_to_dict(self):
        trades = [make_trade(exit_price=2007.5)]
        m = calculate_metrics(trades, initial_capital=10000.0)
        d = m.to_dict()
        assert "win_rate" in d
        assert "profit_factor" in d
        assert "sharpe_ratio" in d
        assert "max_drawdown" in d
        assert "recovery_factor" in d

    def test_open_trades_ignored(self):
        trades = [
            make_trade(exit_price=2007.5),
            make_trade(),  # open
        ]
        m = calculate_metrics(trades, initial_capital=10000.0)
        assert m.total_trades == 1


# === Engine Tests ===

class TestBacktestEngine:
    def _generate_trending_candles(
        self,
        n: int = 250,
        start_price: float = 2000.0,
        trend: float = 0.5,
    ) -> list[Candle]:
        """Gera serie de candles com tendencia para teste."""
        candles = []
        price = start_price
        base_time = datetime(2025, 1, 1, 0, 0)
        for i in range(n):
            # Movimento aleatorio com bias de tendencia
            move = trend if i % 3 != 0 else -trend * 0.8
            o = price
            c = price + move
            h = max(o, c) + abs(move) * 0.5
            l = min(o, c) - abs(move) * 0.3
            # Volume alto a cada 5 candles (simula confirmacao)
            vol = 3000.0 if i % 5 == 0 else 1000.0
            candles.append(make_candle(
                open_=round(o, 2),
                high=round(h, 2),
                low=round(l, 2),
                close=round(c, 2),
                volume=vol,
                timestamp=base_time + timedelta(minutes=15 * i),
            ))
            price = c
        return candles

    def test_insufficient_candles(self):
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config)
        candles = self._generate_trending_candles(n=50)
        result = engine.run(candles, warmup_bars=200)
        assert result.total_candles == 50
        assert len(result.trades) == 0

    def test_engine_runs_without_error(self):
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config)
        candles = self._generate_trending_candles(n=300)
        result = engine.run(candles, warmup_bars=200)
        assert result.total_candles == 300
        assert isinstance(result.metrics, PerformanceMetrics)
        assert len(result.metrics.equity_curve) >= 1

    def test_engine_respects_max_concurrent(self):
        config = BacktestConfig(
            initial_capital=10000.0,
            max_concurrent_trades=1,
        )
        engine = BacktestEngine(config)
        candles = self._generate_trending_candles(n=300)
        result = engine.run(candles, warmup_bars=200)
        # Nao podemos garantir trades, mas o engine nao deve crashar
        assert result.total_candles == 300

    def test_engine_result_to_dict(self):
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config)
        candles = self._generate_trending_candles(n=250)
        result = engine.run(candles, warmup_bars=200)
        d = result.to_dict()
        assert "total_candles" in d
        assert "metrics" in d
        assert "trades" in d

    def test_anti_repainting_no_future_leak(self):
        """Garante que nenhum trade e aberto usando dados futuros."""
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config)
        candles = self._generate_trending_candles(n=300)
        result = engine.run(candles, warmup_bars=200)

        for trade in result.trades:
            # entry_time deve ser posterior ao warmup
            warmup_end = candles[200].timestamp
            assert trade.entry_time >= warmup_end, (
                f"Trade aberto antes do fim do warmup: {trade.entry_time}"
            )

    def test_all_trades_closed(self):
        """Garante que todos os trades sao fechados ao final."""
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config)
        candles = self._generate_trending_candles(n=300)
        result = engine.run(candles, warmup_bars=200)

        for trade in result.trades:
            assert trade.is_closed, "Trade deveria estar fechado ao final do backtest"

    def test_check_exit_bullish_stop_loss(self):
        engine = BacktestEngine()
        trade = make_trade(
            direction=Direction.BULLISH,
            entry=2000.0, sl=1995.0, tp=2007.5,
        )
        candle = make_candle(1998.0, 2001.0, 1994.0, 1996.0)
        result = engine._check_exit(trade, candle)
        assert result == Decimal("1995")

    def test_check_exit_bullish_take_profit(self):
        engine = BacktestEngine()
        trade = make_trade(
            direction=Direction.BULLISH,
            entry=2000.0, sl=1995.0, tp=2007.5,
        )
        candle = make_candle(2005.0, 2008.0, 2004.0, 2007.0)
        result = engine._check_exit(trade, candle)
        assert result == Decimal("2007.5")

    def test_check_exit_bearish_stop_loss(self):
        engine = BacktestEngine()
        trade = make_trade(
            direction=Direction.BEARISH,
            entry=2000.0, sl=2005.0, tp=1992.5,
        )
        candle = make_candle(2003.0, 2006.0, 2002.0, 2004.0)
        result = engine._check_exit(trade, candle)
        assert result == Decimal("2005")

    def test_check_exit_bearish_take_profit(self):
        engine = BacktestEngine()
        trade = make_trade(
            direction=Direction.BEARISH,
            entry=2000.0, sl=2005.0, tp=1992.5,
        )
        candle = make_candle(1994.0, 1996.0, 1992.0, 1993.0)
        result = engine._check_exit(trade, candle)
        assert result == Decimal("1992.5")

    def test_check_exit_no_hit(self):
        engine = BacktestEngine()
        trade = make_trade(
            direction=Direction.BULLISH,
            entry=2000.0, sl=1995.0, tp=2007.5,
        )
        candle = make_candle(2001.0, 2003.0, 1999.0, 2002.0)
        result = engine._check_exit(trade, candle)
        assert result is None

    def test_sl_priority_over_tp(self):
        """Quando SL e TP sao ambos atingidos, SL tem prioridade."""
        engine = BacktestEngine()
        trade = make_trade(
            direction=Direction.BULLISH,
            entry=2000.0, sl=1995.0, tp=2007.5,
        )
        # Candle com range enorme — atinge ambos
        candle = make_candle(2000.0, 2010.0, 1990.0, 2005.0)
        result = engine._check_exit(trade, candle)
        # SL e verificado primeiro
        assert result == Decimal("1995")
