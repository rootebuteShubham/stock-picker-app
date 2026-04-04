"""
Market Structure Analysis.
Identifies trend direction, support/resistance levels, and trendlines.
Based on concepts from "The Candlestick Trading Bible".
"""

import pandas as pd
import numpy as np
from config import settings


def find_swing_points(df: pd.DataFrame, window: int = None) -> tuple:
    """
    Find swing highs and swing lows in price data.

    Returns:
        (swing_highs, swing_lows) — each is a list of (index, price) tuples
    """
    window = window or settings.SR_PIVOT_WINDOW
    highs = []
    lows = []

    high = df["high"].values
    low = df["low"].values

    for i in range(window, len(df) - window):
        # Swing high: highest high in the window
        if high[i] == max(high[i - window:i + window + 1]):
            highs.append((df.index[i], high[i]))
        # Swing low: lowest low in the window
        if low[i] == min(low[i - window:i + window + 1]):
            lows.append((df.index[i], low[i]))

    return highs, lows


def identify_trend(df: pd.DataFrame, lookback: int = 60) -> dict:
    """
    Identify the current market trend using higher highs/higher lows logic
    from "The Candlestick Trading Bible".

    Returns:
        dict with: trend, description, strength
    """
    if len(df) < lookback:
        lookback = len(df)

    recent = df.iloc[-lookback:]
    swing_highs, swing_lows = find_swing_points(recent, window=3)

    result = {
        "trend": "ranging",
        "description": "Market is in a sideways range — no clear directional bias",
        "strength": "weak",
    }

    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        # Check for higher highs and higher lows (uptrend)
        hh = [p for _, p in swing_highs[-3:]]
        hl = [p for _, p in swing_lows[-3:]]

        higher_highs = all(hh[i] > hh[i - 1] for i in range(1, len(hh)))
        higher_lows = all(hl[i] > hl[i - 1] for i in range(1, len(hl)))

        lower_highs = all(hh[i] < hh[i - 1] for i in range(1, len(hh)))
        lower_lows = all(hl[i] < hl[i - 1] for i in range(1, len(hl)))

        if higher_highs and higher_lows:
            result["trend"] = "uptrend"
            result["description"] = "Market is making higher highs and higher lows — bullish structure"
            result["strength"] = "strong"
        elif lower_highs and lower_lows:
            result["trend"] = "downtrend"
            result["description"] = "Market is making lower highs and lower lows — bearish structure"
            result["strength"] = "strong"
        elif higher_highs or higher_lows:
            result["trend"] = "uptrend"
            result["description"] = "Market shows some bullish structure but not fully confirmed"
            result["strength"] = "moderate"
        elif lower_highs or lower_lows:
            result["trend"] = "downtrend"
            result["description"] = "Market shows some bearish structure but not fully confirmed"
            result["strength"] = "moderate"

    # Also use SMA slope as confirmation
    if len(df) >= 50:
        sma50 = df["close"].rolling(50).mean()
        sma50_slope = (sma50.iloc[-1] - sma50.iloc[-10]) / sma50.iloc[-10] if sma50.iloc[-10] > 0 else 0
        if sma50_slope > 0.02 and result["trend"] != "downtrend":
            result["trend"] = "uptrend"
            result["strength"] = "strong" if result["strength"] == "strong" else "moderate"
        elif sma50_slope < -0.02 and result["trend"] != "uptrend":
            result["trend"] = "downtrend"
            result["strength"] = "strong" if result["strength"] == "strong" else "moderate"

    return result


def find_support_resistance(df: pd.DataFrame, lookback: int = None) -> dict:
    """
    Find key support and resistance levels using pivot points and clustering.

    Returns:
        dict with: support_levels, resistance_levels
    """
    lookback = lookback or settings.SR_LOOKBACK_PERIODS
    if len(df) < lookback:
        lookback = len(df)

    recent = df.iloc[-lookback:]
    current_price = recent["close"].iloc[-1]

    swing_highs, swing_lows = find_swing_points(recent)

    # Cluster nearby levels
    all_highs = [p for _, p in swing_highs]
    all_lows = [p for _, p in swing_lows]

    support_levels = _cluster_levels([p for p in all_lows if p < current_price], current_price)
    resistance_levels = _cluster_levels([p for p in all_highs if p > current_price], current_price)

    # Sort: support descending (nearest first), resistance ascending (nearest first)
    support_levels.sort(reverse=True)
    resistance_levels.sort()

    return {
        "support_levels": support_levels[:5],
        "resistance_levels": resistance_levels[:5],
        "current_price": current_price,
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
    }


def _cluster_levels(prices: list, reference_price: float) -> list:
    """Cluster nearby price levels within tolerance."""
    if not prices:
        return []

    tolerance = reference_price * settings.SR_CLUSTER_PCT
    prices = sorted(prices)
    clusters = []
    current_cluster = [prices[0]]

    for i in range(1, len(prices)):
        if prices[i] - current_cluster[-1] <= tolerance:
            current_cluster.append(prices[i])
        else:
            clusters.append(np.mean(current_cluster))
            current_cluster = [prices[i]]
    clusters.append(np.mean(current_cluster))

    return clusters


def compute_fibonacci_levels(df: pd.DataFrame, trend: str) -> dict:
    """
    Compute Fibonacci retracement levels from the last major swing.

    Per "The Candlestick Trading Bible" (pages 120, 154):
    After a trending move, Fib levels (38.2%, 50%, 61.8%) act as confluence zones.
    Patterns forming at these levels have higher probability.

    Returns:
        dict with: swing_high, swing_low, fib_382, fib_500, fib_618, levels (list)
    """
    result = {"swing_high": None, "swing_low": None, "fib_382": None, "fib_500": None, "fib_618": None, "levels": []}

    swing_highs, swing_lows = find_swing_points(df, window=5)

    if not swing_highs or not swing_lows:
        return result

    if trend == "uptrend":
        # In uptrend: retrace from recent high down to recent low
        swing_high = max(swing_highs, key=lambda x: x[1])[1]
        # Find the most recent swing low BEFORE the high
        recent_lows = [p for _, p in swing_lows]
        swing_low = min(recent_lows[-3:]) if len(recent_lows) >= 3 else min(recent_lows)
    elif trend == "downtrend":
        # In downtrend: retrace from recent low up to recent high
        swing_low = min(swing_lows, key=lambda x: x[1])[1]
        recent_highs = [p for _, p in swing_highs]
        swing_high = max(recent_highs[-3:]) if len(recent_highs) >= 3 else max(recent_highs)
    else:
        # Ranging: use overall high and low
        swing_high = max(p for _, p in swing_highs)
        swing_low = min(p for _, p in swing_lows)

    diff = swing_high - swing_low
    if diff <= 0:
        return result

    result["swing_high"] = swing_high
    result["swing_low"] = swing_low

    for level in settings.FIB_LEVELS:
        if trend == "uptrend":
            # Retracement levels below the high
            fib_price = swing_high - (diff * level)
        else:
            # Retracement levels above the low
            fib_price = swing_low + (diff * level)
        result["levels"].append(fib_price)

    if len(result["levels"]) >= 3:
        result["fib_382"] = result["levels"][0]
        result["fib_500"] = result["levels"][1]
        result["fib_618"] = result["levels"][2]

    return result


def is_near_level(price: float, levels: list, tolerance_pct: float = 0.02) -> tuple:
    """
    Check if price is near any support/resistance level.

    Returns:
        (is_near, nearest_level, distance_pct)
    """
    if not levels:
        return False, None, None

    for level in levels:
        distance_pct = abs(price - level) / level
        if distance_pct <= tolerance_pct:
            return True, level, distance_pct

    return False, None, None
