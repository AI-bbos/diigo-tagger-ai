# REST API Design
**Project**: Diigo Tagger AI - Web Interface
**Created**: 2025-11-04
**Branch**: `feat/web-ui`
**Status**: System Architecture Phase

---

## Table of Contents
1. [API Principles](#api-principles)
2. [Base Configuration](#base-configuration)
3. [Endpoints by Phase](#endpoints-by-phase)
4. [Request/Response Schemas](#requestresponse-schemas)
5. [Error Handling](#error-handling)
6. [Authentication Placeholder](#authentication-placeholder)
7. [CORS & Security](#cors--security)
8. [OpenAPI Documentation](#openapi-documentation)

---

## API Principles

### Design Philosophy
- **RESTful**: Use standard HTTP methods (GET, POST, PUT, DELETE)
- **Stateless**: No server-side session state
- **Thin Layer**: All business logic in services, API just validates and routes
- **Hypermedia-Ready**: Design for HTMX partial responses
- **Auth-Ready**: Structure supports easy middleware insertion

### HTTP Methods
- `GET`: Retrieve resources (idempotent)
- `POST`: Create resources or complex queries
- `PUT`: Update entire resource (idempotent)
- `PATCH`: Partial update (not used initially)
- `DELETE`: Remove resources

### Response Codes
- `200 OK`: Successful GET/PUT
- `201 Created`: Successful POST (new resource)
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Validation error
- `401 Unauthorized`: Missing/invalid auth (future)
- `403 Forbidden`: Insufficient permissions (future)
- `404 Not Found`: Resource doesn't exist
- `409 Conflict`: Duplicate resource (bookmark conflict)
- `422 Unprocessable Entity`: Semantic validation error
- `500 Internal Server Error`: Unexpected server error

---

## Base Configuration

### FastAPI App Structure

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(
    title="Diigo Tagger API",
    description="Bookmark management with AI-powered tagging",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS (localhost initially)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Future: frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Templates
templates = Jinja2Templates(directory="web/templates")

# Include routers
from api.routes import health, bookmarks, tags, analytics

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(bookmarks.router, prefix="/api", tags=["bookmarks"])
app.include_router(tags.router, prefix="/api", tags=["tags"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
```

### URL Structure

```
Base URL: http://localhost:8000

/api/                    # API endpoints (JSON)
├── /health              # Health check
├── /bookmarks           # Bookmark operations
├── /tags                # Tag operations
└── /analytics           # Analytics/reporting

/                        # Web UI (HTML)
├── /                    # Homepage (bookmark list)
├── /add                 # Add bookmark form
├── /tags                # Tag management
└── /graph               # Interest graph
```

---

## Endpoints by Phase

### Phase 0: Foundation

#### Health Check

```http
GET /api/health
```

**Response 200:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "llm_providers": {
    "openai": "available",
    "anthropic": "available",
    "gemini": "unavailable"
  }
}
```

---

### Phase 1: View/Search Bookmarks

#### List Bookmarks (Paginated)

```http
GET /api/bookmarks?page=1&limit=50&q=title:*neural* AND tags:(python OR tutorial)&sort=created_desc
```

**Query Parameters:**
- `page` (int, default=1): Page number
- `limit` (int, default=50, max=100): Items per page
- `q` (string, optional): **Lucene query syntax** (see Query Language section below)
- `sort` (enum: created_desc|created_asc|title_asc, default=created_desc): Sort order

**Query Language (Lucene Syntax):**

Powered by **luqum** library for full Lucene query support.

**Basic Syntax:**
```
field:value              # Field match (substring)
field:*value*            # Explicit wildcard
field:"exact phrase"     # Exact phrase match
term                     # Search all fields for term
term1 AND term2          # Boolean AND
term1 OR term2           # Boolean OR
-field:value             # Negation (NOT)
NOT field:value          # Negation (explicit)
(grouped) AND queries    # Grouping with parentheses
```

**Examples:**
```
# Simple field search
title:neural
description:swimming
url:youtube.com

# Tag filtering (single)
tags:python

# Tag filtering (multiple - AND)
tags:python AND tags:tutorial

# Tag filtering (multiple - OR)
tags:(python OR javascript)

# Combined filters
title:*neural* AND tags:python
title:*neural* OR title:*network*

# Negation
tags:python -tags:beginner
tags:python NOT tags:beginner

# Complex queries
(title:neural OR title:network) AND tags:(python OR ai) -tags:beginner

# Search all fields (no field specified)
machine learning          # Finds "machine" AND "learning" in any field
"machine learning"        # Finds exact phrase in any field
```

**Supported Fields:**
- `title`: Bookmark title
- `description`: Bookmark description
- `url`: Bookmark URL
- `tags`: Tag names (exact match)

**Response 200:**
```json
{
  "bookmarks": [
    {
      "id": 123,
      "display_id": "P7K9M",
      "url": "https://example.com/article",
      "title": "How to Learn Python",
      "description": "A beginner's guide...",
      "tags": ["python", "tutorial", "programming"],
      "created_at": "2025-11-01T10:30:00Z",
      "updated_at": "2025-11-01T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total_items": 150,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

#### Get Single Bookmark

```http
GET /api/bookmarks/{display_id}
```

**Path Parameters:**
- `display_id` (string): Bookmark display ID (e.g., "P7K9M")

**Response 200:**
```json
{
  "id": 123,
  "display_id": "P7K9M",
  "url": "https://example.com/article",
  "title": "How to Learn Python",
  "description": "A beginner's guide to Python programming",
  "tags": ["python", "tutorial", "programming"],
  "metadata": {
    "content_type": "webpage",
    "fetched_at": "2025-11-01T10:29:00Z"
  },
  "created_at": "2025-11-01T10:30:00Z",
  "updated_at": "2025-11-01T10:30:00Z"
}
```

**Response 404:**
```json
{
  "detail": "Bookmark not found",
  "error_code": "BOOKMARK_NOT_FOUND",
  "display_id": "P7K9M"
}
```

---

### Phase 2: Add Bookmarks

#### Create Bookmark

```http
POST /api/bookmarks
Content-Type: application/json
```

**Request Body:**
```json
{
  "url": "https://youtube.com/watch?v=abc123",  // REQUIRED
  "title": "Swimming Techniques",               // optional
  "description": "Tutorial on freestyle",       // optional
  "tags": ["swimming", "sport", "tutorial"],    // optional
  "conflict_resolution": "nns"                  // optional (if known duplicate)
}
```

**Response 201 (Success - New Bookmark):**
```json
{
  "id": 124,
  "display_id": "Q8R3T",
  "url": "https://youtube.com/watch?v=abc123",
  "title": "Swimming Techniques",
  "description": "Tutorial on freestyle swimming",
  "tags": ["swimming", "sport", "tutorial", "fitness"],  // LLM may add more
  "metadata": {
    "content_type": "youtube",
    "fetched_title": "Swimming Techniques",
    "fetched_keywords": ["swimming", "sport", "fitness"],
    "llm_provider": "anthropic",
    "llm_model": "claude-3-haiku-20240307"
  },
  "created_at": "2025-11-04T14:20:00Z",
  "updated_at": "2025-11-04T14:20:00Z"
}
```

**Response 409 (Conflict - Duplicate Detected):**
```json
{
  "conflict": true,
  "existing": {
    "id": 120,
    "display_id": "M5N8P",
    "url": "https://youtube.com/watch?v=abc123",
    "title": "Swim Tutorial",
    "description": "Learn freestyle swimming",
    "tags": ["swimming", "tutorial"]
  },
  "new": {
    "url": "https://youtube.com/watch?v=abc123",
    "title": "Swimming Techniques",
    "description": "Tutorial on freestyle swimming",
    "tags": ["swimming", "sport", "tutorial", "fitness"]
  },
  "suggestions": {
    "title": "Swimming Techniques",      // LLM suggested (if different)
    "description": "Tutorial on freestyle swimming",
    "tags": ["swimming", "sport", "tutorial", "fitness"]
  },
  "message": "Bookmark already exists. Provide conflict_resolution to update."
}
```

**Response 400 (Validation Error):**
```json
{
  "detail": [
    {
      "loc": ["body", "url"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### Resolve Conflict

When a conflict occurs (409 response), client can retry with `conflict_resolution` code:

```http
POST /api/bookmarks
Content-Type: application/json
```

**Request Body:**
```json
{
  "url": "https://youtube.com/watch?v=abc123",
  "title": "Swimming Techniques",
  "description": "Tutorial on freestyle swimming",
  "tags": ["swimming", "sport", "tutorial"],
  "conflict_resolution": "nns"  // n=new, o=original, s=smart(LLM)
}
```

**Resolution Codes:**
- Format: 3 characters for `[title][description][tags]`
- Values: `n` (new), `o` (original), `s` (smart/LLM)
- Examples:
  - `"nnn"`: Use all new values
  - `"ooo"`: Keep all original values (no update)
  - `"nns"`: New title, new description, smart tags (merge)
  - `"sos"`: Smart title, original description, smart tags

**Response 200 (Updated):**
```json
{
  "id": 120,
  "display_id": "M5N8P",
  "url": "https://youtube.com/watch?v=abc123",
  "title": "Swimming Techniques",  // Updated per resolution
  "description": "Learn freestyle swimming",  // Kept original
  "tags": ["swimming", "sport", "tutorial", "fitness"],  // Smart merge
  "updated_at": "2025-11-04T14:22:00Z"
}
```

---

### Phase 3: Tag Management

#### List Tags

```http
GET /api/tags?sort=count&limit=100&q=python
```

**Query Parameters:**
- `sort` (enum: count|date|similarity, default=count): Sort order
  - `count`: Sort by usage count (descending)
  - `date`: Sort by creation date (newest first)
  - `similarity`: Sort by semantic similarity (requires `reference_tag`)
- `limit` (int, default=100, max=500): Max tags to return
- `q` (string, optional): Alpha substring search
- `reference_tag` (string, optional): Required if `sort=similarity`

**Response 200:**
```json
{
  "tags": [
    {
      "name": "python",
      "count": 45,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2025-11-04T12:00:00Z"
    },
    {
      "name": "programming",
      "count": 38,
      "created_at": "2024-01-10T09:00:00Z",
      "updated_at": "2025-11-03T15:30:00Z"
    }
  ],
  "total": 2
}
```

#### Get Related Tags (Vector Similarity)

```http
GET /api/tags/related/{tag_name}?limit=10
```

**Path Parameters:**
- `tag_name` (string): Tag to find related tags for

**Query Parameters:**
- `limit` (int, default=10, max=50): Max related tags

**Response 200:**
```json
{
  "tag": "python",
  "related": [
    {
      "name": "programming",
      "similarity": 0.89,
      "count": 38
    },
    {
      "name": "scripting",
      "similarity": 0.76,
      "count": 12
    },
    {
      "name": "automation",
      "similarity": 0.71,
      "count": 8
    }
  ]
}
```

**Response 404:**
```json
{
  "detail": "Tag not found or has no embedding",
  "error_code": "TAG_NOT_FOUND",
  "tag": "nonexistent-tag"
}
```

#### Get Tag Suggestions (Context-Aware)

```http
GET /api/tags/suggestions?q=pyth&url=https://example.com
```

**Query Parameters:**
- `q` (string): Partial tag query (for autocomplete)
- `url` (string, optional): URL context for same-TLD suggestions

**Response 200:**
```json
{
  "suggestions": [
    {
      "name": "python",
      "count": 45,
      "match_type": "prefix"
    },
    {
      "name": "pytest",
      "count": 8,
      "match_type": "substring"
    },
    {
      "name": "jupyter",
      "count": 12,
      "match_type": "same_tld",  // If url is from jupyter.org
      "reason": "Used with other bookmarks from jupyter.org"
    }
  ]
}
```

#### Merge Tags

```http
POST /api/tags/merge
Content-Type: application/json
```

**Request Body:**
```json
{
  "source_tags": ["javascript", "js", "ecmascript"],
  "target_tag": "JavaScript"  // Proper noun capitalization
}
```

**Response 200:**
```json
{
  "target_tag": "JavaScript",
  "merged_count": 3,
  "bookmarks_updated": 28,
  "new_count": 73,  // Combined count from all sources
  "message": "Successfully merged 3 tags into 'JavaScript'"
}
```

**Response 400:**
```json
{
  "detail": "Cannot merge tag into itself",
  "error_code": "INVALID_MERGE",
  "source_tags": ["javascript"],
  "target_tag": "javascript"
}
```

---

### Phase 5: Interest Graph & Analytics

#### Get Timeline Data

```http
GET /api/analytics/timeline?granularity=week&start=2025-01-01&end=2025-11-04
```

**Query Parameters:**
- `granularity` (enum: day|week|month, default=week): Time bucket size
- `start` (date, optional): Start date (ISO 8601)
- `end` (date, optional): End date (ISO 8601)

**Response 200:**
```json
{
  "granularity": "week",
  "start_date": "2025-01-01",
  "end_date": "2025-11-04",
  "data": [
    {
      "period": "2025-W01",
      "start_date": "2025-01-01",
      "end_date": "2025-01-07",
      "bookmark_count": 5,
      "new_tags": 12,
      "top_tags": [
        {"name": "python", "count": 3},
        {"name": "tutorial", "count": 2}
      ]
    },
    {
      "period": "2025-W02",
      "start_date": "2025-01-08",
      "end_date": "2025-01-14",
      "bookmark_count": 8,
      "new_tags": 6,
      "top_tags": [
        {"name": "javascript", "count": 4},
        {"name": "web-development", "count": 3}
      ]
    }
  ]
}
```

#### Get Top Tags by Period

```http
GET /api/analytics/top-tags?period=30d&limit=20
```

**Query Parameters:**
- `period` (enum: 7d|30d|90d|all, default=30d): Time period
- `limit` (int, default=20, max=100): Max tags to return

**Response 200:**
```json
{
  "period": "30d",
  "tags": [
    {
      "name": "python",
      "count": 12,
      "trend": "rising",       // rising|stable|declining
      "trend_percentage": 15.5, // % change vs previous period
      "first_used": "2024-03-15T10:00:00Z",
      "last_used": "2025-11-03T14:30:00Z"
    },
    {
      "name": "tutorial",
      "count": 10,
      "trend": "stable",
      "trend_percentage": 2.1,
      "first_used": "2024-02-01T09:00:00Z",
      "last_used": "2025-11-04T11:00:00Z"
    }
  ]
}
```

---

## Request/Response Schemas

### Pydantic Models (api/schemas/)

#### bookmark.py

```python
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, HttpUrl, Field, validator

# Request schemas
class BookmarkCreate(BaseModel):
    """Request body for creating/updating bookmarks."""
    url: HttpUrl
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    conflict_resolution: Optional[str] = Field(
        None,
        regex="^[nos]{3}$",
        description="3-char code: [n=new, o=original, s=smart] for [title][desc][tags]"
    )

    @validator('tags')
    def normalize_tags(cls, v):
        """Normalize tags to lowercase, strip whitespace."""
        if v:
            return [tag.strip().lower() for tag in v if tag.strip()]
        return v

    @validator('url')
    def validate_url_security(cls, v):
        """Ensure HTTPS URLs only (security requirement)."""
        if v.scheme != 'https':
            raise ValueError('Only HTTPS URLs are allowed')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/article",
                "title": "Learn Python",
                "description": "Beginner's guide",
                "tags": ["python", "tutorial"]
            }
        }


# Response schemas
class BookmarkResponse(BaseModel):
    """Standard bookmark response."""
    id: int
    display_id: str
    url: str
    title: str
    description: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy model compatibility


class BookmarkListResponse(BaseModel):
    """Paginated bookmark list."""
    bookmarks: List[BookmarkResponse]
    pagination: dict


class BookmarkConflictResponse(BaseModel):
    """Conflict response (409)."""
    conflict: bool = True
    existing: BookmarkResponse
    new: dict
    suggestions: dict
    message: str
```

#### tag.py

```python
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Request schemas
class TagMergeRequest(BaseModel):
    """Request body for merging tags."""
    source_tags: List[str] = Field(..., min_items=1)
    target_tag: str = Field(..., min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "source_tags": ["javascript", "js"],
                "target_tag": "JavaScript"
            }
        }


# Response schemas
class TagResponse(BaseModel):
    """Standard tag response."""
    name: str
    count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    """Tag list response."""
    tags: List[TagResponse]
    total: int


class RelatedTagResponse(BaseModel):
    """Related tag with similarity score."""
    name: str
    similarity: float = Field(..., ge=0.0, le=1.0)
    count: int


class TagRelatedResponse(BaseModel):
    """Related tags response."""
    tag: str
    related: List[RelatedTagResponse]


class TagSuggestionResponse(BaseModel):
    """Tag suggestion (autocomplete)."""
    name: str
    count: int
    match_type: Literal["prefix", "substring", "same_tld", "semantic"]
    reason: Optional[str] = None


class TagMergeResponse(BaseModel):
    """Tag merge result."""
    target_tag: str
    merged_count: int
    bookmarks_updated: int
    new_count: int
    message: str
```

---

## Error Handling

### Error Response Schema

```python
# api/schemas/error.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    """Validation error detail."""
    loc: List[str]  # Field location (e.g., ["body", "url"])
    msg: str        # Error message
    type: str       # Error type (e.g., "value_error.missing")


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str | List[ErrorDetail]
    error_code: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
```

### Custom Exceptions

```python
# api/exceptions.py
from fastapi import HTTPException, status

class BookmarkNotFoundError(HTTPException):
    def __init__(self, display_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": "Bookmark not found",
                "error_code": "BOOKMARK_NOT_FOUND",
                "display_id": display_id
            }
        )

class BookmarkConflictError(HTTPException):
    def __init__(self, existing: dict, new: dict, suggestions: dict):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "conflict": true,
                "existing": existing,
                "new": new,
                "suggestions": suggestions,
                "message": "Bookmark already exists. Provide conflict_resolution to update."
            }
        )

class TagNotFoundError(HTTPException):
    def __init__(self, tag: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": "Tag not found or has no embedding",
                "error_code": "TAG_NOT_FOUND",
                "tag": tag
            }
        )
```

### Global Exception Handler

```python
# api/main.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unexpected errors."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "request_id": request.state.request_id  # For debugging
        }
    )
```

---

## Authentication Placeholder

### Middleware Structure

```python
# api/middleware/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

# Security scheme (no-op initially)
bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> dict:
    """
    Get current authenticated user.

    PLACEHOLDER: Returns default user (id=1).
    FUTURE: Validate JWT token, query user from DB.
    """
    # TODO: Implement JWT validation when auth is enabled
    # if credentials:
    #     payload = jwt.decode(credentials.credentials, SECRET_KEY)
    #     user = db.query(User).filter_by(id=payload["sub"]).first()
    #     if not user:
    #         raise HTTPException(status_code=401, detail="Invalid token")
    #     return user

    # For now, return default user
    return {
        "id": 1,
        "username": "default",
        "email": "user@localhost"
    }

# Usage in routes:
# @router.get("/bookmarks")
# async def list_bookmarks(user: dict = Depends(get_current_user)):
#     # user is always {"id": 1} for now
#     bookmarks = bookmark_service.list_bookmarks(user_id=user["id"])
#     return bookmarks
```

### Future Auth Flow

When ready to enable authentication:

1. **Install dependencies**: `python-jose[cryptography]`, `passlib[bcrypt]`
2. **Uncomment user tables** in Alembic migration
3. **Implement JWT generation**: Login endpoint returns token
4. **Update `get_current_user`**: Validate token, query DB
5. **Add registration endpoint**: `POST /api/auth/register`
6. **Add login endpoint**: `POST /api/auth/login`

**No changes required in route handlers** - they already accept `user: dict = Depends(get_current_user)`

---

## CORS & Security

### CORS Configuration

```python
# api/main.py
from fastapi.middleware.cors import CORSMiddleware

# Development (localhost)
CORS_ORIGINS_DEV = [
    "http://localhost:8000",
    "http://localhost:3000",  # If separate frontend dev server
    "http://127.0.0.1:8000",
]

# Production (future)
CORS_ORIGINS_PROD = [
    "https://your-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS_DEV,  # TODO: Switch to PROD in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],  # For debugging
)
```

### Input Validation

All input validation handled by **Pydantic schemas**:
- Type checking (string, int, URL)
- Required vs optional fields
- Min/max length, regex patterns
- Custom validators

### Security Headers

```python
# api/middleware/security.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Request ID for tracing
        response.headers["X-Request-ID"] = request.state.request_id

        return response

# Add to app
app.add_middleware(SecurityHeadersMiddleware)
```

### Rate Limiting (Future)

```python
# Future: Add slowapi for rate limiting
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded

# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Usage in routes:
# @router.post("/bookmarks")
# @limiter.limit("10/minute")
# async def create_bookmark(request: Request, ...):
#     ...
```

---

## OpenAPI Documentation

### Automatic Documentation

FastAPI generates OpenAPI schema automatically:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Enhanced Metadata

```python
# api/main.py
from fastapi import FastAPI

tags_metadata = [
    {
        "name": "health",
        "description": "Health check and system status"
    },
    {
        "name": "bookmarks",
        "description": "Bookmark management (create, read, update, search)"
    },
    {
        "name": "tags",
        "description": "Tag operations (list, merge, related tags, suggestions)"
    },
    {
        "name": "analytics",
        "description": "Analytics and reporting (timeline, top tags, trends)"
    }
]

app = FastAPI(
    title="Diigo Tagger API",
    description="""
    Bookmark management system with AI-powered tagging.

    ## Features
    * **Bookmarks**: Add, search, and manage bookmarks
    * **Tags**: AI-generated tags with normalization and merging
    * **Search**: Field-specific search with tag expressions
    * **Analytics**: Interest graph and trend visualization
    * **LLM**: Multi-provider support (OpenAI, Anthropic, Gemini)

    ## Authentication
    Currently in development mode (no auth required).
    Future: JWT bearer token authentication.
    """,
    version="1.0.0",
    contact={
        "name": "Diigo Tagger",
        "url": "https://github.com/yourusername/diigo-tagger",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=tags_metadata,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)
```

### Route Documentation

```python
# api/routes/bookmarks.py
@router.post(
    "/bookmarks",
    response_model=BookmarkResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Bookmark created successfully"},
        409: {
            "description": "Conflict - bookmark already exists",
            "model": BookmarkConflictResponse
        },
        400: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    },
    summary="Create new bookmark",
    description="""
    Create a new bookmark with AI-generated tags.

    **Required**: URL (HTTPS only)
    **Optional**: title, description, tags

    If a bookmark with the same URL already exists, returns 409 Conflict
    with suggestions. Client can retry with conflict_resolution code.

    **Conflict Resolution Codes** (3 chars: [title][description][tags]):
    * `n` = Use new value
    * `o` = Keep original value
    * `s` = Smart merge (LLM suggestion)

    Examples: `nnn` (all new), `ooo` (no change), `nns` (new title/desc, smart tags)
    """,
    tags=["bookmarks"]
)
async def create_bookmark(
    bookmark: BookmarkCreate,
    user: dict = Depends(get_current_user)
) -> BookmarkResponse:
    ...
```

---

## Next Steps

1. ✅ **System Architect Review**: This document
2. ⏳ **Security Engineer**: Audit this design for vulnerabilities
3. ⏳ **Phase 0 Implementation**: Build FastAPI app skeleton with these endpoints

---

**Questions for Security Engineer:**

1. Are CORS settings secure for development?
2. Is HTTPS-only validation sufficient for URLs?
3. Should we add request ID middleware for tracing?
4. Rate limiting strategy for API endpoints?
5. Any missing security headers or validations?
