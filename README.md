# Amazon Price Tracker → API → RapidAPI

A ready-to-deploy Amazon price tracker that works as a local CLI and a cloud API product.

This project is built to:
- scrape Amazon product prices reliably,
- expose those results via FastAPI,
- use Browserless for cloud rendering,
- and become a monetizable RapidAPI listing.

**Status:** ✅ CLI works locally | 🚀 API ready for deployment

---

## 🎯 Product Overview

This is more than a scraper — it is a developer-friendly price tracking API.

### What it does
- Scrapes Amazon product pages for buy-box price, Prime price, list price, stock status, and discount data
- Provides a lightweight price endpoint and a full product detail endpoint
- Tracks items in local JSON storage for repeat monitoring
- Supports condition-specific pricing (used/refurbished tiers)
- Exposes item management and monitoring endpoints for API-driven workflows

### Who it helps
- resellers monitoring price movements
- bargain hunters building custom alerts
- competitors tracking pricing trends
- developers building dashboards or price comparison tools

---

## 🔧 How it works

### Local mode
- `main.py` runs an interactive CLI
- lets users add and manage tracked Amazon products
- uses local Playwright scraping when available
- stores data in `./data/items.json`

### API mode
- `api.py` exposes REST endpoints via FastAPI
- `scraper.py` handles page parsing
- `browserless.py` fetches rendered pages in the cloud
- endpoints are ready for RapidAPI listing

### Deployment flow

```text
RapidAPI user
      ↓
RapidAPI gateway
      ↓
Deployed Render/Railway service
      ↓
api.py → scraper.py → browserless.py
      ↓
Amazon product page
```

---

## 🚀 Quick Start

### 1) Run the CLI locally

```bash
pip install -r requirements.txt
python main.py
```

### 2) Run the API locally

```bash
python -m uvicorn api:app --reload --port 8000
```

Open the docs at:

```text
http://localhost:8000/docs
```

### 3) Test the endpoints

```bash
curl "http://localhost:8000/scrape/price?url=https://www.amazon.com/dp/B0DHJ896RY"

curl "http://localhost:8000/scrape/full?url=https://www.amazon.com/dp/B0DHJ896RY"

curl "http://localhost:8000/validate?url=https://www.amazon.com/dp/B0DHJ896RY"

curl "http://localhost:8000/health"
```

---

## 📂 Project Structure

```
Price Tracker/
├── main.py              # CLI entry point
├── models.py            # Data structures
├── scraper.py           # Amazon scraping logic
├── storage.py           # JSON persistence
├── notifier.py          # Alerts & notifications
│
├── api.py               # FastAPI server
├── browserless.py       # Browserless integration
├── requirements.txt     # Python dependencies
│
├── DEPLOYMENT_GUIDE.md  # RapidAPI deployment guide
├── .env.example         # Environment template
├── .gitignore           # Git ignore rules
│
└── data/
    ├── config.json      # app settings
    └── items.json       # tracked items
```

---

## 📋 API Endpoints

### `GET /scrape/price`
Fetch the current price and availability for a product.

- query: `url` (required)
- query: `condition` (optional)
- returns: price, original price, Prime price, stock, discount
- use case: alerts, dashboards, price monitoring

### `GET /scrape/full`
Fetch detailed Amazon product metadata and variants.

- query: `url` (required)
- returns: title, ASIN, pricing tiers, variants, stock data
- use case: product research, catalogs, comparison tools

### `GET /validate`
Check whether a URL is a valid Amazon product link.

- query: `url` (required)
- returns: valid flag, normalized URL, ASIN
- use case: request validation before scraping

### `GET /health`
Service health check.

- returns: service status, version
- use case: uptime monitoring

---

## 🚀 Deploy to the Cloud

### Recommended hosts
- Render
- Railway

### Deploy steps
1. Push the repo to GitHub
2. Create a new web service on Render or Railway
3. Use start command:
   `uvicorn api:app --host 0.0.0.0 --port 8000`
4. Add environment variables
5. Deploy and copy your service URL

---

## 💡 RapidAPI Integration

This service is built to be published as a RapidAPI product:
- point RapidAPI to your deployed backend URL
- add the scraping endpoints
- define pricing tiers
- publish the listing

Your backend handles scraping and Browserless calls; RapidAPI handles authentication, billing, and marketplace distribution.

---

## 🛠️ Configuration

Create a `.env` file from `.env.example`:

```env
BROWSERLESS_API_KEY=your_api_key_here
PORT=8000
```

Use Browserless when your cloud host cannot run local Chromium directly.

---

## ⚠️ Notes

### Local vs Cloud

| Mode | `main.py` | `api.py` |
|------|-----------|----------|
| Local | CLI + local scraping | not used |
| Cloud | not used | API + Browserless |

### Amazon scraping best practices
- Keep request volume moderate
- Add pauses between checks
- Use Browserless to avoid browser binary issues
- Respect Amazon’s terms of service

---

## 🧪 Testing

### Local

```bash
python -m uvicorn api:app --reload --port 8000
```

### RapidAPI

- Open your app in RapidAPI dashboard
- Use the built-in endpoint tester
- Confirm the backend URL is live

---

## 🐛 Troubleshooting

### `Connection refused`
Make sure API is running and reachable.

### `Module not found: scraper`
Run from the repo root:

```bash
cd "c:\Users\fulto\Downloads\Some Projects\Price Tracker"
python -m uvicorn api:app --reload
```

### Playwright / Chromium issues
Use `BROWSERLESS_API_KEY` with Browserless.io instead of local browser execution.

---

## 📌 Next Steps

1. Run the CLI locally
2. Run the API locally and verify `/docs`
3. Deploy to Render/Railway
4. Connect the deployed URL to RapidAPI
5. Publish and monitor usage

---

## 📞 Resources

- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [FastAPI docs](https://fastapi.tiangolo.com/)
- [RapidAPI docs](https://rapidapi.com/documentation)
- [Browserless docs](https://www.browserless.io/docs)

**Built for developers who want a real API product, not just a script.**
