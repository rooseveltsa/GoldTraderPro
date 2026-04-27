"""Script para rodar Paper Trading ao vivo.

Uso:
    python scripts/run_paper_trading.py
    python scripts/run_paper_trading.py --symbol PAXG/USDT --timeframe M15 --capital 10000
    python scripts/run_paper_trading.py --poll 30  # Verificar a cada 30s

Ctrl+C para parar e ver o resumo.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.execution.paper_trader import PaperTrader, PaperTradingConfig
from packages.core.models.enums import Timeframe

TIMEFRAME_MAP = {
    "M5": Timeframe.M5,
    "M15": Timeframe.M15,
    "M30": Timeframe.M30,
    "H1": Timeframe.H1,
    "H4": Timeframe.H4,
}


def on_signal(signal_obj) -> None:
    print(f"\n  [SINAL] {signal_obj.direction.value} {signal_obj.pattern_type.value} "
          f"| Confluence: {signal_obj.confluence.total:.2f} "
          f"| Entry: ${signal_obj.entry_price} "
          f"| SL: ${signal_obj.stop_loss} TP: ${signal_obj.take_profit}")


def on_trade_open(trade) -> None:
    print(f"  [TRADE ABERTO] {trade.direction.value} {trade.pattern_type.value} "
          f"@ ${float(trade.entry_price):.2f} "
          f"| SL: ${float(trade.stop_loss):.2f} TP: ${float(trade.take_profit):.2f} "
          f"| Size: {float(trade.position_size):.4f}")


def on_trade_close(trade) -> None:
    emoji = "+" if trade.is_winner else "-"
    print(f"  [{emoji}TRADE FECHADO] {trade.direction.value} "
          f"@ ${float(trade.exit_price):.2f} "
          f"| PnL: ${float(trade.net_pnl):.2f} ({trade.r_multiple:.1f}R) "
          f"| Motivo: {trade.exit_reason}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="GoldTrader Pro - Paper Trading")
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--symbol", default="PAXG/USDT")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--capital", type=float, default=10000.0)
    parser.add_argument("--risk", type=float, default=0.01)
    parser.add_argument("--poll", type=int, default=60, help="Intervalo de polling em segundos")
    parser.add_argument("--warmup", type=int, default=200)
    args = parser.parse_args()

    tf = TIMEFRAME_MAP.get(args.timeframe)
    if tf is None:
        print(f"Timeframe invalido: {args.timeframe}. Use: {list(TIMEFRAME_MAP.keys())}")
        sys.exit(1)

    config = PaperTradingConfig(
        exchange_id=args.exchange,
        symbol=args.symbol,
        timeframe=tf,
        initial_capital=args.capital,
        risk_per_trade=args.risk,
        warmup_bars=args.warmup,
        poll_interval_seconds=args.poll,
    )

    trader = PaperTrader(
        config=config,
        on_signal=on_signal,
        on_trade_open=on_trade_open,
        on_trade_close=on_trade_close,
    )

    print(f"\n{'=' * 60}")
    print(f"  GoldTrader Pro - Paper Trading ao Vivo")
    print(f"{'=' * 60}")
    print(f"  Exchange:    {args.exchange}")
    print(f"  Simbolo:     {args.symbol}")
    print(f"  Timeframe:   {args.timeframe}")
    print(f"  Capital:     ${args.capital:,.2f}")
    print(f"  Risco/trade: {args.risk * 100:.1f}%")
    print(f"  Polling:     a cada {args.poll}s")
    print(f"  Inicio:      {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'=' * 60}")
    print(f"  Ctrl+C para parar e ver resumo\n")

    # Tratar Ctrl+C
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_stop():
        print("\n  Parando Paper Trading...")
        stop_event.set()

    loop.add_signal_handler(signal.SIGINT, handle_stop)

    # Iniciar em task separada
    task = asyncio.create_task(trader.start())

    # Aguardar stop
    await stop_event.wait()
    await trader.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Resumo final
    summary = trader.summary()
    m = trader.metrics

    print(f"\n{'=' * 60}")
    print(f"  Resumo Final - Paper Trading")
    print(f"{'=' * 60}")
    print(f"  Equity final:      ${summary['equity']:,.2f}")
    print(f"  Trades abertos:    {summary['open_trades']}")
    print(f"  Trades fechados:   {summary['closed_trades']}")
    print(f"  Sinais gerados:    {summary['signals_generated']}")

    if m.total_trades > 0:
        print(f"\n  Win Rate:          {m.win_rate * 100:.1f}%")
        print(f"  Profit Factor:     {m.profit_factor:.2f}")
        print(f"  Lucro liquido:     ${m.net_profit}")
        print(f"  Max Drawdown:      {m.max_drawdown_pct * 100:.2f}%")
        print(f"  Sharpe Ratio:      {m.sharpe_ratio:.2f}")

    print(f"{'=' * 60}\n")

    # Salvar estado
    state_file = Path("data/paper_trading_state.json")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(summary, indent=2, default=str))
    print(f"  Estado salvo em: {state_file}")


if __name__ == "__main__":
    asyncio.run(main())
