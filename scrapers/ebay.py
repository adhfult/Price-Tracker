"""
eBay scraper.

Parses an eBay product listing page and extracts:
  - Title, price, condition, seller, seller feedback %, shipping, stock status
  - Item ID, thumbnail, bid count (for auction listings)
"""

import re
from typing import Optional, Dict

from bs4 import BeautifulSoup
import engine
from models.ebay import EbayListing


# ── URL validation ────────────────────────────────────────────────────────────

def is_valid_ebay_url(url: str) -> bool:
    return bool(re.match(r"https?://(?:www\.)?ebay\.[a-z.]+", url))


# ── Price parsing ─────────────────────────────────────────────────────────────

def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,]", "", text.strip())
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", "")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def _detect_currency(soup: BeautifulSoup) -> str:
    """Best-effort currency detection from the page's price display."""
    price_el = soup.select_one(".x-price-primary span, #prcIsum")
    if price_el:
        text = price_el.get_text(strip=True)
        if text.startswith("£"):   return "GBP"
        if text.startswith("€"):   return "EUR"
        if text.startswith("A$"):  return "AUD"
        if text.startswith("CA$"): return "CAD"
    return "USD"


# ── Field extractors ─────────────────────────────────────────────────────────

def _title(soup: BeautifulSoup) -> str:
    el = soup.find("h1", {"class": re.compile(r"x-item-title__mainTitle|it-ttl")})
    if el:
        span = el.find("span")
        return (span or el).get_text(strip=True)
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else "Unknown Item"


def _price(soup: BeautifulSoup) -> Optional[float]:
    for sel in (
        ".x-price-primary .ux-textspans",
        "#prcIsum",
        ".notranslate[itemprop='price']",
        ".vi-price .notranslate",
    ):
        el = soup.select_one(sel)
        if el:
            p = _parse_price(el.get_text())
            if p:
                return p
    return None


def _condition(soup: BeautifulSoup) -> str:
    el = soup.select_one(".x-item-condition-text .ux-textspans, #vi-itm-cond")
    return el.get_text(strip=True) if el else "Not specified"


def _seller(soup: BeautifulSoup) -> str:
    el = soup.select_one(".x-sellercard-atf__info__about-seller a, #mbgLink a, .seller-persona a")
    return el.get_text(strip=True) if el else ""


def _seller_feedback(soup: BeautifulSoup) -> Optional[float]:
    el = soup.select_one(".x-sellercard-atf__data-item--feedback, #si-fb, .mbg-feedback")
    if el:
        m = re.search(r"([\d.]+)%", el.get_text())
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


def _shipping(soup: BeautifulSoup) -> str:
    el = soup.select_one(".ux-labels-values--shipping .ux-textspans, #fshippingCost, .vi-ship-to-cnt")
    return el.get_text(" ", strip=True) if el else ""


def _in_stock(soup: BeautifulSoup) -> bool:
    el = soup.select_one(".d-quantity__availability, #qtySubTxt, .vi-availability")
    if el:
        text = el.get_text(strip=True).lower()
        if any(w in text for w in ("sold out", "unavailable", "0 available")):
            return False
    atc = soup.find("a", {"id": re.compile(r"isCartBtn|atcBtn|btnBin")})
    return bool(atc)


def _item_id(soup: BeautifulSoup, url: str) -> str:
    m = re.search(r"/itm/(?:\S+-)?(\d{10,})", url)
    if m:
        return m.group(1)
    el = soup.find("div", {"data-itemid": True})
    if el:
        return el["data-itemid"]
    return ""


def _thumbnail(soup: BeautifulSoup) -> str:
    img = soup.select_one("#icImg, .ux-image-carousel-item img, .img img")
    if img:
        return img.get("src", "") or img.get("data-src", "")
    return ""


def _bids(soup: BeautifulSoup) -> Optional[int]:
    el = soup.select_one("#qty-test, .vi-bid-count")
    if el:
        m = re.search(r"(\d+)", el.get_text())
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_listing(url: str) -> Dict:
    """
    Scrape an eBay product listing page and return structured data.

    Args:
        url: Full eBay listing URL (e.g. https://www.ebay.com/itm/1234567890)

    Returns:
        Dict representation of EbayListing.

    Raises:
        ValueError: If the URL is not a valid eBay listing URL.
    """
    if not is_valid_ebay_url(url):
        raise ValueError("Invalid eBay URL. Must be from ebay.com or a regional eBay domain.")

    html, final_url = engine.fetch(url)
    soup            = BeautifulSoup(html, "lxml")

    listing = EbayListing(
        title           = _title(soup),
        url             = final_url,
        price           = _price(soup),
        currency        = _detect_currency(soup),
        condition       = _condition(soup),
        seller          = _seller(soup),
        seller_feedback = _seller_feedback(soup),
        shipping        = _shipping(soup),
        in_stock        = _in_stock(soup),
        image_url       = _thumbnail(soup),
        item_id         = _item_id(soup, final_url),
        bids            = _bids(soup),
    )
    return listing.__dict__
