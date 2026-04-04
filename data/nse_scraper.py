"""
NSE India scraper for quarterly shareholding pattern data.
"""

import requests
import time


NSE_BASE = "https://www.nseindia.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _get_nse_session() -> requests.Session:
    """Create a session with NSE cookies."""
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get(NSE_BASE, timeout=10)
        time.sleep(0.5)
    except requests.RequestException:
        pass
    return session


def get_shareholding_pattern(symbol: str) -> dict:
    """
    Fetch quarterly shareholding pattern from NSE India.

    Args:
        symbol: NSE symbol without suffix (e.g. "RELIANCE")

    Returns:
        dict with keys: promoter, fii, dii, public, promoter_pledge, quarters
    """
    result = {
        "promoter": None,
        "fii": None,
        "dii": None,
        "public": None,
        "promoter_pledge": None,
        "quarters": [],
    }

    session = _get_nse_session()

    # Try corporate shareholding API
    try:
        url = f"{NSE_BASE}/api/corporate-shareholding?symbol={symbol}"
        resp = session.get(url, timeout=10)

        if resp.status_code == 200:
            data = resp.json()

            if isinstance(data, list) and len(data) > 0:
                latest = data[0]
                shareholding = latest.get("shareholdingPatterns", [])

                for entry in shareholding:
                    category = entry.get("category", "").lower()
                    pct = entry.get("shareholding")

                    if pct is not None:
                        try:
                            pct = float(pct)
                        except (ValueError, TypeError):
                            continue

                        if "promoter" in category and "pledge" not in category:
                            result["promoter"] = pct
                        elif "fii" in category or "foreign" in category:
                            result["fii"] = pct
                        elif "dii" in category or "domestic" in category or "mutual" in category:
                            result["dii"] = pct
                        elif "public" in category:
                            result["public"] = pct

                # Try quarterly trend
                for quarter_data in data[:4]:
                    quarter_info = {
                        "quarter": quarter_data.get("quarter", ""),
                        "promoter": None,
                        "fii": None,
                        "dii": None,
                        "public": None,
                    }
                    for entry in quarter_data.get("shareholdingPatterns", []):
                        cat = entry.get("category", "").lower()
                        val = entry.get("shareholding")
                        if val is not None:
                            try:
                                val = float(val)
                            except (ValueError, TypeError):
                                continue
                            if "promoter" in cat and "pledge" not in cat:
                                quarter_info["promoter"] = val
                            elif "fii" in cat or "foreign" in cat:
                                quarter_info["fii"] = val
                            elif "dii" in cat or "domestic" in cat:
                                quarter_info["dii"] = val
                            elif "public" in cat:
                                quarter_info["public"] = val
                    result["quarters"].append(quarter_info)

    except requests.RequestException:
        pass
    except (ValueError, KeyError):
        pass

    # Try promoter pledge data
    try:
        url = f"{NSE_BASE}/api/corporate-pledgedata?symbol={symbol}"
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            pledge_data = resp.json()
            if isinstance(pledge_data, list) and len(pledge_data) > 0:
                latest_pledge = pledge_data[0]
                result["promoter_pledge"] = latest_pledge.get("percPromoterShares")
    except Exception:
        pass

    return result
