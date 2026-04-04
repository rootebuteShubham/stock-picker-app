"""
Google Finance scraper for supplementary data: news, price, sector/industry, key stats.
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
        dict with keys: current_price, change, change_pct, news, about,
                        sector, industry, employees, key_stats
    """
    result = {
        "current_price": None,
        "change": None,
        "change_pct": None,
        "news": [],
        "about": "",
        "sector": None,
        "industry": None,
        "employees": None,
        "ceo": None,
        "headquarters": None,
        "key_stats": {},
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

        # Extract "About" section — contains description, sector, industry, employees
        _extract_about_section(soup, result)

        # Extract key stats table (P/E, dividend yield, etc.)
        _extract_key_stats(soup, result)

        # Extract news headlines
        news_items = soup.find_all("div", class_="Yfwt5")
        for item in news_items[:10]:
            headline = item.get_text(strip=True)
            if headline:
                result["news"].append(headline)

        if not result["news"]:
            for article in soup.find_all("a", {"data-article-url": True})[:10]:
                title_div = article.find("div", class_="Yfwt5")
                if title_div:
                    result["news"].append(title_div.get_text(strip=True))

    except requests.RequestException:
        pass
    except Exception:
        pass

    return result


def _extract_about_section(soup: BeautifulSoup, result: dict):
    """Extract sector, industry, employees, CEO from the About section."""
    # Description
    about_section = soup.find("div", class_="bLLb2d")
    if about_section:
        result["about"] = about_section.get_text(strip=True)

    # Google Finance shows key-value pairs in the About section
    # Look for all label-value pairs on the page
    all_text = soup.get_text(separator="\n")
    lines = [l.strip() for l in all_text.split("\n") if l.strip()]

    # Scan for known labels and grab the next line as value
    # Google Finance labels appear as "CEO\nShersingh B Khyalia\nFounded\nAug 22, 1996" etc.
    label_map = {
        "ceo": "ceo",
        "headquarters": "headquarters",
        "employees": "employees",
        "founded": "founded",
        "sector": "sector",
        "industry": "industry",
    }

    for i, line in enumerate(lines):
        lower = line.lower().strip()
        for label_key, result_key in label_map.items():
            if lower == label_key and i + 1 < len(lines):
                value = lines[i + 1].strip()
                if value and len(value) < 200 and value.lower() not in label_map:
                    if result_key == "employees":
                        try:
                            result[result_key] = int(value.replace(",", "").replace(".", ""))
                        except ValueError:
                            result[result_key] = value
                    else:
                        result[result_key] = value
                break

    # Infer sector from "About" description if not explicitly found
    if not result["sector"] and result["about"]:
        about_lower = result["about"].lower()
        sector_keywords = {
            "Utilities": ["power", "electricity", "energy company", "thermal power", "renewable energy"],
            "Technology": ["software", "technology", "it services", "consulting"],
            "Financial Services": ["bank", "financial", "insurance", "lending", "nbfc"],
            "Healthcare": ["pharma", "pharmaceutical", "hospital", "healthcare", "drug"],
            "Consumer Goods": ["fmcg", "consumer goods", "food product", "beverage"],
            "Oil & Gas": ["oil", "petroleum", "refinery", "natural gas"],
            "Automobile": ["automobile", "automotive", "car", "vehicle", "motor"],
            "Metals & Mining": ["steel", "metal", "mining", "aluminium", "copper"],
            "Cement": ["cement", "building material"],
            "Telecom": ["telecom", "telecommunication", "mobile network"],
            "Real Estate": ["real estate", "property", "construction"],
            "Retail": ["retail", "e-commerce", "supermarket"],
        }
        for sector, keywords in sector_keywords.items():
            if any(kw in about_lower for kw in keywords):
                result["sector"] = sector
                break


def _extract_key_stats(soup: BeautifulSoup, result: dict):
    """Extract key statistics table from Google Finance."""
    # Google Finance uses table-like divs for stats
    # Look for stat rows with label-value pairs
    stat_rows = soup.find_all("div", class_="gyFHrc")
    for row in stat_rows:
        label_el = row.find("div", class_="mfs7Fc")
        value_el = row.find("div", class_="P6K39c")
        if label_el and value_el:
            label = label_el.get_text(strip=True).lower()
            value = value_el.get_text(strip=True)
            result["key_stats"][label] = value

            # Parse specific stats
            if "p/e" in label and "ratio" in label:
                try:
                    result["key_stats"]["pe_ratio"] = float(value.replace(",", ""))
                except ValueError:
                    pass
            elif "dividend yield" in label:
                try:
                    result["key_stats"]["dividend_yield"] = float(value.replace("%", "").replace(",", ""))
                except ValueError:
                    pass
