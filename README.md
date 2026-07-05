# Open Data API

An open-source, multi-platform web data extraction API and CLI tool.

Scrapes real-time data from Amazon, Google Search, Google Shopping, Google News, eBay, and any generic URL — all through a single FastAPI server or an interactive terminal interface.

**Status:** ✅ CLI working | ✅ API working | ✅ 44/44 tests passing

---

## 🌐 What it does

| Platform | Data |
|---|---|
| **Amazon** | Price, Prime price, original price, discount %, stock, variants, condition tiers |
| **Google Search** | Organic results, People Also Ask, related searches |
| **Google Shopping** | Product cards, prices, stores, ratings, reviews |
| **Google News** | Articles, sources, published times, thumbnails |
| **eBay** | Title, price, condition, seller, shipping, stock, bid count |
| **Generic Web** | Fully rendered HTML + optional plain-text for any URL |

---

## 🔧 How it works

### Two modes

**CLI mode** (`main.py`) — interactive terminal tool. Select a platform, enter a query or URL, get formatted results. Includes full Amazon price tracking with persistent monitoring and alerts.

**API mode** (`api.py`) — FastAPI server. Self-hostable REST endpoints, browsable at `/docs`.

### Two browser engines

The engine is selected automatically based on your `.env`:

```
BROWSERLESS_API_KEY set?
    YES → Browserless.io (no local Chromium needed)
    NO  → Local Playwright (free, requires: playwright install chromium)
```

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up browser engine (choose one)
playwright install chromium          # Option A: local, free
# OR: set BROWSERLESS_API_KEY in .env  # Option B: Browserless.io

# 3a. Run the CLI
python main.py

# 3b. OR run the API
python -m uvicorn api:app --reload --port 8000
# Open: http://localhost:8000/docs
```

See [QUICK_START.md](QUICK_START.md) for a full setup walkthrough and [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for hosting on Render, Railway, or Fly.io.

---

## 📂 Project Structure

```
Price Tracker/
│
├── engine.py               # Central fetch layer (Playwright ↔ Browserless)
├── api.py                  # FastAPI server — all endpoints
├── main.py                 # Interactive CLI
├── storage.py              # JSON or SQLite persistence
├── notifier.py             # Desktop alerts + console output
│
├── scrapers/               # One module per platform
│   ├── amazon.py
│   ├── google_search.py
│   ├── google_shopping.py
│   ├── google_news.py
│   ├── ebay.py
│   └── generic.py
│
├── models/                 # Domain-split data models
│   ├── amazon.py
│   ├── google.py
│   └── ebay.py
│
├── tests/                  # pytest test suite (44 tests)
│   ├── test_engine.py
│   ├── test_amazon.py
│   ├── test_google_search.py
│   ├── test_ebay.py
│   └── test_api.py
│
├── data/                   # Runtime storage (git-ignored)
│   ├── config.json
│   ├── items.json
│   └── tracker.db          # (only if STORAGE_BACKEND=sqlite)
│
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 📋 API Endpoints

All endpoints return `{ "status": "ok", "data": {...}, "timestamp": "..." }`.

### Amazon
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/amazon/price?url=` | Price + stock (fast, ~10-15s) |
| `GET` | `/amazon/product?url=` | Full details + variants (~20-30s) |
| `POST` | `/amazon/items` | Add product to tracking list |
| `GET` | `/amazon/items` | List all tracked products |
| `POST` | `/amazon/items/{id}/check` | Refresh price for one item |
| `POST` | `/amazon/monitor/check-all` | Refresh all tracked items |

### Google
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/google/search?query=` | Web search (organic + PAA) |
| `GET` | `/google/shopping?query=` | Product search + prices |
| `GET` | `/google/news?query=` | News articles |

### eBay
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/ebay/product?url=` | Listing details |

### Web
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/web/fetch?url=` | Rendered HTML for any URL |

### System
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Status + active engine |
| `GET` | `/validate?url=` | Amazon URL validator |
| `GET` | `/docs` | Swagger UI |

---

## 🛠️ Configuration

Copy `.env.example` to `.env`:

```env
# Leave blank for local Playwright, or set for Browserless.io
BROWSERLESS_API_KEY=

# Optional: self-hosted Browserless endpoint
BROWSERLESS_URL=https://chrome.browserless.io

# API port
PORT=8000

# Storage: "json" (default) or "sqlite" (enables price history)
STORAGE_BACKEND=json
```

---

## 🗄️ Storage

| Backend | Config | Features |
|---|---|---|
| JSON (default) | `STORAGE_BACKEND=json` | Zero config, human-readable files |
| SQLite | `STORAGE_BACKEND=sqlite` | Price history tracking, concurrent-safe |

SQLite adds a `price_history` table — every price check is appended as a row, enabling historical data queries.

---

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

44 tests covering engine routing, Amazon parsing, Google Search parsing, eBay parsing, and all API endpoints. All tests run with mocked HTML — no live network calls required.

---

## 🚀 Deployment

Works on any host that supports Python. Free tiers available on:
- [Render](https://render.com) — add `playwright install chromium` as a build command
- [Railway](https://railway.app)
- [Fly.io](https://fly.io)

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for step-by-step instructions.

---

## 🤝 Contributing

Adding a new scraper is straightforward:

1. Create `scrapers/yourplatform.py` — import `engine`, parse with BeautifulSoup, return a dict
2. Create `models/yourplatform.py` — dataclass or Pydantic model for the result
3. Add a router in `api.py` under a new prefix (e.g. `/yourplatform/...`)
4. Add a flow function in `main.py` for CLI access
5. Write tests in `tests/test_yourplatform.py`

---

## ⚠️ Usage Notes

- **Rate limiting:** Add pauses between requests. Amazon and Google will throttle or CAPTCHA-block aggressive scrapers.
- **Bot detection:** Use Browserless or a proxy service if you hit CAPTCHA walls.
- **Terms of service:** Use responsibly and respect each platform's ToS.
