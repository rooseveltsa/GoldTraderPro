"use client";

import { useEffect, useState } from "react";
import Card from "@/components/Card";
import { api, type CandleData, type PaperStatus } from "@/lib/api";

export default function DashboardPage() {
  const [price, setPrice] = useState<CandleData | null>(null);
  const [paperStatus, setPaperStatus] = useState<PaperStatus | null>(null);
  const [apiOnline, setApiOnline] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        await api.health();
        setApiOnline(true);
        const p = await api.latest("PAXG/USDT");
        setPrice(p);
        try {
          const ps = await api.paperStatus();
          if (ps.status !== "not_initialized") setPaperStatus(ps);
        } catch { /* paper trading nao iniciado */ }
      } catch {
        setApiOnline(false);
      } finally {
        setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse text-[var(--muted)]">Carregando...</div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <div className="flex items-center gap-2 text-sm">
          <div className={`w-2 h-2 rounded-full ${apiOnline ? "bg-[var(--accent)]" : "bg-[var(--accent-red)]"}`} />
          <span className="text-[var(--muted)]">{apiOnline ? "API Online" : "API Offline"}</span>
        </div>
      </div>

      {!apiOnline && (
        <div className="bg-[var(--accent-red)]/10 border border-[var(--accent-red)]/30 rounded-xl p-4 text-sm">
          <p className="font-medium text-[var(--accent-red)]">API nao conectada</p>
          <p className="text-[var(--muted)] mt-1">
            Inicie o backend: <code className="bg-white/5 px-2 py-0.5 rounded">uvicorn packages.api.main:app --port 8000</code>
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card
          title="PAXG/USDT (Ouro)"
          value={price ? `$${parseFloat(price.close).toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "--"}
          subtitle={price ? `H: $${parseFloat(price.high).toFixed(2)} / L: $${parseFloat(price.low).toFixed(2)}` : ""}
          trend={price && parseFloat(price.close) >= parseFloat(price.open) ? "up" : "down"}
        />
        <Card
          title="Status"
          value={apiOnline ? "Operacional" : "Offline"}
          subtitle={paperStatus?.status === "running" ? "Paper Trading ativo" : "Modo observacao"}
          trend={apiOnline ? "up" : "neutral"}
        />
        <Card
          title="Equity"
          value={paperStatus ? `$${paperStatus.equity.toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "$10,000.00"}
          subtitle={paperStatus ? `PF: ${paperStatus.profit_factor}` : "Capital inicial"}
          trend={paperStatus && paperStatus.equity > 10000 ? "up" : "neutral"}
        />
        <Card
          title="Win Rate"
          value={paperStatus ? `${(paperStatus.win_rate * 100).toFixed(1)}%` : "--"}
          subtitle={paperStatus ? `${paperStatus.closed_trades} trades fechados` : "Sem trades"}
          trend={paperStatus && paperStatus.win_rate > 0.5 ? "up" : "neutral"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6">
          <h3 className="text-sm font-medium text-[var(--muted)] mb-4">Acesso Rapido</h3>
          <div className="space-y-3">
            <a href="/charts" className="flex items-center gap-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-[var(--accent-blue)]/20 flex items-center justify-center text-[var(--accent-blue)]">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
              </div>
              <div>
                <p className="text-sm font-medium">Charts ao Vivo</p>
                <p className="text-xs text-[var(--muted)]">Graficos de candlestick com dados reais</p>
              </div>
            </a>
            <a href="/backtest" className="flex items-center gap-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-[var(--accent-yellow)]/20 flex items-center justify-center text-[var(--accent-yellow)]">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
              </div>
              <div>
                <p className="text-sm font-medium">Backtest Lab</p>
                <p className="text-xs text-[var(--muted)]">Testar estrategia com dados historicos</p>
              </div>
            </a>
            <a href="/paper-trading" className="flex items-center gap-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-[var(--accent)]/20 flex items-center justify-center text-[var(--accent)]">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              </div>
              <div>
                <p className="text-sm font-medium">Paper Trading</p>
                <p className="text-xs text-[var(--muted)]">Operar ao vivo sem risco</p>
              </div>
            </a>
          </div>
        </div>

        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6">
          <h3 className="text-sm font-medium text-[var(--muted)] mb-4">Regras do Sistema</h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between"><span className="text-[var(--muted)]">ADX Gate</span><span>&gt; 32 (tendencia)</span></div>
            <div className="flex justify-between"><span className="text-[var(--muted)]">Confluencia minima</span><span>0.65 (65%)</span></div>
            <div className="flex justify-between"><span className="text-[var(--muted)]">Risco/Retorno min</span><span>1:1.5</span></div>
            <div className="flex justify-between"><span className="text-[var(--muted)]">Risco por trade</span><span>1% do capital</span></div>
            <div className="flex justify-between"><span className="text-[var(--muted)]">Max trades simultaneos</span><span>3</span></div>
            <div className="flex justify-between"><span className="text-[var(--muted)]">Drawdown diario max</span><span>3%</span></div>
            <div className="flex justify-between"><span className="text-[var(--muted)]">Anti-repainting</span><span className="text-[var(--accent)]">Ativo</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
