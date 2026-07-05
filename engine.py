"""
Page-fetching engine for the multi-platform data API.

Auto-selects backend based on environment:
  BROWSERLESS_API_KEY set  → Browserless.io (no local Chromium needed)
  BROWSERLESS_API_KEY unset → Local Playwright (requires: playwright install chromium)

All scraper modules call engine.fetch(url) exclusively.
"""

import os
import asyncio
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────────

def _browserless_key() -> str:
    return os.getenv("BROWSERLESS_API_KEY", "").strip()


def _browserless_url() -> str:
    return os.getenv("BROWSERLESS_URL", "https://chrome.browserless.io").rstrip("/")


def using_browserless() -> bool:
    return bool(_browserless_key())


# ── Browserless backend ────────────────────────────────────────────────────────

async def _fetch_browserless(url: str) -> Tuple[str, str]:
    import httpx
    key      = _browserless_key()
    base_url = _browserless_url()

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/content?token={key}",
            json={"url": url},
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
        )

    if response.status_code != 200:
        raise ConnectionError(
            f"Browserless error {response.status_code}: {response.text[:300]}"
        )

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        data = response.json()
        return data.get("data", ""), data.get("finalUrl", url)

    return response.text, url


# ── Local Playwright backend ──────────────────────────────────────────────────

# User-agents to rotate through to reduce bot-detection likelihood
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

_ua_index = 0


def _next_ua() -> str:
    global _ua_index
    ua = _USER_AGENTS[_ua_index % len(_USER_AGENTS)]
    _ua_index += 1
    return ua


# Resource types to abort — saves bandwidth and speeds up rendering
_BLOCKED_RESOURCES = {"image", "media", "font", "stylesheet"}


def _fetch_playwright_sync(url: str) -> Tuple[str, str]:
    """Synchronous Playwright fetch using a fresh browser context per call."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx     = browser.new_context(
            user_agent=_next_ua(),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = ctx.new_page()

        # Block unnecessary resources
        def _route(route, request):
            if request.resource_type in _BLOCKED_RESOURCES:
                route.abort()
            else:
                route.continue_()

        page.route("**/*", _route)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            page.wait_for_timeout(1_500)   # let JS settle
            html      = page.content()
            final_url = page.url
        finally:
            browser.close()

    return html, final_url


# ── Public API ────────────────────────────────────────────────────────────────

def fetch(url: str) -> Tuple[str, str]:
    """
    Fetch a fully-rendered page and return (html, final_url).

    Raises:
        ConnectionError: if Browserless returns a non-200 status.
        Exception:       if Playwright fails to load the page.
    """
    if using_browserless():
        logger.debug("engine.fetch: using Browserless for %s", url)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_fetch_browserless(url))
        finally:
            loop.close()
    else:
        logger.debug("engine.fetch: using local Playwright for %s", url)
        return _fetch_playwright_sync(url)


async def fetch_async(url: str) -> Tuple[str, str]:
    """
    Async variant — use from async contexts (e.g., FastAPI endpoints).
    Offloads the synchronous Playwright call to a thread pool automatically.
    """
    if using_browserless():
        return await _fetch_browserless(url)
    else:
        return await asyncio.to_thread(_fetch_playwright_sync, url)
