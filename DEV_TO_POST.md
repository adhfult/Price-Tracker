# From Hobby Project to Revenue Stream: Building an Amazon Price Scraper API

Ever built a cool CLI tool and thought "what if I could actually make money from this?" That's exactly what I did—and I want to show you how.

---

## The Journey

I started with a simple goal: track Amazon prices and get alerts when they drop. So I built a Python CLI with:
- **Playwright** for web automation (JavaScript-heavy pages)
- **Beautiful Soup** for HTML parsing
- **Local JSON storage** for simplicity
- **Desktop notifications** for alerts

The CLI worked great locally. But then I had an idea: *What if I turned this into an API and sold it?*

---

## The Problem with Most APIs

Most web scraping APIs are **expensive** ($50-200/month) because they:
1. Host servers 24/7
2. Maintain complex infrastructure
3. Have enterprise licensing

I wanted to build something **lean** that could be **profitable at scale** without breaking the bank.

---

## The Solution Stack

Here's what I chose:

### **Framework: FastAPI**
Why? It's:
- ⚡ Fast (ASGI, async by default)
- 📚 Auto-generates Swagger docs
- 🔒 Built-in data validation (Pydantic)
- 🚀 Production-ready

```python
from fastapi import FastAPI, Query

app = FastAPI()

@app.get("/scrape/price")
def get_price(url: str = Query(...)):
    result = scraper.get_current_price(url)
    return {"status": "success", "data": result}
```

### **Hosting: Render.com**
Why not PythonAnywhere? 
- ❌ PythonAnywhere = WSGI only (no ASGI support)
- ✅ Render = ASGI native
- ✅ Free tier works great for low traffic
- ✅ One-click GitHub deploy

### **Monetization: RapidAPI**
Why RapidAPI instead of custom Stripe integration?
- 🎯 Built-in user management
- 💳 Handles all payments
- 📊 Analytics dashboard
- 🔑 Auto-generates API keys
- 💰 You get 70% revenue split

---

## The Technical Architecture

```
RapidAPI Marketplace
        ↓
    Your API Docs
        ↓
  Render Web Server (FastAPI)
        ↓
   api.py (4 endpoints)
        ↓
   scraper.py (Playwright)
        ↓
   Amazon Product Pages
```

### **The 4 Endpoints:**

**1. Get Current Price (Lightweight)**
```bash
GET /scrape/price?url=amazon_url&condition=optional
Response: 15-30 seconds
Returns: Current price, original price, stock status
```

**2. Get Full Details (Comprehensive)**
```bash
GET /scrape/full?url=amazon_url
Response: 20-30 seconds
Returns: All variants, pricing tiers, conditions
```

**3. Validate URL (Fast)**
```bash
GET /validate?url=url
Response: <100ms
Returns: Valid/invalid + normalized URL + ASIN
```

**4. Health Check**
```bash
GET /health
Response: <10ms
Returns: Service status
```

---

## Deployment in 5 Steps

### **Step 1: Push to GitHub**
```bash
git init
git add .
git commit -m "Add FastAPI backend"
git push origin main
```

### **Step 2: Deploy to Render**
1. Connect GitHub repo
2. Set start command: `uvicorn api:app --host 0.0.0.0 --port 8000`
3. Deploy (takes 2 min)
4. Get live URL: `https://your-app.onrender.com`

### **Step 3: Set Up RapidAPI**
1. Create app on RapidAPI
2. Set base URL to your Render URL
3. Define 4 endpoints
4. Set pricing tiers

### **Step 4: Configure Pricing**
```
Free:   $0/month   → 100 requests
Basic:  $4.99/mo   → 1,000 requests
Pro:    $14.99/mo  → 10,000 requests
Ultra:  $39.99/mo  → 100,000 requests
Mega:   $99.99/mo  → 500,000 requests
```

### **Step 5: Publish & Launch**
Click publish, wait for marketplace review (24-48 hours), and start earning!

---

## Revenue Potential

With just **100 active users**:

| Plan | Users | Price | Monthly Revenue (You get 70%) |
|------|-------|-------|-----|
| Free | 30 | $0 | $0 |
| Basic | 40 | $4.99 | $140 |
| Pro | 20 | $14.99 | $210 |
| Ultra | 8 | $39.99 | $224 |
| Mega | 2 | $99.99 | $140 |
| **Total** | **100** | | **~$714/month** |

Scale to 500 users? That's $3,500+/month of **passive income**.

---

## Key Lessons I Learned

### 1. **ASGI vs WSGI Matters**
PythonAnywhere was my first choice—until I hit the ASGI wall. Render was a lifesaver. Always check hosting compatibility with your framework.

### 2. **Pricing Strategy is Everything**
Lower prices = more users = more reviews = better ranking.
I started with $1.99/tier, then realized the value prop was higher. Adjusted to $4.99+ and didn't lose users.

### 3. **Documentation Drives Adoption**
I created:
- Interactive Swagger UI (`/docs`)
- Detailed README with examples
- Python, JavaScript, and cURL code samples

Users want to see **working examples**, not just API specs.

### 4. **Rate Limiting is Critical**
Without it, one user could drain your quota. RapidAPI handles it automatically per tier—you don't have to build it.

### 5. **Start Simple**
My first version was 200 lines of FastAPI code. Not fancy. Not over-engineered. Just **working**.

---

## What's Next?

After launch, I'm planning:

- 📊 Analytics dashboard (request frequency, response times)
- 🔄 Response caching (reduce redundant Playwright calls)
- 🌍 Webhook notifications (alert users on price drops)
- 📱 Mobile SDK (Python, JS, Go)
- 🎯 Advanced filters (by condition, seller, delivery)

---

## TL;DR

**Build:**
1. FastAPI + Playwright scraper
2. 4 simple endpoints
3. Clean error handling

**Deploy:**
1. Push to GitHub
2. Deploy to Render (free tier works!)
3. 5 minutes total

**Monetize:**
1. List on RapidAPI
2. Set pricing tiers
3. Watch revenue roll in

**Result:**
- 💰 $700+/month with 100 users
- 🚀 Scales automatically
- 👥 Zero customer support overhead (RapidAPI handles it)
- 🔐 Your code stays private

---

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Render Hosting](https://render.com/)
- [RapidAPI](https://rapidapi.com/)
- [My GitHub](https://github.com/yourusername/price-tracker)

---

## Questions?

- How do you monetize side projects?
- What APIs would you build if you had an audience?
- Any other questions?

Drop a comment! ⬇️

---

**P.S.** If you want the full code (CLI + API), check out my GitHub. It's all open source (for now 😉).
