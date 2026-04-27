"use client";

import { useEffect, useState } from "react";
import CandlestickChart from "@/components/CandlestickChart";
import { api, type CandleData, type SignalData } from "@/lib/api";

const TIMEFRAMES = ["M15", "M30", "H1", "H4", "D1"];
const DAYS_OPTIONS = [7, 14, 30, 60, 90];

export default function ChartsPage() {
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [timeframe, setTimeframe] = useState("H1");
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [lastPrice, setLastPrice] = useState<string | null>(null);
  const [signals, setSignals] = useState<Array<{ time: string; direction: "BULLISH" | "BEARISH"; pattern: string; price: number }>>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await api.candles("PAXG/USDT", timeframe, days);
        setCandles(data.candles);
        if (data.candles.length > 0) {
          setLastPrice(data.candles[data.candles.length - 1].close);
        }
        try {
          const sigData = await api.signals("PAXG/USDT", timeframe);
          const mapped = sigData.signals
            .filter((s: SignalData) => s.is_valid)
            .map((s: SignalData) => ({
              time: data.candles.length > 0 ? data.candles[data.candles.length - 1].timestamp : new Date().toISOString(),
              direction: s.direction as "BULLISH" | "BEARISH",
              pattern: s.pattern,
              price: parseFloat(s.entry_price),
            }));
          setSignals(mapped);
        } catch {
          setSignals([]);
        }
      } catch {
        setCandles([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [timeframe, days]);

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">PAXG/USDT</h2>
          {lastPrice && (
            <p className="text-3xl font-bold text-[var(--accent-yellow)] mt-1">
              ${parseFloat(lastPrice).toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
          )}
        </div>
        <div className="flex gap-3">
          <div className="flex bg-[var(--card)] border border-[var(--card-border)] rounded-lg overflow-hidden">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  timeframe === tf
                    ? "bg-[var(--accent)] text-black"
                    : "text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="bg-[var(--card)] border border-[var(--card-border)] rounded-lg px-3 py-1.5 text-xs text-[var(--foreground)]"
          >
            {DAYS_OPTIONS.map((d) => (
              <option key={d} value={d}>{d} dias</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="h-[500px] bg-[var(--card)] border border-[var(--card-border)] rounded-xl flex items-center justify-center">
          <div className="animate-pulse text-[var(--muted)]">Carregando grafico...</div>
        </div>
      ) : candles.length > 0 ? (
        <CandlestickChart candles={candles} height={500} signals={signals} />
      ) : (
        <div className="h-[500px] bg-[var(--card)] border border-[var(--card-border)] rounded-xl flex items-center justify-center">
          <p className="text-[var(--muted)]">Sem dados. Verifique se a API esta online.</p>
        </div>
      )}

      <div className="grid grid-cols-4 gap-4 text-sm">
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4">
          <p className="text-[var(--muted)] text-xs">Candles</p>
          <p className="text-lg font-bold">{candles.length}</p>
        </div>
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4">
          <p className="text-[var(--muted)] text-xs">High</p>
          <p className="text-lg font-bold text-[var(--accent)]">
            ${candles.length > 0 ? Math.max(...candles.map(c => parseFloat(c.high))).toFixed(2) : "--"}
          </p>
        </div>
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4">
          <p className="text-[var(--muted)] text-xs">Low</p>
          <p className="text-lg font-bold text-[var(--accent-red)]">
            ${candles.length > 0 ? Math.min(...candles.map(c => parseFloat(c.low))).toFixed(2) : "--"}
          </p>
        </div>
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-4">
          <p className="text-[var(--muted)] text-xs">Volume Total</p>
          <p className="text-lg font-bold">
            {candles.length > 0 ? candles.reduce((acc, c) => acc + parseFloat(c.volume), 0).toFixed(0) : "--"}
          </p>
        </div>
      </div>
    </div>
  );
}
