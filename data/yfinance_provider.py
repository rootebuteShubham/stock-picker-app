"""
Primary data provider using yfinance for Indian stock market data.
"""

import yfinance as yf
import pandas as pd


def get_stock_info(ticker: str) -> dict:
    """Fetch company info and fundamental data."""
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    return {
        "name": info.get("longName") or info.get("shortName", ticker.split(".")[0]),
        "symbol": info.get("symbol", ticker),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "previous_close": info.get("previousClose"),
        "open_price": info.get("open") or info.get("regularMarketOpen"),
        "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
        "day_low": info.get("dayLow") or info.get("regularMarketDayLow"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "volume": info.get("volume") or info.get("regularMarketVolume"),
        "avg_volume": info.get("averageVolume"),
        # Fundamental metrics
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "price_to_book": info.get("priceToBook"),
        "book_value": info.get("bookValue"),
        "return_on_equity": info.get("returnOnEquity"),
        "return_on_assets": info.get("returnOnAssets"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "quick_ratio": info.get("quickRatio"),
        "earnings_growth": info.get("earningsGrowth"),
        "revenue_growth": info.get("revenueGrowth"),
        "gross_margins": info.get("grossMargins"),
        "operating_margins": info.get("operatingMargins"),
        "profit_margins": info.get("profitMargins"),
        "dividend_yield": info.get("dividendYield"),
        "dividend_rate": info.get("dividendRate"),
        "payout_ratio": info.get("payoutRatio"),
        "beta": info.get("beta"),
        "eps_trailing": info.get("trailingEps"),
        "eps_forward": info.get("forwardEps"),
        "peg_ratio": info.get("pegRatio"),
        # Description
        "long_description": info.get("longBusinessSummary", ""),
        "website": info.get("website", ""),
        "employees": info.get("fullTimeEmployees"),
        "currency": info.get("currency", "INR"),
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
