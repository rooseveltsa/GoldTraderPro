const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchAPI<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(path, API_BASE);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchAPIPut<T>(path: string, body: unknown): Promise<T> {
  const url = new URL(path, API_BASE);
  const res = await fetch(url.toString(), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface CandleData {
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

export interface SignalData {
  id: string;
  pattern: string;
  direction: string;
  strength: number;
  entry_price: string;
  stop_loss: string;
  take_profit: string;
  confluence: { total: number; is_executable: boolean };
  is_valid: boolean;
  risk_reward: number;
}

export interface BacktestResult {
  summary: {
    total_trades: number;
    win_rate: number;
    profit_factor: number;
    net_profit: string;
    return_pct: number;
    max_drawdown_pct: number;
  };
  trades: TradeData[];
  equity_curve: number[];
  metrics: Record<string, unknown>;
  period: { start: string; end: string; days: number; candles: number };
}

export interface TradeData {
  direction: string;
  pattern: string;
  entry_price: string;
  exit_price: string | null;
  stop_loss: string;
  take_profit: string;
  pnl: string;
  r_multiple: number;
  exit_reason: string;
  confluence: number;
  entry_time: string;
  exit_time: string | null;
}

export interface PaperStatus {
  status: string;
  equity: number;
  open_trades: number;
  closed_trades: number;
  signals_generated: number;
  win_rate: number;
  net_profit: string;
  profit_factor: number;
  max_drawdown_pct: number;
  recent_trades?: TradeData[];
}

export interface RiskSummary {
  status: string;
  equity: number;
  initial_capital: number;
  capital_at_risk: number;
  capital_at_risk_pct: number;
  daily_pnl: number;
  weekly_pnl: number;
  monthly_pnl: number;
  current_drawdown_pct: number;
  max_drawdown_pct: number;
  open_positions: Array<{
    direction: string;
    pattern: string;
    entry_price: string;
    stop_loss: string;
    take_profit: string;
    risk_amount: number;
    confluence: number;
    entry_time: string;
  }>;
  risk_alerts: Array<{ level: string; message: string }>;
  metrics: Record<string, number>;
  equity_curve: number[];
}

export interface SystemConfig {
  adx_threshold: number;
  min_confluence: number;
  risk_per_trade: number;
  min_risk_reward: number;
  max_concurrent_trades: number;
  max_daily_drawdown: number;
  slippage_pips: number;
  spread_pips: number;
  default_timeframe: string;
  default_symbol: string;
  default_exchange: string;
}

export const api = {
  health: () => fetchAPI<{ status: string }>("/health"),

  candles: (symbol: string, timeframe: string, days: number) =>
    fetchAPI<{ candles: CandleData[]; count: number }>("/market/candles", { symbol, timeframe, days }),

  latest: (symbol: string) =>
    fetchAPI<CandleData>("/market/latest", { symbol }),

  symbols: (exchange?: string) =>
    fetchAPI<{ symbols: string[] }>("/market/symbols", exchange ? { exchange } : {}),

  signals: (symbol: string, timeframe: string) =>
    fetchAPI<{ signals: SignalData[]; total_signals: number; valid_signals: number; last_price: string }>("/signals/evaluate", { symbol, timeframe }),

  backtest: (params: { symbol?: string; timeframe?: string; days?: number; capital?: number }) =>
    fetchAPI<BacktestResult>("/backtest/run", params as Record<string, string | number>),

  paperStart: (params: Record<string, string | number>) =>
    fetchAPI<{ status: string }>("/trading/paper/start", params),

  paperStop: () =>
    fetchAPI<PaperStatus>("/trading/paper/stop"),

  paperStatus: () =>
    fetchAPI<PaperStatus>("/trading/paper/status"),

  riskSummary: () =>
    fetchAPI<RiskSummary>("/risk/summary"),

  getConfig: () =>
    fetchAPI<SystemConfig>("/config"),

  updateConfig: (config: SystemConfig) =>
    fetchAPIPut<{ status: string; config: SystemConfig }>("/config", config),

  getTelegramConfig: () =>
    fetchAPI<{ enabled: boolean; chat_id: string; configured: boolean }>("/config/telegram"),

  updateTelegramConfig: (settings: { bot_token: string; chat_id: string; enabled: boolean }) =>
    fetchAPIPut<{ status: string; enabled: boolean }>("/config/telegram", settings),
};
