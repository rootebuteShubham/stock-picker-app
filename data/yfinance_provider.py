"""
Primary data provider using yfinance for Indian stock market data.
Uses fast_info as fallback and computes ratios from financials when .info is throttled.
"""

import yfinance as yf
import pandas as pd
import numpy as np


def _safe_get(d, *keys):
    """Try multiple keys in a dict, return first non-None value."""
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return None


def _get_latest_value(df: pd.DataFrame, row_names: list):
    """Get the most recent value from a financial statement row (tries multiple name variants)."""
    if df.empty:
        return None
    for name in row_names:
        if name in df.index:
            vals = df.loc[name].dropna()
            if not vals.empty:
                return vals.iloc[0]
    return None


def _compute_fundamentals_from_financials(stock, history: pd.DataFrame) -> dict:
    """
    Compute fundamental metrics directly from financial statements.
    This is the fallback when .info is throttled/blocked on cloud deployments.
    """
    result = {}

    try:
        inc = stock.income_stmt
        bs = stock.balance_sheet
    except Exception:
        return result

    if inc is None or inc.empty or bs is None or bs.empty:
        return result

    current_price = history["Close"].iloc[-1] if not history.empty else None

    # Net Income
    net_income = _get_latest_value(inc, ["Net Income", "Net Income Common Stockholders"])
    prev_net_income = None
    if inc is not None and not inc.empty:
        for name in ["Net Income", "Net Income Common Stockholders"]:
            if name in inc.index:
                vals = inc.loc[name].dropna()
                if len(vals) >= 2:
                    prev_net_income = vals.iloc[1]
                    break

    # Revenue
    revenue = _get_latest_value(inc, ["Total Revenue", "Operating Revenue"])
    prev_revenue = None
    if inc is not None and not inc.empty:
        for name in ["Total Revenue", "Operating Revenue"]:
            if name in inc.index:
                vals = inc.loc[name].dropna()
                if len(vals) >= 2:
                    prev_revenue = vals.iloc[1]
                    break

    # Total Equity
    equity = _get_latest_value(bs, ["Total Stockholders Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"])

    # Total Debt
    total_debt = _get_latest_value(bs, ["Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"])

    # Total Assets
    total_assets = _get_latest_value(bs, ["Total Assets"])

    # Book Value per share
    shares = None
    try:
        fi = stock.fast_info
        shares = getattr(fi, "shares", None)
    except Exception:
        pass
    if shares is None:
        shares = _get_latest_value(bs, ["Share Issued", "Ordinary Shares Number"])

    # ─── Compute Ratios ──────────────────────────────────────────────────

    # EPS
    if net_income is not None and shares and shares > 0:
        result["eps_trailing"] = float(net_income) / float(shares)

    # P/E
    if current_price and result.get("eps_trailing") and result["eps_trailing"] > 0:
        result["trailing_pe"] = current_price / result["eps_trailing"]

    # ROE
    if net_income is not None and equity is not None and float(equity) > 0:
        result["return_on_equity"] = float(net_income) / float(equity)

    # ROA
    if net_income is not None and total_assets is not None and float(total_assets) > 0:
        result["return_on_assets"] = float(net_income) / float(total_assets)

    # Debt/Equity
    if total_debt is not None and equity is not None and float(equity) > 0:
        result["debt_to_equity"] = float(total_debt) / float(equity)

    # P/B
    if current_price and equity is not None and shares and float(shares) > 0:
        book_per_share = float(equity) / float(shares)
        if book_per_share > 0:
            result["price_to_book"] = current_price / book_per_share
            result["book_value"] = book_per_share

    # Profit Margin
    if net_income is not None and revenue is not None and float(revenue) > 0:
        result["profit_margins"] = float(net_income) / float(revenue)

    # Earnings Growth
    if net_income is not None and prev_net_income is not None and float(prev_net_income) != 0:
        result["earnings_growth"] = (float(net_income) - float(prev_net_income)) / abs(float(prev_net_income))

    # Revenue Growth
    if revenue is not None and prev_revenue is not None and float(prev_revenue) != 0:
        result["revenue_growth"] = (float(revenue) - float(prev_revenue)) / abs(float(prev_revenue))

    # Market Cap
    if current_price and shares and float(shares) > 0:
        result["market_cap"] = current_price * float(shares)

    return result


def get_stock_info(ticker: str) -> dict:
    """Fetch company info and fundamental data with multiple fallback layers."""
    stock = yf.Ticker(ticker)

    # Layer 1: Try .info (may be throttled on cloud)
    try:
        info = stock.info or {}
    except Exception:
        info = {}

    # Layer 2: Try fast_info for basic price data
    fast = {}
    try:
        fi = stock.fast_info
        fast = {
            "current_price": getattr(fi, "last_price", None),
            "previous_close": getattr(fi, "previous_close", None),
            "market_cap": getattr(fi, "market_cap", None),
            "fifty_two_week_high": getattr(fi, "year_high", None),
            "fifty_two_week_low": getattr(fi, "year_low", None),
            "currency": getattr(fi, "currency", "INR"),
        }
    except Exception:
        pass

    # Layer 3: Compute fundamentals from financial statements
    history = pd.DataFrame()
    try:
        history = stock.history(period="5d")
    except Exception:
        pass
    computed = _compute_fundamentals_from_financials(stock, history)

    # Merge: info takes priority, then computed, then fast_info
    def pick(info_key, computed_key=None, fast_key=None):
        val = info.get(info_key)
        if val is not None:
            return val
        if computed_key and computed_key in computed:
            return computed[computed_key]
        if fast_key and fast_key in fast:
            return fast[fast_key]
        return None

    return {
        "name": info.get("longName") or info.get("shortName", ticker.split(".")[0]),
        "symbol": info.get("symbol", ticker),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "market_cap": pick("marketCap", "market_cap", "market_cap"),
        "enterprise_value": info.get("enterpriseValue"),
        "current_price": _safe_get(info, "currentPrice", "regularMarketPrice") or fast.get("current_price"),
        "previous_close": info.get("previousClose") or fast.get("previous_close"),
        "open_price": _safe_get(info, "open", "regularMarketOpen"),
        "day_high": _safe_get(info, "dayHigh", "regularMarketDayHigh"),
        "day_low": _safe_get(info, "dayLow", "regularMarketDayLow"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh") or fast.get("fifty_two_week_high"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow") or fast.get("fifty_two_week_low"),
        "volume": _safe_get(info, "volume", "regularMarketVolume"),
        "avg_volume": info.get("averageVolume"),
        # Fundamental metrics — with computed fallback
        "trailing_pe": pick("trailingPE", "trailing_pe"),
        "forward_pe": info.get("forwardPE"),
        "price_to_book": pick("priceToBook", "price_to_book"),
        "book_value": pick("bookValue", "book_value"),
        "return_on_equity": pick("returnOnEquity", "return_on_equity"),
        "return_on_assets": pick("returnOnAssets", "return_on_assets"),
        "debt_to_equity": pick("debtToEquity", "debt_to_equity"),
        "current_ratio": info.get("currentRatio"),
        "quick_ratio": info.get("quickRatio"),
        "earnings_growth": pick("earningsGrowth", "earnings_growth"),
        "revenue_growth": pick("revenueGrowth", "revenue_growth"),
        "gross_margins": info.get("grossMargins"),
        "operating_margins": info.get("operatingMargins"),
        "profit_margins": pick("profitMargins", "profit_margins"),
        "dividend_yield": info.get("dividendYield"),
        "dividend_rate": info.get("dividendRate"),
        "payout_ratio": info.get("payoutRatio"),
        "beta": info.get("beta"),
        "eps_trailing": pick("trailingEps", "eps_trailing"),
        "eps_forward": info.get("forwardEps"),
        "peg_ratio": info.get("pegRatio"),
        # Description
        "long_description": info.get("longBusinessSummary", ""),
        "website": info.get("website", ""),
        "employees": info.get("fullTimeEmployees"),
        "currency": info.get("currency") or fast.get("currency", "INR"),
    }


def get_historical_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV historical price data."""
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    if df.empty:
        return pd.DataFrame()
    # Standardize column names
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    return df


def get_holders(ticker: str) -> dict:
    """Fetch major, institutional, and mutual fund holders."""
    stock = yf.Ticker(ticker)
    result = {
        "major": pd.DataFrame(),
        "institutional": pd.DataFrame(),
        "mutualfund": pd.DataFrame(),
    }
    try:
        mh = stock.major_holders
        if mh is not None and not mh.empty:
            result["major"] = mh
    except Exception:
        pass
    try:
        ih = stock.institutional_holders
        if ih is not None and not ih.empty:
            result["institutional"] = ih
    except Exception:
        pass
    try:
        mfh = stock.mutualfund_holders
        if mfh is not None and not mfh.empty:
            result["mutualfund"] = mfh
    except Exception:
        pass
    return result


def get_financials(ticker: str) -> dict:
    """Fetch income statement, balance sheet, and cash flow."""
    stock = yf.Ticker(ticker)
    result = {
        "income_stmt": pd.DataFrame(),
        "balance_sheet": pd.DataFrame(),
        "cashflow": pd.DataFrame(),
    }
    try:
        inc = stock.income_stmt
        if inc is not None and not inc.empty:
            result["income_stmt"] = inc
    except Exception:
        pass
    try:
        bs = stock.balance_sheet
        if bs is not None and not bs.empty:
            result["balance_sheet"] = bs
    except Exception:
        pass
    try:
        cf = stock.cashflow
        if cf is not None and not cf.empty:
            result["cashflow"] = cf
    except Exception:
        pass
    return result
