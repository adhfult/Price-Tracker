# 🕷️ Amazon Price Scraper API

**Real-time Amazon product price tracking with Playwright web automation**

Live API: `https://price-tracker-puef.onrender.com`

---

## ✨ Features

✅ **Real-time price scraping** - Get current Amazon prices instantly  
✅ **Product details** - Extract title, ASIN, variants, stock status  
✅ **URL validation** - Quick Amazon URL checks  
✅ **Fast response** - 15-30 seconds per request  
✅ **Error handling** - Graceful failures with detailed messages  
✅ **Rate limiting** - Per-tier request limits  

---

## 📋 API Endpoints

### 1. **Get Current Price** (Lightweight)
```
GET /scrape/price?url={amazon_url}&condition={optional}
```
**Response time:** 10-15 seconds

**Returns:**
- Current price (Buy-box)
- Original price
- Prime member price (if available)
- Stock status
- Prime eligibility

**Example:**
```bash
curl "https://price-tracker-puef.onrender.com/scrape/price?url=https://www.amazon.com/dp/B0DHJ896RY"
```

---

### 2. **Get Full Details** (Comprehensive)
```
GET /scrape/full?url={amazon_url}
```
**Response time:** 20-30 seconds

**Returns:**
- All price tiers
- Product title & ASIN
- Variant groups (color, size, storage, condition)
- Stock status
- Prime eligibility

**Best for:** Product comparison, catalog scraping, research

---

### 3. **Validate URL** (Fast Check)
```
GET /validate?url={url}
```
**Response time:** <100ms

**Returns:**
- Valid/invalid status
- Normalized URL
- Extracted ASIN

**Best for:** Pre-validation before scraping

---

### 4. **Health Check**
```
GET /health
```
Returns service status + version

---

## 💰 Pricing

| Plan | Price/Month | Requests/Month | Rate Limit | Best For |
|------|-----------|----------------|-----------|----------|
| **Free** | $0 | 100 | 5 req/min | Testing |
| **Basic** | $4.99 | 1,000 | 10 req/min | Indie devs |
| **Pro** | $14.99 | 10,000 | 50 req/min | Production |
| **Ultra** | $39.99 | 100,000 | 200 req/min | Enterprise |
| **Mega** | $99.99 | 500,000 | Unlimited | Scale |

---

## 🚀 Quick Start

### 1. Get Your API Key
Subscribe to any plan above and get your RapidAPI key

### 2. Make Your First Request
```bash
curl -X GET "https://price-tracker-puef.onrender.com/scrape/price?url=https://www.amazon.com/dp/B0DHJ896RY" \
  -H "x-rapidapi-key: YOUR_API_KEY" \
  -H "x-rapidapi-host: price-tracker-puef.p.rapidapi.com"
```

### 3. Parse Response
```json
{
  "status": "success",
  "data": {
    "current_price": 799.99,
    "original_price": 999.99,
    "prime_price": null,
    "in_stock": true,
    "is_prime_eligible": true,
    "condition": "New"
  },
  "timestamp": "2026-07-04T02:00:00Z"
}
```

---

## 📝 Use Cases

### Price Monitoring
Track competitor prices and alert when they drop
```bash
/scrape/price?url=amazon.com/dp/ASIN
```

### Product Research
Get detailed specs and variants for market analysis
```bash
/scrape/full?url=amazon.com/dp/ASIN
```

### URL Validation
Pre-check Amazon URLs before processing
```bash
/validate?url=amazon.com/dp/ASIN
```

### Catalog Scraping
Build product databases with pricing tiers
```bash
# Call /scrape/full for each product
# Parse variants and prices
# Store in database
```

---

## ⚙️ Integration Examples

### Python
```python
import requests

url = "https://price-tracker-puef.p.rapidapi.com/scrape/price"
params = {"url": "https://www.amazon.com/dp/B0DHJ896RY"}
headers = {
    "x-rapidapi-key": "YOUR_API_KEY",
    "x-rapidapi-host": "price-tracker-puef.p.rapidapi.com"
}

response = requests.get(url, params=params, headers=headers)
data = response.json()
print(f"Price: ${data['data']['current_price']}")
```

### JavaScript
```javascript
const url = "https://price-tracker-puef.p.rapidapi.com/scrape/price";
const params = new URLSearchParams({
  url: "https://www.amazon.com/dp/B0DHJ896RY"
});

fetch(`${url}?${params}`, {
  headers: {
    "x-rapidapi-key": "YOUR_API_KEY",
    "x-rapidapi-host": "price-tracker-puef.p.rapidapi.com"
  }
})
.then(res => res.json())
.then(data => console.log(`Price: $${data.data.current_price}`));
```

### cURL
```bash
curl -X GET "https://price-tracker-puef.p.rapidapi.com/scrape/price?url=https://www.amazon.com/dp/B0DHJ896RY" \
  -H "x-rapidapi-key: YOUR_API_KEY" \
  -H "x-rapidapi-host: price-tracker-puef.p.rapidapi.com"
```

---

## 📊 Response Examples

### Success Response
```json
{
  "status": "success",
  "data": {
    "current_price": 799.99,
    "original_price": 999.99,
    "prime_price": 749.99,
    "in_stock": true,
    "is_prime_eligible": true,
    "discount_percent": 20.0
  },
  "url": "https://www.amazon.com/dp/B0DHJ896RY",
  "asin": "B0DHJ896RY",
  "timestamp": "2026-07-04T02:00:00Z"
}
```

### Error Response
```json
{
  "status": "error",
  "error": "Invalid Amazon URL",
  "code": 400
}
```

---

## ⚠️ Rate Limits

Requests are rate-limited per your subscription plan:

- **Free:** 100 requests/month, 5 req/min
- **Basic:** 1,000 requests/month, 10 req/min
- **Pro:** 10,000 requests/month, 50 req/min
- **Ultra:** 100,000 requests/month, 200 req/min
- **Mega:** 500,000 requests/month, unlimited req/min

Exceeded limit? Upgrade your plan or wait for monthly reset.

---

## 🔒 Important Notes

### Compliance
- Respect Amazon's `robots.txt`
- Don't scrape >100 products/hour per IP
- Use for legitimate price monitoring only
- Not for automated inventory/catalog copying

### Rate Limiting Best Practice
- Add delays between requests (2-5 seconds)
- Rotate user agents
- Use proxy rotation for bulk scraping
- Cache results to minimize redundant requests

### Terms of Service
Amazon's terms prohibit automated scraping. Use this API responsibly and at your own risk.

---

## 🆘 Troubleshooting

### "Invalid Amazon URL"
- Ensure URL is from `amazon.com`
- Include full product page URL with `/dp/ASIN`
- Remove query parameters if any

### "Connection timeout"
- Try again (Amazon may be temporarily blocking)
- Add 2-3 second delay between requests
- Upgrade to higher tier for priority

### "Empty response"
- Product may be out of stock (try without `condition` param)
- URL may be region-restricted
- Try validating URL first with `/validate`

### "Variant not found"
- Condition tier may not exist for that product
- Use `/scrape/full` to see all available conditions

---

## 📞 Support

- **API Status:** Check `/health` endpoint
- **Documentation:** RapidAPI Hub
- **Issues:** Contact via RapidAPI support

---

## 💡 Pro Tips

1. **Cache results** to avoid redundant calls and save quota
2. **Batch requests** with delays instead of rapid-fire
3. **Use `/validate`** before expensive `/scrape/full` calls
4. **Monitor your usage** in RapidAPI dashboard
5. **Set alerts** when approaching rate limit

---

## 🎯 Next Steps

1. ✅ Subscribe to a plan
2. ✅ Get your API key from RapidAPI
3. ✅ Test with `/health` endpoint
4. ✅ Start scraping with `/scrape/price`
5. ✅ Integrate into your app

**Ready?** Click **Subscribe** above! 🚀

---

**API Version:** 1.0.0  
**Last Updated:** July 4, 2026  
**Status:** ✅ Live & Production Ready
