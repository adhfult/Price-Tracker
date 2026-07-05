# Deployment Guide

This guide covers deploying the Open Data API to three free cloud platforms: **Render**, **Railway**, and **Fly.io**. No Docker, no credit card required.

---

## Before you deploy

### Choose your browser engine

When deployed to the cloud, you need to render JavaScript-heavy pages. You have two options:

**Option A — Local Playwright (install Chromium on the host)**

Most hosts support this via a build command. This is completely free.

**Option B — Browserless.io**

If your host can't install Chromium or you want a managed solution, use Browserless.io. The free tier provides 100 pages/month.

Sign up at [browserless.io](https://www.browserless.io/) and copy your API key.

---

## Render

Render's free tier supports web services with persistent deploys.

### Steps

**1. Push your repo to GitHub**

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/your-username/your-repo.git
git push -u origin main
```

**2. Create a new Web Service on Render**

- Go to [render.com](https://render.com) → New → Web Service
- Connect your GitHub repo

**3. Configure the service**

| Setting | Value |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt && playwright install chromium` |
| Start Command | `uvicorn api:app --host 0.0.0.0 --port $PORT` |

> If using Browserless instead of local Playwright, remove `playwright install chromium` from the build command.

**4. Add environment variables**

In the Render dashboard → Environment:

```
PORT=10000
STORAGE_BACKEND=json
```

If using Browserless:
```
BROWSERLESS_API_KEY=your_key_here
```

**5. Deploy**

Click **Deploy**. After a few minutes your service will be live at:
```
https://your-service-name.onrender.com
```

**6. Verify**

```bash
curl https://your-service-name.onrender.com/health
```

Expected response:
```json
{ "status": "ok", "engine": "playwright", "version": "2.0.0" }
```

---

## Railway

Railway provides a generous free tier with easy GitHub integration.

### Steps

**1. Push your repo to GitHub** (same as Render step 1 above)

**2. Create a new project on Railway**

- Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
- Select your repo

**3. Add a Nixpacks build configuration**

Create a file `nixpacks.toml` in your project root:

```toml
[phases.setup]
nixPkgs = ["chromium", "nss", "at-spi2-atk", "cups", "libxcomposite"]

[phases.install]
cmds = ["pip install -r requirements.txt && playwright install chromium"]

[start]
cmd = "uvicorn api:app --host 0.0.0.0 --port $PORT"
```

> If using Browserless, skip the nixpacks.toml and just set the env var.

**4. Set environment variables**

In Railway → Settings → Variables:

```
STORAGE_BACKEND=json
BROWSERLESS_API_KEY=your_key_here   # only if using Browserless
```

**5. Deploy**

Railway auto-deploys on every `git push`. Your service URL is shown in the Railway dashboard.

---

## Fly.io

Fly.io is a great option for persistent workloads. The free tier includes 3 shared-CPU VMs.

### Steps

**1. Install the Fly CLI**

```bash
# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex

# macOS/Linux
curl -L https://fly.io/install.sh | sh
```

**2. Login**

```bash
fly auth login
```

**3. Create a `fly.toml` in your project root**

```toml
app = "your-app-name"
primary_region = "iad"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8080"
  STORAGE_BACKEND = "json"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [[services.ports]]
    port = 80
    handlers = ["http"]
```

**4. Add a `Procfile`**

```
web: playwright install chromium && uvicorn api:app --host 0.0.0.0 --port $PORT
```

> Replace the Playwright install with just `uvicorn api:app ...` if using Browserless.

**5. Set secrets (env vars)**

```bash
fly secrets set BROWSERLESS_API_KEY=your_key_here   # only if using Browserless
```

**6. Deploy**

```bash
fly launch
fly deploy
```

**7. Verify**

```bash
curl https://your-app-name.fly.dev/health
```

---

## Post-deployment: testing your endpoints

Once live, test any endpoint by replacing `localhost:8000` with your deployed URL:

```bash
BASE=https://your-service-url.onrender.com

# Health check
curl $BASE/health

# Amazon price
curl "$BASE/amazon/price?url=https://www.amazon.com/dp/B0DHJ896RY"

# Google Search
curl "$BASE/google/search?query=python+web+scraping"

# Google Shopping
curl "$BASE/google/shopping?query=mechanical+keyboard"

# Google News
curl "$BASE/google/news?query=open+source+tools"

# eBay listing
curl "$BASE/ebay/product?url=https://www.ebay.com/itm/YOUR_ITEM_ID"

# Generic web fetch
curl "$BASE/web/fetch?url=https://example.com"
```

Browse the full interactive docs at:
```
https://your-service-url/docs
```

---

## Switching to SQLite on a cloud host

If your host supports a persistent disk volume, switch to SQLite to get price history:

Set the environment variable:
```
STORAGE_BACKEND=sqlite
```

SQLite stores everything in `data/tracker.db`. Make sure your host mounts a persistent disk at the `data/` path — otherwise the database will be wiped on each redeploy.

- **Render:** Add a Disk in the Render dashboard, mount path `/app/data`
- **Railway:** Use Railway's Volume feature, mount at `/app/data`
- **Fly.io:** Add a volume in `fly.toml`:

```toml
[mounts]
  source = "data_volume"
  destination = "/app/data"
```

---

## Uptime monitoring (optional)

To keep your free-tier service from spinning down due to inactivity, set up a free uptime monitor:

- [UptimeRobot](https://uptimerobot.com) — free, monitors every 5 minutes
- [Freshping](https://www.freshworks.com/website-monitoring/) — free tier available

Point it at your `/health` endpoint.

---

## Troubleshooting

### `playwright._impl._errors.Error: Executable doesn't exist`
Chromium wasn't installed. Make sure `playwright install chromium` is in your build command.

### `BROWSERLESS_API_KEY not set`
You removed the Playwright install step but forgot to set the env var. Either reinstall Playwright or set the key.

### `Module not found: scrapers`
Make sure you're running from the project root. The start command should be:
```
uvicorn api:app --host 0.0.0.0 --port $PORT
```
Not from a subdirectory.

### Amazon/Google returning CAPTCHA errors
- Reduce request frequency
- Switch to Browserless if using local Playwright
- Add residential proxy support to `engine.py`
