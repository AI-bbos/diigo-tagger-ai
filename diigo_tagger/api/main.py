# ABOUTME: Main FastAPI application with security middleware and routing
# ABOUTME: Implements rate limiting, CORS, security headers, and request ID tracking

import uuid
import logging
import os
import sys
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging BEFORE any other imports that use logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .routes import health, bookmarks
from ..db import get_session

logger = logging.getLogger(__name__)

# Global sync progress tracker (simple in-memory storage)
sync_progress = {
    "downloaded": 0,
    "new_bookmarks": 0,
    "updated_bookmarks": 0,
    "new_tags": 0,
    "updated_tags": 0,
    "active": False
}

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
app.include_router(bookmarks.router, prefix="/api/v1", tags=["bookmarks"])

# TODO: Add additional routers in future phases
# app.include_router(tags.router, prefix="/api/v1", tags=["tags"])
# app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])


# Mount static files
static_dir = Path(__file__).parent.parent / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = Path(__file__).parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# Web UI routes
@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    q: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    sort: str = "created_desc"
):
    """
    Homepage - bookmark list with search.

    Displays paginated bookmarks with optional Lucene query search.
    """
    from .routes.bookmarks import BookmarkService

    session = get_session()
    try:
        service = BookmarkService(session=session)
        result = service.search_bookmarks(
            query=q,
            page=page,
            limit=limit,
            sort=sort
        )

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "bookmarks": result["bookmarks"],
                "pagination": result["pagination"],
                "query": result["query"],
                "sort": sort,
                "active_nav": "bookmarks"
            }
        )
    except ValueError as e:
        # Invalid query - show error
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "bookmarks": [],
                "pagination": None,
                "query": q,
                "error": str(e),
                "sort": sort,
                "active_nav": "bookmarks"
            }
        )
    finally:
        session.close()


@app.get("/help", response_class=HTMLResponse)
async def help_index(request: Request):
    """Help index page."""
    return templates.TemplateResponse(
        "help_index.html",
        {"request": request, "active_nav": "help"}
    )


@app.get("/help/display-ids", response_class=HTMLResponse)
async def help_display_ids(request: Request):
    """Help page explaining Display IDs."""
    return templates.TemplateResponse(
        "help.html",
        {"request": request, "active_nav": "help"}
    )


@app.get("/help/database-operations", response_class=HTMLResponse)
async def help_database_operations(request: Request):
    """Help page for database operations (dangerous zone)."""
    return templates.TemplateResponse(
        "help_database.html",
        {"request": request, "active_nav": "help"}
    )


@app.get("/help/search-syntax", response_class=HTMLResponse)
async def help_search_syntax(request: Request):
    """Help page for search query syntax."""
    return templates.TemplateResponse(
        "help_search.html",
        {"request": request, "active_nav": "help"}
    )


@app.get("/tags", response_class=HTMLResponse)
async def tags_page(request: Request):
    """Tag statistics and analytics dashboard."""
    from .routes.bookmarks import TagModel
    from ..services.tag_service import TagService

    session = get_session()
    try:
        service = TagService(session=session)
        stats = service.get_statistics()
        return templates.TemplateResponse(
            "tags.html",
            {"request": request, "active_nav": "tags", "stats": stats}
        )
    finally:
        session.close()


@app.get("/tags/suggestions", response_class=HTMLResponse)
async def tag_suggestions_page(request: Request):
    """AI-powered tag cleanup suggestions page."""
    return templates.TemplateResponse(
        "tag_suggestions.html",
        {"request": request, "active_nav": "tags"}
    )


@app.get("/add", response_class=HTMLResponse)
async def add_bookmark_page(request: Request):
    """Add bookmark page."""
    return templates.TemplateResponse(
        "add_bookmark.html",
        {"request": request, "active_nav": "add"}
    )


@app.get("/sync", response_class=HTMLResponse)
async def sync_page(request: Request):
    """Sync from Diigo page."""
    return templates.TemplateResponse(
        "sync.html",
        {"request": request, "active_nav": "bookmarks"}
    )


@app.get("/api/sync/progress")
async def sync_progress_stream(request: Request):
    """
    Server-Sent Events endpoint for sync progress updates.

    Streams progress updates while sync is active, then sends completion event.
    """
    from fastapi.responses import StreamingResponse
    import asyncio
    import json

    async def event_generator():
        last_state = {}

        # Stream progress updates while active
        while sync_progress["active"] or not sync_progress.get("complete", False):
            current_state = {
                "downloaded": sync_progress["downloaded"],
                "new_bookmarks": sync_progress["new_bookmarks"],
                "updated_bookmarks": sync_progress["updated_bookmarks"],
                "new_tags": sync_progress["new_tags"],
                "updated_tags": sync_progress["updated_tags"],
                "active": sync_progress["active"],
                "complete": sync_progress.get("complete", False),
                "error": sync_progress.get("error")
            }

            # Send update if state changed
            if current_state != last_state:
                yield f"data: {json.dumps(current_state)}\n\n"
                last_state = current_state.copy()
                logger.debug(f"SSE sent: {current_state}")

            # Exit if complete
            if sync_progress.get("complete", False):
                logger.info("SSE: Sync complete, closing stream")
                break

            await asyncio.sleep(0.1)  # Check every 100ms

        # Send final completion event
        final_state = {
            "downloaded": sync_progress["downloaded"],
            "new_bookmarks": sync_progress["new_bookmarks"],
            "updated_bookmarks": sync_progress["updated_bookmarks"],
            "new_tags": sync_progress["new_tags"],
            "updated_tags": sync_progress["updated_tags"],
            "active": False,
            "complete": True,
            "error": sync_progress.get("error")
        }
        yield f"data: {json.dumps(final_state)}\n\n"
        logger.info(f"SSE: Final state sent: {final_state}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@app.post("/api/sync", response_class=HTMLResponse)
async def sync_from_diigo(request: Request):
    """
    Trigger sync from Diigo in a background thread.

    Returns HTMX-compatible HTML fragment that triggers SSE progress monitoring.
    """
    logger.info("=== SYNC ENDPOINT CALLED ===")
    import threading
    from .routes.bookmarks import BookmarkService
    from ..clients.diigo_client import DiigoClient

    # Parse form data
    form = await request.form()
    mode = form.get("mode", "incremental")
    logger.info(f"Sync mode: {mode}")
    count = int(form.get("count", 50)) if form.get("count") else 50

    # Determine sync parameters
    if mode == "full":
        fetch_all = True
        target_new_tags = 0
    elif mode == "custom":
        fetch_all = False
        target_new_tags = count
    else:  # incremental
        fetch_all = False
        target_new_tags = 50

    # Check for required credentials
    api_key = os.getenv("DIIGO_API_KEY")
    username = os.getenv("DIIGO_USERNAME")
    password = os.getenv("DIIGO_PASSWORD")

    if not all([api_key, username, password]):
        return HTMLResponse("""
            <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex">
                    <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Missing Credentials</h3>
                        <p class="mt-1 text-sm text-red-700">
                            Please set DIIGO_API_KEY, DIIGO_USERNAME, and DIIGO_PASSWORD in your .env file
                        </p>
                    </div>
                </div>
            </div>
        """)

    # Reset and activate progress tracking
    sync_progress["downloaded"] = 0
    sync_progress["new_bookmarks"] = 0
    sync_progress["updated_bookmarks"] = 0
    sync_progress["new_tags"] = 0
    sync_progress["updated_tags"] = 0
    sync_progress["active"] = True
    sync_progress["error"] = None
    sync_progress["complete"] = False

    def run_sync_in_thread():
        """Run the sync operation in a background thread."""
        session = None
        try:
            logger.info("Starting background sync thread")
            # Create clients and service in the thread
            session = get_session()
            diigo_client = DiigoClient(api_key=api_key, username=username, password=password)
            service = BookmarkService(session=session, diigo_client=diigo_client)

            # Progress callback to update counters
            def progress_callback(downloaded, new_bookmarks, updated_bookmarks, new_tags, updated_tags):
                sync_progress["downloaded"] = downloaded
                sync_progress["new_bookmarks"] = new_bookmarks
                sync_progress["updated_bookmarks"] = updated_bookmarks
                sync_progress["new_tags"] = new_tags
                sync_progress["updated_tags"] = updated_tags
                logger.info(f"Progress update: downloaded={downloaded}, new_bm={new_bookmarks}, updated_bm={updated_bookmarks}")

            # Run sync with progress callback
            downloaded, new_bookmarks, updated_bookmarks, new_tags, updated_tags = service.sync(
                target_new_tags=target_new_tags,
                fetch_all=fetch_all,
                progress_callback=progress_callback
            )

            # Mark as complete
            sync_progress["complete"] = True
            logger.info(f"Sync complete: {downloaded} downloaded, {new_bookmarks} new, {updated_bookmarks} updated")

        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            sync_progress["error"] = str(e)
            sync_progress["complete"] = True

        finally:
            # Deactivate progress tracking
            sync_progress["active"] = False
            if session:
                session.close()
            logger.info("Background sync thread finished")

    # Start sync in background thread
    sync_thread = threading.Thread(target=run_sync_in_thread, daemon=True)
    sync_thread.start()
    logger.info("Background sync thread started")

    # Return empty response - progress is handled by SSE
    return HTMLResponse("")


logger.info("FastAPI application initialized")
