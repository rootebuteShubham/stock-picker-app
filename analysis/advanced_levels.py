"""
Advanced Levels with MA — Multi-Timeframe 144-Period Moving Average Analysis.

Replicates a TradingView indicator that computes a 144-period (Fibonacci) Moving
Average across 6 timeframes, adds Fibonacci-based envelope levels, and shows
reference Indian market index MA levels for broader context.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import settings
from data.yfinance_provider import get_historical_data


# ─── Resilient Settings Access ──────────────────────────────────────────────

_DEFAULTS = {
    "ADV_LEVELS_MA_LENGTH": 144,
    "ADV_LEVELS_ADJUSTABLE_RATIO": 1.272,
    "ADV_LEVELS_ATR_PERIOD": 14,
    "ADV_LEVELS_TIMEFRAMES": {
        "15min":   {"period": "1mo",  "interval": "15m"},
        "30min":   {"period": "1mo",  "interval": "30m"},
        "1h":      {"period": "3mo",  "interval": "1h"},
        "Daily":   {"period": "2y",   "interval": "1d"},
        "Weekly":  {"period": "10y",  "interval": "1wk"},
        "Monthly": {"period": "max",  "interval": "1mo"},
    },
    "ADV_LEVELS_L1_TIMEFRAMES": ["15min", "30min"],
    "ADV_LEVELS_L2_TIMEFRAMES": ["1h", "Daily"],
    "ADV_LEVELS_L3_TIMEFRAMES": ["Weekly", "Monthly"],
    "ADV_LEVELS_REFERENCE_INDICES": {
        "NIFTY 50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "NIFTY FIN SERVICE": "NIFTY_FIN_SERVICE.NS",
        "NIFTY MIDCAP SEL": "NIFTYMIDSELECT.NS",
        "INDIA VIX": "^INDIAVIX",
    },
    "ADV_LEVELS_PROXIMITY_PCT": 0.02,
    "ADV_LEVELS_CLUSTER_BONUS": 8,
    "ADV_LEVELS_CLUSTER_THRESHOLD": 3,
}


def _s(name):
    """Get setting with fallback to built-in default."""
    return getattr(settings, name, _DEFAULTS[name])


# ─── Dataclasses ────────────────────────────────────────────────────────────

@dataclass
class MALevel:
    """A single computed MA level for one timeframe."""
    timeframe: str          # "15min", "30min", "1h", "Daily", "Weekly", "Monthly"
    ma_value: float         # The 144-period MA value
    group: str              # "L1", "L2", "L3"
    position: str = ""      # "support", "resistance", "near"
    distance_pct: float = 0.0


@dataclass
class EnvelopeLevel:
    """Upper and lower envelope levels based on adjustable Fibonacci ratio."""
    upper: float = 0.0
    lower: float = 0.0
    daily_ma: float = 0.0
    atr_value: float = 0.0
    ratio: float = 1.272


@dataclass
class IndexMAInfo:
    """144-period Daily MA info for a reference index."""
    name: str = ""
    ticker: str = ""
    ma_value: float = 0.0
    current_price: float = 0.0
    position: str = ""          # "above", "below", "near"
    distance_pct: float = 0.0
    fetched: bool = True


@dataclass
class AdvancedLevelsResult:
    """Complete result from Advanced Levels analysis."""
    detected: bool = False
    stock_levels: list = field(default_factory=list)
    envelope: object = None
    index_levels: list = field(default_factory=list)
    normalized_score: float = 50.0
    verdict: str = "Neutral"
    summary: str = ""
    errors: list = field(default_factory=list)
    support_count: int = 0
    resistance_count: int = 0
    near_count: int = 0
    cluster_detected: bool = False
    index_bullish_count: int = 0
    index_bearish_count: int = 0


# ─── Internal Helpers ───────────────────────────────────────────────────────

def _get_group(tf_key):
    """Determine the level group (L1/L2/L3) for a timeframe key."""
    if tf_key in _s("ADV_LEVELS_L1_TIMEFRAMES"):
        return "L1"
    elif tf_key in _s("ADV_LEVELS_L2_TIMEFRAMES"):
        return "L2"
    else:
        return "L3"


def _classify_position(ma_value, current_price, proximity_pct):
    """Classify a level as support, resistance, or near relative to current price."""
    if current_price <= 0:
        return "near", 0.0
    distance_pct = (current_price - ma_value) / current_price
    if abs(distance_pct) <= proximity_pct:
        return "near", abs(distance_pct)
    elif ma_value < current_price:
        return "support", abs(distance_pct)
    else:
        return "resistance", abs(distance_pct)


def _compute_atr(df, period=14):
    """Compute Average True Range from OHLC data."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = true_range.rolling(window=period).mean()
    last_atr = atr.dropna().iloc[-1] if not atr.dropna().empty else None
    return last_atr


# ─── Data Fetching ──────────────────────────────────────────────────────────

def _fetch_ma_for_timeframe(ticker, tf_key, tf_config, ma_length):
    """
    Fetch historical data for a single timeframe and compute the MA.
    Returns (tf_key, ma_value, df_or_None) or raises on failure.
    """
    df = get_historical_data(
        ticker,
        period=tf_config["period"],
        interval=tf_config["interval"],
    )
    if df.empty or len(df) < ma_length:
        return tf_key, None, None

    ma_series = df["close"].rolling(window=ma_length).mean()
    ma_value = ma_series.dropna().iloc[-1] if not ma_series.dropna().empty else None
    return tf_key, ma_value, df


def _fetch_all_stock_levels(ticker, current_price, ma_length):
    """
    Fetch 144-MA for all 6 timeframes in parallel.
    Returns (list[MALevel], list[str] errors, daily_df or None).
    """
    timeframes = _s("ADV_LEVELS_TIMEFRAMES")
    proximity = _s("ADV_LEVELS_PROXIMITY_PCT")
    levels = []
    errors = []
    daily_df = None

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {}
        for tf_key, tf_config in timeframes.items():
            future = executor.submit(
                _fetch_ma_for_timeframe, ticker, tf_key, tf_config, ma_length
            )
            futures[future] = tf_key

        for future in as_completed(futures):
            tf_key = futures[future]
            try:
                result_key, ma_value, df = future.result()
                if ma_value is not None:
                    group = _get_group(result_key)
                    position, distance = _classify_position(
                        ma_value, current_price, proximity
                    )
                    levels.append(MALevel(
                        timeframe=result_key,
                        ma_value=round(ma_value, 2),
                        group=group,
                        position=position,
                        distance_pct=round(distance, 4),
                    ))
                    if result_key == "Daily" and df is not None:
                        daily_df = df
                else:
                    errors.append(f"{tf_key}: Insufficient data for {ma_length}-period MA")
            except Exception as e:
                errors.append(f"{tf_key}: {str(e)[:80]}")

    # Sort by timeframe order for display
    tf_order = list(timeframes.keys())
    levels.sort(key=lambda lv: tf_order.index(lv.timeframe) if lv.timeframe in tf_order else 99)
    return levels, errors, daily_df


def _compute_envelope(daily_df, ma_length, atr_period, ratio):
    """Compute the Fibonacci envelope levels from Daily data."""
    if daily_df is None or daily_df.empty or len(daily_df) < ma_length:
        return None

    ma_series = daily_df["close"].rolling(window=ma_length).mean()
    daily_ma = ma_series.dropna().iloc[-1] if not ma_series.dropna().empty else None
    if daily_ma is None:
        return None

    atr_value = _compute_atr(daily_df, period=atr_period)
    if atr_value is None or atr_value <= 0:
        return None

    return EnvelopeLevel(
        upper=round(daily_ma + ratio * atr_value, 2),
        lower=round(daily_ma - ratio * atr_value, 2),
        daily_ma=round(daily_ma, 2),
        atr_value=round(atr_value, 2),
        ratio=ratio,
    )


def _fetch_index_ma(name, yf_ticker, ma_length):
    """Fetch 144-period Daily MA for a single reference index."""
    df = get_historical_data(yf_ticker, period="2y", interval="1d")
    if df.empty or len(df) < ma_length:
        return IndexMAInfo(name=name, ticker=yf_ticker, fetched=False)

    ma_series = df["close"].rolling(window=ma_length).mean()
    ma_value = ma_series.dropna().iloc[-1] if not ma_series.dropna().empty else None
    current_price = df["close"].iloc[-1]

    if ma_value is None:
        return IndexMAInfo(name=name, ticker=yf_ticker, fetched=False)

    distance_pct = (current_price - ma_value) / ma_value if ma_value > 0 else 0
    if abs(distance_pct) < 0.02:
        position = "near"
    elif current_price > ma_value:
        position = "above"
    else:
        position = "below"

    return IndexMAInfo(
        name=name,
        ticker=yf_ticker,
        ma_value=round(ma_value, 2),
        current_price=round(current_price, 2),
        position=position,
        distance_pct=round(abs(distance_pct), 4),
        fetched=True,
    )


def _fetch_all_index_levels(ma_length):
    """Fetch 144-MA for all reference indices in parallel."""
    indices = _s("ADV_LEVELS_REFERENCE_INDICES")
    index_levels = []
    errors = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for name, yf_ticker in indices.items():
            future = executor.submit(_fetch_index_ma, name, yf_ticker, ma_length)
            futures[future] = name

        for future in as_completed(futures):
            name = futures[future]
            try:
                info = future.result()
                index_levels.append(info)
                if not info.fetched:
                    errors.append(f"Index {name}: Data unavailable")
            except Exception as e:
                errors.append(f"Index {name}: {str(e)[:80]}")
                index_levels.append(IndexMAInfo(name=name, fetched=False))

    # Sort by name for consistent display
    index_levels.sort(key=lambda x: x.name)
    return index_levels, errors


# ─── Scoring ────────────────────────────────────────────────────────────────

def _compute_score(stock_levels, envelope, index_levels, current_price):
    """
    Compute a normalized 0-100 score based on MA levels position.

    Components:
        - Stock MA position:  60 pts max (10 per support, 5 per near, 0 per resistance)
        - Envelope position:  15 pts max
        - Index context:      15 pts max (3 per bullish index)
        - Clustering bonus:   10 pts max
    """
    raw_score = 0.0

    # ── Stock MA Position (60 pts max) ──────────────────────────────────
    support_count = 0
    resistance_count = 0
    near_count = 0

    for level in stock_levels:
        if level.position == "support":
            raw_score += 10
            support_count += 1
        elif level.position == "near":
            raw_score += 5
            near_count += 1
        else:
            resistance_count += 1

    # ── Envelope Position (15 pts) ──────────────────────────────────────
    if envelope is not None:
        env_upper = getattr(envelope, "upper", 0)
        env_lower = getattr(envelope, "lower", 0)
        env_ma = getattr(envelope, "daily_ma", 0)

        if env_ma > 0:
            if current_price > env_ma and current_price <= env_upper:
                raw_score += 15  # Healthy uptrend
            elif abs(current_price - env_ma) / env_ma <= 0.01:
                raw_score += 10  # Consolidation near MA
            elif current_price > env_upper:
                raw_score += 7   # Overextended above
            elif current_price < env_ma and current_price >= env_lower:
                raw_score += 5   # Below MA but within envelope
            # Below lower envelope: 0 points (bearish)

    # ── Index Context (15 pts) ──────────────────────────────────────────
    index_bullish = 0
    index_bearish = 0

    for idx in index_levels:
        if not getattr(idx, "fetched", False):
            continue
        idx_name = getattr(idx, "name", "")
        idx_position = getattr(idx, "position", "")

        # India VIX is inverted: below MA = low fear = bullish for market
        if "VIX" in idx_name.upper():
            if idx_position == "below":
                raw_score += 3
                index_bullish += 1
            elif idx_position == "above":
                index_bearish += 1
        else:
            if idx_position == "above":
                raw_score += 3
                index_bullish += 1
            elif idx_position == "below":
                index_bearish += 1

    # ── Clustering Bonus (10 pts) ───────────────────────────────────────
    proximity = _s("ADV_LEVELS_PROXIMITY_PCT")
    cluster_threshold = _s("ADV_LEVELS_CLUSTER_THRESHOLD")
    cluster_bonus = _s("ADV_LEVELS_CLUSTER_BONUS")
    cluster_detected = False

    near_levels = [lv for lv in stock_levels if lv.distance_pct <= proximity]
    if len(near_levels) >= cluster_threshold:
        raw_score += cluster_bonus
        cluster_detected = True
        # Extra bonus if envelope overlaps the cluster
        if envelope is not None:
            env_ma = getattr(envelope, "daily_ma", 0)
            if env_ma > 0 and abs(current_price - env_ma) / current_price <= proximity:
                raw_score += 2

    # ── Normalize ───────────────────────────────────────────────────────
    normalized = min(100.0, max(0.0, raw_score))

    # Determine verdict label
    if normalized >= 75:
        verdict = "Strong Support"
    elif normalized >= 60:
        verdict = "Support"
    elif normalized >= 40:
        verdict = "Neutral"
    elif normalized >= 25:
        verdict = "Resistance"
    else:
        verdict = "Strong Resistance"

    return (
        round(normalized, 1),
        verdict,
        support_count,
        resistance_count,
        near_count,
        cluster_detected,
        index_bullish,
        index_bearish,
    )


def _generate_summary(result):
    """Generate a plain-English summary of the Advanced Levels analysis."""
    total = result.support_count + result.resistance_count + result.near_count
    if total == 0:
        return "Insufficient data to compute multi-timeframe MA levels."

    parts = []

    # MA position summary
    if result.support_count > result.resistance_count:
        parts.append(
            f"Price is above {result.support_count} of {total} timeframe MAs "
            f"— multi-timeframe trend is bullish."
        )
    elif result.resistance_count > result.support_count:
        parts.append(
            f"Price is below {result.resistance_count} of {total} timeframe MAs "
            f"— multi-timeframe trend is bearish."
        )
    else:
        parts.append(
            f"Price is between timeframe MAs ({result.support_count} support, "
            f"{result.resistance_count} resistance) — mixed signals."
        )

    # Clustering
    if result.cluster_detected:
        parts.append(
            "Multiple MA levels cluster near the current price — strong confluence zone."
        )

    # Index context
    total_idx = result.index_bullish_count + result.index_bearish_count
    if total_idx > 0:
        if result.index_bullish_count > result.index_bearish_count:
            parts.append(
                f"Broad market context is bullish ({result.index_bullish_count}/{total_idx} "
                f"indices above their 144-MA)."
            )
        elif result.index_bearish_count > result.index_bullish_count:
            parts.append(
                f"Broad market context is bearish ({result.index_bearish_count}/{total_idx} "
                f"indices below their 144-MA)."
            )

    return " ".join(parts)


# ─── Public Entry Point ─────────────────────────────────────────────────────

def analyze(ticker, current_price):
    """
    Run Advanced Levels with MA analysis.

    Args:
        ticker: yfinance ticker (e.g. "RELIANCE.NS")
        current_price: Current stock price

    Returns:
        AdvancedLevelsResult with multi-timeframe MA levels, envelope, index context, and score
    """
    result = AdvancedLevelsResult()
    ma_length = _s("ADV_LEVELS_MA_LENGTH")

    if current_price is None or current_price <= 0:
        result.summary = "Current price unavailable — cannot compute levels."
        return result

    # ── Fetch stock MA levels across all timeframes ─────────────────────
    try:
        stock_levels, stock_errors, daily_df = _fetch_all_stock_levels(
            ticker, current_price, ma_length
        )
        result.stock_levels = stock_levels
        result.errors.extend(stock_errors)
    except Exception as e:
        result.errors.append(f"Stock levels: {str(e)[:100]}")
        stock_levels = []
        daily_df = None

    # ── Compute envelope from Daily data ────────────────────────────────
    try:
        ratio = _s("ADV_LEVELS_ADJUSTABLE_RATIO")
        atr_period = _s("ADV_LEVELS_ATR_PERIOD")
        envelope = _compute_envelope(daily_df, ma_length, atr_period, ratio)
        result.envelope = envelope
    except Exception as e:
        result.errors.append(f"Envelope: {str(e)[:100]}")
        envelope = None

    # ── Fetch reference index levels ────────────────────────────────────
    try:
        index_levels, index_errors = _fetch_all_index_levels(ma_length)
        result.index_levels = index_levels
        result.errors.extend(index_errors)
    except Exception as e:
        result.errors.append(f"Index levels: {str(e)[:100]}")
        index_levels = []

    # ── Compute score ───────────────────────────────────────────────────
    if len(stock_levels) >= 2:  # Need at least 2 timeframes for meaningful analysis
        (
            result.normalized_score,
            result.verdict,
            result.support_count,
            result.resistance_count,
            result.near_count,
            result.cluster_detected,
            result.index_bullish_count,
            result.index_bearish_count,
        ) = _compute_score(stock_levels, envelope, index_levels, current_price)
        result.detected = True
    else:
        result.summary = (
            "Insufficient multi-timeframe data — could not compute enough MA levels. "
            f"Only {len(stock_levels)} of 6 timeframes returned valid data."
        )
        return result

    # ── Generate summary ────────────────────────────────────────────────
    result.summary = _generate_summary(result)

    return result
