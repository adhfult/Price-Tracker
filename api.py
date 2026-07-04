"""
FastAPI web server for Amazon Price Tracker.
Exposes scraping functionality as REST API endpoints for RapidAPI integration.

Deploy to: PythonAnywhere / Render / Railway
Base URL: https://yourusername.pythonanywhere.com (example)
RapidAPI Base URL: Set to above in RapidAPI Studio
"""

import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging

import scraper

# ══════════════════════════════════════════════════════════════════════════════
#  Configuration
# ══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(
    title="Amazon Price Scraper API",
    description="Real-time Amazon product price scraping with Playwright. Monetized via RapidAPI.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for RapidAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  Response Models
# ══════════════════════════════════════════════════════════════════════════════

class PriceResponse(BaseModel):
    status: str = Field(..., example="success")
    data: Dict[str, Any] = Field(..., description="Price and product data")
    url: str = Field(..., description="The Amazon URL that was scraped")
    asin: Optional[str] = Field(None, description="Amazon Standard Identification Number")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the request")


class FullDetailsResponse(BaseModel):
    status: str = Field(..., example="success")
    data: Dict[str, Any] = Field(..., description="Complete product details")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the request")


class ErrorResponse(BaseModel):
    status: str = Field(default="error")
    error: str = Field(..., description="Error message")
    code: int = Field(..., description="HTTP status code")


class HealthResponse(BaseModel):
    status: str = Field(default="online")
    version: str = Field(default="1.0.0")
    service: str = Field(default="Amazon Price Scraper API")


# ══════════════════════════════════════════════════════════════════════════════
#  Core Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get(
    "/scrape/price",
    response_model=PriceResponse,
    summary="Get Current Price",
    tags=["Scraping"],
    responses={
        200: {"description": "Successfully scraped price data"},
        400: {"description": "Invalid URL or Amazon returned an error"},
        429: {"description": "Rate limited by Amazon"},
        500: {"description": "Server error during scraping"},
    }
)
async def get_price(
    url: str = Query(
        ...,
        description="Full Amazon product URL (e.g., https://www.amazon.com/dp/B0DHJ896RY)",
        min_length=10,
    ),
    condition: Optional[str] = Query(
        None,
        description="Product condition tier (e.g., 'Refurbished - Good') to get specific price",
    ),
) -> PriceResponse:
    """
    **Lightweight endpoint** - returns only price and key product info.
    
    Best for: price monitoring, alert systems, dashboards.
    
    **Response fields:**
    - `current_price`: Buy-box price (lowest available)
    - `original_price`: List/MSRP
    - `prime_price`: Prime member price (if available)
    - `in_stock`: Boolean stock status
    - `is_prime_eligible`: Boolean Prime eligibility
    
    **Example:**
    ```
    GET /scrape/price?url=https://www.amazon.com/dp/B0DHJ896RY
    ```
    """
    from datetime import datetime
    
    try:
        # Validate URL is Amazon
        if not scraper.is_valid_amazon_url(url):
            raise HTTPException(
                status_code=400,
                detail="Invalid Amazon URL. Must be from amazon.com domain.",
            )
        
        # Normalize URL
        norm_url = scraper.normalize_amazon_url(url)
        logger.info(f"Scraping price for: {norm_url}")
        
        # Get price data
        result = scraper.get_current_price(norm_url, condition=condition)
        
        return PriceResponse(
            status="success",
            data=result,
            url=url,
            asin=scraper._asin(norm_url, None),  # Extract ASIN from URL
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scraping error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to scrape price: {str(e)}",
        )


@app.get(
    "/scrape/full",
    response_model=FullDetailsResponse,
    summary="Get Full Product Details",
    tags=["Scraping"],
    responses={
        200: {"description": "Successfully scraped full product details"},
        400: {"description": "Invalid URL or Amazon returned an error"},
        429: {"description": "Rate limited by Amazon"},
        500: {"description": "Server error during scraping"},
    }
)
async def get_full_details(
    url: str = Query(
        ...,
        description="Full Amazon product URL",
        min_length=10,
    ),
) -> FullDetailsResponse:
    """
    **Comprehensive endpoint** - returns all product data including variants.
    
    Best for: product comparison, catalog scraping, detailed research.
    
    **Response includes:**
    - Product title, ASIN, all prices
    - Stock status, Prime eligibility
    - Variant groups (size, color, storage, etc.)
    - Condition tiers with individual ASINs
    
    **Example:**
    ```
    GET /scrape/full?url=https://www.amazon.com/dp/B0DHJ896RY
    ```
    
    ⚠️ **Note:** This endpoint takes longer (~15-30s) due to rendering variants.
    """
    from datetime import datetime
    
    try:
        if not scraper.is_valid_amazon_url(url):
            raise HTTPException(
                status_code=400,
                detail="Invalid Amazon URL.",
            )
        
        norm_url = scraper.normalize_amazon_url(url)
        logger.info(f"Scraping full details for: {norm_url}")
        
        result = scraper.get_product_details(norm_url)
        
        return FullDetailsResponse(
            status="success",
            data=result,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scraping error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to scrape product details: {str(e)}",
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Utility Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """
    Simple health check endpoint for uptime monitoring.
    
    Use external services like UptimeRobot to monitor this endpoint.
    Returns `200 OK` if service is running.
    """
    return HealthResponse(
        status="online",
        version="1.0.0",
        service="Amazon Price Scraper API",
    )


@app.get(
    "/validate",
    summary="Validate Amazon URL",
    tags=["Utility"],
    responses={
        200: {"description": "URL is valid"},
        400: {"description": "URL is invalid"},
    }
)
async def validate_url(
    url: str = Query(..., description="URL to validate"),
) -> Dict[str, Any]:
    """
    Quickly validate if a URL is a valid Amazon product link.
    
    **Returns:**
    - `valid`: Boolean (true/false)
    - `normalized_url`: Cleaned URL if valid
    - `asin`: Extracted ASIN if valid
    """
    try:
        is_valid = scraper.is_valid_amazon_url(url)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid Amazon URL")
        
        norm_url = scraper.normalize_amazon_url(url)
        import re
        asin_match = re.search(r"/dp/([A-Z0-9]{10})", norm_url)
        asin = asin_match.group(1) if asin_match else None
        
        return {
            "valid": True,
            "normalized_url": norm_url,
            "asin": asin,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  Info & Documentation
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Info"])
async def root() -> Dict[str, Any]:
    """API root endpoint with documentation links."""
    return {
        "service": "Amazon Price Scraper API",
        "version": "1.0.0",
        "docs": "/docs",  # Swagger UI
        "redoc": "/redoc",  # ReDoc
        "endpoints": {
            "price": "GET /scrape/price?url=<amazon_url>",
            "details": "GET /scrape/full?url=<amazon_url>",
            "validate": "GET /validate?url=<amazon_url>",
            "health": "GET /health",
        },
        "rate_limit": "Per RapidAPI subscription plan",
        "response_time": "10-30 seconds per request",
    }


@app.get("/docs-api", tags=["Info"])
async def api_documentation() -> Dict[str, Any]:
    """Comprehensive API documentation."""
    return {
        "title": "Amazon Price Scraper API",
        "description": "Real-time Amazon product scraping via RapidAPI",
        "base_url": "https://yourusername.pythonanywhere.com (example)",
        "authentication": "API key via RapidAPI headers",
        "rate_limiting": {
            "free_tier": "100 requests/month",
            "pro_tier": "1000 requests/month",
            "enterprise": "Custom limits",
        },
        "endpoints": [
            {
                "path": "/scrape/price",
                "method": "GET",
                "params": {
                    "url": "Amazon product URL (required)",
                    "condition": "Product condition tier (optional)",
                },
                "response_time": "10-15 seconds",
                "use_case": "Price monitoring, alerts, dashboards",
            },
            {
                "path": "/scrape/full",
                "method": "GET",
                "params": {"url": "Amazon product URL (required)"},
                "response_time": "20-30 seconds",
                "use_case": "Catalog scraping, variants, detailed research",
            },
            {
                "path": "/validate",
                "method": "GET",
                "params": {"url": "URL to validate"},
                "response_time": "<100ms",
                "use_case": "Quick URL validation before scraping",
            },
        ],
        "examples": {
            "get_price": "curl 'https://yourusername.pythonanywhere.com/scrape/price?url=https://www.amazon.com/dp/B0DHJ896RY'",
            "get_full": "curl 'https://yourusername.pythonanywhere.com/scrape/full?url=https://www.amazon.com/dp/B0DHJ896RY'",
        },
        "support": "Contact via RapidAPI dashboard",
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Error Handlers
# ══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler for consistent error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": exc.detail,
            "code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Catch-all exception handler for unexpected errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": "Internal server error",
            "code": 500,
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Server Info
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        log_level="info",
    )
