"""
Final Verdict Engine.
Combines fundamental, technical, and candlestick analysis into a single recommendation.
"""

from dataclasses import dataclass, field
from config import settings


@dataclass
class FinalVerdict:
    recommendation: str = "Hold"          # Strong Buy / Buy / Hold / Sell / Strong Sell
    confidence: float = 50.0              # 0-100
    composite_score: float = 50.0         # 0-100 weighted composite
    entry_price: float = 0.0
    target_price: float = 0.0
    stop_loss: float = 0.0
    timeframe: str = "Medium-term (1-6 months)"
    position_advice: str = ""             # For existing holders: Hold / Add / Exit / Partial Exit
    pnl_pct: float = 0.0                 # P&L percentage if position held
    pnl_value: float = 0.0               # P&L value if position held
    reasoning: list = field(default_factory=list)
    fundamental_verdict: str = ""
    technical_verdict: str = ""
    candlestick_verdict: str = ""


def generate_verdict(
    fundamental_result,
    technical_result,
    candlestick_score: dict,
    market_structure: dict,
    sr_levels: dict,
    current_price: float,
    user_units: float = 0,
    user_buy_price: float = 0,
    selected_timeframe: str = "Daily",
    elliott_result=None,
    advanced_levels_result=None,
) -> FinalVerdict:
    """
    Generate final Buy/Sell/Hold recommendation.

    Weighting: 45% fundamental + 30% technical + 15% candlestick + 10% advanced levels.
    """
    verdict = FinalVerdict()

    # ─── Composite Score ─────────────────────────────────────────────────
    fund_score = fundamental_result.normalized_score  # 0-100
    tech_score = technical_result.normalized_score     # 0-100

    # Candlestick score is -100 to +100, normalize to 0-100
    candle_raw = candlestick_score.get("score", 0)
    candle_score = (candle_raw + 100) / 2  # Maps [-100,100] to [0,100]

    # Advanced Levels score (0-100), default to neutral if unavailable
    adv_score = 50.0
    if advanced_levels_result and getattr(advanced_levels_result, "detected", False):
        adv_score = getattr(advanced_levels_result, "normalized_score", 50.0)

    composite = (
        fund_score * settings.WEIGHT_FUNDAMENTAL
        + tech_score * settings.WEIGHT_TECHNICAL
        + candle_score * settings.WEIGHT_CANDLESTICK
        + adv_score * getattr(settings, "WEIGHT_ADVANCED_LEVELS", 0.10)
    )
    verdict.composite_score = composite

    # ─── Recommendation ──────────────────────────────────────────────────
    if composite >= settings.VERDICT_STRONG_BUY:
        verdict.recommendation = "Strong Buy"
        verdict.confidence = min(95, composite)
    elif composite >= settings.VERDICT_BUY:
        verdict.recommendation = "Buy"
        verdict.confidence = composite
    elif composite >= settings.VERDICT_HOLD_LOW:
        verdict.recommendation = "Hold"
        verdict.confidence = 50 + abs(composite - 50)
    elif composite >= settings.VERDICT_STRONG_SELL:
        verdict.recommendation = "Sell"
        verdict.confidence = 100 - composite
    else:
        verdict.recommendation = "Strong Sell"
        verdict.confidence = min(95, 100 - composite)

    verdict.fundamental_verdict = fundamental_result.verdict
    verdict.technical_verdict = technical_result.verdict
    verdict.candlestick_verdict = candlestick_score.get("verdict", "Neutral")

    # ─── Entry / Target / Stop Loss ──────────────────────────────────────
    support_levels = sr_levels.get("support_levels", [])
    resistance_levels = sr_levels.get("resistance_levels", [])
    trend = market_structure.get("trend", "ranging")

    # Entry: nearest support level or current price with a small discount
    if support_levels:
        verdict.entry_price = support_levels[0]  # Nearest support
    else:
        verdict.entry_price = current_price * 0.98  # 2% below current

    # Target: nearest resistance or percentage-based
    if resistance_levels:
        verdict.target_price = resistance_levels[0]  # Nearest resistance
    else:
        if verdict.recommendation in ("Strong Buy", "Buy"):
            verdict.target_price = current_price * 1.15  # 15% upside
        else:
            verdict.target_price = current_price * 1.05  # 5% upside

    # Stop loss: below nearest support or percentage-based
    if len(support_levels) >= 2:
        verdict.stop_loss = support_levels[1]  # Second support level
    elif support_levels:
        verdict.stop_loss = support_levels[0] * 0.97  # 3% below first support
    else:
        verdict.stop_loss = current_price * 0.93  # 7% below current

    # ─── Timeframe — matches the user's selected chart timeframe ────────
    timeframe_map = {
        "Hourly":  "Intraday / Short-term (days to 1-2 weeks)",
        "Daily":   "Short to Medium-term (1-8 weeks)",
        "Weekly":  "Medium-term (1-6 months)",
        "Monthly": "Long-term (6+ months)",
    }
    verdict.timeframe = timeframe_map.get(selected_timeframe, "Medium-term (1-6 months)")

    # ─── Position Advice ─────────────────────────────────────────────────
    if user_units > 0 and user_buy_price > 0:
        verdict.pnl_pct = ((current_price - user_buy_price) / user_buy_price) * 100
        verdict.pnl_value = (current_price - user_buy_price) * user_units

        if verdict.recommendation in ("Strong Buy", "Buy"):
            if verdict.pnl_pct > 0:
                verdict.position_advice = "Hold & Add on dips"
            else:
                verdict.position_advice = "Average down — fundamentals support buying more"
        elif verdict.recommendation == "Hold":
            if verdict.pnl_pct > 20:
                verdict.position_advice = "Book partial profits (25-50%)"
            elif verdict.pnl_pct > 0:
                verdict.position_advice = "Hold — no strong signal to exit"
            else:
                verdict.position_advice = "Hold — wait for clearer direction"
        elif verdict.recommendation in ("Sell", "Strong Sell"):
            if verdict.pnl_pct > 0:
                verdict.position_advice = "Exit position — book profits"
            elif verdict.pnl_pct > -10:
                verdict.position_advice = "Exit position — cut losses early"
            else:
                verdict.position_advice = "Exit position — stop loss triggered"

    # ─── Reasoning ───────────────────────────────────────────────────────
    verdict.reasoning = []

    # Fundamental reasoning
    verdict.reasoning.append(
        f"Fundamental Analysis ({fund_score:.0f}/100): {fundamental_result.verdict} — {fundamental_result.summary}"
    )

    # Technical reasoning
    verdict.reasoning.append(
        f"Technical Analysis ({tech_score:.0f}/100): {technical_result.verdict} — {technical_result.summary}"
    )

    # Candlestick reasoning
    candle_exp = candlestick_score.get("explanation", "No patterns")
    verdict.reasoning.append(
        f"Candlestick Patterns: {candlestick_score.get('verdict', 'Neutral')} — {candle_exp}"
    )

    # Market structure
    verdict.reasoning.append(
        f"Market Structure: {market_structure.get('description', 'N/A')}"
    )

    # Support/Resistance context
    if support_levels:
        verdict.reasoning.append(f"Key Support: ₹{support_levels[0]:,.0f}")
    if resistance_levels:
        verdict.reasoning.append(f"Key Resistance: ₹{resistance_levels[0]:,.0f}")

    # Advanced Levels context
    if advanced_levels_result and getattr(advanced_levels_result, "detected", False):
        al_verdict = getattr(advanced_levels_result, "verdict", "Neutral")
        al_summary = getattr(advanced_levels_result, "summary", "")
        verdict.reasoning.append(
            f"Advanced Levels ({adv_score:.0f}/100): {al_verdict} — {al_summary}"
        )

    # Elliott Wave context (informational only — NOT scored)
    if elliott_result and getattr(elliott_result, "detected", False):
        if elliott_result.confidence >= 55:  # Moderate or higher
            wave_desc = elliott_result.wave_type.replace("_", " ").title()
            verdict.reasoning.append(
                f"Elliott Wave: {wave_desc} detected "
                f"(Confidence: {elliott_result.confidence:.0f}/100). "
                f"Currently in Wave {elliott_result.current_wave}. {elliott_result.summary}"
            )

    return verdict
