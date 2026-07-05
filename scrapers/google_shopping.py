"""
Google Shopping scraper.

Fetches Google Shopping results for a product query and parses:
  - Product title, price, currency, store, rating, review count, URL
"""

import re
import urllib.parse
from typing import List, Dict, Optional

from bs4 import BeautifulSoup
import engine
from models.google import ShoppingResult

# Currency symbol → ISO code map for price extraction
_SYM_TO_CODE: Dict[str, str] = {
    "$": "USD", "£": "GBP", "€": "EUR", "¥": "JPY",
    "₹": "INR", "₩": "KRW", "A$": "AUD", "CA$": "CAD",
}


# ── URL builder ───────────────────────────────────────────────────────────────

def _build_url(query: str, country: str = "us", lang: str = "en") -> str:
    params = urllib.parse.urlencode({
        "q":   query,
        "tbm": "shop",
        "hl":  lang,
        "gl":  country,
    })
    return f"https://www.google.com/search?{params}"


# ── Price parsing ─────────────────────────────────────────────────────────────

def _extract_price(text: str) -> tuple[Optional[float], str]:
    """Return (amount, currency_code) from a price string like '$19.99'."""
    text = text.strip()
    for sym, code in _SYM_TO_CODE.items():
        if text.startswith(sym):
            raw = re.sub(r"[^\d.,]", "", text[len(sym):])
            try:
                return round(float(raw.replace(",", "")), 2), code
            except ValueError:
                pass
    # Fallback: strip all non-numeric and guess USD
    raw = re.sub(r"[^\d.,]", "", text).replace(",", "")
    try:
        return round(float(raw), 2), "USD"
    except ValueError:
        return None, "USD"


# ── Result parsing ────────────────────────────────────────────────────────────

def _parse_results(soup: BeautifulSoup) -> List[ShoppingResult]:
    results: List[ShoppingResult] = []
    position = 0

    # Google Shopping uses varying container selectors — try both
    containers = soup.select(".sh-dgr__grid-result, .u30d4, [data-docid]")

    for item in containers:
        # Title
        title_el = item.select_one("h3, .tAxDx, [aria-label]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue

        # Price
        price_el = item.select_one(".a8Pemb, .T14wmb, [data-price]")
        price_text = price_el.get_text(strip=True) if price_el else ""
        amount, currency = _extract_price(price_text)

        # Store
        store_el = item.select_one(".aULzUe, .LbUacb, .IuHnof")
        store = store_el.get_text(strip=True) if store_el else ""

        # Rating
        rating: Optional[float] = None
        rating_el = item.select_one(".QIrs8, [aria-label*='stars']")
        if rating_el:
            aria = rating_el.get("aria-label", "")
            m = re.search(r"([\d.]+)\s*star", aria, re.I)
            if m:
                try:
                    rating = float(m.group(1))
                except ValueError:
                    pass

        # Review count
        reviews: Optional[int] = None
        rev_el = item.select_one(".NzUzee, .Rsc7Yb")
        if rev_el:
            m = re.search(r"([\d,]+)", rev_el.get_text())
            if m:
                try:
                    reviews = int(m.group(1).replace(",", ""))
                except ValueError:
                    pass

        # URL — Shopping results link via redirect; extract destination
        url = ""
        a_tag = item.find("a", href=True)
        if a_tag:
            raw_href = a_tag["href"]
            if raw_href.startswith("http"):
                url = raw_href
            elif raw_href.startswith("/url?"):
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                url = parsed.get("q", [raw_href])[0]
            else:
                url = "https://www.google.com" + raw_href

        # Thumbnail
        thumb = ""
        img = item.find("img")
        if img:
            thumb = img.get("src", "") or img.get("data-src", "")

        position += 1
        results.append(ShoppingResult(
            position=position,
            title=title,
            price=amount,
            currency=currency,
            store=store,
            rating=rating,
            reviews=reviews,
            product_url=url,
            thumbnail=thumb,
        ))

    return results


# ── Public API ────────────────────────────────────────────────────────────────

def shopping_search(
    query:   str,
    country: str = "us",
    lang:    str = "en",
) -> Dict:
    """
    Run a Google Shopping search and return product cards.

    Args:
        query:   Product search query.
        country: Two-letter country code for localized results (default 'us').
        lang:    Language code (default 'en').

    Returns:
        { query, results: [...], result_count }
    """
    url             = _build_url(query, country=country, lang=lang)
    html, _         = engine.fetch(url)
    soup            = BeautifulSoup(html, "lxml")
    results         = _parse_results(soup)

    return {
        "query":        query,
        "results":      [r.__dict__ for r in results],
        "result_count": len(results),
    }
