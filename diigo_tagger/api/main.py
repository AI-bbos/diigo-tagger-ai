# ABOUTME: Main FastAPI application with security middleware and routing
# ABOUTME: Implements rate limiting, CORS, security headers, and request ID tracking

import uuid
import logging
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .routes import health

logger = logging.getLogger(__name__)

# Rate limiter configuration (security requirement H-1)
limiter = Limiter(key_func=get_remote_address)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request for tracing.

    Security requirement: L-1 (observability)
    """
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Security requirements: M-3 (security headers)
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limit request body size to prevent memory exhaustion.

    Security requirement: H-3 (resource exhaustion prevention)
    """
    MAX_REQUEST_SIZE = 1_000_000  # 1MB

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')

        if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": "Request too large (max 1MB)",
                    "error_code": "REQUEST_TOO_LARGE"
                }
            )

        return await call_next(request)


# Create FastAPI app
app = FastAPI(
    title="Diigo Tagger API",
    description="""
    Bookmark management system with AI-powered tagging.

    ## Features
    * **Bookmarks**: Add, search, and manage bookmarks
    * **Tags**: AI-generated tags with normalization and merging
    * **Search**: Lucene query syntax powered by luqum
    * **Analytics**: Interest graph and trend visualization
    * **LLM**: Multi-provider support (OpenAI, Anthropic, Google)

    ## Authentication
    Currently in development mode (no auth required).
    Future: JWT bearer token authentication.
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add middleware (order matters - first added = outermost)
# 1. Request ID (outermost - for all requests)
app.add_middleware(RequestIDMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Request size limit
app.add_middleware(RequestSizeLimitMiddleware)

# 4. CORS (development - localhost only)
# Security requirement: M-1 (CORS hardening)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://localhost:3000",  # Future: separate frontend dev server
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Explicit only
    allow_headers=[
        "Content-Type",
        "Authorization",  # For future JWT
        "X-Request-ID"
    ],
    expose_headers=["X-Request-ID"],
)

# Global exception handler (security requirement: M-3)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for unexpected errors.

    Prevents leaking sensitive information in error messages.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Log full details server-side
    logger.error(
        f"Unexpected error: {exc}",
        exc_info=True,
        extra={"request_id": request_id}
    )

    # Return minimal info to client
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "request_id": request_id
        }
    )


# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])

# TODO: Add additional routers in future phases
# app.include_router(bookmarks.router, prefix="/api/v1", tags=["bookmarks"])
# app.include_router(tags.router, prefix="/api/v1", tags=["tags"])
# app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])


# Mount static files
static_dir = Path(__file__).parent.parent / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = Path(__file__).parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# Web UI routes (placeholder for Phase 1+)
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Homepage - bookmark list.

    Phase 0: Basic template
    Phase 1: Will add search and bookmark display
    """
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


logger.info("FastAPI application initialized")
