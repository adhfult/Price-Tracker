"""
Generic web fetcher (Web Unblocker).

Fetches and returns the rendered HTML for any URL.
Useful for pages that require JS execution, with CAPTCHA detection
as a best-effort safety check.

No parsing is performed — the raw HTML is returned to the caller.
"""

import re
from typing import Dict

from bs4 import BeautifulSoup
import engine


# ── CAPTCHA / block detection ─────────────────────────────────────────────────

_BLOCK_PATTERNS = re.compile(
    r"captcha|cloudflare|just a moment|ddos|access denied|robot check|verify you are human",
    re.I,
)


def _is_blocked(soup: BeautifulSoup, final_url: str) -> bool:
    url_lower = final_url.lower()
    if any(k in url_lower for k in ("captcha", "challenge", "blocked")):
        return True
    title_el = soup.find("title")
    if title_el and _BLOCK_PATTERNS.search(title_el.get_text()):
        return True
    return False


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_html(url: str, include_text: bool = False) -> Dict:
    """
    Fetch and return the fully-rendered HTML for any URL.

    Args:
        url:          The URL to fetch.
        include_text: If True, also return a stripped plain-text version of the page.

    Returns:
        {
            url (str):        The final URL after any redirects.
            html (str):       Full rendered HTML.
            status (str):     'ok' | 'blocked'
            text (str|None):  Plain text content (only if include_text=True).
        }

    Raises:
        ConnectionError: If the page could not be loaded at all.
    """
    html, final_url = engine.fetch(url)
    soup            = BeautifulSoup(html, "lxml")

    blocked = _is_blocked(soup, final_url)

    result: Dict = {
        "url":    final_url,
        "html":   html,
        "status": "blocked" if blocked else "ok",
        "text":   None,
    }

    if include_text:
        # Remove script/style tags before extracting text
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        result["text"] = soup.get_text(separator=" ", strip=True)

    return result
