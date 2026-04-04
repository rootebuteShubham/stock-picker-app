"""
Technical Analysis Engine.
Computes indicators using pandas-ta and scores them on a -2 to +2 scale.
"""

from dataclasses import dataclass, field
import pandas as pd
import numpy as np

try:
    import pandas_ta as ta
except ImportError:
    ta = None

from config import settings


@dataclass
class IndicatorScore:
    name: str
    value: object
    score: int      # -2 to +2
    label: str
    explanation: str


@dataclass
class TechnicalResult:
    indicators: list = field(default_factory=list)
    total_score: int = 0
    max_possible: int = 0
    normalized_score: float = 50.0
    verdict: str = "Hold"
    summary: str = ""
    # Computed data for charting
    sma_20: pd.Series = field(default_factory=pd.Series)
    sma_50: pd.Series = field(default_factory=pd.Series)
    sma_200: pd.Series = field(default_factory=pd.Series)
    rsi: pd.Series = field(default_factory=pd.Series)
    macd_line: pd.Series = field(default_factory=pd.Series)
    macd_signal: pd.Series = field(default_factory=pd.Series)
    macd_hist: pd.Series = field(default_factory=pd.Series)
    bb_upper: pd.Series = field(default_factory=pd.Series)
    bb_middle: pd.Series = field(default_factory=pd.Series)
    bb_lower: pd.Series = field(default_factory=pd.Series)


def _compute_sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period).mean()


def _compute_ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _compute_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _compute_bollinger(close: pd.Series, period=20, std_dev=2):
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower


def _compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> pd.Series:
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr.replace(0, np.nan))

    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.rolling(window=period).mean()
    return adx


def analyze(df: pd.DataFrame) -> TechnicalResult:
    """
    Run full technical analysis on OHLCV data.

    Args:
        df: DataFrame with columns: open, high, low, close, volume

    Returns:
        TechnicalResult with scored indicators and verdict
    """
    result = TechnicalResult()

    if df.empty or len(df) < 30:
        result.summary = "Insufficient price data for technical analysis"
        return result

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(dtype=float)
    current_price = close.iloc[-1]

    # ─── Compute Indicators ──────────────────────────────────────────────
    sma_20 = _compute_sma(close, settings.SMA_SHORT)
    sma_50 = _compute_sma(close, settings.SMA_MEDIUM)
    sma_200 = _compute_sma(close, settings.SMA_LONG) if len(df) >= 200 else pd.Series(dtype=float)
    macd_line, macd_signal, macd_hist = _compute_macd(close, settings.MACD_FAST, settings.MACD_SLOW, settings.MACD_SIGNAL)
    rsi = _compute_rsi(close)
    bb_upper, bb_middle, bb_lower = _compute_bollinger(close, settings.BB_PERIOD, settings.BB_STD)
    adx = _compute_adx(high, low, close)

    # Store for charting
    result.sma_20 = sma_20
    result.sma_50 = sma_50
    result.sma_200 = sma_200
    result.rsi = rsi
    result.macd_line = macd_line
    result.macd_signal = macd_signal
    result.macd_hist = macd_hist
    result.bb_upper = bb_upper
    result.bb_middle = bb_middle
    result.bb_lower = bb_lower

    # ─── Score: Moving Average Position ──────────────────────────────────
    sma20_val = sma_20.iloc[-1] if not sma_20.empty and not pd.isna(sma_20.iloc[-1]) else None
    sma50_val = sma_50.iloc[-1] if not sma_50.empty and not pd.isna(sma_50.iloc[-1]) else None
    sma200_val = sma_200.iloc[-1] if not sma_200.empty and not pd.isna(sma_200.iloc[-1]) else None

    ma_score = 0
    ma_reasons = []
    if sma20_val and current_price > sma20_val:
        ma_score += 1
        ma_reasons.append("above SMA20")
    elif sma20_val:
        ma_score -= 1
        ma_reasons.append("below SMA20")

    if sma50_val and sma200_val:
        if sma50_val > sma200_val:
            ma_score += 1
            ma_reasons.append("Golden Cross (SMA50 > SMA200)")
        else:
            ma_score -= 1
            ma_reasons.append("Death Cross (SMA50 < SMA200)")

    ma_score = max(-2, min(2, ma_score))
    ma_label = "Bullish" if ma_score > 0 else ("Bearish" if ma_score < 0 else "Neutral")
    result.indicators.append(IndicatorScore(
        "Moving Averages", f"SMA20: {sma20_val:.2f}" if sma20_val else "N/A",
        ma_score, ma_label, f"Price {', '.join(ma_reasons)}" if ma_reasons else "Insufficient MA data"
    ))

    # ─── Score: RSI ──────────────────────────────────────────────────────
    rsi_val = rsi.iloc[-1] if not rsi.empty and not pd.isna(rsi.iloc[-1]) else None
    if rsi_val is not None:
        if rsi_val < settings.RSI_OVERSOLD:
            rsi_score = 2
            rsi_label = "Oversold"
            rsi_exp = f"RSI at {rsi_val:.1f} — oversold territory, potential reversal upward"
        elif rsi_val < 40:
            rsi_score = 1
            rsi_label = "Approaching Oversold"
            rsi_exp = f"RSI at {rsi_val:.1f} — nearing oversold levels"
        elif rsi_val <= 60:
            rsi_score = 0
            rsi_label = "Neutral"
            rsi_exp = f"RSI at {rsi_val:.1f} — neutral momentum"
        elif rsi_val < settings.RSI_OVERBOUGHT:
            rsi_score = -1
            rsi_label = "Approaching Overbought"
            rsi_exp = f"RSI at {rsi_val:.1f} — nearing overbought levels"
        else:
            rsi_score = -2
            rsi_label = "Overbought"
            rsi_exp = f"RSI at {rsi_val:.1f} — overbought territory, potential reversal downward"
        result.indicators.append(IndicatorScore("RSI (14)", f"{rsi_val:.1f}", rsi_score, rsi_label, rsi_exp))

    # ─── Score: MACD ─────────────────────────────────────────────────────
    macd_val = macd_line.iloc[-1] if not macd_line.empty and not pd.isna(macd_line.iloc[-1]) else None
    macd_sig_val = macd_signal.iloc[-1] if not macd_signal.empty and not pd.isna(macd_signal.iloc[-1]) else None
    macd_hist_val = macd_hist.iloc[-1] if not macd_hist.empty and not pd.isna(macd_hist.iloc[-1]) else None

    if macd_val is not None and macd_sig_val is not None:
        if macd_val > macd_sig_val and macd_hist_val > 0:
            macd_score = 2 if macd_val > 0 else 1
            macd_label = "Bullish"
            macd_exp = f"MACD ({macd_val:.2f}) above signal ({macd_sig_val:.2f}) — bullish momentum"
        elif macd_val < macd_sig_val and macd_hist_val < 0:
            macd_score = -2 if macd_val < 0 else -1
            macd_label = "Bearish"
            macd_exp = f"MACD ({macd_val:.2f}) below signal ({macd_sig_val:.2f}) — bearish momentum"
        else:
            macd_score = 0
            macd_label = "Neutral"
            macd_exp = f"MACD ({macd_val:.2f}) near signal ({macd_sig_val:.2f}) — momentum shifting"
        result.indicators.append(IndicatorScore("MACD", f"{macd_val:.2f}", macd_score, macd_label, macd_exp))

    # ─── Score: Bollinger Bands ──────────────────────────────────────────
    bb_up = bb_upper.iloc[-1] if not bb_upper.empty and not pd.isna(bb_upper.iloc[-1]) else None
    bb_lo = bb_lower.iloc[-1] if not bb_lower.empty and not pd.isna(bb_lower.iloc[-1]) else None
    bb_mid = bb_middle.iloc[-1] if not bb_middle.empty and not pd.isna(bb_middle.iloc[-1]) else None

    if bb_up is not None and bb_lo is not None:
        bb_width = (bb_up - bb_lo) / bb_mid if bb_mid else 0
        if current_price <= bb_lo:
            bb_score = 2
            bb_label = "Oversold"
            bb_exp = f"Price at/below lower Bollinger Band (₹{bb_lo:.2f}) — potential bounce"
        elif current_price < bb_mid:
            bb_score = 1
            bb_label = "Below Mean"
            bb_exp = f"Price below middle band — may revert to mean (₹{bb_mid:.2f})"
        elif current_price < bb_up:
            bb_score = 0
            bb_label = "Neutral"
            bb_exp = f"Price between middle and upper band — normal range"
        else:
            bb_score = -2
            bb_label = "Overbought"
            bb_exp = f"Price at/above upper Bollinger Band (₹{bb_up:.2f}) — potential pullback"
        result.indicators.append(IndicatorScore("Bollinger Bands", f"Width: {bb_width:.3f}", bb_score, bb_label, bb_exp))

    # ─── Score: ADX (Trend Strength) ─────────────────────────────────────
    adx_val = adx.iloc[-1] if not adx.empty and not pd.isna(adx.iloc[-1]) else None
    if adx_val is not None:
        if adx_val >= settings.ADX_TRENDING:
            adx_label = "Strong Trend"
            adx_exp = f"ADX at {adx_val:.1f} — strong trend in place, follow the trend"
        elif adx_val >= settings.ADX_WEAK_TREND:
            adx_label = "Moderate Trend"
            adx_exp = f"ADX at {adx_val:.1f} — moderate trend strength"
        else:
            adx_label = "Weak/Ranging"
            adx_exp = f"ADX at {adx_val:.1f} — market is ranging, avoid trend-following strategies"
        # ADX doesn't indicate direction, just strength — score 0
        result.indicators.append(IndicatorScore("ADX", f"{adx_val:.1f}", 0, adx_label, adx_exp))

    # ─── Score: Volume ───────────────────────────────────────────────────
    if not volume.empty and len(volume) >= 20:
        avg_vol = volume.rolling(20).mean().iloc[-1]
        curr_vol = volume.iloc[-1]
        if avg_vol and avg_vol > 0:
            vol_ratio = curr_vol / avg_vol
            if vol_ratio >= settings.VOLUME_SPIKE_MULTIPLIER:
                vol_score = 1 if current_price > close.iloc[-2] else -1
                vol_label = "High Volume"
                vol_exp = f"Volume {vol_ratio:.1f}x above 20-day average — confirms price move"
            else:
                vol_score = 0
                vol_label = "Normal"
                vol_exp = f"Volume at {vol_ratio:.1f}x of 20-day average — normal activity"
            result.indicators.append(IndicatorScore("Volume", f"{curr_vol:,.0f}", vol_score, vol_label, vol_exp))

    # ─── Aggregate Score ─────────────────────────────────────────────────
    scored = [i for i in result.indicators if i.label != "N/A"]
    if scored:
        result.total_score = sum(i.score for i in scored)
        result.max_possible = len(scored) * 2
        min_s = -result.max_possible
        max_s = result.max_possible
        if max_s != min_s:
            result.normalized_score = ((result.total_score - min_s) / (max_s - min_s)) * 100
        else:
            result.normalized_score = 50.0

    # Verdict
    if result.normalized_score >= settings.VERDICT_STRONG_BUY:
        result.verdict = "Strong Buy"
        result.summary = "Technical indicators are overwhelmingly bullish. Momentum, trend, and price action all point upward."
    elif result.normalized_score >= settings.VERDICT_BUY:
        result.verdict = "Buy"
        result.summary = "Technical indicators are mostly bullish. Positive momentum with supportive trend."
    elif result.normalized_score >= settings.VERDICT_HOLD_LOW:
        result.verdict = "Hold"
        result.summary = "Technical indicators are mixed. No clear directional bias."
    elif result.normalized_score >= settings.VERDICT_STRONG_SELL:
        result.verdict = "Sell"
        result.summary = "Technical indicators are mostly bearish. Negative momentum and weakening trend."
    else:
        result.verdict = "Strong Sell"
        result.summary = "Technical indicators are overwhelmingly bearish. Strong downward pressure across indicators."

    return result
