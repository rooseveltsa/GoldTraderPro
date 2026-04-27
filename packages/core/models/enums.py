"""Enumerações centrais do GoldTrader Pro."""

from enum import Enum


class Timeframe(str, Enum):
    """Periodicidades suportadas."""

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN = "MN"

    @property
    def minutes(self) -> int:
        mapping = {
            "M1": 1, "M5": 5, "M15": 15, "M30": 30,
            "H1": 60, "H4": 240, "D1": 1440, "W1": 10080, "MN": 43200,
        }
        return mapping[self.value]


class Direction(str, Enum):
    """Direção do sinal."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class MarketContext(str, Enum):
    """Contexto de mercado onde o padrão foi identificado."""

    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    CONGESTION = "CONGESTION"


class PatternType(str, Enum):
    """Tipos de padrões de candlestick."""

    # Single candle
    HAMMER = "HAMMER"
    INVERTED_HAMMER = "INVERTED_HAMMER"
    SHOOTING_STAR = "SHOOTING_STAR"
    HANGING_MAN = "HANGING_MAN"
    DOJI = "DOJI"
    DRAGONFLY_DOJI = "DRAGONFLY_DOJI"
    GRAVESTONE_DOJI = "GRAVESTONE_DOJI"

    # Multi candle
    BULLISH_ENGULFING = "BULLISH_ENGULFING"
    BEARISH_ENGULFING = "BEARISH_ENGULFING"
    MORNING_STAR = "MORNING_STAR"
    EVENING_STAR = "EVENING_STAR"

    # Chart patterns
    HEAD_AND_SHOULDERS = "HEAD_AND_SHOULDERS"
    INVERSE_HEAD_AND_SHOULDERS = "INVERSE_HEAD_AND_SHOULDERS"
    ASCENDING_TRIANGLE = "ASCENDING_TRIANGLE"
    DESCENDING_TRIANGLE = "DESCENDING_TRIANGLE"
    WEDGE = "WEDGE"


class VolumeVerdict(str, Enum):
    """Resultado da validação de volume."""

    CLIMACTIC = "CLIMACTIC"    # >= 3.0x média — confirmação muito forte
    CONFIRMED = "CONFIRMED"    # >= 1.5x média — confirmação padrão
    NEUTRAL = "NEUTRAL"        # >= 1.0x média — sem confirmação
    WEAK = "WEAK"              # < 1.0x média — ruído


class OrderSide(str, Enum):
    """Lado da ordem."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Tipo da ordem."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    """Status da ordem."""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OperationMode(str, Enum):
    """Modos de operação do sistema."""

    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"
    SIGNAL_ONLY = "signal_only"


class TrendDirection(str, Enum):
    """Direção da tendência para validação multi-timeframe."""

    UP = "UP"
    DOWN = "DOWN"
    LATERAL = "LATERAL"


class SystemState(Enum):
    """Estado do sistema baseado no ADX."""

    TRADING = "TRADING"   # ADX > threshold — mercado direcional
    WAIT = "WAIT"         # ADX < threshold — mercado congestionado
