"use client";

import { useEffect, useState } from "react";
import Card from "@/components/Card";
import { api, type PaperStatus } from "@/lib/api";

export default function PaperTradingPage() {
  const [status, setStatus] = useState<PaperStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [timeframe, setTimeframe] = useState("H1");
  const [capital, setCapital] = useState(10000);

  async function loadStatus() {
    try {
      const s = await api.paperStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  async function handleStart() {
    setActionLoading(true);
    try {
      await api.paperStart({ symbol: "PAXG/USDT", timeframe, capital, poll_interval: 60 });
      await loadStatus();
    } catch { /* erro */ }
    setActionLoading(false);
  }

  async function handleStop() {
    setActionLoading(true);
    try {
      const result = await api.paperStop();
      setStatus(result);
    } catch { /* erro */ }
    setActionLoading(false);
  }

  const isRunning = status?.status === "running";

  if (loading) {
    return <div className="flex items-center justify-center h-full animate-pulse text-[var(--muted)]">Carregando...</div>;
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Paper Trading</h2>
          <p className="text-sm text-[var(--muted)] mt-1">Opere ao vivo sem risco real</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
            isRunning ? "bg-[var(--accent)]/10 text-[var(--accent)]" : "bg-[var(--muted)]/10 text-[var(--muted)]"
          }`}>
            <div className={`w-2 h-2 rounded-full ${isRunning ? "bg-[var(--accent)] animate-pulse" : "bg-[var(--muted)]"}`} />
            {isRunning ? "Rodando" : "Parado"}
          </div>
        </div>
      </div>

      {!isRunning && (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6">
          <h3 className="text-sm font-medium text-[var(--muted)] mb-4">Configurar e Iniciar</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-[var(--muted)] mb-1">Timeframe</label>
              <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}
                className="w-full bg-[var(--background)] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm">
                <option value="M15">M15</option>
                <option value="H1">H1</option>
                <option value="H4">H4</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-[var(--muted)] mb-1">Capital ($)</label>
              <input type="number" value={capital} onChange={(e) => setCapital(Number(e.target.value))}
                className="w-full bg-[var(--background)] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex items-end">
              <button onClick={handleStart} disabled={actionLoading}
                className="w-full bg-[var(--accent)] text-black font-medium rounded-lg px-4 py-2 text-sm hover:opacity-90 disabled:opacity-50">
                {actionLoading ? "Iniciando..." : "Iniciar Paper Trading"}
              </button>
            </div>
          </div>
        </div>
      )}

      {isRunning && (
        <div className="flex justify-end">
          <button onClick={handleStop} disabled={actionLoading}
            className="bg-[var(--accent-red)] text-white font-medium rounded-lg px-4 py-2 text-sm hover:opacity-90 disabled:opacity-50">
            {actionLoading ? "Parando..." : "Parar Paper Trading"}
          </button>
        </div>
      )}

      {status && status.status !== "not_initialized" && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card
              title="Equity"
              value={`$${status.equity.toLocaleString("en-US", { minimumFractionDigits: 2 })}`}
              trend={status.equity > capital ? "up" : status.equity < capital ? "down" : "neutral"}
            />
            <Card title="Win Rate" value={`${(status.win_rate * 100).toFixed(1)}%`} trend={status.win_rate > 0.5 ? "up" : "neutral"} />
            <Card title="Profit Factor" value={status.profit_factor.toFixed(2)} trend={status.profit_factor > 1.5 ? "up" : "neutral"} />
            <Card title="Max Drawdown" value={`${(status.max_drawdown_pct * 100).toFixed(2)}%`} trend={status.max_drawdown_pct < 0.05 ? "up" : "down"} />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4 text-center">
              <p className="text-xs text-[var(--muted)]">Trades Abertos</p>
              <p className="text-3xl font-bold text-[var(--accent-blue)]">{status.open_trades}</p>
            </div>
            <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4 text-center">
              <p className="text-xs text-[var(--muted)]">Trades Fechados</p>
              <p className="text-3xl font-bold">{status.closed_trades}</p>
            </div>
            <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4 text-center">
              <p className="text-xs text-[var(--muted)]">Sinais Gerados</p>
              <p className="text-3xl font-bold">{status.signals_generated}</p>
            </div>
          </div>

          {status.recent_trades && status.recent_trades.length > 0 && (
            <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl overflow-hidden">
              <h3 className="text-sm font-medium text-[var(--muted)] px-4 py-3 border-b border-[var(--card-border)]">
                Trades Recentes
              </h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--card-border)] text-[var(--muted)] text-xs uppercase">
                    <th className="px-4 py-2 text-left">Direcao</th>
                    <th className="px-4 py-2 text-left">Padrao</th>
                    <th className="px-4 py-2 text-right">Entry</th>
                    <th className="px-4 py-2 text-right">Exit</th>
                    <th className="px-4 py-2 text-right">PnL</th>
                    <th className="px-4 py-2 text-left">Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {status.recent_trades.map((t, i) => {
                    const pnl = parseFloat(t.pnl);
                    return (
                      <tr key={i} className="border-b border-[var(--card-border)]">
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
                        <td className="px-4 py-2 text-xs text-[var(--muted)]">{t.exit_reason}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
