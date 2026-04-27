# PRD-001: GoldTrader Pro — Sistema Algorítmico de Trading para o Mercado de Ouro

**Versão:** 1.0
**Data:** 2026-04-23
**Autor:** Junior Miranda
**Status:** Draft

---

## 1. Visão Geral

### 1.1 Problema

Traders discricionários no mercado de ouro (XAU/USD) enfrentam:
- **Viés cognitivo** que compromete decisões em tempo real
- **Incapacidade de processar múltiplos timeframes** simultaneamente
- **Hesitação na execução** de stop loss em movimentos voláteis
- **Impossibilidade de monitoramento 24h** em um mercado global
- **Falta de backtesting rigoroso** para validar estratégias

### 1.2 Solução

**GoldTrader Pro** — um sistema algorítmico completo que automatiza:
1. Detecção de padrões de candlestick com parametrização rigorosa
2. Validação multi-timeframe (intraday + diário + semanal)
3. Filtragem por indicadores quantitativos (ADX, RSI, Didi Index, Médias Móveis)
4. Confirmação por volume institucional
5. Execução automática com gestão de risco OCO
6. Backtesting com proteção anti-repainting

### 1.3 Público-Alvo

- Traders independentes que operam ouro (XAU/USD)
- Analistas técnicos que buscam automatizar estratégias
- Mesas proprietárias que necessitam de sistemas quantitativos

---

## 2. Arquitetura do Sistema

### 2.1 Visão Macro

```
┌─────────────────────────────────────────────────────────────────┐
│                      GoldTrader Pro                             │
├─────────────┬──────────────┬──────────────┬────────────────────┤
│  Data Feed  │   Engine     │  Execution   │   Dashboard        │
│  (Ingest)   │  (Analysis)  │  (Orders)    │   (Monitoring)     │
├─────────────┼──────────────┼──────────────┼────────────────────┤
│ • WebSocket │ • Candle     │ • Broker API │ • Real-time charts │
│ • REST API  │   Patterns   │ • OCO Orders │ • Signal log       │
│ • Historical│ • Indicators │ • Position   │ • P&L tracker      │
│   CSV/DB    │ • Multi-TF   │   Manager    │ • Risk dashboard   │
│             │ • Volume     │ • Paper      │ • Backtest results │
│             │   Filter     │   Trading    │                    │
└─────────────┴──────────────┴──────────────┴────────────────────┘
         │              │              │               │
         └──────────────┴──────────────┴───────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   Storage Layer   │
                    │ • TimescaleDB     │
                    │ • Redis (cache)   │
                    │ • File logs       │
                    └───────────────────┘
```

### 2.2 Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| **Backend / Engine** | Python 3.12+ | Ecossistema robusto para análise quantitativa (pandas, numpy, ta-lib) |
| **Framework de Trading** | Custom + CCXT | Conexão universal com exchanges/brokers |
| **Banco de Dados** | TimescaleDB (PostgreSQL) | Otimizado para séries temporais de preços |
| **Cache** | Redis | Armazenamento de estado e sinais em tempo real |
| **Frontend / Dashboard** | Next.js 15 + React | Dashboard interativo com charts em tempo real |
| **Charts** | Lightweight Charts (TradingView) | Renderização profissional de candlesticks |
| **WebSocket** | FastAPI + WebSocket | Streaming de dados em tempo real |
| **Message Queue** | Redis Streams | Comunicação entre módulos desacoplados |
| **Containerização** | Docker + Docker Compose | Deploy consistente e isolado |
| **CI/CD** | GitHub Actions | Testes e deploy automatizados |

---

## 3. Módulos do Sistema

### 3.1 Módulo 1 — Data Feed (Ingestão de Dados)

**Responsabilidade:** Capturar, normalizar e armazenar dados de mercado.

**Funcionalidades:**
- Conexão WebSocket para dados em tempo real (tick-by-tick)
- Ingestão de dados históricos via REST API
- Agregação de candles em múltiplos timeframes (1m, 5m, 15m, 1h, 4h, D, W)
- Normalização do formato OHLCV (Open, High, Low, Close, Volume)
- Detecção de gaps e dados corrompidos
- Buffer circular para os últimos N candles em memória (Redis)

**Fontes de Dados Suportadas:**
- MetaTrader 5 (MT5) via API
- Brokers via CCXT (Binance, OANDA, etc.)
- CSV/Parquet para dados históricos

**Modelo de Dados (Candle):**
```python
@dataclass
class Candle:
    timestamp: datetime
    timeframe: Timeframe  # M1, M5, M15, H1, H4, D1, W1
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    tick_volume: int
    spread: int
```

---

### 3.2 Módulo 2 — Pattern Engine (Detecção de Padrões)

**Responsabilidade:** Identificar padrões de candlestick com parametrização matemática rigorosa.

#### 3.2.1 Padrões Implementados

**Single Candle Patterns:**

| Padrão | Condições Matemáticas |
|--------|----------------------|
| **Martelo (Hammer)** | `corpo <= 30% amplitude` AND `pavio_inferior >= 2x corpo` AND `pavio_superior <= 10% amplitude` |
| **Martelo Invertido** | `corpo <= 30% amplitude` AND `pavio_superior >= 2x corpo` AND `pavio_inferior <= 10% amplitude` |
| **Estrela Cadente (Shooting Star)** | `corpo <= 30% amplitude` AND `pavio_superior >= 2x corpo` AND `close próximo da low` |
| **Enforcado (Hanging Man)** | Mesma forma do Martelo, mas em contexto de topo |
| **Doji** | `corpo <= 5% amplitude` (abertura ≈ fechamento) |
| **Dragonfly Doji** | Doji + `pavio_inferior >= 3x corpo` + `pavio_superior <= 5% amplitude` |
| **Gravestone Doji** | Doji + `pavio_superior >= 3x corpo` + `pavio_inferior <= 5% amplitude` |

**Multi-Candle Patterns:**

| Padrão | Condições |
|--------|-----------|
| **Engolfo de Alta** | Candle[0] bearish + Candle[1] bullish + `body[1] > body[0]` + `open[1] < close[0]` + `close[1] > open[0]` |
| **Engolfo de Baixa** | Candle[0] bullish + Candle[1] bearish + `body[1] > body[0]` + `open[1] > close[0]` + `close[1] < open[0]` |
| **Estrela da Manhã** | 3 candles: bearish longo + doji/corpo pequeno com gap + bullish longo |
| **Estrela da Noite** | 3 candles: bullish longo + doji/corpo pequeno com gap + bearish longo |

**Chart Patterns (Complexos):**

| Padrão | Detecção |
|--------|----------|
| **OCO (Ombro-Cabeça-Ombro)** | 3 topos onde o central é o mais alto + neckline como suporte |
| **OCOI (OCO Invertido)** | 3 fundos onde o central é o mais baixo + neckline como resistência |
| **Triângulo Ascendente** | Resistência horizontal + LTAs convergentes |
| **Triângulo Descendente** | Suporte horizontal + LTBs convergentes |
| **Cunha** | Duas linhas de tendência convergentes na mesma direção |

#### 3.2.2 Métricas de Cada Sinal

```python
@dataclass
class PatternSignal:
    pattern_name: str           # ex: "hammer"
    direction: Direction        # BULLISH | BEARISH | NEUTRAL
    strength: float             # 0.0 a 1.0 (força do padrão)
    timeframe: Timeframe
    candle_index: int           # índice do candle de referência
    timestamp: datetime
    confirmation_required: bool # aguarda próximo candle?
    volume_confirmed: bool      # volume acima da média?
    context: MarketContext      # SUPPORT | RESISTANCE | TREND
```

---

### 3.3 Módulo 3 — Indicator Engine (Indicadores Técnicos)

**Responsabilidade:** Calcular indicadores e fornecer filtros de tendência/momentum.

#### 3.3.1 Indicadores Implementados

**Médias Móveis:**
- **MMA (Simples):** Períodos 20, 50, 100, 200
- **MME (Exponencial):** Períodos 9, 21, 50
- **Cruzamentos:** Golden Cross (50 > 200), Death Cross (50 < 200)
- **MMA 200 como suporte macro:** Proximidade do preço à MMA200 gera alerta

**ADX (Average Directional Index):**
- Período padrão: 14
- **Regra do sistema:** Tendência válida SOMENTE se `ADX > 32`
- **Filtro adicional:** Linha ADX deve estar ACIMA de DI+ e DI-
- **Se ADX < 32:** Sistema em modo `WAIT` (sem operações)

**Didi Index (Agulhada do Didi):**
- Médias: 3, 8, 20 períodos
- **Agulhada de compra:** Média de 3 cruza acima da de 20, com média de 8 horizontal
- **Agulhada de venda:** Média de 3 cruza abaixo da de 20, com média de 8 horizontal
- **Validação obrigatória:** ADX deve confirmar tendência

**RSI (Índice de Força Relativa):**
- Período padrão: 14
- **Sobrecompra:** RSI > 70 (potencial reversão de baixa)
- **Sobrevenda:** RSI < 30 (potencial reversão de alta)
- **Divergências:** RSI divergindo do preço = sinal forte de reversão

#### 3.3.2 Confluence Score (Pontuação de Confluência)

Cada sinal recebe uma pontuação baseada na confluência de indicadores:

```
confluence_score = (
    pattern_weight      * 0.30 +  # Padrão de candle detectado
    volume_weight       * 0.20 +  # Volume acima da média
    adx_weight          * 0.15 +  # ADX confirma tendência
    ma_alignment_weight * 0.15 +  # Médias alinhadas
    rsi_weight          * 0.10 +  # RSI em zona favorável
    didi_weight         * 0.10    # Agulhada confirma
)

# Execução somente se confluence_score >= 0.65
```

---

### 3.4 Módulo 4 — Multi-Timeframe Validator

**Responsabilidade:** Garantir alinhamento entre timeframes antes da execução.

**Regra do "Passo Atrás":**
```
Sinal em M15 → Validar em D1 → Confirmar em W1

SE timeframe_operacional == M15:
    tendência_diária  = calcular_tendência(D1)
    tendência_semanal = calcular_tendência(W1)
    
    SE sinal == COMPRA E tendência_diária == BAIXA:
        REJEITAR sinal (contra-fluxo macro)
    
    SE sinal == COMPRA E tendência_diária == ALTA E tendência_semanal == ALTA:
        CONFIRMAR sinal (alinhamento total)
        bonus_confluence += 0.10
```

**Matriz de Validação:**

| Sinal (M15) | Tendência D1 | Tendência W1 | Decisão |
|-------------|-------------|-------------|---------|
| COMPRA | ALTA | ALTA | EXECUTAR (+bonus) |
| COMPRA | ALTA | LATERAL | EXECUTAR |
| COMPRA | ALTA | BAIXA | REJEITAR |
| COMPRA | LATERAL | - | REJEITAR (sem inércia) |
| COMPRA | BAIXA | - | REJEITAR (contra-fluxo) |
| VENDA | BAIXA | BAIXA | EXECUTAR (+bonus) |
| VENDA | BAIXA | LATERAL | EXECUTAR |
| VENDA | BAIXA | ALTA | REJEITAR |

---

### 3.5 Módulo 5 — Volume Analyzer

**Responsabilidade:** Validar sinais com análise de volume institucional.

**Regras:**
- Volume do candle de sinal deve ser `>= 1.5x` a média dos últimos 20 candles
- Padrão gráfico SEM volume correspondente = **RUÍDO** (filtrado)
- Picos de volume em zonas de S/R indicam atividade institucional
- Volume climático (>3x média) em reversão = confirmação forte

```python
def validate_volume(candle: Candle, lookback: int = 20) -> VolumeVerdict:
    avg_volume = mean(volumes[-lookback:])
    ratio = candle.volume / avg_volume
    
    if ratio >= 3.0:
        return VolumeVerdict.CLIMACTIC    # Confirmação muito forte
    elif ratio >= 1.5:
        return VolumeVerdict.CONFIRMED    # Confirmação padrão
    elif ratio >= 1.0:
        return VolumeVerdict.NEUTRAL      # Sem confirmação
    else:
        return VolumeVerdict.WEAK         # Volume fraco = ruído
```

---

### 3.6 Módulo 6 — Execution Engine (Motor de Execução)

**Responsabilidade:** Executar ordens com gestão de risco rigorosa.

#### 3.6.1 Fluxo de Execução

```
Signal Detected
    │
    ├─ Pattern Engine ✓
    ├─ Indicator Filter ✓
    ├─ Multi-TF Validation ✓
    ├─ Volume Confirmation ✓
    ├─ Confluence Score >= 0.65 ✓
    ├─ Candle CLOSED (anti-repainting) ✓
    │
    ▼
Execute Order
    │
    ├─ Calcular posição (risk-based sizing)
    ├─ Emitir ordem a mercado (próximo tick)
    ├─ Configurar OCO (Stop Loss + Take Profit)
    └─ Registrar no log de operações
```

#### 3.6.2 Gestão de Risco

| Parâmetro | Valor Padrão | Configurável |
|-----------|-------------|-------------|
| Risco por operação | 1% do capital | Sim (0.5% - 3%) |
| Risco/Retorno mínimo | 1:1.5 | Sim (1:1 - 1:3) |
| Stop Loss | Mínima/Máxima do candle de sinal | Sim |
| Take Profit | 1.5x distância do Stop | Sim |
| Max operações simultâneas | 3 | Sim |
| Max drawdown diário | 3% | Sim |
| Trailing Stop | Opcional (ativação em 1:1) | Sim |

#### 3.6.3 Position Sizing (Dimensionamento)

```python
def calculate_position_size(
    capital: Decimal,
    risk_percent: float,      # ex: 0.01 (1%)
    entry_price: Decimal,
    stop_loss_price: Decimal
) -> Decimal:
    risk_amount = capital * Decimal(str(risk_percent))
    stop_distance = abs(entry_price - stop_loss_price)
    position_size = risk_amount / stop_distance
    return position_size
```

#### 3.6.4 Ordens OCO (One Cancels the Other)

Toda entrada gera automaticamente:
1. **Stop Loss** — na mínima (compra) ou máxima (venda) do candle de sinal
2. **Take Profit** — a 1.5x a distância do Stop Loss
3. Se um for acionado, o outro é cancelado automaticamente

---

### 3.7 Módulo 7 — Backtesting Engine

**Responsabilidade:** Validar estratégias em dados históricos com proteção anti-repainting.

**Funcionalidades:**
- Replay de mercado candle-a-candle
- Execução somente no **fechamento confirmado** do candle (anti-repainting)
- Simulação de slippage e spread
- Cálculo de métricas de performance
- Geração de equity curve

**Métricas de Performance:**

| Métrica | Descrição |
|---------|-----------|
| Win Rate | % de operações lucrativas |
| Profit Factor | Lucro bruto / Prejuízo bruto |
| Sharpe Ratio | Retorno ajustado ao risco |
| Max Drawdown | Maior queda do equity peak |
| Recovery Factor | Lucro líquido / Max Drawdown |
| Expectancy | Ganho médio esperado por operação |
| Total Trades | Número total de operações |
| Avg Win / Avg Loss | Tamanho médio de ganhos vs perdas |

---

### 3.8 Módulo 8 — Dashboard (Frontend)

**Responsabilidade:** Monitoramento visual em tempo real.

**Telas:**

1. **Live Trading**
   - Gráfico de candlesticks com indicadores overlay
   - Sinais marcados no gráfico (setas, ícones)
   - Painel lateral com posições abertas
   - Feed de sinais em tempo real

2. **Backtest Lab**
   - Seleção de período e parâmetros
   - Equity curve interativa
   - Tabela de operações com filtros
   - Heatmap de performance por hora/dia

3. **Risk Monitor**
   - Exposição atual (capital em risco)
   - Drawdown em tempo real
   - P&L diário/semanal/mensal
   - Alertas de limite de risco

4. **Signal Log**
   - Histórico de todos os sinais gerados
   - Filtros por padrão, timeframe, resultado
   - Exportação CSV/JSON

5. **Configuração**
   - Parâmetros de cada indicador
   - Pesos do confluence score
   - Limites de risco
   - Conexão com broker

---

## 4. Regras de Negócio Críticas

### 4.1 Anti-Repainting
- **NUNCA** executar ordens em candle ainda aberto
- Todos os sinais são calculados no `candle[-1]` (último fechado)
- Ordens emitidas no **próximo tick** após fechamento

### 4.2 Filtro de Periodicidade Dupla
- Sinais intraday (M15) só são válidos se a tendência primária (D1) estiver alinhada
- Tendência semanal (W1) oferece bonus ou veto

### 4.3 Volume como Validador
- Padrão gráfico sem volume = ruído = ignorado
- Volume mínimo: 1.5x média de 20 períodos

### 4.4 ADX como Gate
- Se `ADX < 32`: sistema em modo WAIT
- Nenhuma operação é aberta em mercado congestionado

### 4.5 Confluência Mínima
- Score mínimo de 0.65 para execução
- Quanto maior a confluência, maior a confiança do sinal

---

## 5. Modos de Operação

| Modo | Descrição | Uso |
|------|-----------|-----|
| **Paper Trading** | Simulação em tempo real sem capital | Validação antes de ir live |
| **Live Trading** | Execução real via broker API | Operação em produção |
| **Backtest** | Replay histórico | Desenvolvimento e otimização |
| **Signal Only** | Gera sinais sem executar | Apoio à decisão manual |

---

## 6. Estrutura do Projeto

```
MercadoFinanceiro/
├── docs/
│   ├── prd/                    # Product Requirements
│   ├── architecture/           # Diagramas e decisões
│   └── guides/                 # Guias de uso
├── packages/
│   ├── core/                   # Lógica central (Python)
│   │   ├── data_feed/          # Módulo 1: Ingestão de dados
│   │   ├── patterns/           # Módulo 2: Detecção de padrões
│   │   ├── indicators/         # Módulo 3: Indicadores técnicos
│   │   ├── multi_tf/           # Módulo 4: Validação multi-timeframe
│   │   ├── volume/             # Módulo 5: Análise de volume
│   │   ├── execution/          # Módulo 6: Motor de execução
│   │   ├── backtest/           # Módulo 7: Backtesting
│   │   └── models/             # Modelos de dados compartilhados
│   └── dashboard/              # Frontend (Next.js)
│       ├── app/                # App Router pages
│       ├── components/         # Componentes React
│       │   ├── charts/         # Gráficos TradingView
│       │   ├── signals/        # Feed de sinais
│       │   ├── risk/           # Dashboard de risco
│       │   └── backtest/       # Interface de backtesting
│       └── lib/                # Utilitários e API client
├── tests/
│   ├── unit/                   # Testes unitários
│   ├── integration/            # Testes de integração
│   └── backtest_validation/    # Validação de backtests
├── config/
│   ├── default.yaml            # Configuração padrão
│   └── strategies/             # Configurações de estratégia
├── data/
│   └── historical/             # Dados históricos (gitignored)
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml              # Python dependencies
└── README.md
```

---

## 7. Roadmap de Desenvolvimento

### Fase 1 — Foundation (Épico 1)
- [ ] Setup do projeto (monorepo, Docker, CI)
- [ ] Modelos de dados (Candle, Signal, Order)
- [ ] Data Feed: conexão e normalização OHLCV
- [ ] Storage: TimescaleDB + schema de candles
- [ ] Testes unitários da fundação

### Fase 2 — Analysis Engine (Épico 2)
- [ ] Pattern Engine: todos os padrões single-candle
- [ ] Pattern Engine: padrões multi-candle
- [ ] Indicator Engine: MMA, MME, cruzamentos
- [ ] Indicator Engine: ADX, RSI, Didi Index
- [ ] Volume Analyzer
- [ ] Multi-Timeframe Validator
- [ ] Confluence Score calculator
- [ ] Testes com dados históricos reais

### Fase 3 — Execution & Backtest (Épico 3)
- [ ] Backtesting Engine com anti-repainting
- [ ] Position sizing e gestão de risco
- [ ] Ordens OCO (Stop Loss + Take Profit)
- [ ] Paper Trading mode
- [ ] Métricas de performance
- [ ] Equity curve e relatórios

### Fase 4 — Dashboard (Épico 4)
- [ ] Setup Next.js + TradingView Charts
- [ ] Tela Live Trading com sinais em tempo real
- [ ] Tela Backtest Lab
- [ ] Tela Risk Monitor
- [ ] Signal Log com filtros
- [ ] Configuração via UI

### Fase 5 — Production (Épico 5)
- [ ] Integração com broker real (MT5 / OANDA)
- [ ] Live Trading mode
- [ ] Alertas (Telegram, email)
- [ ] Monitoramento e observabilidade
- [ ] Documentação completa
- [ ] Deploy em produção

---

## 8. Requisitos Não-Funcionais

| Requisito | Especificação |
|-----------|---------------|
| **Latência** | Processamento de sinal < 100ms |
| **Disponibilidade** | 99.5% durante horário de mercado |
| **Dados históricos** | Suporte a 10+ anos de dados |
| **Backtesting** | 1 ano de dados em < 30 segundos |
| **Escalabilidade** | Suporte a múltiplos pares no futuro |
| **Segurança** | API keys criptografadas, sem secrets em código |
| **Observabilidade** | Logs estruturados, métricas exportáveis |

---

## 9. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Dados de mercado indisponíveis | Sistema parado | Fallback para múltiplas fontes |
| Slippage alto em execução | Perda financeira | Simulação de slippage no backtest |
| Overfitting no backtest | Falsa lucratividade | Walk-forward analysis, out-of-sample |
| Latência de rede | Execução atrasada | Server próximo ao broker, retry logic |
| API do broker instável | Ordens não executadas | Circuit breaker, notificação imediata |

---

## 10. Glossário

| Termo | Definição |
|-------|-----------|
| **OHLCV** | Open, High, Low, Close, Volume — dados de um candle |
| **OCO** | One Cancels the Other — par de ordens (SL + TP) |
| **Repainting** | Sinal que muda após o fato, invalidando backtest |
| **Confluence** | Convergência de múltiplos indicadores confirmando um sinal |
| **Drawdown** | Queda percentual do pico máximo de capital |
| **S/R** | Suporte e Resistência — zonas de memória do mercado |
| **ADX** | Average Directional Index — mede força da tendência |
| **RSI** | Relative Strength Index — mede sobrecompra/sobrevenda |
| **Didi Index** | Indicador brasileiro de explosão de volatilidade |

---

*GoldTrader Pro — Consistência estatística através de disciplina algorítmica.*
