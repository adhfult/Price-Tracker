"""
Google News scraper.

Fetches https://news.google.com/search?q=<query> and parses:
  - Article title, source, published time, URL, snippet, thumbnail
"""

import re
import urllib.parse
from typing import List, Dict

from bs4 import BeautifulSoup
import engine
from models.google import NewsResult


# ── URL builder ───────────────────────────────────────────────────────────────

def _build_url(query: str, lang: str = "en", country: str = "US") -> str:
    params = urllib.parse.urlencode({
        "q":  query,
        "hl": lang,
        "gl": country,
        "ceid": f"{country}:{lang}",
    })
    return f"https://news.google.com/search?{params}"


# ── Article parsing ───────────────────────────────────────────────────────────

def _parse_articles(soup: BeautifulSoup) -> List[NewsResult]:
    articles: List[NewsResult] = []
    position = 0

    # Google News uses article tags
    for article in soup.find_all("article"):
        # Title — inside an <a> or <h3>/<h4>
        title = ""
        h_tag = article.find(["h3", "h4"])
        if h_tag:
            a = h_tag.find("a")
            title = (a or h_tag).get_text(strip=True)
        if not title:
            continue

        # URL — Google News uses ./articles/... relative paths
        url = ""
        a_tag = article.find("a", href=True)
        if a_tag:
            href = a_tag["href"]
            if href.startswith("./"):
                url = "https://news.google.com/" + href[2:]
            elif href.startswith("http"):
                url = href
            else:
                url = "https://news.google.com/" + href.lstrip("/")

        # Source name
        source = ""
        src_el = article.find("div", {"class": re.compile(r"vr1PYe|wEwyrc|source")})
        if not src_el:
            # Some layouts use a <time> sibling next to the source span
            src_el = article.find("span", {"class": re.compile(r"vr1PYe|source")})
        if src_el:
            source = src_el.get_text(strip=True)

        # Published time (relative string like "2 hours ago")
        published = ""
        time_el = article.find("time")
        if time_el:
            published = time_el.get("datetime", "") or time_el.get_text(strip=True)

        # Snippet — not always available on News
        snippet = ""
        snippet_el = article.find("span", {"class": re.compile(r"snippet|GI74Re")})
        if snippet_el:
            snippet = snippet_el.get_text(" ", strip=True)

        # Thumbnail
        thumb = ""
        img = article.find("img")
        if img:
            thumb = img.get("src", "") or img.get("data-src", "")

        position += 1
        articles.append(NewsResult(
            position=position,
            title=title,
            source=source,
            url=url,
            snippet=snippet,
            published=published,
            thumbnail=thumb,
        ))

    return articles


# ── Public API ────────────────────────────────────────────────────────────────

def news_search(
    query:   str,
    lang:    str = "en",
    country: str = "US",
) -> Dict:
    """
    Search Google News and return structured article results.

    Args:
        query:   News search query.
        lang:    Language code (default 'en').
        country: Two-letter country code (default 'US').

    Returns:
        { query, articles: [...], article_count }
    """
    url             = _build_url(query, lang=lang, country=country)
    html, _         = engine.fetch(url)
    soup            = BeautifulSoup(html, "lxml")
    articles        = _parse_articles(soup)

    return {
        "query":         query,
        "articles":      [a.__dict__ for a in articles],
        "article_count": len(articles),
    }
