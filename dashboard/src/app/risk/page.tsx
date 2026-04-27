"use client";

import { useEffect, useState } from "react";
import Card from "@/components/Card";
import EquityCurveChart from "@/components/EquityCurveChart";
import { api, type RiskSummary } from "@/lib/api";

export default function RiskPage() {
  const [risk, setRisk] = useState<RiskSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.riskSummary();
        setRisk(data);
      } catch {
        setRisk(null);
      } finally {
        setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse text-[var(--muted)]">Carregando...</div>
      </div>
    );
  }

  if (!risk) {
    return (
      <div className="p-8">
        <h2 className="text-2xl font-bold mb-4">Risk Monitor</h2>
        <div className="bg-[var(--accent-red)]/10 border border-[var(--accent-red)]/30 rounded-xl p-4 text-sm">
          <p className="font-medium text-[var(--accent-red)]">API nao conectada</p>
          <p className="text-[var(--muted)] mt-1">
            Inicie o backend: <code className="bg-white/5 px-2 py-0.5 rounded">uvicorn packages.api.main:app --port 8000</code>
          </p>
        </div>
      </div>
    );
  }

  const pnlColor = (v: number) => v > 0 ? "text-[var(--accent)]" : v < 0 ? "text-[var(--accent-red)]" : "text-[var(--muted)]";
  const pnlSign = (v: number) => v > 0 ? "+" : "";

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Risk Monitor</h2>
        <div className="flex items-center gap-2 text-sm">
          <div className={`w-2 h-2 rounded-full ${risk.status === "active" ? "bg-[var(--accent)] animate-pulse" : "bg-[var(--muted)]"}`} />
          <span className="text-[var(--muted)]">{risk.status === "active" ? "Monitorando" : risk.status === "stopped" ? "Parado" : "Inativo"}</span>
        </div>
      </div>

      {/* Main Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card
          title="Equity"
          value={`$${risk.equity.toLocaleString("en-US", { minimumFractionDigits: 2 })}`}
          trend={risk.equity >= risk.initial_capital ? "up" : "down"}
        />
        <Card
          title="Capital em Risco"
          value={`$${risk.capital_at_risk.toFixed(2)}`}
          subtitle={`${risk.capital_at_risk_pct.toFixed(1)}% do equity`}
          trend={risk.capital_at_risk_pct < 3 ? "up" : "down"}
        />
        <Card
          title="Drawdown Atual"
          value={`${risk.current_drawdown_pct.toFixed(2)}%`}
          subtitle={`Max: ${risk.max_drawdown_pct.toFixed(2)}%`}
          trend={risk.current_drawdown_pct < 2 ? "up" : "down"}
        />
        <Card
          title="Win Rate"
          value={`${risk.metrics.win_rate?.toFixed(1) ?? 0}%`}
          subtitle={`${risk.metrics.total_trades ?? 0} trades`}
          trend={(risk.metrics.win_rate ?? 0) > 50 ? "up" : "neutral"}
        />
      </div>

      {/* Risk Alerts */}
      {risk.risk_alerts.length > 0 && (
        <div className="space-y-2">
          {risk.risk_alerts.map((alert, i) => {
            const colors = {
              HIGH: "bg-[var(--accent-red)]/10 border-[var(--accent-red)]/30 text-[var(--accent-red)]",
              WARNING: "bg-[var(--accent-yellow)]/10 border-[var(--accent-yellow)]/30 text-[var(--accent-yellow)]",
              INFO: "bg-[var(--accent-blue)]/10 border-[var(--accent-blue)]/30 text-[var(--accent-blue)]",
            }[alert.level] || "bg-white/5 border-white/10 text-[var(--muted)]";
            return (
              <div key={i} className={`border rounded-xl px-4 py-3 text-sm ${colors}`}>
                <span className="font-medium mr-2">[{alert.level}]</span>
                {alert.message}
              </div>
            );
          })}
        </div>
      )}

      {/* P&L by Period */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5 text-center">
          <p className="text-xs text-[var(--muted)] uppercase tracking-wider mb-1">P&L Diario</p>
          <p className={`text-2xl font-bold ${pnlColor(risk.daily_pnl)}`}>
            {pnlSign(risk.daily_pnl)}${risk.daily_pnl.toFixed(2)}
          </p>
        </div>
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5 text-center">
          <p className="text-xs text-[var(--muted)] uppercase tracking-wider mb-1">P&L Semanal</p>
          <p className={`text-2xl font-bold ${pnlColor(risk.weekly_pnl)}`}>
            {pnlSign(risk.weekly_pnl)}${risk.weekly_pnl.toFixed(2)}
          </p>
        </div>
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5 text-center">
          <p className="text-xs text-[var(--muted)] uppercase tracking-wider mb-1">P&L Mensal</p>
          <p className={`text-2xl font-bold ${pnlColor(risk.monthly_pnl)}`}>
            {pnlSign(risk.monthly_pnl)}${risk.monthly_pnl.toFixed(2)}
          </p>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6">
        <h3 className="text-sm font-medium text-[var(--muted)] mb-4">Metricas de Performance</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-[var(--muted)] text-xs">Profit Factor</p>
            <p className="text-lg font-bold">{risk.metrics.profit_factor?.toFixed(2) ?? "--"}</p>
          </div>
          <div>
            <p className="text-[var(--muted)] text-xs">Sharpe Ratio</p>
            <p className="text-lg font-bold">{risk.metrics.sharpe_ratio?.toFixed(2) ?? "--"}</p>
          </div>
          <div>
            <p className="text-[var(--muted)] text-xs">Expectativa</p>
            <p className="text-lg font-bold">${risk.metrics.expectancy?.toFixed(2) ?? "--"}</p>
          </div>
          <div>
            <p className="text-[var(--muted)] text-xs">R Multiplo Medio</p>
            <p className="text-lg font-bold">{risk.metrics.avg_r_multiple?.toFixed(2) ?? "--"}R</p>
          </div>
          <div>
            <p className="text-[var(--muted)] text-xs">Recovery Factor</p>
            <p className="text-lg font-bold">{risk.metrics.recovery_factor?.toFixed(2) ?? "--"}</p>
          </div>
          <div>
            <p className="text-[var(--muted)] text-xs">Wins Consecutivos Max</p>
            <p className="text-lg font-bold text-[var(--accent)]">{risk.metrics.max_consecutive_wins ?? 0}</p>
          </div>
          <div>
            <p className="text-[var(--muted)] text-xs">Losses Consecutivos Max</p>
            <p className="text-lg font-bold text-[var(--accent-red)]">{risk.metrics.max_consecutive_losses ?? 0}</p>
          </div>
          <div>
            <p className="text-[var(--muted)] text-xs">Total Trades</p>
            <p className="text-lg font-bold">{risk.metrics.total_trades ?? 0}</p>
          </div>
        </div>
      </div>

      {/* Open Positions */}
      {risk.open_positions.length > 0 && (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl overflow-hidden">
          <h3 className="text-sm font-medium text-[var(--muted)] px-4 py-3 border-b border-[var(--card-border)]">
            Posicoes Abertas ({risk.open_positions.length})
          </h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--card-border)] text-[var(--muted)] text-xs uppercase">
                <th className="px-4 py-2 text-left">Direcao</th>
                <th className="px-4 py-2 text-left">Padrao</th>
                <th className="px-4 py-2 text-right">Entry</th>
                <th className="px-4 py-2 text-right">Stop Loss</th>
                <th className="px-4 py-2 text-right">Take Profit</th>
                <th className="px-4 py-2 text-right">Risco ($)</th>
                <th className="px-4 py-2 text-right">Confluencia</th>
              </tr>
            </thead>
            <tbody>
              {risk.open_positions.map((p, i) => (
                <tr key={i} className="border-b border-[var(--card-border)] hover:bg-white/5">
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      p.direction === "BULLISH" ? "bg-[var(--accent)]/20 text-[var(--accent)]" : "bg-[var(--accent-red)]/20 text-[var(--accent-red)]"
                    }`}>{p.direction === "BULLISH" ? "COMPRA" : "VENDA"}</span>
                  </td>
                  <td className="px-4 py-2 text-xs">{p.pattern}</td>
                  <td className="px-4 py-2 text-right font-mono">${parseFloat(p.entry_price).toFixed(2)}</td>
                  <td className="px-4 py-2 text-right font-mono text-[var(--accent-red)]">${parseFloat(p.stop_loss).toFixed(2)}</td>
                  <td className="px-4 py-2 text-right font-mono text-[var(--accent)]">${parseFloat(p.take_profit).toFixed(2)}</td>
                  <td className="px-4 py-2 text-right font-mono">${p.risk_amount.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right">{(p.confluence * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Equity Curve */}
      {risk.equity_curve.length > 1 && (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6">
          <h3 className="text-sm font-medium text-[var(--muted)] mb-4">Equity Curve</h3>
          <EquityCurveChart data={risk.equity_curve} initialCapital={risk.initial_capital} height={200} />
        </div>
      )}
    </div>
  );
}
