"use client";

import { useEffect, useState } from "react";
import { api, type SystemConfig } from "@/lib/api";

export default function SettingsPage() {
  const [config, setConfig] = useState<SystemConfig>({
    adx_threshold: 32,
    min_confluence: 0.65,
    risk_per_trade: 0.01,
    min_risk_reward: 1.5,
    max_concurrent_trades: 3,
    max_daily_drawdown: 0.03,
    slippage_pips: 0.5,
    spread_pips: 2.0,
    default_timeframe: "H1",
    default_symbol: "PAXG/USDT",
    default_exchange: "binance",
  });
  const [telegram, setTelegram] = useState({ bot_token: "", chat_id: "", enabled: false });
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [telegramStatus, setTelegramStatus] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [c, t] = await Promise.all([api.getConfig(), api.getTelegramConfig()]);
        setConfig(c as SystemConfig);
        setTelegram({ bot_token: "", chat_id: t.chat_id || "", enabled: t.enabled });
      } catch { /* API offline */ }
      setLoading(false);
    }
    load();
  }, []);

  async function saveConfig() {
    setSaveStatus(null);
    try {
      await api.updateConfig(config);
      setSaveStatus("ok");
      setTimeout(() => setSaveStatus(null), 3000);
    } catch {
      setSaveStatus("error");
    }
  }

  async function saveTelegram() {
    setTelegramStatus(null);
    try {
      await api.updateTelegramConfig(telegram);
      setTelegramStatus("ok");
      setTimeout(() => setTelegramStatus(null), 3000);
    } catch {
      setTelegramStatus("error");
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-full animate-pulse text-[var(--muted)]">Carregando...</div>;
  }

  const inputClass = "w-full bg-[var(--background)] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm text-[var(--foreground)]";
  const labelClass = "block text-xs text-[var(--muted)] mb-1";

  return (
    <div className="p-8 space-y-6 max-w-3xl">
      <h2 className="text-2xl font-bold">Configuracao</h2>

      {/* Trading Parameters */}
      <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6">
        <h3 className="text-sm font-medium text-[var(--muted)] mb-4">Parametros de Trading</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className={labelClass}>ADX Threshold</label>
            <input type="number" value={config.adx_threshold} step={1} min={10} max={50}
              onChange={(e) => setConfig({ ...config, adx_threshold: Number(e.target.value) })}
              className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Confluencia Minima</label>
            <input type="number" value={config.min_confluence} step={0.05} min={0} max={1}
              onChange={(e) => setConfig({ ...config, min_confluence: Number(e.target.value) })}
              className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Risco por Trade (%)</label>
            <input type="number" value={config.risk_per_trade} step={0.005} min={0.001} max={0.05}
              onChange={(e) => setConfig({ ...config, risk_per_trade: Number(e.target.value) })}
              className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Risco/Retorno Minimo</label>
            <input type="number" value={config.min_risk_reward} step={0.1} min={1} max={5}
              onChange={(e) => setConfig({ ...config, min_risk_reward: Number(e.target.value) })}
              className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Max Trades Simultaneos</label>
            <input type="number" value={config.max_concurrent_trades} step={1} min={1} max={10}
              onChange={(e) => setConfig({ ...config, max_concurrent_trades: Number(e.target.value) })}
              className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Max Drawdown Diario (%)</label>
            <input type="number" value={config.max_daily_drawdown} step={0.01} min={0.01} max={0.10}
              onChange={(e) => setConfig({ ...config, max_daily_drawdown: Number(e.target.value) })}
              className={inputClass} />
          </div>
        </div>
      </div>

      {/* Execution Parameters */}
      <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6">
        <h3 className="text-sm font-medium text-[var(--muted)] mb-4">Parametros de Execucao</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className={labelClass}>Slippage (pips)</label>
            <input type="number" value={config.slippage_pips} step={0.1} min={0}
              onChange={(e) => setConfig({ ...config, slippage_pips: Number(e.target.value) })}
              className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Spread (pips)</label>
            <input type="number" value={config.spread_pips} step={0.1} min={0}
              onChange={(e) => setConfig({ ...config, spread_pips: Number(e.target.value) })}
              className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Timeframe Padrao</label>
            <select value={config.default_timeframe}
              onChange={(e) => setConfig({ ...config, default_timeframe: e.target.value })}
              className={inputClass}>
              <option value="M15">M15</option>
              <option value="M30">M30</option>
              <option value="H1">H1</option>
              <option value="H4">H4</option>
              <option value="D1">D1</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Simbolo</label>
            <input type="text" value={config.default_symbol}
              onChange={(e) => setConfig({ ...config, default_symbol: e.target.value })}
              className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Exchange</label>
            <select value={config.default_exchange}
              onChange={(e) => setConfig({ ...config, default_exchange: e.target.value })}
              className={inputClass}>
              <option value="binance">Binance</option>
              <option value="bybit">Bybit</option>
              <option value="kraken">Kraken</option>
            </select>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={saveConfig}
            className="bg-[var(--accent)] text-black font-medium rounded-lg px-6 py-2 text-sm hover:opacity-90 transition-opacity">
            Salvar Configuracao
          </button>
          {saveStatus === "ok" && <span className="text-sm text-[var(--accent)]">Salvo com sucesso</span>}
          {saveStatus === "error" && <span className="text-sm text-[var(--accent-red)]">Erro ao salvar</span>}
        </div>
      </div>

      {/* Telegram Alerts */}
      <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6">
        <h3 className="text-sm font-medium text-[var(--muted)] mb-4">Alertas Telegram</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Bot Token</label>
            <input type="password" value={telegram.bot_token} placeholder="Cole o token do BotFather"
              onChange={(e) => setTelegram({ ...telegram, bot_token: e.target.value })}
              className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Chat ID</label>
            <input type="text" value={telegram.chat_id} placeholder="ID do chat ou grupo"
              onChange={(e) => setTelegram({ ...telegram, chat_id: e.target.value })}
              className={inputClass} />
          </div>
        </div>
        <div className="mt-4 flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={telegram.enabled}
              onChange={(e) => setTelegram({ ...telegram, enabled: e.target.checked })}
              className="w-4 h-4 rounded accent-[var(--accent)]" />
            <span className="text-sm">Ativar alertas</span>
          </label>
          <button onClick={saveTelegram}
            className="bg-[var(--accent-blue)] text-white font-medium rounded-lg px-6 py-2 text-sm hover:opacity-90 transition-opacity">
            Salvar Telegram
          </button>
          {telegramStatus === "ok" && <span className="text-sm text-[var(--accent)]">Salvo</span>}
          {telegramStatus === "error" && <span className="text-sm text-[var(--accent-red)]">Erro</span>}
        </div>
      </div>
    </div>
  );
}
