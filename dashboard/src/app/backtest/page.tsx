"use client";

import { useState } from "react";
import Card from "@/components/Card";
import EquityCurveChart from "@/components/EquityCurveChart";
import { api, type BacktestResult } from "@/lib/api";

export default function BacktestPage() {
  const [timeframe, setTimeframe] = useState("H4");
  const [days, setDays] = useState(90);
  const [capital, setCapital] = useState(10000);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runBacktest() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.backtest({ timeframe, days, capital });
      setResult(data);
    } catch (e) {
      setError("Erro ao rodar backtest. Verifique se a API esta online.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 space-y-6">
      <h2 className="text-2xl font-bold">Backtest Lab</h2>

      <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6">
        <h3 className="text-sm font-medium text-[var(--muted)] mb-4">Parametros</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">Timeframe</label>
            <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}
              className="w-full bg-[var(--background)] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm">
              <option value="M15">M15</option>
              <option value="H1">H1</option>
              <option value="H4">H4</option>
              <option value="D1">D1</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">Periodo (dias)</label>
            <input type="number" value={days} onChange={(e) => setDays(Number(e.target.value))} min={7} max={365}
              className="w-full bg-[var(--background)] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">Capital Inicial ($)</label>
            <input type="number" value={capital} onChange={(e) => setCapital(Number(e.target.value))} min={100}
              className="w-full bg-[var(--background)] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm" />
          </div>
          <div className="flex items-end">
            <button onClick={runBacktest} disabled={loading}
              className="w-full bg-[var(--accent-yellow)] text-black font-medium rounded-lg px-4 py-2 text-sm hover:opacity-90 disabled:opacity-50 transition-opacity">
              {loading ? "Rodando..." : "Rodar Backtest"}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-[var(--accent-red)]/10 border border-[var(--accent-red)]/30 rounded-xl p-4 text-sm text-[var(--accent-red)]">{error}</div>
      )}

      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <Card title="Trades" value={result.summary.total_trades} />
            <Card title="Win Rate" value={`${result.summary.win_rate}%`} trend={result.summary.win_rate > 50 ? "up" : "down"} />
            <Card title="Profit Factor" value={result.summary.profit_factor.toFixed(2)} trend={result.summary.profit_factor > 1.5 ? "up" : "neutral"} />
            <Card title="Retorno" value={`${result.summary.return_pct}%`} trend={result.summary.return_pct > 0 ? "up" : "down"} />
            <Card title="Max Drawdown" value={`${result.summary.max_drawdown_pct}%`} trend={result.summary.max_drawdown_pct < 5 ? "up" : "down"} />
            <Card title="Lucro Liq." value={`$${parseFloat(result.summary.net_profit).toFixed(2)}`} trend={parseFloat(result.summary.net_profit) > 0 ? "up" : "down"} />
          </div>

          <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6">
            <h3 className="text-sm font-medium text-[var(--muted)] mb-4">
              Equity Curve
              <span className="ml-2 text-xs font-normal">
                (${Math.min(...result.equity_curve).toFixed(2)} — ${Math.max(...result.equity_curve).toFixed(2)})
              </span>
            </h3>
            <EquityCurveChart data={result.equity_curve} initialCapital={capital} height={250} />
          </div>

          {result.trades.length > 0 && (
            <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl overflow-hidden">
              <h3 className="text-sm font-medium text-[var(--muted)] px-4 py-3 border-b border-[var(--card-border)]">
                Trades ({result.trades.length})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--card-border)] text-[var(--muted)] text-xs uppercase">
                      <th className="px-4 py-2 text-left">#</th>
                      <th className="px-4 py-2 text-left">Direcao</th>
                      <th className="px-4 py-2 text-left">Padrao</th>
                      <th className="px-4 py-2 text-right">Entry</th>
                      <th className="px-4 py-2 text-right">Exit</th>
                      <th className="px-4 py-2 text-right">PnL</th>
                      <th className="px-4 py-2 text-right">R</th>
                      <th className="px-4 py-2 text-left">Motivo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((t, i) => {
                      const pnl = parseFloat(t.pnl);
                      return (
                        <tr key={i} className="border-b border-[var(--card-border)] hover:bg-white/5">
                          <td className="px-4 py-2 text-[var(--muted)]">{i + 1}</td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                              t.direction === "BULLISH" ? "bg-[var(--accent)]/20 text-[var(--accent)]" : "bg-[var(--accent-red)]/20 text-[var(--accent-red)]"
                            }`}>{t.direction === "BULLISH" ? "COMPRA" : "VENDA"}</span>
                          </td>
                          <td className="px-4 py-2 text-xs">{t.pattern}</td>
                          <td className="px-4 py-2 text-right font-mono">${parseFloat(t.entry_price).toFixed(2)}</td>
                          <td className="px-4 py-2 text-right font-mono">{t.exit_price ? `$${parseFloat(t.exit_price).toFixed(2)}` : "--"}</td>
                          <td className={`px-4 py-2 text-right font-mono font-bold ${pnl >= 0 ? "text-[var(--accent)]" : "text-[var(--accent-red)]"}`}>
                            {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}
                          </td>
                          <td className="px-4 py-2 text-right font-mono">{t.r_multiple.toFixed(1)}R</td>
                          <td className="px-4 py-2 text-xs text-[var(--muted)]">{t.exit_reason}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
