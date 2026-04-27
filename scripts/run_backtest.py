"""Script para rodar backtest com dados reais do mercado via CCXT.

Uso:
    python scripts/run_backtest.py
    python scripts/run_backtest.py --exchange bybit --symbol PAXG/USDT --days 180
    python scripts/run_backtest.py --timeframe H1 --capital 50000
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar root ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.backtest.engine import BacktestConfig, BacktestEngine
from packages.core.data_feed.ccxt_provider import CCXTProvider
from packages.core.models.enums import Timeframe

TIMEFRAME_MAP = {
    "M5": Timeframe.M5,
    "M15": Timeframe.M15,
    "M30": Timeframe.M30,
    "H1": Timeframe.H1,
    "H4": Timeframe.H4,
    "D1": Timeframe.D1,
}


def print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_section(title: str) -> None:
    print(f"\n--- {title} ---")


async def fetch_data(
    exchange_id: str,
    symbol: str,
    timeframe: Timeframe,
    days: int,
) -> list:
    """Busca dados historicos via CCXT."""
    provider = CCXTProvider(exchange_id=exchange_id)
    await provider.connect()

    gold_symbols = provider.list_gold_symbols()
    print(f"  Simbolos de ouro disponiveis: {gold_symbols[:8]}")

    start = datetime.utcnow() - timedelta(days=days)
    print(f"  Buscando {days} dias de {symbol} ({timeframe.value})...")

    candles = await provider.fetch_candles(
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        limit=days * (1440 // timeframe.minutes),  # Estimar quantidade
    )

    await provider.disconnect()
    return candles


async def main() -> None:
    parser = argparse.ArgumentParser(description="GoldTrader Pro - Backtest")
    parser.add_argument("--exchange", default="binance", help="Exchange (default: binance)")
    parser.add_argument("--symbol", default="PAXG/USDT", help="Simbolo (default: PAXG/USDT)")
    parser.add_argument("--timeframe", default="H4", help="Timeframe (default: H4)")
    parser.add_argument("--days", type=int, default=90, help="Dias de historico (default: 90)")
    parser.add_argument("--capital", type=float, default=10000.0, help="Capital inicial (default: 10000)")
    parser.add_argument("--risk", type=float, default=0.01, help="Risco por trade (default: 0.01)")
    parser.add_argument("--warmup", type=int, default=50, help="Barras de warmup (default: 50)")
    args = parser.parse_args()

    tf = TIMEFRAME_MAP.get(args.timeframe)
    if tf is None:
        print(f"Timeframe invalido: {args.timeframe}. Use: {list(TIMEFRAME_MAP.keys())}")
        sys.exit(1)

    print_header("GoldTrader Pro - Backtest com Dados Reais")
    print(f"  Exchange:   {args.exchange}")
    print(f"  Simbolo:    {args.symbol}")
    print(f"  Timeframe:  {args.timeframe}")
    print(f"  Periodo:    {args.days} dias")
    print(f"  Capital:    ${args.capital:,.2f}")
    print(f"  Risco/trade: {args.risk * 100:.1f}%")

    # 1. Buscar dados
    print_section("Buscando dados do mercado")
    candles = await fetch_data(args.exchange, args.symbol, tf, args.days)
    print(f"  Candles carregados: {len(candles)}")

    if not candles:
        print("  ERRO: Nenhum candle retornado. Verifique o simbolo e a exchange.")
        sys.exit(1)

    first = candles[0]
    last = candles[-1]
    print(f"  Periodo: {first.timestamp.strftime('%Y-%m-%d')} -> {last.timestamp.strftime('%Y-%m-%d')}")
    print(f"  Preco inicial: ${first.open}")
    print(f"  Preco final:   ${last.close}")
    price_change = float((last.close - first.open) / first.open * 100)
    print(f"  Variacao:      {price_change:+.2f}%")

    # 2. Configurar e rodar backtest
    print_section("Executando Backtest")
    config = BacktestConfig(
        initial_capital=args.capital,
        risk_per_trade=args.risk,
        min_risk_reward=1.5,
        max_concurrent_trades=3,
        max_daily_drawdown=0.03,
        slippage_pips=0.5,
        spread_pips=2.0,
        min_confluence=0.65,
        adx_threshold=32.0,
        pip_value=0.01,
    )

    engine = BacktestEngine(config)
    result = engine.run(candles, timeframe=tf, warmup_bars=args.warmup)

    # 3. Exibir resultados
    m = result.metrics
    print_section("Resultados")
    print(f"  Total de candles analisados:  {result.total_candles}")
    print(f"  Sinais gerados:               {result.total_signals}")
    print(f"  Sinais filtrados:             {result.signals_filtered}")
    print(f"  Trades executados:            {m.total_trades}")

    if m.total_trades == 0:
        print("\n  Nenhum trade foi executado.")
        print("  Possivel causa: ADX < 32 (mercado sem tendencia), ou")
        print("  confluencia < 0.65 nos sinais detectados.")
        print("  Tente: --timeframe H1 ou --timeframe D1 ou --days 180")
        return

    print_section("Performance")
    print(f"  Trades vencedores:  {m.winning_trades} ({m.win_rate * 100:.1f}%)")
    print(f"  Trades perdedores:  {m.losing_trades} ({m.loss_rate * 100:.1f}%)")
    print(f"  Breakeven:          {m.breakeven_trades}")

    print_section("Financeiro")
    print(f"  Lucro bruto:    ${m.gross_profit:>10}")
    print(f"  Perda bruta:    ${m.gross_loss:>10}")
    print(f"  Lucro liquido:  ${m.net_profit:>10}")
    print(f"  Profit Factor:  {m.profit_factor:.2f}")
    print(f"  Expectancia:    ${m.expectancy:.2f} por trade")

    print_section("Risco")
    print(f"  Max Drawdown:          ${m.max_drawdown:.2f} ({m.max_drawdown_pct * 100:.2f}%)")
    print(f"  Sharpe Ratio:          {m.sharpe_ratio:.2f}")
    print(f"  Recovery Factor:       {m.recovery_factor:.2f}")
    print(f"  Max vitórias seguidas: {m.max_consecutive_wins}")
    print(f"  Max derrotas seguidas: {m.max_consecutive_losses}")

    print_section("Medias")
    print(f"  Media ganho:     ${m.avg_win}")
    print(f"  Media perda:     ${m.avg_loss}")
    print(f"  Media R-multiple: {m.avg_r_multiple:.2f}R")

    # 4. Listar trades
    if result.trades:
        print_section(f"Ultimos Trades (mostrando {min(10, len(result.trades))})")
        print(f"  {'#':>3} {'Dir':>5} {'Padrao':>18} {'Entry':>10} {'Exit':>10} {'PnL':>10} {'R':>5} {'Saida':>12}")
        print(f"  {'---':>3} {'-----':>5} {'------------------':>18} {'----------':>10} {'----------':>10} {'----------':>10} {'-----':>5} {'------------':>12}")
        for i, t in enumerate(result.trades[-10:], 1):
            d = t.to_dict()
            print(
                f"  {i:>3} {d['direction']:>5} {d['pattern']:>18} "
                f"${float(t.entry_price):>9.2f} ${float(t.exit_price):>9.2f} "
                f"${float(t.net_pnl):>9.2f} {t.r_multiple:>4.1f}R {d['exit_reason']:>12}"
            )

    # 5. Equity curve resumida
    eq = m.equity_curve
    if len(eq) > 1:
        print_section("Equity Curve (resumo)")
        retorno_total = (eq[-1] - eq[0]) / eq[0] * 100
        print(f"  Capital inicial: ${eq[0]:,.2f}")
        print(f"  Capital final:   ${eq[-1]:,.2f}")
        print(f"  Retorno total:   {retorno_total:+.2f}%")
        peak = max(eq)
        valley = min(eq)
        print(f"  Pico:            ${peak:,.2f}")
        print(f"  Vale:            ${valley:,.2f}")

    print_header("Backtest Concluido")


if __name__ == "__main__":
    asyncio.run(main())
