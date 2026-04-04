"""
Unified data fetcher that orchestrates all data providers.
"""

from dataclasses import dataclass, field
import pandas as pd

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
        if data.google_data.get("current_price") and not data.info.get("current_price"):
            data.info["current_price"] = data.google_data["current_price"]

        if data.google_data.get("about") and not data.info.get("long_description"):
            data.info["long_description"] = data.google_data["about"]
    except Exception as e:
        data.errors.append(f"Google Finance: {e}")

    # 6. NSE scraper: shareholding pattern
    try:
        symbol = ticker.replace(".NS", "").replace(".BO", "")
        data.shareholding = get_shareholding_pattern(symbol)
    except Exception as e:
        data.errors.append(f"NSE shareholding: {e}")

    return data
