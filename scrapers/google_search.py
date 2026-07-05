"""
Google Search (SERP) scraper.

Fetches https://www.google.com/search?q=<query> and parses:
  - Organic results (title, URL, snippet, position)
  - People Also Ask questions
  - Related searches
"""

import re
import urllib.parse
from typing import List, Dict, Optional

from bs4 import BeautifulSoup
import engine
from models.google import SearchResult


# ── URL builder ───────────────────────────────────────────────────────────────

def _build_url(query: str, num: int = 10, lang: str = "en") -> str:
    params = urllib.parse.urlencode({
        "q":  query,
        "hl": lang,
        "gl": "us",
        "num": num,
    })
    return f"https://www.google.com/search?{params}"


# ── Organic result parsing ────────────────────────────────────────────────────

def _parse_organic(soup: BeautifulSoup) -> List[SearchResult]:
    results: List[SearchResult] = []
    position = 0

    for div in soup.select("div.g, div[data-sokoban-container]"):
        a_tag = div.find("a", href=True)
        if not a_tag:
            continue
        href = a_tag["href"]
        if not href.startswith("http") or "google.com" in href:
            continue

        h3 = div.find("h3")
        if not h3:
            continue
        title = h3.get_text(strip=True)
        if not title:
            continue

        # Snippet — try common containers
        snippet = ""
        for sel in ("[data-sncf]", ".VwiC3b", ".st", "span.aCOpRe"):
            el = div.select_one(sel)
            if el:
                snippet = el.get_text(" ", strip=True)
                break

        # Displayed URL (breadcrumb beneath title)
        displayed = ""
        cite = div.find("cite")
        if cite:
            displayed = cite.get_text(strip=True)

        position += 1
        results.append(SearchResult(
            position=position,
            title=title,
            url=href,
            snippet=snippet,
            displayed_url=displayed,
        ))

    return results


# ── People Also Ask ───────────────────────────────────────────────────────────

def _parse_paa(soup: BeautifulSoup) -> List[str]:
    questions: List[str] = []
    for el in soup.select("[data-q], .related-question-pair"):
        q = el.get("data-q") or el.get_text(strip=True)
        if q and len(q) < 200:
            questions.append(q)
    return questions[:8]


# ── Related searches ─────────────────────────────────────────────────────────

def _parse_related(soup: BeautifulSoup) -> List[str]:
    related: List[str] = []
    for a in soup.select("a[href*='search?q='] p, #brs a"):
        text = a.get_text(strip=True)
        if text and len(text) < 150:
            related.append(text)
    return list(dict.fromkeys(related))[:8]


# ── Public API ────────────────────────────────────────────────────────────────

def search(
    query: str,
    num:   int = 10,
    lang:  str = "en",
) -> Dict:
    """
    Run a Google web search and return structured results.

    Args:
        query: Search query string.
        num:   Number of organic results to request (max ~20 via URL param).
        lang:  Language code (default 'en').

    Returns:
        {
            query, organic_results, people_also_ask, related_searches,
            result_count (int)
        }
    """
    url             = _build_url(query, num=num, lang=lang)
    html, final_url = engine.fetch(url)
    soup            = BeautifulSoup(html, "lxml")

    organic  = _parse_organic(soup)
    paa      = _parse_paa(soup)
    related  = _parse_related(soup)

    return {
        "query":            query,
        "organic_results":  [r.__dict__ for r in organic],
        "people_also_ask":  paa,
        "related_searches": related,
        "result_count":     len(organic),
    }
