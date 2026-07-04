# 🚀 Complete Implementation Plan: Price Tracker → RapidAPI

## Current Architecture (Local CLI)
```
main.py (CLI Menu)
├── scraper.py (Playwright)
├── models.py (Data structures)
├── storage.py (JSON files)
└── notifier.py (Alerts)
```

## New Architecture (API + Marketplace)
```
┌─────────────────────────────────────────────────────────────────┐
│                    RapidAPI Marketplace                          │
│  (User pays → RapidAPI gateway → Routes requests → Collects fees)│
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTP GET /scrape/price?url=...&key=...
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              PythonAnywhere / Render / Railway                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ api.py (FastAPI)                                          │  │
│  │ - /scrape/price       (lightweight, ~15s)               │  │
│  │ - /scrape/full        (comprehensive, ~25s)             │  │
│  │ - /validate           (quick URL check, <100ms)         │  │
│  │ - /health             (uptime monitoring)                │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
   ┌─────────────┐            ┌──────────────────┐
   │ scraper.py  │            │ browserless.py   │
   │(Local or    │◄──────────►│(Cloud-based      │
   │Browserless) │            │ Playwright)      │
   └─────────────┘            └──────────────────┘
```

---

## 📋 Implementation Checklist

### Phase 1: Local Development & Testing

#### ✅ Step 1: Install FastAPI Dependencies
```bash
pip install fastapi uvicorn pydantic
# Or: pip install -r requirements.txt
```

#### ✅ Step 2: Test API Locally
```bash
cd "c:\Users\fulto\Downloads\Some Projects\Price Tracker"
python -m uvicorn api:app --reload --port 8000
```

Navigate to: `http://localhost:8000/docs`

You'll see interactive Swagger UI where you can test all endpoints!

**Test the endpoints:**
- GET `/scrape/price?url=https://www.amazon.com/dp/B0DHJ896RY`
- GET `/scrape/full?url=https://www.amazon.com/dp/B0DHJ896RY`
- GET `/validate?url=https://www.amazon.com/dp/B0DHJ896RY`
- GET `/health`

#### ✅ Step 3: Verify Existing Code Still Works
```bash
python main.py  # CLI should work unchanged
```

Both CLI (main.py) and API (api.py) coexist!

---

### Phase 2: Cloud-Based Playwright (Browserless.io)

> **Why?** PythonAnywhere doesn't support installing system binaries like Chromium. Solution: Use Browserless.io API instead.

#### ✅ Step 1: Sign Up for Browserless.io
1. Go to https://www.browserless.io/
2. Sign up (free tier: 100 pages/month)
3. Copy your API key from dashboard

#### ✅ Step 2: Configure Browserless
```bash
# Set environment variable:
$env:BROWSERLESS_API_KEY = "your_api_key_here"

# Or run interactive setup:
python -c "from browserless import setup_browserless; setup_browserless()"
```

#### ✅ Step 3: (Optional) Enable in scraper.py
If deploying to PythonAnywhere, uncomment this in scraper.py:
```python
# from browserless import fetch_page_browserless_sync as _fetch_page
```

And comment out the local Playwright version:
```python
# with sync_playwright() as p: ...
```

> **Cost:** ~$0.02-0.05 per 1000 pages (includes free tier)

---

### Phase 3: Deploy to PythonAnywhere

#### ✅ Step 1: Prepare GitHub Repository
```bash
git init
git add .
git commit -m "Add FastAPI backend for RapidAPI"
git remote add origin https://github.com/yourusername/price-tracker.git
git push -u origin main
```

> Need GitHub? Free account at https://github.com

#### ✅ Step 2: Create PythonAnywhere Account
1. Go to https://www.pythonanywhere.com/
2. Sign up (free tier: 100MB storage, auto-shutdowns)
3. Upgrade to paid if needed ($5/month for always-on)

#### ✅ Step 3: Deploy from GitHub
On PythonAnywhere:
1. **Web** → **Add a new web app** → Select **FastAPI**
2. **Source code** → **Clone from GitHub**
3. Enter: `https://github.com/yourusername/price-tracker.git`
4. Configure **WSGI file** to load: `api:app`
5. Set **Python version** to 3.9+

#### ✅ Step 4: Install Dependencies
In PythonAnywhere **Bash console:**
```bash
cd /home/yourusername/price-tracker
pip install -r requirements.txt
```

#### ✅ Step 5: Get Your Live URL
Your API is now live at:
```
https://yourusername.pythonanywhere.com
```

Test it:
```bash
curl https://yourusername.pythonanywhere.com/health
```

Should return:
```json
{
  "status": "online",
  "version": "1.0.0",
  "service": "Amazon Price Scraper API"
}
```

---

### Phase 4: Connect to RapidAPI

#### ✅ Step 1: Go to Your RapidAPI Dashboard
You already have an "Amazon-Price-Scraper" app set up (from your screenshot).

#### ✅ Step 2: Set Base URL
1. Click your app → **Settings** tab
2. Find **Base URL** field
3. Enter: `https://yourusername.pythonanywhere.com`
4. **Save**

#### ✅ Step 3: Define Endpoints
Click **Endpoints** → **Create Endpoint** (repeat for each):

**Endpoint 1: Get Price**
- **Name:** `Get Current Price`
- **Method:** `GET`
- **Path:** `/scrape/price`
- **Required Parameters:**
  - `url` (query string, string)
- **Optional Parameters:**
  - `condition` (query string, string)

**Endpoint 2: Get Full Details**
- **Name:** `Get Full Product Details`
- **Method:** `GET`
- **Path:** `/scrape/full`
- **Required Parameters:**
  - `url` (query string, string)

**Endpoint 3: Validate URL**
- **Name:** `Validate Amazon URL`
- **Method:** `GET`
- **Path:** `/validate`
- **Required Parameters:**
  - `url` (query string, string)

**Endpoint 4: Health Check**
- **Name:** `Health Check`
- **Method:** `GET`
- **Path:** `/health`

#### ✅ Step 4: Configure Rate Limits
In RapidAPI Studio:
1. **Hub Listing** → **Pricing**
2. Set your pricing tiers:
   - **Free:** 100 calls/month
   - **Basic:** $9.99/month → 1000 calls/month
   - **Pro:** $49.99/month → 10,000 calls/month

#### ✅ Step 5: Publish to Marketplace
1. Click **Publish**
2. Fill out listing details
3. Submit for review (~24-48 hours)

Once approved, your API is live on RapidAPI marketplace!

---

### Phase 5: Monitoring & Maintenance

#### ✅ Set Up Uptime Monitoring
Use **UptimeRobot.com** (free):
1. Go to https://uptimerobot.com/
2. Add new monitor: `https://yourusername.pythonanywhere.com/health`
3. Get alerted if your API goes down

#### ✅ Monitor Usage on RapidAPI
- **Analytics** tab shows calls/month
- **Revenue** tab shows earnings
- **Requests** tab shows errors/logs

#### ✅ Handle Rate Limiting
Add to api.py if needed:
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.util import get_redis

# Limit to 100 requests per minute
@limiter.limit("100/minute")
@app.get("/scrape/price")
async def get_price(...):
    ...
```

---

## 📊 Pricing & Revenue Model

| Tier | Price | Calls/Month | My Revenue (70%) |
|------|-------|-------------|-----------------|
| **Free** | $0 | 100 | $0 |
| **Basic** | $9.99 | 1000 | ~$7 |
| **Pro** | $49.99 | 10,000 | ~$35 |
| **Ultra** | $99.99 | 50,000 | ~$70 |

> RapidAPI takes 30%, you keep 70% (standard commission).
> 
> At 100 developers using Pro tier = **$3,500/month revenue**

---

## 🔧 Troubleshooting

### "Module not found" error on PythonAnywhere
```bash
# SSH into PythonAnywhere and reinstall:
pip install -r requirements.txt --force-reinstall
```

### Playwright fails on PythonAnywhere
**Solution:** Use Browserless.io instead (already configured in this guide).

### API returns 429 (Amazon rate limiting)
**Solution:** 
- Add delay between requests: `time.sleep(3)`
- Use rotating proxies (Bright Data, Oxylabs)
- Respect robots.txt

### RapidAPI shows "Endpoint unreachable"
**Debugging:**
```bash
# Test from PythonAnywhere:
curl https://yourusername.pythonanywhere.com/health

# Check logs:
# PythonAnywhere Dashboard → Web → Error log
```

---

## 📚 Files Created/Modified

| File | Purpose |
|------|---------|
| `api.py` | **NEW** - FastAPI server with endpoints |
| `browserless.py` | **NEW** - Cloud Playwright integration |
| `requirements.txt` | **UPDATED** - Added FastAPI + uvicorn |
| `main.py` | Unchanged - CLI still works |
| `scraper.py` | Unchanged - API reuses it |

---

## 🎯 Next Steps

1. **Test locally** → `python -m uvicorn api:app --reload --port 8000`
2. **Push to GitHub** → Create repo + push code
3. **Deploy to PythonAnywhere** → Connect GitHub + deploy
4. **Configure RapidAPI** → Set base URL + endpoints
5. **Test endpoints** → Use RapidAPI's "Test Endpoint" feature
6. **Publish** → Submit to marketplace
7. **Monitor** → Track usage + revenue

---

## 💡 Additional Features (Future)

- **Caching:** Cache results for 1 hour to reduce API calls
- **Webhooks:** Notify customers when price drops
- **Batch API:** Accept multiple URLs in one request
- **CSV Export:** Return results as CSV
- **Scheduled Monitoring:** Integration with automation platforms

---

## 📞 Support Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **RapidAPI Hub:** https://rapidapi.com/documentation
- **PythonAnywhere:** https://help.pythonanywhere.com/
- **Browserless.io:** https://www.browserless.io/docs

---

**Built with ❤️ for developers who want to monetize their tools.**
