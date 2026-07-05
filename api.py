"""
FastAPI application — multi-platform open-source data extraction API.

Endpoints are domain-prefixed using APIRouter:
  /amazon/*   - Amazon product data
  /google/*   - Google Search, Shopping, News
  /ebay/*     - eBay listings
  /web/*      - Generic web fetcher
  /health     - Health check
  /validate   - Amazon URL validator (preserved for compatibility)
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging

import scrapers
import storage
import main as cli_main
from models.amazon import TrackedItem, AlertCriteria, AlertType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── App init ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Open Data API",
    description=(
        "Open-source, multi-platform data extraction API. "
        "Supports Amazon, Google Search, Google Shopping, Google News, eBay, "
        "and generic web fetching. "
        "Run locally with Playwright or configure BROWSERLESS_API_KEY for cloud use."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class AlertCriteriaInput(BaseModel):
    alert_type:   str            = Field(default="any_drop")
    target_price: Optional[float] = None
    min_price:    Optional[float] = None
    max_price:    Optional[float] = None
    drop_amount:  Optional[float] = None
    drop_percent: Optional[float] = None


class AddItemRequest(BaseModel):
    url:               str                      = Field(..., description="Amazon product URL")
    currency:          Optional[str]            = Field(None)
    location:          Optional[str]            = Field(None)
    selected_variants: Optional[Dict[str, str]] = Field(default_factory=dict)
    alert_criteria:    Optional[AlertCriteriaInput] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _criteria_from_payload(payload: Optional[AlertCriteriaInput]) -> AlertCriteria:
    if not payload:
        return AlertCriteria(alert_type=AlertType.ANY_DROP)
    mapping = {
        "below_price":    AlertType.BELOW_PRICE,
        "in_range":       AlertType.IN_RANGE,
        "any_drop":       AlertType.ANY_DROP,
        "drop_by_amount": AlertType.DROP_BY_AMOUNT,
        "drop_by_percent": AlertType.DROP_BY_PERCENT,
    }
    return AlertCriteria(
        alert_type   = mapping.get(payload.alert_type.lower(), AlertType.ANY_DROP),
        target_price = payload.target_price,
        min_price    = payload.min_price,
        max_price    = payload.max_price,
        drop_amount  = payload.drop_amount,
        drop_percent = payload.drop_percent,
    )


def _item_to_payload(item: TrackedItem) -> Dict:
    return {
        "id":                   item.id,
        "url":                  item.url,
        "title":                item.title,
        "asin":                 item.asin,
        "currency":             item.currency,
        "location":             item.location,
        "selected_variants":    item.selected_variants,
        "last_price":           item.last_price,
        "last_original_price":  item.last_original_price,
        "last_prime_price":     item.last_prime_price,
        "last_discount_percent": item.last_discount_percent,
        "baseline_price":       item.baseline_price,
        "is_prime_eligible":    item.is_prime_eligible,
        "in_stock":             item.in_stock,
        "date_added":           item.date_added,
        "last_checked":         item.last_checked,
        "alert_triggered":      item.alert_triggered,
        "alert_criteria": {
            "alert_type":  item.alert_criteria.alert_type.value,
            "target_price": item.alert_criteria.target_price,
            "min_price":   item.alert_criteria.min_price,
            "max_price":   item.alert_criteria.max_price,
            "drop_amount": item.alert_criteria.drop_amount,
            "drop_percent": item.alert_criteria.drop_percent,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  /amazon  Router
# ══════════════════════════════════════════════════════════════════════════════

amazon_router = APIRouter(prefix="/amazon", tags=["Amazon"])


@amazon_router.get("/price", summary="Get current Amazon product price")
async def amazon_price(
    url:       str           = Query(..., description="Amazon product URL"),
    condition: Optional[str] = Query(None, description="Condition tier, e.g. 'Refurbished - Good'"),
) -> Dict[str, Any]:
    """
    Lightweight endpoint — returns price and basic availability only.
    Best for monitoring, alerts, and dashboards.
    """
    if not scrapers.is_valid_amazon_url(url):
        raise HTTPException(status_code=400, detail="Invalid Amazon URL.")
    norm_url = scrapers.normalize_amazon_url(url)
    try:
        result = await asyncio.to_thread(
            lambda: scrapers.get_current_price(norm_url, condition=condition)
        )
    except Exception as e:
        logger.error("amazon/price error: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "status":    "ok",
        "url":       url,
        "asin":      scrapers.normalize_amazon_url(url).split("/dp/")[-1][:10] or None,
        "data":      result,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@amazon_router.get("/product", summary="Get full Amazon product details")
async def amazon_product(
    url: str = Query(..., description="Amazon product URL"),
) -> Dict[str, Any]:
    """
    Full product scrape — title, ASIN, all prices, variants, stock.
    Takes ~15-30 seconds due to JS rendering.
    """
    if not scrapers.is_valid_amazon_url(url):
        raise HTTPException(status_code=400, detail="Invalid Amazon URL.")
    try:
        result = await asyncio.to_thread(scrapers.get_product_details, url)
    except Exception as e:
        logger.error("amazon/product error: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "status":    "ok",
        "data":      result,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


# ── Amazon item management (preserved from v1) ────────────────────────────────

@amazon_router.post("/items", summary="Track a new Amazon product")
async def amazon_add_item(payload: AddItemRequest) -> Dict[str, Any]:
    if not scrapers.is_valid_amazon_url(payload.url):
        raise HTTPException(status_code=400, detail="Invalid Amazon URL.")
    cfg      = storage.load_config()
    currency = payload.currency or cfg.get("currency") or "USD"
    location = payload.location or cfg.get("location") or "Unknown"
    try:
        details = await asyncio.to_thread(scrapers.get_product_details, payload.url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch product: {exc}")
    effective = cli_main._effective_price(details.get("price"), details.get("prime_price"))
    criteria  = _criteria_from_payload(payload.alert_criteria)
    item = TrackedItem(
        id                    = str(uuid.uuid4()),
        url                   = details.get("normalized_url", payload.url),
        title                 = details.get("title", "Unknown Product"),
        asin                  = details.get("asin", ""),
        currency              = currency,
        location              = location,
        alert_criteria        = criteria,
        selected_variants     = payload.selected_variants or {},
        last_price            = effective,
        last_original_price   = details.get("original_price"),
        last_prime_price      = details.get("prime_price"),
        last_discount_percent = details.get("discount_percent"),
        baseline_price        = effective,
        is_prime_eligible     = details.get("is_prime_eligible", False),
        in_stock              = details.get("in_stock", True),
        date_added            = datetime.now().isoformat(),
        last_checked          = datetime.now().isoformat(),
    )
    storage.add_item(item)
    return {"status": "ok", "item": _item_to_payload(item)}


@amazon_router.get("/items", summary="List all tracked Amazon products")
async def amazon_list_items() -> List[Dict[str, Any]]:
    return [_item_to_payload(i) for i in storage.load_items()]


@amazon_router.post("/items/{item_id}/check", summary="Check price for one tracked item")
async def amazon_check_item(item_id: str) -> Dict[str, Any]:
    items = storage.load_items()
    item  = next((i for i in items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found.")
    cfg     = storage.load_config()
    updated = await asyncio.to_thread(cli_main._check_one, item, cfg)
    return {"status": "ok", "item": _item_to_payload(updated)}


@amazon_router.post("/monitor/check-all", summary="Check all tracked Amazon items")
async def amazon_check_all() -> Dict[str, Any]:
    cfg   = storage.load_config()
    items = storage.load_items()
    updated = []
    for item in items:
        u = await asyncio.to_thread(cli_main._check_one, item, cfg)
        updated.append(_item_to_payload(u))
    return {"status": "ok", "checked_count": len(updated), "items": updated}


# ══════════════════════════════════════════════════════════════════════════════
#  /google  Router
# ══════════════════════════════════════════════════════════════════════════════

google_router = APIRouter(prefix="/google", tags=["Google"])


@google_router.get("/search", summary="Google web search (SERP)")
async def google_search(
    query: str           = Query(..., description="Search query"),
    num:   int           = Query(10, ge=1, le=20, description="Number of results"),
    lang:  str           = Query("en", description="Language code"),
) -> Dict[str, Any]:
    """Returns organic results, People Also Ask, and related searches."""
    try:
        result = await asyncio.to_thread(scrapers.search, query, num, lang)
    except Exception as e:
        logger.error("google/search error: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "data": result, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}


@google_router.get("/shopping", summary="Google Shopping product search")
async def google_shopping(
    query:   str = Query(..., description="Product search query"),
    country: str = Query("us", description="Two-letter country code"),
    lang:    str = Query("en", description="Language code"),
) -> Dict[str, Any]:
    """Returns product cards: title, price, store, rating, reviews."""
    try:
        result = await asyncio.to_thread(scrapers.shopping_search, query, country, lang)
    except Exception as e:
        logger.error("google/shopping error: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "data": result, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}


@google_router.get("/news", summary="Google News search")
async def google_news(
    query:   str = Query(..., description="News search query"),
    lang:    str = Query("en", description="Language code"),
    country: str = Query("US", description="Two-letter country code"),
) -> Dict[str, Any]:
    """Returns news articles: title, source, published time, URL, thumbnail."""
    try:
        result = await asyncio.to_thread(scrapers.news_search, query, lang, country)
    except Exception as e:
        logger.error("google/news error: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "data": result, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}


# ══════════════════════════════════════════════════════════════════════════════
#  /ebay  Router
# ══════════════════════════════════════════════════════════════════════════════

ebay_router = APIRouter(prefix="/ebay", tags=["eBay"])


@ebay_router.get("/product", summary="Get eBay listing details")
async def ebay_product(
    url: str = Query(..., description="Full eBay listing URL"),
) -> Dict[str, Any]:
    """Returns title, price, condition, seller, feedback, shipping, stock."""
    try:
        result = await asyncio.to_thread(scrapers.get_listing, url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("ebay/product error: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "data": result, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}


# ══════════════════════════════════════════════════════════════════════════════
#  /web  Router
# ══════════════════════════════════════════════════════════════════════════════

web_router = APIRouter(prefix="/web", tags=["Web"])


@web_router.get("/fetch", summary="Fetch rendered HTML for any URL")
async def web_fetch(
    url:          str  = Query(..., description="URL to fetch"),
    include_text: bool = Query(False, description="Include plain-text extraction"),
) -> Dict[str, Any]:
    """
    Generic web unblocker — returns fully rendered HTML for any URL.
    Useful for pages requiring JavaScript execution.
    """
    try:
        result = await asyncio.to_thread(scrapers.fetch_html, url, include_text)
    except Exception as e:
        logger.error("web/fetch error: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "data": result, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}


# ══════════════════════════════════════════════════════════════════════════════
#  System / utility endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health", tags=["System"], summary="Health check")
async def health() -> Dict[str, Any]:
    import engine as eng
    return {
        "status":  "ok",
        "version": "2.0.0",
        "engine":  "browserless" if eng.using_browserless() else "playwright",
    }


@app.get("/validate", tags=["Utility"], summary="Validate an Amazon URL")
async def validate_url(url: str = Query(...)) -> Dict[str, Any]:
    is_valid = scrapers.is_valid_amazon_url(url)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Amazon URL.")
    norm = scrapers.normalize_amazon_url(url)
    import re
    m    = re.search(r"/dp/([A-Z0-9]{10})", norm)
    return {"valid": True, "normalized_url": norm, "asin": m.group(1) if m else None}


@app.get("/", tags=["System"], summary="API root")
async def root() -> Dict[str, Any]:
    return {
        "name":    "Open Data API",
        "version": "2.0.0",
        "docs":    "/docs",
        "endpoints": {
            "amazon_price":    "GET /amazon/price?url=",
            "amazon_product":  "GET /amazon/product?url=",
            "google_search":   "GET /google/search?query=",
            "google_shopping": "GET /google/shopping?query=",
            "google_news":     "GET /google/news?query=",
            "ebay_product":    "GET /ebay/product?url=",
            "web_fetch":       "GET /web/fetch?url=",
            "health":          "GET /health",
        },
        "source": "https://github.com/",
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Error handlers
# ══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "error": exc.detail, "code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": "Internal server error", "code": 500},
    )


# ── Register routers ──────────────────────────────────────────────────────────

app.include_router(amazon_router)
app.include_router(google_router)
app.include_router(ebay_router)
app.include_router(web_router)


# ── Dev server ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        log_level="info",
    )
