"""
Ticker resolution: maps user input (stock name, ticker, BSE code) to yfinance ticker format.
"""

# Top NSE stocks mapped from common names to yfinance tickers
NSE_TICKER_MAP = {
    "reliance": "RELIANCE.NS",
    "reliance industries": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "tata consultancy": "TCS.NS",
    "tata consultancy services": "TCS.NS",
    "hdfc bank": "HDFCBANK.NS",
    "hdfcbank": "HDFCBANK.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "icici bank": "ICICIBANK.NS",
    "icicibank": "ICICIBANK.NS",
    "hindustan unilever": "HINDUNILVR.NS",
    "hul": "HINDUNILVR.NS",
    "hindunilvr": "HINDUNILVR.NS",
    "itc": "ITC.NS",
    "sbi": "SBIN.NS",
    "sbin": "SBIN.NS",
    "state bank": "SBIN.NS",
    "state bank of india": "SBIN.NS",
    "bharti airtel": "BHARTIARTL.NS",
    "airtel": "BHARTIARTL.NS",
    "bhartiartl": "BHARTIARTL.NS",
    "kotak mahindra": "KOTAKBANK.NS",
    "kotak bank": "KOTAKBANK.NS",
    "kotakbank": "KOTAKBANK.NS",
    "larsen": "LT.NS",
    "l&t": "LT.NS",
    "lt": "LT.NS",
    "larsen & toubro": "LT.NS",
    "axis bank": "AXISBANK.NS",
    "axisbank": "AXISBANK.NS",
    "asian paints": "ASIANPAINT.NS",
    "asianpaint": "ASIANPAINT.NS",
    "bajaj finance": "BAJFINANCE.NS",
    "bajfinance": "BAJFINANCE.NS",
    "maruti": "MARUTI.NS",
    "maruti suzuki": "MARUTI.NS",
    "wipro": "WIPRO.NS",
    "hcl tech": "HCLTECH.NS",
    "hcltech": "HCLTECH.NS",
    "hcl technologies": "HCLTECH.NS",
    "sun pharma": "SUNPHARMA.NS",
    "sunpharma": "SUNPHARMA.NS",
    "titan": "TITAN.NS",
    "titan company": "TITAN.NS",
    "tata motors": "TATAMOTORS.NS",
    "tatamotors": "TATAMOTORS.NS",
    "tata steel": "TATASTEEL.NS",
    "tatasteel": "TATASTEEL.NS",
    "ntpc": "NTPC.NS",
    "power grid": "POWERGRID.NS",
    "powergrid": "POWERGRID.NS",
    "ultra cement": "ULTRACEMCO.NS",
    "ultratech": "ULTRACEMCO.NS",
    "ultracemco": "ULTRACEMCO.NS",
    "nestle": "NESTLEIND.NS",
    "nestleind": "NESTLEIND.NS",
    "nestle india": "NESTLEIND.NS",
    "tech mahindra": "TECHM.NS",
    "techm": "TECHM.NS",
    "m&m": "M&M.NS",
    "mahindra": "M&M.NS",
    "mahindra and mahindra": "M&M.NS",
    "bajaj finserv": "BAJAJFINSV.NS",
    "bajajfinsv": "BAJAJFINSV.NS",
    "dr reddy": "DRREDDY.NS",
    "drreddy": "DRREDDY.NS",
    "dr reddys": "DRREDDY.NS",
    "indusind bank": "INDUSINDBK.NS",
    "indusindbk": "INDUSINDBK.NS",
    "coal india": "COALINDIA.NS",
    "coalindia": "COALINDIA.NS",
    "grasim": "GRASIM.NS",
    "grasim industries": "GRASIM.NS",
    "cipla": "CIPLA.NS",
    "adani enterprises": "ADANIENT.NS",
    "adanient": "ADANIENT.NS",
    "adani ports": "ADANIPORTS.NS",
    "adaniports": "ADANIPORTS.NS",
    "adani power": "ADANIPOWER.NS",
    "adanipower": "ADANIPOWER.NS",
    "adani green": "ADANIGREEN.NS",
    "adanigreen": "ADANIGREEN.NS",
    "adani green energy": "ADANIGREEN.NS",
    "adani total gas": "ATGL.NS",
    "atgl": "ATGL.NS",
    "adani wilmar": "AWL.NS",
    "awl": "AWL.NS",
    "adani energy solutions": "ADANIENSOL.NS",
    "adaniensol": "ADANIENSOL.NS",
    "britannia": "BRITANNIA.NS",
    "britannia industries": "BRITANNIA.NS",
    "divis lab": "DIVISLAB.NS",
    "divislab": "DIVISLAB.NS",
    "divis laboratories": "DIVISLAB.NS",
    "eicher motors": "EICHERMOT.NS",
    "eichermot": "EICHERMOT.NS",
    "hero motocorp": "HEROMOTOCO.NS",
    "heromotoco": "HEROMOTOCO.NS",
    "ongc": "ONGC.NS",
    "bpcl": "BPCL.NS",
    "tata consumer": "TATACONSUM.NS",
    "tataconsum": "TATACONSUM.NS",
    "apollo hospital": "APOLLOHOSP.NS",
    "apollohosp": "APOLLOHOSP.NS",
    "apollo hospitals": "APOLLOHOSP.NS",
    "sbi life": "SBILIFE.NS",
    "sbilife": "SBILIFE.NS",
    "hdfc life": "HDFCLIFE.NS",
    "hdfclife": "HDFCLIFE.NS",
    "pidilite": "PIDILITIND.NS",
    "pidilitind": "PIDILITIND.NS",
    "pidilite industries": "PIDILITIND.NS",
    "havells": "HAVELLS.NS",
    "havells india": "HAVELLS.NS",
    "dmart": "DMART.NS",
    "avenue supermarts": "DMART.NS",
    "irctc": "IRCTC.NS",
    "tata elxsi": "TATAELXSI.NS",
    "tataelxsi": "TATAELXSI.NS",
    "zomato": "ZOMATO.NS",
    "paytm": "PAYTM.NS",
    "nykaa": "NYKAA.NS",
    "policybazaar": "POLICYBZR.NS",
    "policybzr": "POLICYBZR.NS",
    "vedanta": "VEDL.NS",
    "vedl": "VEDL.NS",
    "jsw steel": "JSWSTEEL.NS",
    "jswsteel": "JSWSTEEL.NS",
    "hindalco": "HINDALCO.NS",
    "hindalco industries": "HINDALCO.NS",
    "bajaj auto": "BAJAJ-AUTO.NS",
    "bajaj-auto": "BAJAJ-AUTO.NS",
    "shriram finance": "SHRIRAMFIN.NS",
    "shriramfin": "SHRIRAMFIN.NS",
    "trent": "TRENT.NS",
    "trent limited": "TRENT.NS",
    "lici": "LICI.NS",
    "lic": "LICI.NS",
    "lic india": "LICI.NS",
    "sbi card": "SBICARD.NS",
    "sbicard": "SBICARD.NS",
    "icici prudential": "ICICIPRULI.NS",
    "icicipruli": "ICICIPRULI.NS",
    "bandhan bank": "BANDHANBNK.NS",
    "bandhanbnk": "BANDHANBNK.NS",
    "ioc": "IOC.NS",
    "indian oil": "IOC.NS",
    "indian oil corporation": "IOC.NS",
}


def resolve_ticker(user_input: str, exchange: str = "NSE") -> tuple:
    """
    Resolve user input to a yfinance ticker and display name.

    Args:
        user_input: Stock name, ticker symbol, or partial name
        exchange: "NSE" or "BSE"

    Returns:
        (yfinance_ticker, display_name)
    """
    cleaned = user_input.strip()
    if not cleaned:
        return None, None

    # If already has .NS or .BO suffix, use as-is
    upper = cleaned.upper()
    if upper.endswith(".NS") or upper.endswith(".BO"):
        symbol = upper.split(".")[0]
        return upper, symbol

    # Try lookup in our map (case-insensitive)
    lower = cleaned.lower()
    if lower in NSE_TICKER_MAP:
        ticker = NSE_TICKER_MAP[lower]
        if exchange == "BSE":
            ticker = ticker.replace(".NS", ".BO")
        symbol = ticker.split(".")[0]
        return ticker, symbol

    # Not in map — strip spaces and assume it's a raw NSE/BSE symbol
    # e.g. "Adani Power" -> "ADANIPOWER.NS"
    symbol = upper.replace(" ", "")
    suffix = ".NS" if exchange == "NSE" else ".BO"
    ticker = symbol + suffix
    return ticker, symbol


def get_google_finance_symbol(yf_ticker: str) -> tuple:
    """
    Convert yfinance ticker to Google Finance format.

    Args:
        yf_ticker: e.g. "RELIANCE.NS"

    Returns:
        (symbol, exchange) e.g. ("RELIANCE", "NSE")
    """
    if yf_ticker.endswith(".NS"):
        return yf_ticker.replace(".NS", ""), "NSE"
    elif yf_ticker.endswith(".BO"):
        return yf_ticker.replace(".BO", ""), "BOM"
    return yf_ticker, "NSE"
