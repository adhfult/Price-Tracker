"""
Browserless.io integration for cloud-based Playwright.

When deployed to PythonAnywhere or other cloud platforms that don't support
local Playwright/Chromium, use Browserless.io instead.

Setup:
1. Sign up at https://www.browserless.io/
2. Get your API key from the dashboard
3. Set environment variable: BROWSERLESS_API_KEY=your_api_key
4. Uncomment the import in scraper.py to enable this module

Cost: ~$0.02-0.05 per 1000 pages (pay-as-you-go)
Alternative: Bright Data, Apify, Scrapinghub
"""

import os
import httpx
from typing import Tuple

def _browserless_api_key() -> str:
    return os.getenv("BROWSERLESS_API_KEY", "").strip()


def _browserless_url() -> str:
    return os.getenv("BROWSERLESS_URL", "https://chrome.browserless.io").rstrip("/")


async def fetch_page_browserless(url: str) -> Tuple[str, str]:
    """
    Fetch and render a page using Browserless.io API.
    
    Args:
        url: The URL to fetch
        
    Returns:
        (html_content, final_url)
    """
    key = _browserless_api_key()
    if not key:
        raise ValueError(
            "BROWSERLESS_API_KEY not set. Get it from https://www.browserless.io/"
        )
    base_url = _browserless_url()

    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "url": url,
            "gotoOptions": {"waitUntil": "networkidle2"},
            "stealth": True,
        }

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }

        response = await client.post(
            f"{base_url}/content?token={key}",
            json=payload,
            headers=headers,
        )
        
        if response.status_code != 200:
            raise Exception(f"Browserless error: {response.text}")

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            return data.get("data", ""), data.get("finalUrl", url)

        return response.text, url


# For synchronous usage (wrapper around async)
def fetch_page_browserless_sync(url: str) -> Tuple[str, str]:
    """Synchronous wrapper for async Browserless fetch."""
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(fetch_page_browserless(url))
    finally:
        loop.close()


# Environment setup helper
def setup_browserless():
    """
    Interactive setup for Browserless.io.
    Run this once to configure your environment.
    """
    print("\n" + "="*70)
    print("  Browserless.io Setup")
    print("="*70)
    print("""
1. Go to https://www.browserless.io/
2. Sign up (free tier: 100 pages/month)
3. Copy your API key from the dashboard
4. Set it as an environment variable:

   On Windows (PowerShell):
   $env:BROWSERLESS_API_KEY = "your_api_key_here"
   
   On Windows (Command Prompt):
   set BROWSERLESS_API_KEY=your_api_key_here
   
   On Linux/Mac:
   export BROWSERLESS_API_KEY=your_api_key_here
   
   Or in your .env file:
   BROWSERLESS_API_KEY=your_api_key_here

Then run: python -c "from browserless import setup_browserless; setup_browserless()"
    """)
    
    api_key = input("\nEnter your Browserless API key (or press Enter to skip): ").strip()
    
    if api_key:
        os.environ["BROWSERLESS_API_KEY"] = api_key
        # Test the connection
        try:
            test_url = "https://www.amazon.com"
            print(f"\nTesting connection with: {test_url}")
            html, final_url = fetch_page_browserless_sync(test_url)
            print(f"✓ Success! Got {len(html)} bytes")
            print(f"✓ Final URL: {final_url}")
        except Exception as e:
            print(f"✗ Error: {e}")
    else:
        print("\nSetup skipped. You can run this again later.")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    setup_browserless()
