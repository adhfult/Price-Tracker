"""Scrapers package — one module per supported platform."""
from scrapers.amazon         import get_product_details, get_current_price, is_valid_amazon_url, normalize_amazon_url
from scrapers.google_search  import search
from scrapers.google_shopping import shopping_search
from scrapers.google_news    import news_search
from scrapers.ebay           import get_listing
from scrapers.generic        import fetch_html

__all__ = [
    "get_product_details", "get_current_price",
    "is_valid_amazon_url", "normalize_amazon_url",
    "search", "shopping_search", "news_search",
    "get_listing", "fetch_html",
]
