"""eBay domain data models."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EbayListing:
    """A single eBay product listing."""
    title:           str
    url:             str
    price:           Optional[float]
    currency:        str
    condition:       str
    seller:          str
    seller_feedback: Optional[float]   # percentage, e.g. 99.8
    shipping:        str               # e.g. "Free shipping" or "$4.99"
    in_stock:        bool
    image_url:       str               = ""
    item_id:         str               = ""
    bids:            Optional[int]     = None   # None for Buy It Now listings
