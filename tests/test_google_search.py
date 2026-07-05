"""
Google Search scraper unit tests.
Engine is mocked — no live network calls.
"""

import pytest
from unittest.mock import patch

from scrapers.google_search import search, _parse_organic, _parse_paa, _parse_related
from bs4 import BeautifulSoup


MOCK_SERP_HTML = """
<html>
<body>
  <div class="g">
    <a href="https://example.com/page1"><h3>First Result Title</h3></a>
    <span class="VwiC3b">This is the snippet for result one.</span>
    <cite>example.com › page1</cite>
  </div>
  <div class="g">
    <a href="https://another.com/article"><h3>Second Result</h3></a>
    <span class="VwiC3b">Snippet for result two.</span>
    <cite>another.com</cite>
  </div>
  <div class="related-question-pair">What is the best Python library?</div>
</body>
</html>
"""


class TestGoogleSearch:
    def setup_method(self):
        self.soup = BeautifulSoup(MOCK_SERP_HTML, "lxml")

    def test_parse_organic_count(self):
        results = _parse_organic(self.soup)
        assert len(results) == 2

    def test_parse_organic_first_result(self):
        results = _parse_organic(self.soup)
        assert results[0].title == "First Result Title"
        assert results[0].url   == "https://example.com/page1"
        assert results[0].position == 1

    def test_parse_paa(self):
        questions = _parse_paa(self.soup)
        assert "What is the best Python library?" in questions

    def test_full_search_mock(self):
        with patch("scrapers.google_search.engine.fetch", return_value=(MOCK_SERP_HTML, "https://www.google.com/search?q=test")):
            result = search("test query")
        assert result["query"] == "test query"
        assert result["result_count"] == 2
        assert len(result["organic_results"]) == 2
