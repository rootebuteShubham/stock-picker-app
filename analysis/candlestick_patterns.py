"""
Candlestick Pattern Detection Engine.
Implements all patterns from "The Candlestick Trading Bible" by Munehisa Homma,
with market-context validation (patterns must occur at proper S/R levels in correct trend).

Patterns implemented:
1. Engulfing Bar (Bullish & Bearish)
2. Doji (Standard, Dragonfly, Gravestone)
3. Morning Star & Evening Star
4. Hammer (Pin Bar) & Shooting Star
5. Inside Bar / Harami
6. Tweezers Tops & Bottoms
"""

import pandas as pd
import numpy as np
from config import settings


# ─── Pattern Detection Functions ──────────────────────────────────────────────

def detect_engulfing(df: pd.DataFrame) -> pd.Series:
    """
    Detect Bullish and Bearish Engulfing patterns.

    Per the book: "The second body engulfs the previous one."
    Bullish: bearish candle followed by larger bullish candle that fully engulfs it.
    Bearish: bullish candle followed by larger bearish candle that fully engulfs it.

    Returns: Series — 100 (bullish), -100 (bearish), 0 (none)
    """
    signals = pd.Series(0, index=df.index)
    o, c, h, l = df["open"].values, df["close"].values, df["high"].values, df["low"].values

    for i in range(1, len(df)):
        prev_body = abs(c[i - 1] - o[i - 1])
        curr_body = abs(c[i] - o[i])
        prev_range = h[i - 1] - l[i - 1]

        if prev_range == 0 or curr_body == 0:
            continue

        prev_bullish = c[i - 1] > o[i - 1]
        curr_bullish = c[i] > o[i]

        # Bullish Engulfing: previous bearish, current bullish, current body engulfs previous
        if not prev_bullish and curr_bullish:
            if o[i] <= c[i - 1] and c[i] >= o[i - 1]:
                if curr_body > prev_body:
                    signals.iloc[i] = 100

        # Bearish Engulfing: previous bullish, current bearish, current body engulfs previous
        if prev_bullish and not curr_bullish:
            if o[i] >= c[i - 1] and c[i] <= o[i - 1]:
                if curr_body > prev_body:
                    signals.iloc[i] = -100

    return signals


def detect_doji(df: pd.DataFrame) -> pd.Series:
    """
    Detect Doji patterns (Standard, Dragonfly, Gravestone).

    Per the book: "The market opens and closes at the same price — equality
    and indecision between buyers and sellers."

    Standard Doji: body <= 10% of total range
    Dragonfly Doji: doji + long lower shadow, minimal upper shadow (bullish)
    Gravestone Doji: doji + long upper shadow, minimal lower shadow (bearish)

    Returns: Series — 100 (dragonfly/bullish), -100 (gravestone/bearish), 50 (standard doji), 0 (none)
    """
    signals = pd.Series(0, index=df.index)
    o, c, h, l = df["open"].values, df["close"].values, df["high"].values, df["low"].values

    for i in range(len(df)):
        total_range = h[i] - l[i]
        if total_range == 0:
            continue

        body = abs(c[i] - o[i])
        body_ratio = body / total_range

        if body_ratio <= settings.DOJI_BODY_RATIO:
            body_top = max(o[i], c[i])
            body_bottom = min(o[i], c[i])
            upper_shadow = h[i] - body_top
            lower_shadow = body_bottom - l[i]

            # Dragonfly Doji: long lower shadow, minimal upper shadow
            if lower_shadow > body * settings.LONG_SHADOW_RATIO and upper_shadow < total_range * 0.15:
                signals.iloc[i] = 100  # Bullish
            # Gravestone Doji: long upper shadow, minimal lower shadow
            elif upper_shadow > body * settings.LONG_SHADOW_RATIO and lower_shadow < total_range * 0.15:
                signals.iloc[i] = -100  # Bearish
            else:
                signals.iloc[i] = 50  # Standard Doji (indecision)

    return signals


def detect_morning_evening_star(df: pd.DataFrame) -> pd.Series:
    """
    Detect Morning Star (bullish) and Evening Star (bearish) patterns.

    Per the book:
    Morning Star (3-candle bullish reversal at bottom of downtrend):
      1. Large bearish candle
      2. Small body (indecision) — can be bullish, bearish, or doji
      3. Large bullish candle closing above midpoint of candle 1

    Evening Star: mirror image at top of uptrend.

    Returns: Series — 100 (morning star), -100 (evening star), 0 (none)
    """
    signals = pd.Series(0, index=df.index)
    o, c, h, l = df["open"].values, df["close"].values, df["high"].values, df["low"].values

    for i in range(2, len(df)):
        body1 = abs(c[i - 2] - o[i - 2])
        body2 = abs(c[i - 1] - o[i - 1])
        body3 = abs(c[i] - o[i])
        range1 = h[i - 2] - l[i - 2]

        if range1 == 0:
            continue

        mid1 = (o[i - 2] + c[i - 2]) / 2
        is_small_body2 = body2 < body1 * settings.SMALL_BODY_RATIO

        # Morning Star: bearish + small + bullish
        if c[i - 2] < o[i - 2] and is_small_body2 and c[i] > o[i]:
            if c[i] >= mid1 and body3 > body1 * 0.5:
                signals.iloc[i] = 100

        # Evening Star: bullish + small + bearish
        if c[i - 2] > o[i - 2] and is_small_body2 and c[i] < o[i]:
            if c[i] <= mid1 and body3 > body1 * 0.5:
                signals.iloc[i] = -100

    return signals


def detect_hammer_shooting_star(df: pd.DataFrame) -> pd.Series:
    """
    Detect Hammer/Pin Bar (bullish) and Shooting Star (bearish).

    Per the book:
    Hammer: "Open, high and close are roughly the same price; characterized
    by a long lower shadow" — shadow >= 2x body, body in upper third.

    Shooting Star: "Open, low and close are roughly the same; characterized
    by a long upper shadow" — shadow >= 2x body, body in lower third.

    Returns: Series — 100 (hammer), -100 (shooting star), 0 (none)
    """
    signals = pd.Series(0, index=df.index)
    o, c, h, l = df["open"].values, df["close"].values, df["high"].values, df["low"].values

    for i in range(len(df)):
        total_range = h[i] - l[i]
        if total_range == 0:
            continue

        body = abs(c[i] - o[i])
        body_top = max(o[i], c[i])
        body_bottom = min(o[i], c[i])
        upper_shadow = h[i] - body_top
        lower_shadow = body_bottom - l[i]

        # Hammer / Bullish Pin Bar
        if body > 0 and lower_shadow >= body * settings.LONG_SHADOW_RATIO:
            if upper_shadow < total_range * 0.25:
                if (body_bottom - l[i]) / total_range >= 0.6:
                    signals.iloc[i] = 100

        # Shooting Star / Bearish Pin Bar
        if body > 0 and upper_shadow >= body * settings.LONG_SHADOW_RATIO:
            if lower_shadow < total_range * 0.25:
                if (h[i] - body_top) / total_range >= 0.6:
                    signals.iloc[i] = -100

    return signals


def detect_inside_bar(df: pd.DataFrame) -> pd.Series:
    """
    Detect Inside Bar / Harami pattern.

    Per the book: "The second candle should close outside the previous one...
    the smaller body closes inside of the first bigger candle."

    Inside Bar: Current candle's range is within previous candle's range.

    Returns: Series — 50 (inside bar detected, direction depends on context), 0 (none)
    """
    signals = pd.Series(0, index=df.index)
    h, l = df["high"].values, df["low"].values

    for i in range(1, len(df)):
        # Current candle is completely inside previous candle
        if h[i] < h[i - 1] and l[i] > l[i - 1]:
            signals.iloc[i] = 50

    return signals


def detect_tweezers(df: pd.DataFrame) -> pd.Series:
    """
    Detect Tweezer Tops and Bottoms.

    Per the book:
    Tweezer Top: Two candles with nearly identical highs. First bullish, second bearish.
    Tweezer Bottom: Two candles with nearly identical lows. First bearish, second bullish.

    Returns: Series — 100 (tweezer bottom/bullish), -100 (tweezer top/bearish), 0 (none)
    """
    signals = pd.Series(0, index=df.index)
    o, c, h, l = df["open"].values, df["close"].values, df["high"].values, df["low"].values

    for i in range(1, len(df)):
        avg_price = (h[i] + l[i]) / 2
        if avg_price == 0:
            continue
        tolerance = avg_price * settings.TWEEZER_TOLERANCE_PCT

        prev_bullish = c[i - 1] > o[i - 1]
        curr_bullish = c[i] > o[i]

        # Tweezer Top: matching highs, first bullish then bearish
        if abs(h[i] - h[i - 1]) <= tolerance:
            if prev_bullish and not curr_bullish:
                signals.iloc[i] = -100

        # Tweezer Bottom: matching lows, first bearish then bullish
        if abs(l[i] - l[i - 1]) <= tolerance:
            if not prev_bullish and curr_bullish:
                signals.iloc[i] = 100

    return signals


# ─── Master Detection & Context Validation ────────────────────────────────────

def detect_all_patterns(df: pd.DataFrame) -> dict:
    """
    Run all pattern detectors and return a dict of signal Series.

    Returns:
        dict: {pattern_name: pd.Series of signals}
    """
    return {
        "engulfing": detect_engulfing(df),
        "doji": detect_doji(df),
        "morning_evening_star": detect_morning_evening_star(df),
        "hammer_shooting_star": detect_hammer_shooting_star(df),
        "inside_bar": detect_inside_bar(df),
        "tweezers": detect_tweezers(df),
    }


def get_recent_signals(patterns: dict, lookback: int = 10) -> list:
    """
    Get recent candlestick pattern signals from the last N candles.

    Returns:
        List of dicts: [{date, pattern, signal, direction}]
    """
    recent = []

    pattern_names = {
        "engulfing": {100: "Bullish Engulfing", -100: "Bearish Engulfing"},
        "doji": {100: "Dragonfly Doji (Bullish)", -100: "Gravestone Doji (Bearish)", 50: "Doji (Indecision)"},
        "morning_evening_star": {100: "Morning Star (Bullish)", -100: "Evening Star (Bearish)"},
        "hammer_shooting_star": {100: "Hammer / Pin Bar (Bullish)", -100: "Shooting Star (Bearish)"},
        "inside_bar": {50: "Inside Bar / Harami"},
        "tweezers": {100: "Tweezer Bottom (Bullish)", -100: "Tweezer Top (Bearish)"},
    }

    for pattern_key, signals in patterns.items():
        tail = signals.iloc[-lookback:]
        for idx, val in tail.items():
            if val != 0:
                direction = "Bullish" if val > 0 else ("Bearish" if val < 0 else "Neutral")
                name = pattern_names.get(pattern_key, {}).get(int(val), pattern_key)
                recent.append({
                    "date": idx,
                    "pattern": name,
                    "signal": int(val),
                    "direction": direction,
                })

    recent.sort(key=lambda x: x["date"], reverse=True)
    return recent


def score_candlestick_signals(patterns: dict, trend: str, support_levels: list, resistance_levels: list, current_price: float) -> dict:
    """
    Score candlestick patterns considering market context.

    Per "The Candlestick Trading Bible":
    - Bullish reversal patterns are only high-probability at support in a downtrend
    - Bearish reversal patterns are only high-probability at resistance in an uptrend
    - Inside bars can be continuation or reversal depending on context

    Returns:
        dict with: score (-100 to +100), verdict, recent_patterns, explanation
    """
    from analysis.market_structure import is_near_level

    recent = get_recent_signals(patterns, lookback=5)
    if not recent:
        return {
            "score": 0,
            "verdict": "Neutral",
            "recent_patterns": [],
            "explanation": "No significant candlestick patterns detected in recent candles",
        }

    total_score = 0
    explanations = []

    for sig in recent:
        signal_val = sig["signal"]
        pattern_name = sig["pattern"]
        raw_score = 0

        if signal_val == 100:  # Bullish signals
            near_support, level, _ = is_near_level(current_price, support_levels, tolerance_pct=0.03)
            if trend == "downtrend" and near_support:
                raw_score = 30  # High probability: reversal at support in downtrend
                explanations.append(f"{pattern_name} at support ₹{level:.0f} in downtrend — strong reversal signal")
            elif trend == "uptrend":
                raw_score = 20  # Continuation signal
                explanations.append(f"{pattern_name} in uptrend — continuation signal")
            else:
                raw_score = 10
                explanations.append(f"{pattern_name} detected — moderate bullish signal")

        elif signal_val == -100:  # Bearish signals
            near_resistance, level, _ = is_near_level(current_price, resistance_levels, tolerance_pct=0.03)
            if trend == "uptrend" and near_resistance:
                raw_score = -30
                explanations.append(f"{pattern_name} at resistance ₹{level:.0f} in uptrend — strong reversal signal")
            elif trend == "downtrend":
                raw_score = -20
                explanations.append(f"{pattern_name} in downtrend — continuation signal")
            else:
                raw_score = -10
                explanations.append(f"{pattern_name} detected — moderate bearish signal")

        elif signal_val == 50:  # Neutral (doji, inside bar)
            raw_score = 5 if trend == "uptrend" else (-5 if trend == "downtrend" else 0)
            explanations.append(f"{pattern_name} — indecision, watch for breakout direction")

        total_score += raw_score

    # Clamp to [-100, 100]
    total_score = max(-100, min(100, total_score))

    if total_score >= 30:
        verdict = "Bullish"
    elif total_score >= 10:
        verdict = "Mildly Bullish"
    elif total_score <= -30:
        verdict = "Bearish"
    elif total_score <= -10:
        verdict = "Mildly Bearish"
    else:
        verdict = "Neutral"

    return {
        "score": total_score,
        "verdict": verdict,
        "recent_patterns": recent,
        "explanation": "; ".join(explanations) if explanations else "No actionable patterns",
    }
