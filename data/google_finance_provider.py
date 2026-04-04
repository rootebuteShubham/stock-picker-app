"""
Google Finance scraper for supplementary data: news headlines and real-time price.
"""

import requests
from bs4 import BeautifulSoup


GOOGLE_FINANCE_URL = "https://www.google.com/finance/quote/{symbol}:{exchange}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def get_google_finance_data(symbol: str, exchange: str = "NSE") -> dict:
    """
    Scrape Google Finance for supplementary stock data.

    Args:
        symbol: Stock symbol without suffix (e.g. "RELIANCE")
        exchange: "NSE" or "BOM"

    Returns:
        dict with keys: current_price, change, change_pct, news, about
    """
    result = {
        "current_price": None,
        "change": None,
        "change_pct": None,
        "news": [],
        "about": "",
    }

    url = GOOGLE_FINANCE_URL.format(symbol=symbol, exchange=exchange)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return result

        soup = BeautifulSoup(resp.text, "lxml")

        # Extract current price
        price_el = soup.find("div", class_="YMlKec fxKbKc")
        if price_el:
            price_text = price_el.get_text(strip=True)
            price_text = price_text.replace("₹", "").replace(",", "").strip()
            try:
                result["current_price"] = float(price_text)
            except ValueError:
                pass

        # Extract price change and percentage
        change_els = soup.find_all("div", class_="JwB6zf")
        if change_els:
            for el in change_els:
                spans = el.find_all("span")
                for span in spans:
                    text = span.get_text(strip=True)
                    if text and ("+" in text or "-" in text):
                        text = text.replace("₹", "").replace(",", "").strip()
                        if "%" in text:
                            try:
                                result["change_pct"] = float(text.replace("%", "").replace("(", "").replace(")", ""))
                            except ValueError:
                                pass
                        else:
                            try:
                                result["change"] = float(text)
                            except ValueError:
                                pass

        # Extract news headlines
        news_items = soup.find_all("div", class_="Yfwt5")
        for item in news_items[:10]:
            headline = item.get_text(strip=True)
            if headline:
                result["news"].append(headline)

        # Fallback: try other news selectors
        if not result["news"]:
            for article in soup.find_all("a", {"data-article-url": True})[:10]:
                title_div = article.find("div", class_="Yfwt5")
                if title_div:
                    result["news"].append(title_div.get_text(strip=True))

        # Extract "About" description
        about_section = soup.find("div", class_="bLLb2d")
        if about_section:
            result["about"] = about_section.get_text(strip=True)

    except requests.RequestException:
        pass
    except Exception:
        pass

    return result
