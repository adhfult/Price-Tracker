"""
Amazon product scraper using Playwright for reliable JS-rendered pages.

Handles:
  - Title, ASIN, price (regular / sale / Prime), original/list price, discount %
  - Prime eligibility and stock status
  - Variant groups (color, size, storage, style, etc.) with per-option ASINs
  - Polite bot-detection avoidance (stealth UA, resource blocking)
"""

import re
import time
from typing import Optional, List, Dict
from browserless import fetch_page_browserless_sync as _fetch_page_browserless_sync
from bs4 import BeautifulSoup


# ── URL utilities ─────────────────────────────────────────────────────────────

def _amazon_base(url: str) -> str:
    m = re.match(r"(https?://(?:www\.)?amazon\.[a-z.]+)", url)
    return m.group(1) if m else "https://www.amazon.com"


def normalize_amazon_url(url: str) -> str:
    """Return a clean /dp/<ASIN> URL, stripping tracking params."""
    for pattern in (
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/gp/aw/d/([A-Z0-9]{10})",
        r"[?&]ASIN=([A-Z0-9]{10})",
    ):
        m = re.search(pattern, url)
        if m:
            return f"{_amazon_base(url)}/dp/{m.group(1)}"
    return url


def is_valid_amazon_url(url: str) -> bool:
    return bool(re.match(r"https?://(?:www\.)?amazon\.[a-z.]+", url))


# ── Price parsing ─────────────────────────────────────────────────────────────

def parse_price(text: str) -> Optional[float]:
    """Convert any price string to a float, handling locale differences."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,]", "", text.strip())
    if not cleaned:
        return None

    if "." in cleaned and "," in cleaned:
        if cleaned.rindex(".") > cleaned.rindex(","):
            cleaned = cleaned.replace(",", "")           # 1,234.56
        else:
            cleaned = cleaned.replace(".", "").replace(",", ".")  # 1.234,56
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            cleaned = cleaned.replace(",", ".")          # 12,99 → 12.99
        else:
            cleaned = cleaned.replace(",", "")           # 1,234 → 1234

    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


# ── Page-level checks ─────────────────────────────────────────────────────────

def _is_captcha(soup: BeautifulSoup, url: str) -> bool:
    if any(k in url.lower() for k in ("captcha", "ap/cvf", "validatecaptcha")):
        return True
    title = soup.find("title")
    if title:
        t = title.get_text().lower()
        if any(w in t for w in ("robot", "captcha", "verify", "just a moment")):
            return True
    if soup.find("form", action=re.compile(r"captcha|validateCaptcha", re.I)):
        return True
    return False


# ── Field extractors ─────────────────────────────────────────────────────────

def _title(soup: BeautifulSoup) -> str:
    for sel in ("productTitle", "title"):
        el = soup.find(id=sel)
        if el:
            return el.get_text(strip=True)
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else "Unknown Product"


def _asin(url: str, soup: BeautifulSoup) -> str:
    m = re.search(r"/dp/([A-Z0-9]{10})", url)
    if m:
        return m.group(1)
    for attr in ({"id": "ASIN"}, {"name": "ASIN"}):
        inp = soup.find("input", attr)
        if inp:
            return inp.get("value", "")
    return ""


def _try_price_from(el) -> Optional[float]:
    """Try all known price sub-elements within a container."""
    if not el:
        return None
    # .a-offscreen gives the cleanest full price string
    off = el.find("span", {"class": "a-offscreen"})
    if off:
        p = parse_price(off.get_text())
        if p:
            return p
    # whole + fraction
    whole = el.find("span", {"class": "a-price-whole"})
    frac  = el.find("span", {"class": "a-price-fraction"})
    if whole:
        raw = whole.get_text().strip().rstrip(".,")
        if frac:
            raw += "." + frac.get_text().strip()
        p = parse_price(raw)
        if p:
            return p
    return parse_price(el.get_text())


def _current_price(soup: BeautifulSoup) -> Optional[float]:
    # Ordered list of container ids/classes to try
    for cid in (
        "corePriceDisplay_desktop_feature_div",
        "corePrice_feature_div",
        "apex_desktop",
    ):
        p = _try_price_from(soup.find(id=cid))
        if p:
            return p

    for cls in ("priceToPay", "apexPriceToPay"):
        p = _try_price_from(soup.find("span", {"class": cls}))
        if p:
            return p

    for lid in ("priceblock_saleprice", "priceblock_ourprice", "priceblock_dealprice"):
        p = _try_price_from(soup.find(id=lid))
        if p:
            return p

    # Generic fallback
    for el in soup.find_all("span", {"class": "a-price"}):
        p = _try_price_from(el)
        if p:
            return p

    return None


def _original_price(soup: BeautifulSoup) -> Optional[float]:
    for sel_id in ("listPrice", "originalPrice"):
        el = soup.find(id=sel_id)
        if el:
            p = _try_price_from(el)
            if p:
                return p

    for el in soup.find_all("span", {"class": "basisPrice"}):
        p = _try_price_from(el)
        if p:
            return p

    for el in soup.find_all("span", {"class": "a-text-strike"}):
        p = parse_price(el.get_text())
        if p:
            return p

    m = re.search(r"(?:List Price|Was):\s*[£$€¥₹]?\s*([\d,\.]+)", soup.get_text())
    if m:
        return parse_price(m.group(1))

    return None


def _prime_price(soup: BeautifulSoup) -> Optional[float]:
    """Return exclusive Prime member price if the page advertises one."""
    for sel_id in ("sns-base-price", "prime_feature_div", "primeDaySection"):
        el = soup.find(id=sel_id)
        if el:
            p = _try_price_from(el)
            if p:
                return p
    return None


def _discount_pct(soup: BeautifulSoup) -> Optional[float]:
    el = soup.find("span", {"class": "savingsPercentage"})
    if el:
        m = re.search(r"(\d+)%", el.get_text())
        if m:
            return float(m.group(1))
    # Badge-style "-20%"
    for el in soup.find_all("span", string=re.compile(r"-\s*\d+\s*%")):
        m = re.search(r"(\d+)", el.get_text())
        if m:
            return float(m.group(1))
    return None


def _prime_eligible(soup: BeautifulSoup) -> bool:
    return bool(
        soup.find("i", {"id": "isPrimeBadge"})
        or soup.find("i", {"class": re.compile(r"a-icon-prime")})
        or soup.find(id="prime_feature_div")
        or soup.find(string=re.compile(r"FREE delivery.*Prime", re.I))
    )


def _in_stock(soup: BeautifulSoup) -> bool:
    avail = soup.find(id="availability")
    if avail:
        t = avail.get_text(strip=True).lower()
        if any(w in t for w in ("out of stock", "unavailable", "currently unavailable")):
            return False
        if any(w in t for w in ("in stock", "available", "ships")):
            return True
    if soup.find("input", {"id": "add-to-cart-button"}):
        return True
    return True  # optimistic default


# ── Variant extraction ────────────────────────────────────────────────────────

def _extract_variants(soup: BeautifulSoup, base_url: str) -> List[Dict]:
    """
    Return a list of variant groups, each containing selectable options.

    Structure:
        [
            {
                "group_id":   "variation_color_name",
                "group_name": "Color",
                "options": [
                    {"name": "Midnight Black", "asin": "B0XXXXX", "url": "https://...", "available": True},
                    ...
                ]
            },
            ...
        ]
    """
    variants: List[Dict] = []
    base = _amazon_base(base_url)

    twister = (
        soup.find(id="twister")
        or soup.find(id="twister-plus-feature-div")
        or soup.find(id="twisterContainer")
        or soup.find("div", {"class": re.compile(r"\btwister\b")})
    )
    if not twister:
        return variants

    for var_div in twister.find_all("div", id=re.compile(r"^variation_")):
        group_id = var_div.get("id", "")

        # Determine human-readable group name
        label = var_div.find("label")
        if label:
            sec = label.find("span", {"class": re.compile(r"a-color-secondary|a-size")})
            group_name = (sec or label).get_text(strip=True).rstrip(":")
        else:
            raw = group_id.replace("variation_", "").replace("_name", "")
            group_name = " ".join(w.capitalize() for w in raw.split("_"))

        options: List[Dict] = []

        # ── Method 1: <li data-defaultasin="..."> buttons / swatches ──────────
        for li in var_div.find_all("li", attrs={"data-defaultasin": True}):
            asin    = li.get("data-defaultasin", "").strip()
            dp_path = li.get("data-dp-url", "").strip()

            # Resolve name: title attr → p/span/a text → img alt
            name = ""
            title_attr = li.get("title", "")
            if title_attr and not any(
                x in title_attr.lower() for x in ("click to select", "select")
            ):
                name = title_attr
            else:
                for tag in ("p", "span", "a", "img"):
                    el = li.find(tag)
                    if el:
                        name = el.get("alt", "") if tag == "img" else el.get_text(strip=True)
                        if name:
                            break

            is_disabled = "a-button-disabled" in " ".join(li.get("class", []))
            if not name or not asin:
                continue

            if dp_path.startswith("/"):
                resolved_url = base + dp_path
            elif dp_path.startswith("http"):
                resolved_url = dp_path
            else:
                resolved_url = f"{base}/dp/{asin}"

            options.append({
                "name":      name[:100],
                "asin":      asin,
                "url":       resolved_url,
                "available": not is_disabled,
            })

        # ── Method 2: native <select> dropdown ────────────────────────────────
        if not options:
            select = var_div.find("select")
            if select:
                for opt in select.find_all("option"):
                    val  = opt.get("value", "").strip()
                    name = opt.get_text(strip=True)
                    if not val or val in ("-1", ""):
                        continue
                    if any(x in name.lower() for x in ("choose", "select", "please")):
                        continue
                    is_asin = bool(re.match(r"^[A-Z0-9]{10}$", val))
                    options.append({
                        "name":      name,
                        "asin":      val if is_asin else "",
                        "url":       f"{base}/dp/{val}" if is_asin else "",
                        "available": True,
                    })

        # ── Method 3: toggle-button list (no per-option ASIN available) ───────
        if not options:
            for btn in var_div.find_all("li", {"class": re.compile(r"a-button-toggle")}):
                span = btn.find("span", {"class": re.compile(r"a-button-text")})
                if span:
                    name = span.get_text(strip=True)
                    is_disabled = "a-button-disabled" in " ".join(btn.get("class", []))
                    if name:
                        options.append({
                            "name":      name,
                            "asin":      "",
                            "url":       "",
                            "available": not is_disabled,
                        })

        if options:
            variants.append({
                "group_id":   group_id,
                "group_name": group_name,
                "options":    options,
            })

    return variants


# ── Condition / quality-tier extraction ─────────────────────────────────────

# Grades Amazon uses for Renewed / Refurbished / Used listings
_CONDITION_RE = re.compile(
    r"(Refurbished|Renewed|Used|Like New)\s*[-–]?\s*"
    r"(Excellent|Very Good|Good|Acceptable|Fair|Premium|Standard|Certified|New Surplus)?",
    re.I,
)


def _price_near(el) -> Optional[float]:
    """Walk up the DOM from `el` looking for an .a-offscreen price string."""
    node = el if hasattr(el, 'find') else el.parent
    for _ in range(6):
        if node is None:
            break
        p_el = node.find("span", {"class": "a-offscreen"})
        if p_el:
            p = parse_price(p_el.get_text())
            if p:
                return p
        node = node.parent
    return None


def _extract_condition_tiers(soup: BeautifulSoup, base_url: str) -> Optional[Dict]:
    """
    Detect refurbished / renewed / used condition-grade options on the page.
    Returns a variant-group dict (same shape as _extract_variants output)
    if any condition tiers are found, otherwise None.

    Handles three layouts Amazon uses:
      1. #renewedConditionOptions  – dedicated Renewed selector
      2. #aod-offer-list           – All-Offers Display sidebar
      3. Generic radio/button rows – any page that lists condition strings
         next to prices (e.g. refurbished-item product pages)
    """
    base    = _amazon_base(base_url)
    options: List[Dict] = []
    seen:    set         = set()

    def _add(name: str, asin: str, url: str, price: Optional[float], avail: bool = True):
        key = name.lower().strip()
        if key in seen or not name.strip():
            return
        seen.add(key)
        options.append({
            "name":      name.strip()[:120],
            "asin":      asin,
            "url":       url,
            "available": avail,
            "price":     price,       # snapshot at scrape time; used for display only
        })

    # ── Strategy 1: Amazon Renewed condition selector ──────────────────────
    for cid in (
        "renewedConditionOptions",
        "renewed_condition_feature_div",
        "usedAndNewSection",
        "olp_feature_div",
    ):
        container = soup.find(id=cid)
        if not container:
            continue
        for row in container.find_all(["li", "div", "label"]):
            text = row.get_text(" ", strip=True)
            m    = _CONDITION_RE.search(text)
            if not m:
                continue
            cname = m.group(0).strip()
            price = _price_near(row)
            # Look for a linked ASIN in this row
            asin, href = "", ""
            link = row.find("a", href=re.compile(r"/dp/[A-Z0-9]{10}"))
            if link:
                am = re.search(r"/dp/([A-Z0-9]{10})", link["href"])
                if am:
                    asin = am.group(1)
                    href = f"{base}/dp/{asin}"
            avail = "unavailable" not in text.lower() and "sold out" not in text.lower()
            _add(cname, asin, href, price, avail)
        if options:
            break

    # ── Strategy 2: All-Offers Display (AOD) sidebar ───────────────────────
    if not options:
        aod = soup.find(id="aod-offer-list") or soup.find(
            "div", {"id": re.compile(r"^aod-offer")}
        )
        if aod:
            for offer in aod.find_all("div", {"id": re.compile(r"aod-offer-\d+")}):
                text = offer.get_text(" ", strip=True)
                m    = _CONDITION_RE.search(text)
                if not m:
                    continue
                cname = m.group(0).strip()
                price = _price_near(offer)
                avail = "unavailable" not in text.lower()
                _add(cname, "", "", price, avail)

    # ── Strategy 3: Radio/button rows anywhere on page ─────────────────────
    if not options:
        # Find every text node matching the condition pattern
        for node in soup.find_all(string=_CONDITION_RE):
            cname = _CONDITION_RE.search(node).group(0).strip()
            price = _price_near(node.parent)
            # Check for a sibling / parent link → ASIN
            asin, href = "", ""
            parent = node.parent
            for _ in range(4):
                link = (parent or soup).find("a", href=re.compile(r"/dp/[A-Z0-9]{10}"))
                if link:
                    am = re.search(r"/dp/([A-Z0-9]{10})", link["href"])
                    if am:
                        asin = am.group(1)
                        href = f"{base}/dp/{asin}"
                    break
                parent = getattr(parent, "parent", None)
            container_text = (node.parent.get_text(" ", strip=True)
                              if node.parent else "")
            avail = "unavailable" not in container_text.lower()
            _add(cname, asin, href, price, avail)

    if not options:
        return None

    return {
        "group_id":   "condition_tier",
        "group_name": "Condition",
        "options":    options,
    }


def _price_for_condition(soup: BeautifulSoup, condition: str) -> Optional[float]:
    """
    Re-read the price for a specific condition label from an already-parsed page.
    Used during periodic monitoring so we track the right tier's price.
    """
    cond_re = re.compile(re.escape(condition.strip()), re.I)
    for node in soup.find_all(string=cond_re):
        price = _price_near(node.parent)
        if price:
            return price
    return None


# ── Public scraping API ───────────────────────────────────────────────────────

def _fetch_page(url: str) -> tuple:
    """Return (html_content, final_url) using Browserless.io if configured."""
    try:
        return _fetch_page_browserless_sync(url)
    except Exception as exc:
        raise ConnectionError(f"Could not load page: {exc}") from exc


def get_product_details(url: str) -> dict:
    """
    Scrape an Amazon product page and return a full details dict.

    Keys: url, normalized_url, title, asin, price, original_price,
          prime_price, discount_percent, is_prime_eligible, in_stock, variants
    """
    norm_url = normalize_amazon_url(url)
    html, final_url = _fetch_page(norm_url)
    soup = BeautifulSoup(html, "lxml")

    if _is_captcha(soup, final_url):
        raise RuntimeError(
            "Amazon is showing a CAPTCHA / bot-verification page.\n"
            "Wait a few minutes and try again. "
            "If it persists, try from a different network or VPN."
        )

    title = _title(soup)
    # Rough check that we actually landed on a product page
    if title == "Unknown Product" and not soup.find(id="dp"):
        page_title = soup.find("title")
        if page_title and "Page Not Found" in page_title.get_text():
            raise ValueError("Product page not found (404). Please check the URL.")

    variants = _extract_variants(soup, final_url)

    # Append condition/quality tiers as an extra variant group when present
    condition_group = _extract_condition_tiers(soup, final_url)
    if condition_group:
        variants.append(condition_group)

    return {
        "url":             final_url,
        "normalized_url":  norm_url,
        "title":           title,
        "asin":            _asin(final_url, soup),
        "price":           _current_price(soup),
        "original_price":  _original_price(soup),
        "prime_price":     _prime_price(soup),
        "discount_percent": _discount_pct(soup),
        "is_prime_eligible": _prime_eligible(soup),
        "in_stock":        _in_stock(soup),
        "variants":        variants,
    }


def get_current_price(url: str, condition: Optional[str] = None) -> dict:
    """
    Lightweight price-only refresh used during monitoring.

    If `condition` is given (e.g. "Refurbished - Good"), the returned `price`
    reflects that specific tier rather than the page's default buy-box price.
    Falls back to the default price when the tier cannot be located.
    """
    norm_url        = normalize_amazon_url(url)
    html, final_url = _fetch_page(norm_url)
    soup            = BeautifulSoup(html, "lxml")

    if _is_captcha(soup, final_url):
        raise RuntimeError(
            "Amazon is showing a CAPTCHA / bot-verification page.\n"
            "Wait a few minutes and try again."
        )

    price = _current_price(soup)

    # Override with condition-specific price when requested
    if condition:
        tier_price = _price_for_condition(soup, condition)
        if tier_price is not None:
            price = tier_price

    return {
        "price":            price,
        "original_price":   _original_price(soup),
        "prime_price":      _prime_price(soup),
        "discount_percent": _discount_pct(soup),
        "is_prime_eligible": _prime_eligible(soup),
        "in_stock":         _in_stock(soup),
    }
