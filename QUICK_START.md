# ⚡ Quick Start

Get the API and CLI running in under 5 minutes.

---

## Step 1 — Install dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2 — Set up your browser engine

You need one of these two options. Pick whichever suits you.

### Option A — Local Playwright (free, no account)

```bash
playwright install chromium
```

That's it. No API key, no account, no cost.

### Option B — Browserless.io (cloud rendering, no Chromium install)

1. Sign up at [browserless.io](https://www.browserless.io/) (free tier: 100 pages/month)
2. Copy your API key from the dashboard
3. Copy `.env.example` to `.env` and fill it in:

```env
BROWSERLESS_API_KEY=your_key_here
```

> **Which should I use?**
> Local Playwright is simpler and costs nothing. Use Browserless if you're deploying to a host that can't install Chromium (e.g. Heroku free tier), or if you'd rather not install a browser binary locally.

---

## Step 3 — Run the CLI

```bash
python main.py
```

You'll see a platform selection menu:

```
  Platform Select
  ──────────────────────────────────────────────────────────────────
  1. Amazon         — Price tracking, alerts, monitoring
  2. Google Search  — Web search results (SERP)
  3. Google Shopping— Product search & price comparison
  4. Google News    — Real-time news articles
  5. eBay           — Product listing lookup
  6. Generic Web    — Fetch rendered HTML for any URL
  7. Exit
```

Select a platform and follow the prompts. Leave any query field blank to go back to the platform menu.

**Amazon** requires a one-time setup (currency + location) the first time you select it.

---

## Step 3 (alt) — Run the API server

```bash
python -m uvicorn api:app --reload --port 8000
```

Then open **http://localhost:8000/docs** in your browser.

The Swagger UI lists every endpoint with a built-in form — no curl required.

---

## Verify everything works

```bash
# 1. Run the automated test suite (no live network calls, completes in ~1s)
python -m pytest tests/ -v

# 2. Start the API
python -m uvicorn api:app --reload --port 8000

# 3. Check which engine is active
curl http://localhost:8000/health
# Response: { "status": "ok", "engine": "playwright" | "browserless" }
```

---

## Quick endpoint reference

```bash
# Amazon — price only (~10-15s)
curl "http://localhost:8000/amazon/price?url=https://www.amazon.com/dp/B0DHJ896RY"

# Amazon — full product details (~20-30s)
curl "http://localhost:8000/amazon/product?url=https://www.amazon.com/dp/B0DHJ896RY"

# Google Search
curl "http://localhost:8000/google/search?query=best+python+libraries"

# Google Shopping
curl "http://localhost:8000/google/shopping?query=rtx+4090"

# Google News
curl "http://localhost:8000/google/news?query=AI+news+2025"

# eBay listing
curl "http://localhost:8000/ebay/product?url=https://www.ebay.com/itm/YOUR_ITEM_ID"

# Generic web fetch (any URL)
curl "http://localhost:8000/web/fetch?url=https://example.com"
```

---

## Switch storage to SQLite (optional)

SQLite enables price history tracking — every check is appended as a row rather than overwriting the last known price.

Add to your `.env`:

```env
STORAGE_BACKEND=sqlite
```

The database is created automatically at `data/tracker.db` on first run.

---

## Deploying to the cloud?

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for step-by-step instructions for Render, Railway, and Fly.io.
