"""
Configuration settings: thresholds, scoring weights, and constants for the Stock Analyzer.
"""

# ─── Fundamental Analysis Thresholds ───────────────────────────────────────────

PE_UNDERVALUED = 15
PE_FAIR_LOW = 15
PE_FAIR_HIGH = 25
PE_OVERVALUED = 40

PB_UNDERVALUED = 1.5
PB_FAIR_HIGH = 3.0
PB_OVERVALUED = 5.0

ROE_EXCELLENT = 20
ROE_GOOD = 15
ROE_POOR = 10

ROCE_EXCELLENT = 20
ROCE_GOOD = 15
ROCE_POOR = 10

DEBT_EQUITY_SAFE = 0.5
DEBT_EQUITY_MODERATE = 1.0
DEBT_EQUITY_DANGER = 1.5

EARNINGS_GROWTH_STRONG = 15
EARNINGS_GROWTH_MODERATE = 0

REVENUE_GROWTH_STRONG = 15
REVENUE_GROWTH_MODERATE = 0

PROMOTER_HOLDING_STRONG = 60
PROMOTER_HOLDING_MODERATE = 40
PROMOTER_HOLDING_WEAK = 30

PROMOTER_PLEDGE_SAFE = 5
PROMOTER_PLEDGE_MODERATE = 20

DIVIDEND_YIELD_GOOD = 3.0
DIVIDEND_YIELD_MODERATE = 1.0

# ─── Technical Analysis Thresholds ─────────────────────────────────────────────

RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

ADX_TRENDING = 25
ADX_WEAK_TREND = 20

VOLUME_SPIKE_MULTIPLIER = 1.5

# Moving average periods
SMA_SHORT = 20
SMA_MEDIUM = 50
SMA_LONG = 200
EMA_FAST = 12
EMA_SLOW = 26

# MACD parameters
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger Bands
BB_PERIOD = 20
BB_STD = 2

# ─── Candlestick Pattern Detection ────────────────────────────────────────────

DOJI_BODY_RATIO = 0.1           # Body <= 10% of total range
LONG_SHADOW_RATIO = 2.0         # Shadow >= 2x body for pin bars
ENGULFING_MIN_BODY_RATIO = 0.6  # Minimum body as % of total range
TWEEZER_TOLERANCE_PCT = 0.002   # 0.2% tolerance for matching highs/lows
SMALL_BODY_RATIO = 0.3          # For star patterns - middle candle body

# ─── Advanced Candlestick Strategies (from "The Candlestick Trading Bible") ──

# 21-EMA as dynamic support/resistance (PDF pages 88-91)
EMA_DYNAMIC_SR = 21
MA_PROXIMITY_PCT = 0.015        # 1.5% proximity to 21-MA for confluence
MA_CONFLUENCE_BOOST = 10        # Score boost when pattern is near 21-MA

# Fibonacci retracement levels (PDF pages 120, 154)
FIB_LEVELS = [0.382, 0.500, 0.618]
FIB_PROXIMITY_PCT = 0.015       # 1.5% proximity to Fib level for confluence
FIB_CONFLUENCE_BOOST = 8        # Score boost when pattern is near Fib level

# False breakout detection (PDF pages 148-158)
FALSE_BREAKOUT_LOOKFORWARD = 2  # Check next 2 candles after inside bar

# ─── Scoring Weights ──────────────────────────────────────────────────────────

WEIGHT_FUNDAMENTAL = 0.45
WEIGHT_TECHNICAL = 0.30
WEIGHT_CANDLESTICK = 0.15
WEIGHT_ADVANCED_LEVELS = 0.10

# Verdict thresholds (on normalized 0-100 scale)
VERDICT_STRONG_BUY = 75
VERDICT_BUY = 60
VERDICT_HOLD_HIGH = 60
VERDICT_HOLD_LOW = 40
VERDICT_SELL = 40
VERDICT_STRONG_SELL = 25

# ─── Timeframe Options ───────────────────────────────────────────────────────

TIMEFRAME_OPTIONS = {
    "Hourly": {
        "period": "1mo",
        "interval": "1h",
        "label": "Hourly (1 Month)",
        "candle_label": "1H",
        "best_for": "Intraday / Short-term trades",
    },
    "Daily": {
        "period": "1y",
        "interval": "1d",
        "label": "Daily (1 Year)",
        "candle_label": "1D",
        "best_for": "Swing trading",
    },
    "Weekly": {
        "period": "5y",
        "interval": "1wk",
        "label": "Weekly (5 Years)",
        "candle_label": "1W",
        "best_for": "Medium-term trend analysis",
    },
    "Monthly": {
        "period": "10y",
        "interval": "1mo",
        "label": "Monthly (10 Years)",
        "candle_label": "1M",
        "best_for": "Long-term investing",
    },
}

DEFAULT_TIMEFRAME = "Daily"

# ─── Data Fetching ────────────────────────────────────────────────────────────

DEFAULT_HISTORY_PERIOD = "1y"
TECHNICAL_LOOKBACK_DAYS = 200
DEFAULT_INTERVAL = "1d"

# ─── Support / Resistance ─────────────────────────────────────────────────────

SR_LOOKBACK_PERIODS = 60
SR_PIVOT_WINDOW = 5            # Window for detecting swing highs/lows
SR_CLUSTER_PCT = 0.02          # 2% clustering tolerance for S/R levels

# ─── Elliott Wave Detection ──────────────────────────────────────────────────

ELLIOTT_SWING_WINDOW = 5        # Swing detection window for wave pivots
ELLIOTT_MIN_SWING_POINTS = 6    # Minimum points needed for impulse detection

# Fibonacci ideal ratios for wave relationships
ELLIOTT_W2_RETRACEMENT = [0.382, 0.500, 0.618, 0.764]
ELLIOTT_W3_EXTENSION = [1.382, 1.618, 2.000, 2.618]
ELLIOTT_W4_RETRACEMENT = [0.236, 0.382, 0.500]
ELLIOTT_W5_RELATIVE_W1 = [0.618, 1.000, 1.618]
ELLIOTT_WB_RETRACEMENT = [0.382, 0.500, 0.618]
ELLIOTT_WC_RELATIVE_WA = [0.618, 1.000, 1.618]

# Maximum deviation from ideal Fib ratio to count as aligned
ELLIOTT_FIB_TOLERANCE = 0.15

# Confidence weights
ELLIOTT_CONFIDENCE_FIB_WEIGHT = 0.50
ELLIOTT_CONFIDENCE_STRUCTURE_WEIGHT = 0.30
ELLIOTT_CONFIDENCE_CLARITY_WEIGHT = 0.20

# Confidence label thresholds
ELLIOTT_CONFIDENCE_HIGH = 75
ELLIOTT_CONFIDENCE_MODERATE = 55
ELLIOTT_CONFIDENCE_LOW = 35

# Timeframe-specific swing window overrides
ELLIOTT_SWING_WINDOW_OVERRIDES = {
    "Hourly": 3,
    "Daily": 5,
    "Weekly": 5,
    "Monthly": 4,
}

# ─── Advanced Levels with MA ────────────────────────────────────────────────

ADV_LEVELS_MA_LENGTH = 144                     # Fibonacci MA period
ADV_LEVELS_ADJUSTABLE_RATIO = 1.272            # Fibonacci extension for envelope
ADV_LEVELS_ATR_PERIOD = 14                     # ATR period for envelope calculation

# Timeframe definitions for multi-timeframe MA computation
ADV_LEVELS_TIMEFRAMES = {
    "15min":   {"period": "1mo",  "interval": "15m"},
    "30min":   {"period": "1mo",  "interval": "30m"},
    "1h":      {"period": "3mo",  "interval": "1h"},
    "Daily":   {"period": "2y",   "interval": "1d"},
    "Weekly":  {"period": "10y",  "interval": "1wk"},
    "Monthly": {"period": "max",  "interval": "1mo"},
}

# Level grouping: L1=short-term, L2=medium-term, L3=long-term
ADV_LEVELS_L1_TIMEFRAMES = ["15min", "30min"]
ADV_LEVELS_L2_TIMEFRAMES = ["1h", "Daily"]
ADV_LEVELS_L3_TIMEFRAMES = ["Weekly", "Monthly"]

# Reference indices (yfinance tickers)
ADV_LEVELS_REFERENCE_INDICES = {
    "NIFTY 50":          "^NSEI",
    "BANK NIFTY":        "^NSEBANK",
    "NIFTY FIN SERVICE": "NIFTY_FIN_SERVICE.NS",
    "NIFTY MIDCAP SEL":  "NIFTYMIDSELECT.NS",
    "INDIA VIX":         "^INDIAVIX",
}

# Proximity: fraction of price within which a level counts as "near"
ADV_LEVELS_PROXIMITY_PCT = 0.02                # 2%

# Clustering: bonus when multiple levels converge near current price
ADV_LEVELS_CLUSTER_BONUS = 8
ADV_LEVELS_CLUSTER_THRESHOLD = 3               # min levels within proximity to trigger
