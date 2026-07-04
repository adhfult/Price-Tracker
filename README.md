# Amazon Price Tracker → API → RapidAPI

Real-time Amazon product price scraping with Playwright, exposed as a monetizable REST API via RapidAPI.

**Status:** ✅ CLI works locally | 🚀 API ready for deployment

---

## 🎯 Overview

This project provides two ways to track Amazon prices:

1. **CLI Mode** (Local) - `python main.py`
   - Interactive menu
   - Auto-monitoring with alerts
   - Local storage

2. **API Mode** (Cloud) - `python -m uvicorn api:app --reload`
   - REST endpoints
   - RapidAPI marketplace integration
   - Monetization ready

---

## 🚀 Quick Start

### Local Testing (5 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run CLI (existing feature)
python main.py

# 3. Test API in another terminal
python -m uvicorn api:app --reload --port 8000

# 4. Visit interactive docs
# Open: http://localhost:8000/docs
```

### Test Endpoints

```bash
# Get current price
curl "http://localhost:8000/scrape/price?url=https://www.amazon.com/dp/B0DHJ896RY"

# Get full product details
curl "http://localhost:8000/scrape/full?url=https://www.amazon.com/dp/B0DHJ896RY"

# Validate URL
curl "http://localhost:8000/validate?url=https://www.amazon.com/dp/B0DHJ896RY"

# Health check
curl "http://localhost:8000/health"
```

---

## 📂 Project Structure

```
Price Tracker/
├── main.py              # CLI entry point (unchanged)
├── models.py            # Data structures
├── scraper.py           # Playwright web scraper
├── storage.py           # JSON file storage
├── notifier.py          # Alerts & notifications
│
├── api.py               # ✨ NEW: FastAPI server
├── browserless.py       # ✨ NEW: Cloud Playwright (for PythonAnywhere)
├── requirements.txt     # ✨ UPDATED: +FastAPI +uvicorn
│
├── DEPLOYMENT_GUIDE.md  # 📖 Step-by-step RapidAPI setup
├── .env.example         # Environment variables template
├── .gitignore           # Git ignore rules
│
└── data/
    ├── config.json      # Settings
    └── items.json       # Tracked items
```

---

## 📋 What's New (Phase 2)

| Feature | Details |
|---------|---------|
| **FastAPI** | Modern, fast web framework for Python APIs |
| **api.py** | 4 endpoints for price scraping & validation |
| **Browserless.io** | Cloud-based Playwright for PythonAnywhere |
| **RapidAPI Ready** | Pre-configured error handling, responses, docs |
| **Interactive Docs** | Swagger UI at `/docs` for testing |
| **CORS Enabled** | Works with web frontends, mobile apps |

---

## 🔗 API Endpoints

### 1. Get Current Price
```
GET /scrape/price?url=<amazon_url>&condition=<optional>
```
- **Response time:** 10-15 seconds
- **Use case:** Price monitoring, dashboards, alerts
- **Returns:** Current price, original price, Prime price, stock status

### 2. Get Full Details
```
GET /scrape/full?url=<amazon_url>
```
- **Response time:** 20-30 seconds
- **Use case:** Catalog scraping, variants, detailed research
- **Returns:** Title, ASIN, all prices, stock, color/size/storage options

### 3. Validate URL
```
GET /validate?url=<url>
```
- **Response time:** <100ms
- **Use case:** Quick URL validation before scraping
- **Returns:** Valid/invalid + normalized URL + ASIN

### 4. Health Check
```
GET /health
```
- **Response time:** <10ms
- **Use case:** Uptime monitoring
- **Returns:** Service status + version

---

## 🌐 Deployment Options

### Option A: PythonAnywhere (Recommended for Beginners)

1. ✅ Sign up at https://www.pythonanywhere.com/
2. ✅ Connect your GitHub repo
3. ✅ Set base URL to `https://yourusername.pythonanywhere.com`
4. ✅ Follow [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

**Pros:** Easy setup, works out of the box
**Cons:** Slow free tier, limited CPU

### Option B: Render / Railway

1. ✅ Push code to GitHub
2. ✅ Connect repo to Render.com or Railway.app
3. ✅ Deploy with one click
4. ✅ Get live URL

**Pros:** Faster, free tier available
**Cons:** More configuration

### Option C: AWS Lambda (Advanced)

1. ✅ Package with `serverless-python-requirements`
2. ✅ Deploy with Serverless Framework
3. ✅ Use API Gateway for HTTP endpoints

**Pros:** Scales automatically, pay-per-request
**Cons:** More complex setup

---

## 💰 Monetization (RapidAPI)

### How It Works

1. You deploy API to cloud
2. You list it on RapidAPI marketplace
3. Users subscribe to pricing tiers
4. RapidAPI routes requests → you get 70% commission
5. Monthly payouts via PayPal/Stripe

### Example Revenue

| Tier | Price | Users | Revenue |
|------|-------|-------|---------|
| Free | $0 | 50 | $0 |
| Basic | $9.99 | 20 | $140/mo |
| Pro | $49.99 | 5 | $175/mo |
| **Total** | | | **$315/mo** |

See: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for full pricing guide

---

## 🛠️ Configuration

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```env
# For cloud Playwright (PythonAnywhere)
BROWSERLESS_API_KEY=your_api_key_here

# For local development
PORT=8000
```

### Browserless.io Setup

Free tier: 100 pages/month
```bash
python -c "from browserless import setup_browserless; setup_browserless()"
```

---

## ⚠️ Important Notes

### Local vs. Cloud

| Aspect | Local (main.py) | Cloud API (api.py) |
|--------|-----------------|------------------|
| Browser | Uses local Playwright | Uses Browserless.io |
| Response time | 15-30s | 15-30s |
| Cost | Free (CPU) | $0-50/month |
| Scalability | 1 request at a time | 100+ concurrent |
| 24/7 Uptime | Requires your computer on | Automatic |

### Amazon Rate Limiting

- Don't scrape >100 products/hour
- Add random delays between requests
- Use rotating proxies for bulk scraping
- Respect `robots.txt`

### Error Handling

All errors return consistent JSON:
```json
{
  "status": "error",
  "error": "Invalid Amazon URL",
  "code": 400
}
```

---

## 📖 Full Documentation

For complete step-by-step deployment guide, see:

**📄 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

Covers:
- Local testing
- Cloud deployment (PythonAnywhere)
- RapidAPI integration
- Pricing setup
- Monitoring & maintenance
- Troubleshooting

---

## 🧪 Testing

### Unit Tests (Optional)

```bash
pip install pytest pytest-asyncio
pytest tests/
```

### Load Testing

```bash
pip install locust

# Create locustfile.py and run:
locust -f locustfile.py --host=http://localhost:8000
```

### RapidAPI Testing

1. Go to your RapidAPI app dashboard
2. Click "Test Endpoint"
3. Fill in parameters
4. Click "Test"

---

## 🔒 Security

- ✅ Input validation on all endpoints
- ✅ CORS enabled for web apps
- ✅ Error messages don't leak system info
- ✅ API keys managed by RapidAPI (you don't handle them)
- ✅ Rate limiting on RapidAPI side

### To Add (Future)

- [ ] Request signing for direct API calls
- [ ] Custom rate limiting per API key
- [ ] Analytics dashboard
- [ ] Webhook notifications

---

## 🐛 Troubleshooting

### "Connection refused" on localhost:8000
```bash
# Make sure API is running:
python -m uvicorn api:app --reload --port 8000
```

### "Module not found: scraper"
```bash
# Add to path:
cd "c:\Users\fulto\Downloads\Some Projects\Price Tracker"
python -m uvicorn api:app --reload
```

### Playwright crashes on PythonAnywhere
```bash
# Set BROWSERLESS_API_KEY and it will use cloud version automatically
export BROWSERLESS_API_KEY=your_key
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for more troubleshooting.

---

## 📞 Support

- **API Docs:** http://localhost:8000/docs (when running locally)
- **FastAPI:** https://fastapi.tiangolo.com/
- **RapidAPI:** https://rapidapi.com/documentation
- **Deployment:** See DEPLOYMENT_GUIDE.md

---

## 📝 License

Personal use for now. Consider: MIT, GPL, or Commercial.

---

## 🚀 Next Steps

1. **Test locally** ✅
   ```bash
   python -m uvicorn api:app --reload --port 8000
   ```

2. **Deploy to cloud** 📋
   - Follow [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
   - Get live URL

3. **Set up RapidAPI** 🎯
   - Connect base URL
   - Define endpoints
   - Set pricing

4. **Monitor revenue** 💰
   - Check RapidAPI dashboard
   - Track usage stats
   - Collect payments

---

**Happy scraping! 🕷️** 

Questions? See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for comprehensive setup instructions.
