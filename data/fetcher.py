"""
Unified data fetcher that orchestrates all data providers.
"""

from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from data.yfinance_provider import (
    get_stock_info,
    get_historical_data,
    get_holders,
    get_financials,
)
from data.google_finance_provider import get_google_finance_data
from data.nse_scraper import get_shareholding_pattern
from config.ticker_map import get_google_finance_symbol


@dataclass
class StockData:
    """Container for all data related to a stock."""
    ticker: str
    info: dict = field(default_factory=dict)
    history: pd.DataFrame = field(default_factory=pd.DataFrame)
    holders: dict = field(default_factory=dict)
    financials: dict = field(default_factory=dict)
    shareholding: dict = field(default_factory=dict)
    google_data: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


def fetch_all(ticker: str, period: str = "1y") -> StockData:
    """
    Fetch all available data for a stock from all providers.
    Handles failures gracefully — partial data is acceptable.
    """
    data = StockData(ticker=ticker)

    # 1. yfinance: company info & fundamentals
    try:
        data.info = get_stock_info(ticker)
    except Exception as e:
        data.errors.append(f"yfinance info: {e}")

    # 2. yfinance: historical price data
    try:
        data.history = get_historical_data(ticker, period=period)
    except Exception as e:
        data.errors.append(f"yfinance history: {e}")

    # 3. yfinance: holders
    try:
        data.holders = get_holders(ticker)
    except Exception as e:
        data.errors.append(f"yfinance holders: {e}")

    # 4. yfinance: financials
    try:
        data.financials = get_financials(ticker)
    except Exception as e:
        data.errors.append(f"yfinance financials: {e}")

    # 5. Google Finance: news & real-time price
    try:
        gf_symbol, gf_exchange = get_google_finance_symbol(ticker)
        data.google_data = get_google_finance_data(gf_symbol, gf_exchange)

        # Supplement yfinance data with Google Finance where missing
        gd = data.google_data
        if gd.get("current_price") and not data.info.get("current_price"):
            data.info["current_price"] = gd["current_price"]

        if gd.get("about") and not data.info.get("long_description"):
            data.info["long_description"] = gd["about"]

        if gd.get("sector") and data.info.get("sector") in (None, "N/A", ""):
            data.info["sector"] = gd["sector"]

        if gd.get("industry") and data.info.get("industry") in (None, "N/A", ""):
            data.info["industry"] = gd["industry"]

        if gd.get("employees") and not data.info.get("employees"):
            data.info["employees"] = gd["employees"]

        if gd.get("ceo"):
            data.info["ceo"] = gd["ceo"]
    except Exception as e:
        data.errors.append(f"Google Finance: {e}")

    # 6. NSE scraper: shareholding pattern
    try:
        symbol = ticker.replace(".NS", "").replace(".BO", "")
        data.shareholding = get_shareholding_pattern(symbol)
    except Exception as e:
        data.errors.append(f"NSE shareholding: {e}")

    # 7. Compute Beta from historical data if missing
    if not data.info.get("beta") and not data.history.empty:
        try:
            data.info["beta"] = _compute_beta(data.history, ticker)
        except Exception:
            pass

    return data


def _compute_beta(stock_history: pd.DataFrame, ticker: str) -> float:
    """Compute beta against NIFTY 50 index."""
    import yfinance as yf
    index_ticker = "^NSEI"  # NIFTY 50
    try:
        nifty = yf.Ticker(index_ticker).history(period="1y")
        if nifty.empty:
            return None
        nifty.columns = [c.lower().replace(" ", "_") for c in nifty.columns]

        stock_ret = stock_history["close"].pct_change().dropna()
        nifty_ret = nifty["close"].pct_change().dropna()

        # Align dates
        common = stock_ret.index.intersection(nifty_ret.index)
        if len(common) < 30:
            return None
        s = stock_ret.loc[common]
        n = nifty_ret.loc[common]

        covariance = np.cov(s, n)[0][1]
        variance = np.var(n)
        if variance == 0:
            return None
        return round(covariance / variance, 2)
    except Exception:
        return None
