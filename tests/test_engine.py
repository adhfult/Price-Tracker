"""
Tests for engine.py — verifies correct backend routing.
No live network calls: engine.fetch() is mocked in both cases.
"""

import os
import pytest
from unittest.mock import patch, MagicMock


# ── Fixture: fake HTML ────────────────────────────────────────────────────────

FAKE_HTML = "<html><body><h1>Test Page</h1></body></html>"
FAKE_URL  = "https://example.com"


# ── Browserless routing ───────────────────────────────────────────────────────

def test_using_browserless_true(monkeypatch):
    monkeypatch.setenv("BROWSERLESS_API_KEY", "test-key-123")
    import importlib, engine
    importlib.reload(engine)
    assert engine.using_browserless() is True


def test_using_browserless_false(monkeypatch):
    monkeypatch.delenv("BROWSERLESS_API_KEY", raising=False)
    import importlib, engine
    importlib.reload(engine)
    assert engine.using_browserless() is False


def test_fetch_routes_to_browserless(monkeypatch):
    """When BROWSERLESS_API_KEY is set, fetch() must call the async browserless path."""
    monkeypatch.setenv("BROWSERLESS_API_KEY", "test-key-123")
    import importlib, engine
    importlib.reload(engine)

    with patch.object(engine, "_fetch_browserless", return_value=(FAKE_HTML, FAKE_URL)) as mock_bl:
        # Wrap async mock so the sync loop can call it
        import asyncio
        async def fake_bl(url):
            return FAKE_HTML, FAKE_URL
        mock_bl.side_effect = None
        with patch.object(engine, "_fetch_browserless", side_effect=fake_bl):
            html, url = engine.fetch(FAKE_URL)

    assert html == FAKE_HTML
    assert url  == FAKE_URL


def test_fetch_routes_to_playwright(monkeypatch):
    """When no API key, fetch() must call the local Playwright path."""
    monkeypatch.delenv("BROWSERLESS_API_KEY", raising=False)
    import importlib, engine
    importlib.reload(engine)

    with patch.object(engine, "_fetch_playwright_sync", return_value=(FAKE_HTML, FAKE_URL)) as mock_pw:
        html, url = engine.fetch(FAKE_URL)
        mock_pw.assert_called_once_with(FAKE_URL)

    assert html == FAKE_HTML
    assert url  == FAKE_URL
