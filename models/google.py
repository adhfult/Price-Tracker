"""Google domain data models."""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class SearchResult:
    """A single organic result from a Google Search SERP."""
    position:  int
    title:     str
    url:       str
    snippet:   str
    displayed_url: str = ""


@dataclass
class ShoppingResult:
    """A single product card from Google Shopping."""
    position:     int
    title:        str
    price:        Optional[float]
    currency:     str
    store:        str
    rating:       Optional[float]
    reviews:      Optional[int]
    product_url:  str
    thumbnail:    str = ""


@dataclass
class NewsResult:
    """A single article from Google News."""
    position:   int
    title:      str
    source:     str
    url:        str
    snippet:    str             = ""
    published:  str             = ""
    thumbnail:  str             = ""
