"use client";

import { useEffect, useState } from "react";
import { api, type SignalData } from "@/lib/api";

const TIMEFRAMES = ["M15", "H1", "H4", "D1"];

export default function SignalsPage() {
  const [signals, setSignals] = useState<SignalData[]>([]);
  const [timeframe, setTimeframe] = useState("H1");
  const [lastPrice, setLastPrice] = useState<string | null>(null);
  const [totalSignals, setTotalSignals] = useState(0);
  const [validSignals, setValidSignals] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await api.signals("PAXG/USDT", timeframe);
        setSignals(data.signals);
        setTotalSignals(data.total_signals);
        setValidSignals(data.valid_signals);
        setLastPrice(data.last_price);
      } catch {
        setSignals([]);
      } finally {
        setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, [timeframe]);

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Sinais de Trading</h2>
          {lastPrice && <p className="text-sm text-[var(--muted)] mt-1">Preco atual: ${parseFloat(lastPrice).toFixed(2)}</p>}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              if (signals.length === 0) return;
              const headers = "Padrao,Direcao,Entry,Stop Loss,Take Profit,Confluencia,R:R,Valido\n";
              const rows = signals.map(s =>
                `${s.pattern},${s.direction},${s.entry_price},${s.stop_loss},${s.take_profit},${(s.confluence.total * 100).toFixed(1)}%,${s.risk_reward.toFixed(1)},${s.is_valid ? "Sim" : "Nao"}`
              ).join("\n");
              const blob = new Blob([headers + rows], { type: "text/csv" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `sinais-${timeframe}-${new Date().toISOString().split("T")[0]}.csv`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            disabled={signals.length === 0}
            className="px-3 py-1.5 text-xs font-medium bg-[var(--card)] border border-[var(--card-border)] rounded-lg text-[var(--muted)] hover:text-[var(--foreground)] disabled:opacity-50 transition-colors"
          >
            Exportar CSV
          </button>
          <div className="flex bg-[var(--card)] border border-[var(--card-border)] rounded-lg overflow-hidden">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  timeframe === tf ? "bg-[var(--accent-blue)] text-white" : "text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4">
          <p className="text-xs text-[var(--muted)]">Sinais Detectados</p>
          <p className="text-2xl font-bold">{totalSignals}</p>
        </div>
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4">
          <p className="text-xs text-[var(--muted)]">Sinais Validos</p>
          <p className="text-2xl font-bold text-[var(--accent)]">{validSignals}</p>
        </div>
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4">
          <p className="text-xs text-[var(--muted)]">Taxa de Filtragem</p>
          <p className="text-2xl font-bold">{totalSignals > 0 ? `${((1 - validSignals / totalSignals) * 100).toFixed(0)}%` : "--"}</p>
        </div>
      </div>

      {loading ? (
        <div className="animate-pulse text-[var(--muted)] text-center py-12">Avaliando sinais...</div>
      ) : signals.length === 0 ? (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-8 text-center">
          <p className="text-[var(--muted)]">Nenhum sinal detectado no momento.</p>
          <p className="text-xs text-[var(--muted)] mt-2">O sistema aguarda padroes com confluencia &gt;= 0.65 e ADX &gt; 32</p>
        </div>
      ) : (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--card-border)] text-[var(--muted)] text-xs uppercase">
                <th className="px-4 py-3 text-left">Padrao</th>
                <th className="px-4 py-3 text-left">Direcao</th>
                <th className="px-4 py-3 text-right">Entry</th>
                <th className="px-4 py-3 text-right">Stop Loss</th>
                <th className="px-4 py-3 text-right">Take Profit</th>
                <th className="px-4 py-3 text-right">Confluencia</th>
                <th className="px-4 py-3 text-right">R:R</th>
                <th className="px-4 py-3 text-center">Valido</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => (
                <tr key={s.id} className="border-b border-[var(--card-border)] hover:bg-white/5">
                  <td className="px-4 py-3 font-medium">{s.pattern}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      s.direction === "BULLISH" ? "bg-[var(--accent)]/20 text-[var(--accent)]" :
                      s.direction === "BEARISH" ? "bg-[var(--accent-red)]/20 text-[var(--accent-red)]" :
                      "bg-[var(--muted)]/20 text-[var(--muted)]"
                    }`}>
                      {s.direction}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono">${parseFloat(s.entry_price).toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono text-[var(--accent-red)]">${parseFloat(s.stop_loss).toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono text-[var(--accent)]">${parseFloat(s.take_profit).toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`font-bold ${s.confluence.total >= 0.65 ? "text-[var(--accent)]" : "text-[var(--accent-red)]"}`}>
                      {(s.confluence.total * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono">{s.risk_reward.toFixed(1)}</td>
                  <td className="px-4 py-3 text-center">
                    {s.is_valid ? (
                      <span className="text-[var(--accent)]">&#10003;</span>
                    ) : (
                      <span className="text-[var(--accent-red)]">&#10007;</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
