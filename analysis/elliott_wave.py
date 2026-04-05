"""
Elliott Wave Theory Detection Engine.

Detects impulse (5-wave) and corrective (ABC) patterns from price data,
validates against the 3 cardinal rules, scores Fibonacci alignment, and
projects wave targets.

IMPORTANT: Elliott Wave counts are inherently subjective. This module is
informational only — it does NOT feed into the Buy/Sell/Hold composite score.
Always use stop losses. Multiple valid wave counts can exist simultaneously.
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import numpy as np

from config import settings
from analysis.market_structure import find_swing_points


# ─── Data Structures ────────────────────────────────────────────────────────

@dataclass
class WavePoint:
    """A single pivot point in a wave sequence."""
    index: object           # DataFrame index (datetime)
    price: float
    wave_label: str         # "0", "1", "2", "3", "4", "5", "A", "B", "C"
    wave_type: str          # "impulse" or "corrective"


@dataclass
class FibRelationship:
    """A Fibonacci ratio measurement between waves."""
    description: str        # e.g. "Wave 2 retracement of Wave 1"
    actual_ratio: float
    ideal_ratio: float      # Nearest ideal Fibonacci ratio
    deviation: float        # abs(actual - ideal)


@dataclass
class WaveProjection:
    """A projected target for the next wave."""
    label: str              # e.g. "Wave 5 Target (1.0x W1)"
    price: float
    fib_ratio: float
    confidence: str         # "high", "medium", "low"


@dataclass
class RuleValidation:
    """Result of validating one of the 3 cardinal rules."""
    rule_name: str
    description: str
    passed: bool
    detail: str


@dataclass
class ElliottWaveResult:
    """Complete Elliott Wave analysis result."""
    detected: bool = False
    wave_type: str = ""                              # "impulse_up", "impulse_down", "corrective"
    wave_points: list = field(default_factory=list)  # List[WavePoint]
    current_wave: str = ""                           # "3", "5", "B", etc.
    current_wave_progress: str = ""                  # "early", "mid", "late"
    trend_direction: str = ""                        # "bullish" or "bearish"
    rules_validation: list = field(default_factory=list)  # List[RuleValidation]
    all_rules_pass: bool = False
    fib_relationships: list = field(default_factory=list)  # List[FibRelationship]
    fib_score: float = 0.0                           # 0-100
    projections: list = field(default_factory=list)   # List[WaveProjection]
    confidence: float = 0.0                          # 0-100
    confidence_label: str = "No Pattern"
    summary: str = ""
    warnings: list = field(default_factory=list)


# ─── Swing Sequence Builder ─────────────────────────────────────────────────

def _build_swing_sequence(swing_highs: list, swing_lows: list) -> list:
    """
    Merge swing highs and lows into a strictly alternating sequence.

    Takes (index, price) tuples from find_swing_points() and returns a
    chronological list of (index, price, "high"/"low") with strict alternation.
    When consecutive same-type pivots appear, keeps the more extreme one.
    """
    # Combine and sort chronologically
    all_points = [(idx, price, "high") for idx, price in swing_highs]
    all_points += [(idx, price, "low") for idx, price in swing_lows]
    all_points.sort(key=lambda x: x[0])

    if not all_points:
        return []

    # Enforce strict alternation: high-low-high-low
    sequence = [all_points[0]]
    for point in all_points[1:]:
        if point[2] == sequence[-1][2]:
            # Same type as last — keep the more extreme one
            if point[2] == "high":
                if point[1] > sequence[-1][1]:
                    sequence[-1] = point
            else:  # low
                if point[1] < sequence[-1][1]:
                    sequence[-1] = point
        else:
            sequence.append(point)

    return sequence


# ─── Cardinal Rule Validation ────────────────────────────────────────────────

def _validate_cardinal_rules(points: list, direction: str) -> list:
    """
    Validate the 3 inviolable Elliott Wave rules on a 6-point impulse sequence.

    points: list of 6 (index, price) — [start, w1_end, w2_end, w3_end, w4_end, w5_end]
    direction: "up" (bullish impulse) or "down" (bearish impulse)

    Returns: list of 3 RuleValidation objects. ALL must pass for a valid count.
    """
    p = [pt[1] for pt in points]  # Extract prices

    rules = []

    # Rule 1: Wave 2 never retraces more than 100% of Wave 1
    if direction == "up":
        # In bullish impulse, Wave 2 low must stay above Wave 0 start
        passed = p[2] > p[0]
        detail = f"Wave 2 low (₹{p[2]:,.0f}) vs Wave start (₹{p[0]:,.0f})"
    else:
        # In bearish impulse, Wave 2 high must stay below Wave 0 start
        passed = p[2] < p[0]
        detail = f"Wave 2 high (₹{p[2]:,.0f}) vs Wave start (₹{p[0]:,.0f})"

    rules.append(RuleValidation(
        rule_name="Rule 1",
        description="Wave 2 never retraces more than 100% of Wave 1",
        passed=passed,
        detail=detail,
    ))

    # Rule 2: Wave 3 is never the shortest of waves 1, 3, 5
    len_w1 = abs(p[1] - p[0])
    len_w3 = abs(p[3] - p[2])
    len_w5 = abs(p[5] - p[4])

    passed = not (len_w3 < len_w1 and len_w3 < len_w5)
    detail = f"W1={len_w1:,.0f}, W3={len_w3:,.0f}, W5={len_w5:,.0f}"
    rules.append(RuleValidation(
        rule_name="Rule 2",
        description="Wave 3 is never the shortest impulse wave",
        passed=passed,
        detail=detail,
    ))

    # Rule 3: Wave 4 must not overlap Wave 1 price territory
    if direction == "up":
        # Wave 4 low must stay above Wave 1 high
        passed = p[4] > p[1]
        detail = f"Wave 4 low (₹{p[4]:,.0f}) vs Wave 1 high (₹{p[1]:,.0f})"
    else:
        # Wave 4 high must stay below Wave 1 low
        passed = p[4] < p[1]
        detail = f"Wave 4 high (₹{p[4]:,.0f}) vs Wave 1 low (₹{p[1]:,.0f})"

    rules.append(RuleValidation(
        rule_name="Rule 3",
        description="Wave 4 must not overlap Wave 1 price territory",
        passed=passed,
        detail=detail,
    ))

    return rules


# ─── Fibonacci Scoring ──────────────────────────────────────────────────────

def _nearest_fib(ratio: float, ideal_ratios: list) -> tuple:
    """Find the nearest ideal Fibonacci ratio and return (ideal, deviation)."""
    best_ideal = ideal_ratios[0]
    best_dev = abs(ratio - best_ideal)
    for r in ideal_ratios[1:]:
        dev = abs(ratio - r)
        if dev < best_dev:
            best_dev = dev
            best_ideal = r
    return best_ideal, best_dev


def _score_fibonacci_alignment(points: list, direction: str) -> tuple:
    """
    Score how well wave ratios align with ideal Fibonacci levels.

    Returns: (fib_score 0-100, list of FibRelationship)
    """
    p = [pt[1] for pt in points]
    relationships = []
    tolerance = settings.ELLIOTT_FIB_TOLERANCE

    # Wave lengths
    w1_len = abs(p[1] - p[0])
    w3_len = abs(p[3] - p[2])
    w5_len = abs(p[5] - p[4])

    if w1_len == 0:
        return 0.0, []

    # 1. Wave 2 retracement of Wave 1
    w2_retrace = abs(p[2] - p[1]) / w1_len
    ideal, dev = _nearest_fib(w2_retrace, settings.ELLIOTT_W2_RETRACEMENT)
    relationships.append(FibRelationship(
        "Wave 2 retracement of Wave 1", w2_retrace, ideal, dev,
    ))

    # 2. Wave 3 extension of Wave 1
    w3_ext = w3_len / w1_len
    ideal, dev = _nearest_fib(w3_ext, settings.ELLIOTT_W3_EXTENSION)
    relationships.append(FibRelationship(
        "Wave 3 extension of Wave 1", w3_ext, ideal, dev,
    ))

    # 3. Wave 4 retracement of Wave 3
    if w3_len > 0:
        w4_retrace = abs(p[4] - p[3]) / w3_len
        ideal, dev = _nearest_fib(w4_retrace, settings.ELLIOTT_W4_RETRACEMENT)
        relationships.append(FibRelationship(
            "Wave 4 retracement of Wave 3", w4_retrace, ideal, dev,
        ))

    # 4. Wave 5 relative to Wave 1
    w5_rel = w5_len / w1_len
    ideal, dev = _nearest_fib(w5_rel, settings.ELLIOTT_W5_RELATIVE_W1)
    relationships.append(FibRelationship(
        "Wave 5 relative to Wave 1", w5_rel, ideal, dev,
    ))

    # Score: each relationship contributes up to 25 points (total 100)
    total = 0.0
    per_rel = 100.0 / len(relationships) if relationships else 0
    for rel in relationships:
        rel_score = max(0, 1 - (rel.deviation / tolerance)) * per_rel
        total += rel_score

    return round(total, 1), relationships


def _score_corrective_fibonacci(points: list, direction: str) -> tuple:
    """
    Score Fibonacci alignment for a 4-point ABC corrective pattern.

    Returns: (fib_score 0-100, list of FibRelationship)
    """
    p = [pt[1] for pt in points]
    relationships = []
    tolerance = settings.ELLIOTT_FIB_TOLERANCE

    wa_len = abs(p[1] - p[0])
    if wa_len == 0:
        return 0.0, []

    # Wave B retracement of Wave A
    wb_retrace = abs(p[2] - p[1]) / wa_len
    ideal, dev = _nearest_fib(wb_retrace, settings.ELLIOTT_WB_RETRACEMENT)
    relationships.append(FibRelationship(
        "Wave B retracement of Wave A", wb_retrace, ideal, dev,
    ))

    # Wave C relative to Wave A
    wc_len = abs(p[3] - p[2])
    wc_rel = wc_len / wa_len
    ideal, dev = _nearest_fib(wc_rel, settings.ELLIOTT_WC_RELATIVE_WA)
    relationships.append(FibRelationship(
        "Wave C relative to Wave A", wc_rel, ideal, dev,
    ))

    total = 0.0
    per_rel = 100.0 / len(relationships) if relationships else 0
    for rel in relationships:
        rel_score = max(0, 1 - (rel.deviation / tolerance)) * per_rel
        total += rel_score

    return round(total, 1), relationships


# ─── Impulse Wave Detection ─────────────────────────────────────────────────

def _find_best_impulse_count(sequence: list, trend: str) -> Optional[dict]:
    """
    Search for the best valid 5-wave impulse pattern in the swing sequence.

    Tries all possible 6-point subsequences from the recent half of data.
    Validates cardinal rules and scores Fibonacci alignment.

    Returns: dict with keys (points, direction, fib_score, fib_rels, rules)
             or None if no valid pattern found.
    """
    n = len(sequence)
    if n < 6:
        return None

    # Only search from the most recent portion to limit complexity
    start_idx = max(0, n - 20)
    best = None
    best_score = -1

    for direction in ["up", "down"]:
        # Skip if direction contradicts strong trend signal
        if trend == "uptrend" and direction == "down":
            continue
        if trend == "downtrend" and direction == "up":
            continue

        # For bullish impulse: pattern starts at a low, then high, low, high, low, high
        # For bearish impulse: starts at a high, then low, high, low, high, low
        if direction == "up":
            expected = ["low", "high", "low", "high", "low", "high"]
        else:
            expected = ["high", "low", "high", "low", "high", "low"]

        # Slide through all valid 6-point windows
        for i in range(start_idx, n - 5):
            candidate = sequence[i:i + 6]

            # Check alternation pattern matches expected
            types = [pt[2] for pt in candidate]
            if types != expected:
                continue

            # Validate cardinal rules
            rules = _validate_cardinal_rules(candidate, direction)
            all_pass = all(r.passed for r in rules)
            if not all_pass:
                continue

            # Score Fibonacci alignment
            fib_score, fib_rels = _score_fibonacci_alignment(candidate, direction)

            if fib_score > best_score:
                best_score = fib_score
                best = {
                    "points": candidate,
                    "direction": direction,
                    "fib_score": fib_score,
                    "fib_rels": fib_rels,
                    "rules": rules,
                }

    return best


# ─── Corrective Wave Detection ──────────────────────────────────────────────

def _find_corrective_pattern(sequence: list, trend: str) -> Optional[dict]:
    """
    Search for the best ABC corrective pattern in the swing sequence.

    Returns: dict with keys (points, direction, fib_score, fib_rels)
             or None if no valid pattern found.
    """
    n = len(sequence)
    if n < 4:
        return None

    start_idx = max(0, n - 16)
    best = None
    best_score = -1

    for direction in ["down", "up"]:
        # Corrective down (after uptrend): starts high, goes A-down, B-up, C-down
        # Corrective up (after downtrend): starts low, goes A-up, B-down, C-up
        if direction == "down":
            expected = ["high", "low", "high", "low"]
        else:
            expected = ["low", "high", "low", "high"]

        for i in range(start_idx, n - 3):
            candidate = sequence[i:i + 4]
            types = [pt[2] for pt in candidate]
            if types != expected:
                continue

            p = [pt[1] for pt in candidate]

            # Basic corrective validation:
            # For downward correction: B must not exceed start, C must go beyond A
            if direction == "down":
                if p[2] >= p[0]:  # B exceeds start (invalid zigzag)
                    continue
                if p[3] >= p[1]:  # C doesn't go beyond A's endpoint
                    continue
            else:
                if p[2] <= p[0]:
                    continue
                if p[3] <= p[1]:
                    continue

            fib_score, fib_rels = _score_corrective_fibonacci(candidate, direction)

            if fib_score > best_score:
                best_score = fib_score
                best = {
                    "points": candidate,
                    "direction": direction,
                    "fib_score": fib_score,
                    "fib_rels": fib_rels,
                }

    return best


# ─── Current Wave Identification ────────────────────────────────────────────

def _identify_current_wave(points: list, df: pd.DataFrame, direction: str,
                           wave_type: str) -> tuple:
    """
    Determine which wave the price is currently in.

    Returns: (wave_label, progress) where progress is "early", "mid", "late"
    """
    current_price = df["close"].iloc[-1]
    last_point = points[-1]
    last_price = last_point[1]

    if wave_type == "impulse":
        # 6 points: 0=start, 1=W1end, 2=W2end, 3=W3end, 4=W4end, 5=W5end
        last_wave_idx = len(points) - 1

        if direction == "up":
            if current_price > last_price:
                # Price moved beyond last wave point — potentially in next wave
                if last_wave_idx == 5:
                    return "A", "early"  # After Wave 5, correction begins
                wave_num = str(last_wave_idx + 1)
                return wave_num, "early"
            else:
                # Price is pulling back from last wave — still in the wave or retracing
                if last_wave_idx >= 5:
                    # Correction after completed impulse
                    retrace = abs(current_price - last_price) / abs(last_price - points[-2][1]) if abs(last_price - points[-2][1]) > 0 else 0
                    progress = "early" if retrace < 0.33 else ("mid" if retrace < 0.66 else "late")
                    return "A", progress
                return str(last_wave_idx), "late"
        else:  # down
            if current_price < last_price:
                if last_wave_idx == 5:
                    return "A", "early"
                wave_num = str(last_wave_idx + 1)
                return wave_num, "early"
            else:
                if last_wave_idx >= 5:
                    retrace = abs(current_price - last_price) / abs(last_price - points[-2][1]) if abs(last_price - points[-2][1]) > 0 else 0
                    progress = "early" if retrace < 0.33 else ("mid" if retrace < 0.66 else "late")
                    return "A", progress
                return str(last_wave_idx), "late"

    else:  # corrective
        # 4 points: start, A_end, B_end, C_end
        if direction == "down":
            if current_price < last_price:
                return "C+", "late"  # Beyond C
            return "C", "late"
        else:
            if current_price > last_price:
                return "C+", "late"
            return "C", "late"

    return "?", "mid"


# ─── Wave Projections ───────────────────────────────────────────────────────

def _compute_projections(points: list, current_wave: str, direction: str,
                         wave_type: str) -> list:
    """
    Compute Fibonacci-based wave targets based on current wave position.

    Returns: list of WaveProjection
    """
    projections = []
    p = [pt[1] for pt in points]

    if wave_type == "impulse" and len(p) >= 6:
        w1_len = abs(p[1] - p[0])

        if current_wave in ("3", "4"):
            # Project Wave 5 targets from Wave 4 end
            w4_end = p[4]
            for ratio, conf in [(1.000, "high"), (0.618, "medium"), (1.618, "low")]:
                if direction == "up":
                    target = w4_end + w1_len * ratio
                else:
                    target = w4_end - w1_len * ratio
                projections.append(WaveProjection(
                    label=f"Wave 5 ({ratio:.3f}x W1)",
                    price=round(target, 2),
                    fib_ratio=ratio,
                    confidence=conf,
                ))

        elif current_wave in ("5", "A"):
            # Project corrective targets: 38.2%, 50%, 61.8% of entire impulse
            impulse_len = abs(p[5] - p[0])
            for ratio, conf in [(0.382, "high"), (0.500, "medium"), (0.618, "medium")]:
                if direction == "up":
                    target = p[5] - impulse_len * ratio
                else:
                    target = p[5] + impulse_len * ratio
                projections.append(WaveProjection(
                    label=f"Correction ({ratio:.1%} retrace)",
                    price=round(target, 2),
                    fib_ratio=ratio,
                    confidence=conf,
                ))

        elif current_wave == "2":
            # Project Wave 3 targets
            w2_end = p[2]
            for ratio, conf in [(1.618, "high"), (2.000, "medium"), (2.618, "low")]:
                if direction == "up":
                    target = w2_end + w1_len * ratio
                else:
                    target = w2_end - w1_len * ratio
                projections.append(WaveProjection(
                    label=f"Wave 3 ({ratio:.3f}x W1)",
                    price=round(target, 2),
                    fib_ratio=ratio,
                    confidence=conf,
                ))

    elif wave_type == "corrective" and len(p) >= 4:
        wa_len = abs(p[1] - p[0])
        # Project end of correction (Wave C targets)
        for ratio, conf in [(1.000, "high"), (0.618, "medium"), (1.618, "low")]:
            if direction == "down":
                target = p[2] - wa_len * ratio
            else:
                target = p[2] + wa_len * ratio
            projections.append(WaveProjection(
                label=f"Wave C ({ratio:.3f}x A)",
                price=round(target, 2),
                fib_ratio=ratio,
                confidence=conf,
            ))

    return projections


# ─── Confidence Scoring ─────────────────────────────────────────────────────

def _compute_confidence(fib_score: float, all_rules_pass: bool,
                        num_points: int, wave_type: str) -> tuple:
    """
    Compute overall confidence score.

    Returns: (confidence 0-100, label str)
    """
    # Fibonacci alignment: 50% weight
    fib_component = fib_score * settings.ELLIOTT_CONFIDENCE_FIB_WEIGHT

    # Structure clarity: 30% weight — more swing points = better defined
    structure = min(100, (num_points / 8) * 100)
    structure_component = structure * settings.ELLIOTT_CONFIDENCE_STRUCTURE_WEIGHT

    # Wave type clarity: 20% weight
    if wave_type == "impulse" and all_rules_pass:
        clarity = 100
    elif wave_type == "corrective":
        clarity = 70
    else:
        clarity = 40
    clarity_component = clarity * settings.ELLIOTT_CONFIDENCE_CLARITY_WEIGHT

    confidence = fib_component + structure_component + clarity_component
    confidence = round(min(95, confidence), 1)  # Cap at 95 — never claim certainty

    if confidence >= settings.ELLIOTT_CONFIDENCE_HIGH:
        label = "High"
    elif confidence >= settings.ELLIOTT_CONFIDENCE_MODERATE:
        label = "Moderate"
    elif confidence >= settings.ELLIOTT_CONFIDENCE_LOW:
        label = "Low"
    else:
        label = "Speculative"

    return confidence, label


# ─── Summary Generator ──────────────────────────────────────────────────────

def _generate_summary(result: ElliottWaveResult) -> str:
    """Generate a human-readable summary of the wave analysis."""
    if not result.detected:
        return "No clear Elliott Wave pattern detected in the current price structure."

    wave_desc = result.wave_type.replace("_", " ").title()
    direction = result.trend_direction

    summary = (
        f"A {direction} {wave_desc} pattern is detected with "
        f"{result.confidence_label.lower()} confidence ({result.confidence:.0f}/100). "
    )

    if result.current_wave:
        summary += (
            f"Price appears to be in Wave {result.current_wave} "
            f"({result.current_wave_progress}). "
        )

    if result.projections:
        top_proj = result.projections[0]
        summary += f"Primary target: ₹{top_proj.price:,.0f} ({top_proj.label})."

    return summary


# ─── Public Entry Point ─────────────────────────────────────────────────────

def analyze(df: pd.DataFrame, trend: str = "",
            timeframe: str = "Daily") -> ElliottWaveResult:
    """
    Run Elliott Wave analysis on OHLCV data.

    Args:
        df: DataFrame with columns: open, high, low, close, volume
        trend: Current market trend from identify_trend() ("uptrend", "downtrend", "ranging")
        timeframe: Selected timeframe for swing window override

    Returns:
        ElliottWaveResult with wave detection, validation, and projections
    """
    result = ElliottWaveResult()

    # Mandatory warnings — real money is at stake
    result.warnings = [
        "Elliott Wave counts are subjective — multiple valid counts often exist for the same data.",
        "This is automated detection. Professional wave analysts may disagree with this count.",
        "Always use stop losses. Wave counts can be invalidated by a single price bar.",
    ]

    if df.empty or len(df) < 30:
        result.summary = "Insufficient price data for Elliott Wave analysis."
        return result

    # Use timeframe-specific swing window
    swing_window = settings.ELLIOTT_SWING_WINDOW_OVERRIDES.get(
        timeframe, settings.ELLIOTT_SWING_WINDOW
    )

    # Step 1: Get swing points
    swing_highs, swing_lows = find_swing_points(df, window=swing_window)

    # Step 2: Build alternating sequence
    sequence = _build_swing_sequence(swing_highs, swing_lows)

    if len(sequence) < settings.ELLIOTT_MIN_SWING_POINTS:
        result.summary = (
            f"Only {len(sequence)} swing points detected (need at least "
            f"{settings.ELLIOTT_MIN_SWING_POINTS}). Not enough structure for wave counting."
        )
        return result

    # Step 3: Try impulse wave detection (priority)
    impulse = _find_best_impulse_count(sequence, trend)

    if impulse:
        pts = impulse["points"]
        direction = impulse["direction"]
        wave_labels = ["0", "1", "2", "3", "4", "5"]

        result.detected = True
        result.wave_type = f"impulse_{direction}"
        result.trend_direction = "bullish" if direction == "up" else "bearish"
        result.wave_points = [
            WavePoint(index=pt[0], price=pt[1], wave_label=lbl, wave_type="impulse")
            for pt, lbl in zip(pts, wave_labels)
        ]
        result.rules_validation = impulse["rules"]
        result.all_rules_pass = True
        result.fib_relationships = impulse["fib_rels"]
        result.fib_score = impulse["fib_score"]

        current_wave, progress = _identify_current_wave(
            pts, df, direction, "impulse"
        )
        result.current_wave = current_wave
        result.current_wave_progress = progress

        result.projections = _compute_projections(
            pts, current_wave, direction, "impulse"
        )

        result.confidence, result.confidence_label = _compute_confidence(
            result.fib_score, True, len(sequence), "impulse"
        )

    else:
        # Step 4: Try corrective pattern
        corrective = _find_corrective_pattern(sequence, trend)

        if corrective:
            pts = corrective["points"]
            direction = corrective["direction"]
            wave_labels = ["Start", "A", "B", "C"]

            result.detected = True
            result.wave_type = "corrective"
            result.trend_direction = "bearish" if direction == "down" else "bullish"
            result.wave_points = [
                WavePoint(index=pt[0], price=pt[1], wave_label=lbl, wave_type="corrective")
                for pt, lbl in zip(pts, wave_labels)
            ]
            result.all_rules_pass = True  # Corrective patterns don't use the 3 impulse rules
            result.fib_relationships = corrective["fib_rels"]
            result.fib_score = corrective["fib_score"]

            current_wave, progress = _identify_current_wave(
                pts, df, direction, "corrective"
            )
            result.current_wave = current_wave
            result.current_wave_progress = progress

            result.projections = _compute_projections(
                pts, current_wave, direction, "corrective"
            )

            result.confidence, result.confidence_label = _compute_confidence(
                result.fib_score, True, len(sequence), "corrective"
            )

    # Add low-confidence warning
    if result.detected and result.confidence < settings.ELLIOTT_CONFIDENCE_MODERATE:
        result.warnings.append(
            "Low confidence count — treat as speculative only. "
            "Do not base trading decisions solely on this wave count."
        )

    result.summary = _generate_summary(result)
    return result
