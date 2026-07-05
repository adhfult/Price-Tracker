"""Models package — domain-split Pydantic/dataclass definitions."""
from models.amazon import TrackedItem, AlertCriteria, AlertType
from models.google import SearchResult, ShoppingResult, NewsResult
from models.ebay   import EbayListing

__all__ = [
    "TrackedItem", "AlertCriteria", "AlertType",
    "SearchResult", "ShoppingResult", "NewsResult",
    "EbayListing",
]
