"""
Amazon scraper unit tests.
Uses static mock HTML fixtures — zero live network calls.
"""

import pytest
from unittest.mock import patch
from bs4 import BeautifulSoup

# Import parser helpers directly (no engine involved)
from scrapers.amazon import (
    parse_price,
    normalize_amazon_url,
    is_valid_amazon_url,
    _title,
    _asin,
    _current_price,
    _original_price,
    _in_stock,
    _prime_eligible,
    get_product_details,
    get_current_price,
)


# ── URL utilities ─────────────────────────────────────────────────────────────

class TestUrlUtilities:
    def test_valid_amazon_url(self):
        assert is_valid_amazon_url("https://www.amazon.com/dp/B0DHJ896RY")
        assert is_valid_amazon_url("https://amazon.co.uk/dp/B0DHJ896RY")

    def test_invalid_url(self):
        assert not is_valid_amazon_url("https://ebay.com/dp/B0DHJ896RY")
        assert not is_valid_amazon_url("not-a-url")

    def test_normalize_strips_params(self):
        url = "https://www.amazon.com/Some-Product/dp/B0DHJ896RY/ref=sr_1_1?keywords=test"
        assert normalize_amazon_url(url) == "https://www.amazon.com/dp/B0DHJ896RY"

    def test_normalize_gp_product(self):
        url = "https://www.amazon.com/gp/product/B0DHJ896RY"
        assert normalize_amazon_url(url) == "https://www.amazon.com/dp/B0DHJ896RY"


# ── Price parsing ─────────────────────────────────────────────────────────────

class TestParsePricePrice:
    def test_us_format(self):
        assert parse_price("$19.99") == 19.99
        assert parse_price("1,299.00") == 1299.0

    def test_eu_format(self):
        assert parse_price("1.299,00") == 1299.0
        assert parse_price("12,99") == 12.99

    def test_none_on_empty(self):
        assert parse_price("") is None
        assert parse_price("N/A") is None


# ── HTML field extraction (mocked HTML) ──────────────────────────────────────

MOCK_PRODUCT_HTML = """
<html>
<body>
  <span id="productTitle">Test Amazon Product</span>
  <input name="ASIN" value="B0DHJ896RY" />
  <div id="corePriceDisplay_desktop_feature_div">
    <span class="a-offscreen">$29.99</span>
  </div>
  <span class="a-text-strike">$39.99</span>
  <div id="availability"><span>In Stock.</span></div>
  <i id="isPrimeBadge"></i>
</body>
</html>
"""

MOCK_OOS_HTML = """
<html>
<body>
  <span id="productTitle">Out of Stock Item</span>
  <div id="availability"><span>Currently unavailable.</span></div>
</body>
</html>
"""


class TestHtmlParsing:
    def setup_method(self):
        self.soup     = BeautifulSoup(MOCK_PRODUCT_HTML, "lxml")
        self.oos_soup = BeautifulSoup(MOCK_OOS_HTML, "lxml")

    def test_title(self):
        assert _title(self.soup) == "Test Amazon Product"

    def test_asin_from_input(self):
        assert _asin("https://www.amazon.com", self.soup) == "B0DHJ896RY"

    def test_asin_from_url(self):
        assert _asin("https://www.amazon.com/dp/B0DHJ896RY", self.soup) == "B0DHJ896RY"

    def test_current_price(self):
        assert _current_price(self.soup) == 29.99

    def test_original_price(self):
        assert _original_price(self.soup) == 39.99

    def test_in_stock_true(self):
        assert _in_stock(self.soup) is True

    def test_in_stock_false(self):
        assert _in_stock(self.oos_soup) is False

    def test_prime_eligible(self):
        assert _prime_eligible(self.soup) is True


# ── Full scrape (engine mocked) ───────────────────────────────────────────────

class TestFullScrape:
    def test_get_product_details(self):
        with patch("scrapers.amazon.engine.fetch", return_value=(MOCK_PRODUCT_HTML, "https://www.amazon.com/dp/B0DHJ896RY")):
            result = get_product_details("https://www.amazon.com/dp/B0DHJ896RY")
        assert result["title"] == "Test Amazon Product"
        assert result["asin"]  == "B0DHJ896RY"
        assert result["price"] == 29.99
        assert result["in_stock"] is True

    def test_get_current_price(self):
        with patch("scrapers.amazon.engine.fetch", return_value=(MOCK_PRODUCT_HTML, "https://www.amazon.com/dp/B0DHJ896RY")):
            result = get_current_price("https://www.amazon.com/dp/B0DHJ896RY")
        assert result["price"] == 29.99
