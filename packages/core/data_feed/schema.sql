-- GoldTrader Pro — Schema TimescaleDB
-- Otimizado para séries temporais de dados OHLCV

-- Extensão TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================
-- Tabela principal de candles
-- ============================================
CREATE TABLE IF NOT EXISTS candles (
    timestamp    TIMESTAMPTZ    NOT NULL,
    symbol       VARCHAR(20)    NOT NULL DEFAULT 'XAU/USD',
    timeframe    VARCHAR(5)     NOT NULL,
    open         NUMERIC(12,5)  NOT NULL,
    high         NUMERIC(12,5)  NOT NULL,
    low          NUMERIC(12,5)  NOT NULL,
    close        NUMERIC(12,5)  NOT NULL,
    volume       NUMERIC(18,2)  NOT NULL DEFAULT 0,
    tick_volume  INTEGER        NOT NULL DEFAULT 0,
    spread       INTEGER        NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_candles PRIMARY KEY (timestamp, symbol, timeframe),
    CONSTRAINT chk_high_low CHECK (high >= low),
    CONSTRAINT chk_high_oc CHECK (high >= open AND high >= close),
    CONSTRAINT chk_low_oc CHECK (low <= open AND low <= close),
    CONSTRAINT chk_volume CHECK (volume >= 0)
);

-- Converter em hypertable (particionamento temporal automático)
SELECT create_hypertable(
    'candles',
    'timestamp',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Índices otimizados
CREATE INDEX IF NOT EXISTS idx_candles_symbol_tf
    ON candles (symbol, timeframe, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_candles_tf_time
    ON candles (timeframe, timestamp DESC);

-- ============================================
-- Tabela de sinais gerados
-- ============================================
CREATE TABLE IF NOT EXISTS signals (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    symbol          VARCHAR(20)    NOT NULL DEFAULT 'XAU/USD',
    timeframe       VARCHAR(5)     NOT NULL,
    pattern_type    VARCHAR(40)    NOT NULL,
    direction       VARCHAR(10)    NOT NULL,
    strength        NUMERIC(5,4)   NOT NULL,
    entry_price     NUMERIC(12,5)  NOT NULL,
    stop_loss       NUMERIC(12,5)  NOT NULL,
    take_profit     NUMERIC(12,5)  NOT NULL,
    volume_verdict  VARCHAR(15)    NOT NULL,
    context         VARCHAR(20)    NOT NULL,
    confluence_score NUMERIC(5,4)  NOT NULL,
    multi_tf_aligned BOOLEAN       NOT NULL DEFAULT FALSE,
    is_valid        BOOLEAN        NOT NULL DEFAULT FALSE,
    candle_timestamp TIMESTAMPTZ   NOT NULL,
    created_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_time
    ON signals (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_signals_pattern
    ON signals (pattern_type, direction);

-- ============================================
-- Tabela de ordens
-- ============================================
CREATE TABLE IF NOT EXISTS orders (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id       UUID           REFERENCES signals(id),
    symbol          VARCHAR(20)    NOT NULL DEFAULT 'XAU/USD',
    side            VARCHAR(5)     NOT NULL,
    order_type      VARCHAR(15)    NOT NULL,
    quantity        NUMERIC(12,5)  NOT NULL,
    price           NUMERIC(12,5)  NOT NULL,
    stop_loss       NUMERIC(12,5),
    take_profit     NUMERIC(12,5),
    status          VARCHAR(20)    NOT NULL DEFAULT 'PENDING',
    filled_price    NUMERIC(12,5),
    filled_at       TIMESTAMPTZ,
    slippage        NUMERIC(8,5)   DEFAULT 0,
    broker_order_id VARCHAR(100),
    created_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_status
    ON orders (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_signal
    ON orders (signal_id);

-- ============================================
-- Tabela de performance (equity tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS equity_snapshots (
    timestamp       TIMESTAMPTZ    NOT NULL,
    balance         NUMERIC(14,2)  NOT NULL,
    equity          NUMERIC(14,2)  NOT NULL,
    drawdown_pct    NUMERIC(6,4)   NOT NULL DEFAULT 0,
    open_positions  INTEGER        NOT NULL DEFAULT 0,
    daily_pnl       NUMERIC(12,2)  NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_equity PRIMARY KEY (timestamp)
);

SELECT create_hypertable(
    'equity_snapshots',
    'timestamp',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- ============================================
-- Tabela de trades (backtest + paper + live)
-- ============================================
CREATE TABLE IF NOT EXISTS trades (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id       UUID,
    mode            VARCHAR(10)    NOT NULL DEFAULT 'backtest', -- backtest | paper | live
    symbol          VARCHAR(20)    NOT NULL DEFAULT 'XAU/USD',
    direction       VARCHAR(10)    NOT NULL,
    pattern_type    VARCHAR(40)    NOT NULL,
    entry_price     NUMERIC(12,5)  NOT NULL,
    stop_loss       NUMERIC(12,5)  NOT NULL,
    take_profit     NUMERIC(12,5)  NOT NULL,
    exit_price      NUMERIC(12,5),
    position_size   NUMERIC(12,5)  NOT NULL,
    confluence_score NUMERIC(5,4)  NOT NULL DEFAULT 0,
    slippage        NUMERIC(8,5)   DEFAULT 0,
    spread          NUMERIC(8,5)   DEFAULT 0,
    pnl             NUMERIC(14,5),
    r_multiple      NUMERIC(6,2),
    exit_reason     VARCHAR(20),
    entry_time      TIMESTAMPTZ    NOT NULL,
    exit_time       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_mode
    ON trades (mode, entry_time DESC);

CREATE INDEX IF NOT EXISTS idx_trades_direction
    ON trades (direction, pattern_type);

-- ============================================
-- Tabela de resultados de backtest
-- ============================================
CREATE TABLE IF NOT EXISTS backtest_runs (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol          VARCHAR(20)    NOT NULL,
    timeframe       VARCHAR(5)     NOT NULL,
    start_date      TIMESTAMPTZ    NOT NULL,
    end_date        TIMESTAMPTZ    NOT NULL,
    initial_capital NUMERIC(14,2)  NOT NULL,
    final_capital   NUMERIC(14,2)  NOT NULL,
    total_trades    INTEGER        NOT NULL DEFAULT 0,
    winning_trades  INTEGER        NOT NULL DEFAULT 0,
    losing_trades   INTEGER        NOT NULL DEFAULT 0,
    win_rate        NUMERIC(5,4)   DEFAULT 0,
    profit_factor   NUMERIC(8,2)   DEFAULT 0,
    sharpe_ratio    NUMERIC(6,2)   DEFAULT 0,
    max_drawdown    NUMERIC(14,2)  DEFAULT 0,
    max_drawdown_pct NUMERIC(6,4)  DEFAULT 0,
    config_json     JSONB,
    created_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- ============================================
-- Views úteis
-- ============================================

-- Último candle por símbolo/timeframe
CREATE OR REPLACE VIEW v_latest_candles AS
SELECT DISTINCT ON (symbol, timeframe)
    symbol, timeframe, timestamp, open, high, low, close, volume
FROM candles
ORDER BY symbol, timeframe, timestamp DESC;

-- Sinais válidos recentes
CREATE OR REPLACE VIEW v_valid_signals AS
SELECT *
FROM signals
WHERE is_valid = TRUE
ORDER BY timestamp DESC
LIMIT 100;

-- Performance diária
CREATE OR REPLACE VIEW v_daily_performance AS
SELECT
    DATE(timestamp) AS trade_date,
    COUNT(*) FILTER (WHERE status = 'FILLED') AS total_trades,
    SUM(CASE
        WHEN side = 'BUY' AND filled_price > price THEN (filled_price - price) * quantity
        WHEN side = 'SELL' AND filled_price < price THEN (price - filled_price) * quantity
        ELSE 0
    END) AS gross_profit,
    SUM(CASE
        WHEN side = 'BUY' AND filled_price < price THEN (price - filled_price) * quantity
        WHEN side = 'SELL' AND filled_price > price THEN (filled_price - price) * quantity
        ELSE 0
    END) AS gross_loss
FROM orders
WHERE status = 'FILLED'
GROUP BY DATE(timestamp)
ORDER BY trade_date DESC;
