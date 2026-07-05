"""
API integration tests using FastAPI TestClient.
All scraper calls are mocked — no live network calls.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


# ── System endpoints ──────────────────────────────────────────────────────────

def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Open Data API"
    assert "amazon_price" in data["endpoints"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["engine"] in ("playwright", "browserless")


def test_validate_valid_url():
    r = client.get("/validate?url=https://www.amazon.com/dp/B0DHJ896RY")
    assert r.status_code == 200
    assert r.json()["valid"] is True
    assert r.json()["asin"] == "B0DHJ896RY"


def test_validate_invalid_url():
    r = client.get("/validate?url=https://ebay.com/itm/123")
    assert r.status_code == 400


# ── Amazon endpoints ──────────────────────────────────────────────────────────

MOCK_PRICE = {
    "price": 29.99, "original_price": 39.99,
    "prime_price": None, "discount_percent": 25.0,
    "is_prime_eligible": True, "in_stock": True,
}

MOCK_PRODUCT = {
    "url": "https://www.amazon.com/dp/B0DHJ896RY",
    "normalized_url": "https://www.amazon.com/dp/B0DHJ896RY",
    "title": "Test Product", "asin": "B0DHJ896RY",
    "price": 29.99, "original_price": 39.99,
    "prime_price": None, "discount_percent": 25.0,
    "is_prime_eligible": True, "in_stock": True,
    "variants": [],
}


def test_amazon_price():
    with patch("scrapers.amazon.engine.fetch") as mock_fetch:
        mock_fetch.return_value = ("<html></html>", "https://www.amazon.com/dp/B0DHJ896RY")
        with patch("scrapers.get_current_price", return_value=MOCK_PRICE):
            r = client.get("/amazon/price?url=https://www.amazon.com/dp/B0DHJ896RY")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_amazon_price_invalid_url():
    r = client.get("/amazon/price?url=https://notamazon.com/item")
    assert r.status_code == 400


def test_amazon_product_invalid_url():
    r = client.get("/amazon/product?url=https://notamazon.com/item")
    assert r.status_code == 400


# ── Google endpoints ──────────────────────────────────────────────────────────

MOCK_SEARCH = {
    "query": "python tutorial",
    "organic_results": [{"position": 1, "title": "Test", "url": "https://example.com", "snippet": "snippet", "displayed_url": "example.com"}],
    "people_also_ask": [],
    "related_searches": [],
    "result_count": 1,
}


def test_google_search():
    with patch("scrapers.search", return_value=MOCK_SEARCH):
        r = client.get("/google/search?query=python+tutorial")
    assert r.status_code == 200
    assert r.json()["data"]["result_count"] == 1


def test_google_search_missing_query():
    r = client.get("/google/search")
    assert r.status_code == 422   # Unprocessable Entity — missing required param


# ── eBay endpoints ────────────────────────────────────────────────────────────

MOCK_LISTING = {
    "title": "LEGO Set", "url": "https://www.ebay.com/itm/123",
    "price": 49.99, "currency": "USD", "condition": "New",
    "seller": "test_seller", "seller_feedback": 99.5,
    "shipping": "Free", "in_stock": True,
    "image_url": "", "item_id": "123", "bids": None,
}


def test_ebay_product():
    with patch("scrapers.get_listing", return_value=MOCK_LISTING):
        r = client.get("/ebay/product?url=https://www.ebay.com/itm/123")
    assert r.status_code == 200
    assert r.json()["data"]["price"] == 49.99


# ── Web fetch endpoint ────────────────────────────────────────────────────────

def test_web_fetch():
    mock_result = {"url": "https://example.com", "html": "<html></html>", "status": "ok", "text": None}
    with patch("scrapers.fetch_html", return_value=mock_result):
        r = client.get("/web/fetch?url=https://example.com")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"
