"""
eBay scraper unit tests.
Engine is mocked — no live network calls.
"""

import pytest
from unittest.mock import patch

from scrapers.ebay import is_valid_ebay_url, get_listing, _title, _price, _condition, _in_stock
from bs4 import BeautifulSoup


MOCK_EBAY_HTML = """
<html>
<body>
  <h1 class="x-item-title__mainTitle">
    <span>LEGO Star Wars Millennium Falcon 75257</span>
  </h1>
  <div class="x-price-primary">
    <span class="ux-textspans">$149.99</span>
  </div>
  <div class="x-item-condition-text">
    <span class="ux-textspans">Brand New</span>
  </div>
  <a id="isCartBtn" href="#">Add to cart</a>
</body>
</html>
"""


class TestEbayUrlValidation:
    def test_valid_ebay_url(self):
        assert is_valid_ebay_url("https://www.ebay.com/itm/1234567890")
        assert is_valid_ebay_url("https://www.ebay.co.uk/itm/9876543210")

    def test_invalid_url(self):
        assert not is_valid_ebay_url("https://amazon.com/dp/B0DHJ896RY")
        assert not is_valid_ebay_url("not-a-url")


class TestEbayParsing:
    def setup_method(self):
        self.soup = BeautifulSoup(MOCK_EBAY_HTML, "lxml")

    def test_title(self):
        assert _title(self.soup) == "LEGO Star Wars Millennium Falcon 75257"

    def test_price(self):
        assert _price(self.soup) == 149.99

    def test_condition(self):
        assert _condition(self.soup) == "Brand New"

    def test_in_stock(self):
        assert _in_stock(self.soup) is True


class TestFullListing:
    def test_get_listing_mock(self):
        with patch("scrapers.ebay.engine.fetch", return_value=(MOCK_EBAY_HTML, "https://www.ebay.com/itm/1234567890")):
            result = get_listing("https://www.ebay.com/itm/1234567890")
        assert result["title"] == "LEGO Star Wars Millennium Falcon 75257"
        assert result["price"] == 149.99
        assert result["in_stock"] is True

    def test_get_listing_invalid_url(self):
        with pytest.raises(ValueError, match="Invalid eBay URL"):
            get_listing("https://amazon.com/dp/B0DHJ896RY")
