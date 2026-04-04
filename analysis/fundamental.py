"""
Fundamental Analysis Engine.
Scores 11 metrics on a -2 to +2 scale and produces a Buy/Sell verdict.
"""

from dataclasses import dataclass, field
from config import settings


@dataclass
class MetricScore:
    name: str
    value: object  # the raw metric value
    score: int     # -2 to +2
    label: str     # "Bullish", "Neutral", "Bearish"
    explanation: str


@dataclass
class FundamentalResult:
    metrics: list = field(default_factory=list)
    total_score: int = 0
    max_possible: int = 0
    normalized_score: float = 50.0  # 0-100 scale
    verdict: str = "Hold"
    summary: str = ""


def _score_pe(pe) -> MetricScore:
    if pe is None:
        return MetricScore("P/E Ratio", None, 0, "N/A", "P/E ratio data not available")
    if pe < 0:
        return MetricScore("P/E Ratio", pe, -1, "Caution", f"P/E is negative ({pe:.1f}), company may be loss-making")
    if pe < settings.PE_UNDERVALUED:
        return MetricScore("P/E Ratio", pe, 2, "Bullish", f"P/E of {pe:.1f} is below {settings.PE_UNDERVALUED} — stock appears undervalued")
    if pe <= settings.PE_FAIR_HIGH:
        return MetricScore("P/E Ratio", pe, 1, "Fairly Valued", f"P/E of {pe:.1f} is in fair value range ({settings.PE_FAIR_LOW}-{settings.PE_FAIR_HIGH})")
    if pe <= settings.PE_OVERVALUED:
        return MetricScore("P/E Ratio", pe, 0, "Neutral", f"P/E of {pe:.1f} is slightly elevated but not extreme")
    return MetricScore("P/E Ratio", pe, -2, "Bearish", f"P/E of {pe:.1f} is above {settings.PE_OVERVALUED} — stock appears overvalued")


def _score_pb(pb) -> MetricScore:
    if pb is None:
        return MetricScore("P/B Ratio", None, 0, "N/A", "P/B ratio data not available")
    if pb < 0:
        return MetricScore("P/B Ratio", pb, -2, "Bearish", f"Negative P/B ({pb:.2f}) — negative book value")
    if pb < settings.PB_UNDERVALUED:
        return MetricScore("P/B Ratio", pb, 2, "Bullish", f"P/B of {pb:.2f} below {settings.PB_UNDERVALUED} — trading below intrinsic value")
    if pb <= settings.PB_FAIR_HIGH:
        return MetricScore("P/B Ratio", pb, 1, "Fair", f"P/B of {pb:.2f} is in reasonable range")
    if pb <= settings.PB_OVERVALUED:
        return MetricScore("P/B Ratio", pb, -1, "Elevated", f"P/B of {pb:.2f} is above {settings.PB_FAIR_HIGH}")
    return MetricScore("P/B Ratio", pb, -2, "Bearish", f"P/B of {pb:.2f} is above {settings.PB_OVERVALUED} — significantly overvalued")


def _score_roe(roe) -> MetricScore:
    if roe is None:
        return MetricScore("ROE", None, 0, "N/A", "Return on Equity data not available")
    roe_pct = roe * 100 if abs(roe) < 1 else roe
    if roe_pct >= settings.ROE_EXCELLENT:
        return MetricScore("ROE", roe_pct, 2, "Bullish", f"ROE of {roe_pct:.1f}% is excellent (>{settings.ROE_EXCELLENT}%) — strong shareholder returns")
    if roe_pct >= settings.ROE_GOOD:
        return MetricScore("ROE", roe_pct, 1, "Good", f"ROE of {roe_pct:.1f}% is good")
    if roe_pct >= settings.ROE_POOR:
        return MetricScore("ROE", roe_pct, 0, "Neutral", f"ROE of {roe_pct:.1f}% is moderate")
    if roe_pct >= 0:
        return MetricScore("ROE", roe_pct, -1, "Weak", f"ROE of {roe_pct:.1f}% is below {settings.ROE_POOR}% — poor capital efficiency")
    return MetricScore("ROE", roe_pct, -2, "Bearish", f"ROE is negative ({roe_pct:.1f}%) — company destroying shareholder value")


def _score_debt_equity(de) -> MetricScore:
    if de is None:
        return MetricScore("Debt/Equity", None, 0, "N/A", "Debt to Equity data not available")
    de_ratio = de / 100 if de > 10 else de  # yfinance sometimes returns as percentage
    if de_ratio < 0:
        return MetricScore("Debt/Equity", de_ratio, 1, "Good", f"D/E of {de_ratio:.2f} — net cash position")
    if de_ratio <= settings.DEBT_EQUITY_SAFE:
        return MetricScore("Debt/Equity", de_ratio, 2, "Bullish", f"D/E of {de_ratio:.2f} is conservative (<{settings.DEBT_EQUITY_SAFE})")
    if de_ratio <= settings.DEBT_EQUITY_MODERATE:
        return MetricScore("Debt/Equity", de_ratio, 1, "Acceptable", f"D/E of {de_ratio:.2f} is manageable")
    if de_ratio <= settings.DEBT_EQUITY_DANGER:
        return MetricScore("Debt/Equity", de_ratio, -1, "Elevated", f"D/E of {de_ratio:.2f} is above {settings.DEBT_EQUITY_MODERATE}")
    return MetricScore("Debt/Equity", de_ratio, -2, "Bearish", f"D/E of {de_ratio:.2f} — high leverage risk")


def _score_earnings_growth(eg) -> MetricScore:
    if eg is None:
        return MetricScore("Earnings Growth", None, 0, "N/A", "Earnings growth data not available")
    eg_pct = eg * 100 if abs(eg) < 5 else eg
    if eg_pct >= settings.EARNINGS_GROWTH_STRONG:
        return MetricScore("Earnings Growth", eg_pct, 2, "Bullish", f"Earnings growth of {eg_pct:.1f}% is strong")
    if eg_pct >= settings.EARNINGS_GROWTH_MODERATE:
        return MetricScore("Earnings Growth", eg_pct, 1, "Positive", f"Earnings growth of {eg_pct:.1f}% is positive")
    if eg_pct >= -10:
        return MetricScore("Earnings Growth", eg_pct, -1, "Weak", f"Earnings declined by {abs(eg_pct):.1f}%")
    return MetricScore("Earnings Growth", eg_pct, -2, "Bearish", f"Earnings dropped {abs(eg_pct):.1f}% — significant decline")


def _score_revenue_growth(rg) -> MetricScore:
    if rg is None:
        return MetricScore("Revenue Growth", None, 0, "N/A", "Revenue growth data not available")
    rg_pct = rg * 100 if abs(rg) < 5 else rg
    if rg_pct >= settings.REVENUE_GROWTH_STRONG:
        return MetricScore("Revenue Growth", rg_pct, 2, "Bullish", f"Revenue growth of {rg_pct:.1f}% is strong")
    if rg_pct >= settings.REVENUE_GROWTH_MODERATE:
        return MetricScore("Revenue Growth", rg_pct, 1, "Positive", f"Revenue growth of {rg_pct:.1f}% is positive")
    if rg_pct >= -10:
        return MetricScore("Revenue Growth", rg_pct, -1, "Weak", f"Revenue declined by {abs(rg_pct):.1f}%")
    return MetricScore("Revenue Growth", rg_pct, -2, "Bearish", f"Revenue dropped {abs(rg_pct):.1f}% — significant concern")


def _score_promoter_holding(ph) -> MetricScore:
    if ph is None:
        return MetricScore("Promoter Holding", None, 0, "N/A", "Promoter holding data not available")
    if ph >= settings.PROMOTER_HOLDING_STRONG:
        return MetricScore("Promoter Holding", ph, 2, "Bullish", f"Promoter holding of {ph:.1f}% shows strong conviction")
    if ph >= settings.PROMOTER_HOLDING_MODERATE:
        return MetricScore("Promoter Holding", ph, 1, "Good", f"Promoter holding of {ph:.1f}% is adequate")
    if ph >= settings.PROMOTER_HOLDING_WEAK:
        return MetricScore("Promoter Holding", ph, 0, "Neutral", f"Promoter holding of {ph:.1f}% is moderate")
    return MetricScore("Promoter Holding", ph, -1, "Weak", f"Promoter holding of {ph:.1f}% is low — may indicate weak promoter commitment")


def _score_promoter_pledge(pp) -> MetricScore:
    if pp is None:
        return MetricScore("Promoter Pledge", None, 0, "N/A", "Promoter pledge data not available")
    if pp <= settings.PROMOTER_PLEDGE_SAFE:
        return MetricScore("Promoter Pledge", pp, 2, "Safe", f"Promoter pledge of {pp:.1f}% is minimal")
    if pp <= settings.PROMOTER_PLEDGE_MODERATE:
        return MetricScore("Promoter Pledge", pp, 0, "Caution", f"Promoter pledge of {pp:.1f}% — monitor closely")
    return MetricScore("Promoter Pledge", pp, -2, "Bearish", f"Promoter pledge of {pp:.1f}% is dangerously high — forced selling risk")


def _score_dividend_yield(dy) -> MetricScore:
    if dy is None:
        return MetricScore("Dividend Yield", None, 0, "N/A", "Dividend yield data not available")
    dy_pct = dy * 100 if dy < 1 else dy
    if dy_pct >= settings.DIVIDEND_YIELD_GOOD:
        return MetricScore("Dividend Yield", dy_pct, 2, "Bullish", f"Dividend yield of {dy_pct:.2f}% is attractive")
    if dy_pct >= settings.DIVIDEND_YIELD_MODERATE:
        return MetricScore("Dividend Yield", dy_pct, 1, "Good", f"Dividend yield of {dy_pct:.2f}% provides income")
    if dy_pct > 0:
        return MetricScore("Dividend Yield", dy_pct, 0, "Neutral", f"Dividend yield of {dy_pct:.2f}% is modest")
    return MetricScore("Dividend Yield", dy_pct, 0, "N/A", "No dividend — may be reinvesting for growth")


def _score_profit_margins(pm) -> MetricScore:
    if pm is None:
        return MetricScore("Profit Margins", None, 0, "N/A", "Profit margins data not available")
    pm_pct = pm * 100 if abs(pm) < 1 else pm
    if pm_pct >= 20:
        return MetricScore("Profit Margins", pm_pct, 2, "Bullish", f"Profit margin of {pm_pct:.1f}% is excellent — strong pricing power")
    if pm_pct >= 10:
        return MetricScore("Profit Margins", pm_pct, 1, "Good", f"Profit margin of {pm_pct:.1f}% is healthy")
    if pm_pct >= 5:
        return MetricScore("Profit Margins", pm_pct, 0, "Neutral", f"Profit margin of {pm_pct:.1f}% is average")
    if pm_pct >= 0:
        return MetricScore("Profit Margins", pm_pct, -1, "Thin", f"Profit margin of {pm_pct:.1f}% is thin")
    return MetricScore("Profit Margins", pm_pct, -2, "Bearish", f"Negative profit margin ({pm_pct:.1f}%) — company is losing money")


def analyze(info: dict, shareholding: dict = None) -> FundamentalResult:
    """
    Run full fundamental analysis on stock data.

    Args:
        info: dict from yfinance_provider.get_stock_info()
        shareholding: dict from nse_scraper.get_shareholding_pattern()

    Returns:
        FundamentalResult with scored metrics and verdict
    """
    result = FundamentalResult()
    shareholding = shareholding or {}

    # Score each metric
    result.metrics = [
        _score_pe(info.get("trailing_pe")),
        _score_pb(info.get("price_to_book")),
        _score_roe(info.get("return_on_equity")),
        _score_debt_equity(info.get("debt_to_equity")),
        _score_earnings_growth(info.get("earnings_growth")),
        _score_revenue_growth(info.get("revenue_growth")),
        _score_promoter_holding(shareholding.get("promoter")),
        _score_promoter_pledge(shareholding.get("promoter_pledge")),
        _score_dividend_yield(info.get("dividend_yield")),
        _score_profit_margins(info.get("profit_margins")),
    ]

    # Calculate total score
    scored_metrics = [m for m in result.metrics if m.label != "N/A"]
    if scored_metrics:
        result.total_score = sum(m.score for m in scored_metrics)
        result.max_possible = len(scored_metrics) * 2
        # Normalize to 0-100: score range is [-2*n, +2*n], map to [0, 100]
        min_score = -result.max_possible
        max_score = result.max_possible
        if max_score != min_score:
            result.normalized_score = ((result.total_score - min_score) / (max_score - min_score)) * 100
        else:
            result.normalized_score = 50.0
    else:
        result.normalized_score = 50.0

    # Determine verdict
    if result.normalized_score >= settings.VERDICT_STRONG_BUY:
        result.verdict = "Strong Buy"
        result.summary = "Fundamentals are very strong. The stock shows excellent value metrics, healthy financials, and strong growth."
    elif result.normalized_score >= settings.VERDICT_BUY:
        result.verdict = "Buy"
        result.summary = "Fundamentals are positive. The stock has good value and growth characteristics."
    elif result.normalized_score >= settings.VERDICT_HOLD_LOW:
        result.verdict = "Hold"
        result.summary = "Fundamentals are mixed. Some metrics are favorable while others raise concerns."
    elif result.normalized_score >= settings.VERDICT_STRONG_SELL:
        result.verdict = "Sell"
        result.summary = "Fundamentals are weak. Multiple metrics suggest the stock is overvalued or financially stressed."
    else:
        result.verdict = "Strong Sell"
        result.summary = "Fundamentals are very weak. Significant financial concerns across multiple metrics."

    return result
