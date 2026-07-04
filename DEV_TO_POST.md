# How I Turned an Amazon Price Tracker into a RapidAPI Product

If you’ve ever built a neat tool and wondered whether it could become a real product, this is the exact path I took.

I started with a local price tracker, then turned it into a cloud API that scrapes Amazon through Browserless, runs on Render, and can be sold through RapidAPI.

---

## Why this project matters

Amazon is the most popular ecommerce marketplace, but its pages are difficult to scrape reliably.

That means a lot of people still pay for overpriced scraping services or build brittle browser automation that breaks the second the page changes.

This project solves that by offering:

- a reliable Amazon price scraper
- a hosted API backend
- a marketplace-ready product on RapidAPI
- an actual monetization path for a side project

---

## The story behind the build

I originally built a Python CLI that tracked Amazon prices, watched for drops, and notified me locally.

It worked great at first, but the project still felt like a toy.

Then I asked myself:

> What if this was not just a script, but an API people could use?

The answer was a backend architecture that separates:

- the scraper logic,
- the API presentation layer,
- deployment and secrets,
- and marketplace billing.

---

## The architecture in plain language

Imagine this as two different responsibilities:

1. **Your app** runs scraping logic and responds to requests.
2. **RapidAPI** publishes that app as a product and handles billing.

The actual flow is:

```text
RapidAPI user
      ↓
RapidAPI gateway
      ↓
Your deployed Render service
      ↓
browserless.py → Browserless.io
      ↓
scraper.py parses HTML
      ↓
FastAPI returns JSON
```

### Why this works

- `RapidAPI` does not execute your code.
- `Render` runs your code.
- `BROWSERLESS_API_KEY` lives on your Render environment, not in RapidAPI.
- RapidAPI simply forwards requests and handles pricing.

---

## What the product does today

The API exposes both scraping and price-tracking behavior.

### Core capabilities

- scrape a product URL and return the current buy-box price
- scrape full product details including variants, Prime eligibility, and discount data
- validate Amazon URLs and normalize them
- manage tracked items with `POST /items` and `GET /items`
- run monitoring checks with `POST /monitor/check-all`

That means it’s more than a scraper. It’s a lightweight price-tracking product.

---

## The tech stack

### Python + FastAPI
FastAPI gives me:

- fast asynchronous API handling,
- Pydantic validation,
- Swagger UI documentation,
- clean route definitions.

### Browserless.io
Browserless lets the service render JavaScript-heavy Amazon pages without bundling Chromium in the deployment.

That is critical for cloud platforms that don’t support local browser binaries reliably.

### Render
Render hosts the app and stores the secret key.

It is the real runtime for the backend.

### RapidAPI
RapidAPI is the front-facing marketplace.

It handles:

- API key issuance,
- user subscriptions,
- billing,
- product discovery.

---

## The API endpoints you should ship

These are the ones that make the product feel complete.

### 1. GET /scrape/price
A lightweight endpoint that returns:

- current price
- original price
- Prime price
- stock status
- discount percent

### 2. GET /scrape/full
Returns:

- full product detail
- variant groups
- condition tiers
- metadata

### 3. GET /validate
Quickly validates if a URL is a real Amazon product and extracts the ASIN.

### 4. GET /health
A simple uptime check for monitoring.

### 5. POST /items
Add a tracked item to the backend.

### 6. GET /items
List all tracked items.

### 7. POST /items/{item_id}/check
Check a single tracked item.

### 8. POST /monitor/check-all
Run a full price monitoring cycle.

---

## Why this is useful for customers

This API is useful for:

- resellers tracking price movements,
- bargain hunters building alerts,
- brands monitoring competitor prices,
- anyone building price comparison tools.

It removes the need to manage browser automation, proxy configuration, and scraping maintenance.

---

## How the service stays reliable

### 1. Use Browserless for rendering
Amazon pages often require JS and client-side rendering. Browserless gives us a stable endpoint for that.

### 2. Keep logic separate
- `browserless.py` fetches rendered HTML
- `scraper.py` parses content
- `api.py` exposes routes
- `storage.py` persists tracked items

### 3. Avoid exposing secrets
`BROWSERLESS_API_KEY` is kept in the host environment, not in RapidAPI.

### 4. Graceful monitoring flow
The app can check multiple items, auto-reset alert state, and preserve item metadata between runs.

---

## Launching on RapidAPI

### Step 1: Deploy the service
Deploy to Render with a command like:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

### Step 2: Set your env vars
On Render, add:

- `BROWSERLESS_API_KEY`
- `BROWSERLESS_URL` if needed

### Step 3: Create the RapidAPI product
- set the base URL to your Render app
- add endpoints and parameter docs
- add pricing tiers

### Step 4: Publish
RapidAPI approval usually takes a couple of days, then your product is live.

---

## A strong monetization model

This is a perfect example of a product that can start as a small recurring revenue stream.

Example pricing tiers:

- Free: 100 requests/month
- Starter: $4.99/month
- Growth: $14.99/month
- Pro: $39.99/month

Even 20 paying users at $14.99 is a meaningful side income.

---

## What I learned building this

### Don’t build a scraping API unless you trust the page renderer
Local Playwright is easy to prototype, but it’s fragile in cloud production.

### RapidAPI is a great first monetization layer
It saves you from building API billing, authentication, and subscription management.

### Deploy fast, then improve
My first deploy was just the scrape endpoint. Then I added tracking and item management after it proved stable.

---

## Why this story is worth sharing

This project is a real indie hack because it crosses three valuable stages:

1. working prototype
2. cloud deployment
3. monetizable API product

If you are building side projects, that sequence is gold.

---

## What’s next for this product

These are the upgrades I want to build next:

- webhook alerts for price drops
- response caching to reduce Browserless calls
- request quotas per RapidAPI user
- support for international Amazon domains
- a small frontend dashboard

---

## Final takeaway

This is not just a scraper.

It is a product that:

- solves a real business need,
- runs in the cloud,
- hides operational complexity from users,
- and can be sold through RapidAPI.

If you want, I can also turn this into a second version with launch copy, a newsletter pitch, and a product page layout.
