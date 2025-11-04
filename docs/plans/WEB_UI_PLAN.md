# Web UI Implementation Plan
**Project**: Diigo Tagger AI - Web Interface
**Created**: 2025-11-04
**Last Updated**: 2025-11-04
**Branch**: `feat/web-ui`
**Status**: Planning Phase (Awaiting Pre-work Completion)
**Approach**: Seven-Agent Workflow (simplified)

---

## Plan Updates (2025-11-04)

### Pre-work Required
- **Current Coverage**: 76% (14 failing tests)
- **Target**: >80% coverage, all tests passing
- **Duration**: 2-3 days
- **Blocker**: Must complete before Phase 0

### Feedback Incorporated

1. **Tag Sorting** - Added "semantically related" option
   - Sort by: count | date | similarity

2. **Tag Expressions** - Designed for evolution
   - Initial: `tags:(woodworking AND tutorial)`
   - Future: `tags:(... OR ...)`, `NOT tags:(...)`, `tags:(...) AND date < 2021`
   - Syntax: Use `tags=` instead of `tags:` to avoid conflict with `<` operator

3. **Conflict Response** - Include existing bookmark ID
   - `{conflict: true, existing: {id, ...}, new: {...}}`

4. **Proper Nouns** - Use canonical downloadable list
   - Source: Tech terms dictionary (researched/curated)
   - Storage: Both service (cache) and DB (persistent)

5. **Multi-user Schema** - Tags are user-specific
   - `ALTER TABLE tags ADD COLUMN user_id INTEGER REFERENCES users(id);`
   - Both bookmarks AND tags have user_id

---

## Executive Summary

Build a web-based interface for Diigo Tagger using **FastAPI + HTMX + Tailwind CSS**, following strict service-layer architecture. All business logic remains in existing services; API and UI are thin wrappers.

**Key Principles:**
- ✅ TDD throughout
- ✅ Thin layers (API/UI) - thick services (existing, reused)
- ✅ LangChain with multi-provider LLM support
- ✅ Design for future auth (placeholders, easy insertion)
- ✅ Containerize for deployment flexibility

---

## Updated Requirements (Post-BSA Feedback)

### Core Corrections

1. **Add Bookmark Form**
   - ❌ ~~URL, title, description required~~
   - ✅ **URL only required** - title, description, tags all optional

2. **Search & Filtering**
   - ✅ Field-specific search (title, description, URL, tags)
   - ✅ Tag conjunctions/expressions (user-written queries)
   - Example: `tag:woodworking AND tag:tutorial`

3. **Tag Management**
   - ✅ Sort by count OR date (toggle)
   - ✅ Related tags via vector similarity
   - ✅ Alpha substring matching
   - ✅ Same-TLD tag suggestions (when searching/adding)

4. **Tag Normalization**
   - ✅ Case-insensitive storage
   - ✅ Auto-lowercase EXCEPT proper nouns
   - ✅ Proper nouns: Capitalized or camelCase
   - Example: `python` but `JavaScript`, `OpenAI`

5. **LLM Provider Strategy**
   - ❌ ~~OpenAI only~~
   - ✅ **LangChain with multi-provider support**
   - ✅ Spot pricing selection (cheapest available)
   - ✅ User supplies own API keys per provider

6. **Phase 5: Interest Graph**
   - ✅ Visualize bookmark/tag trends over time
   - ✅ Show evolving interests
   - ✅ Graph library TBD (Chart.js, Plotly, etc.)

### Deployment & Security

- **Initial**: Localhost (dev/personal use)
- **Future**: Docker container (deploy anywhere)
- **Auth**: None initially, **design with auth placeholders**
  - Routes structured for easy middleware insertion
  - Database ready for user tables (commented out)
  - Future: multi-user, secure, private

---

## Architecture Overview

### Layer Separation

```
┌─────────────────────────────────────────┐
│   Browser (HTMX + Tailwind CSS)        │  ← Thin UI
│   - Templates (Jinja2)                  │
│   - Hypermedia responses                │
└──────────────┬──────────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────────┐
│   FastAPI Routes (api/)                 │  ← Thin API
│   - Input validation (Pydantic)         │
│   - Call services                       │
│   - Return responses                    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Services Layer (EXISTING - REUSE)     │  ← Thick Business Logic
│   - BookmarkService                     │
│   - TagService                          │
│   - MetadataFetcher                     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   LangChain LLM Router (NEW)            │  ← Multi-provider
│   - OpenAI, Anthropic, Gemini, etc.     │
│   - Spot pricing selection              │
│   - Fallback on failure                 │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Database (SQLAlchemy + Alembic)       │
│   - Bookmarks, Tags (existing)          │
│   - [Users] table (future, commented)   │
└─────────────────────────────────────────┘
```

### Directory Structure (New Files)

```
diigo_tagger/
├── api/                          # NEW - FastAPI routes
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, CORS, middleware
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── bookmarks.py          # Bookmark endpoints
│   │   ├── tags.py               # Tag endpoints
│   │   └── health.py             # Health check
│   ├── schemas/                  # Pydantic models
│   │   ├── __init__.py
│   │   ├── bookmark.py
│   │   └── tag.py
│   └── middleware/
│       ├── __init__.py
│       └── auth.py               # Placeholder (no-op initially)
│
├── web/                          # NEW - HTMX UI
│   ├── templates/
│   │   ├── base.html             # Base layout (Tailwind)
│   │   ├── index.html            # Homepage (bookmark list)
│   │   ├── add_bookmark.html     # Add form
│   │   ├── tags.html             # Tag management
│   │   ├── conflict.html         # Conflict resolution
│   │   ├── graph.html            # Interest graph (Phase 5)
│   │   └── partials/             # HTMX partial templates
│   │       ├── bookmark_card.html
│   │       ├── tag_list.html
│   │       └── search_bar.html
│   └── static/
│       ├── css/
│       │   └── tailwind.css
│       └── js/
│           └── htmx.min.js
│
├── clients/
│   ├── llm_router.py             # NEW - LangChain multi-provider
│   └── openai_client.py          # REFACTOR - use via llm_router
│
├── services/                     # EXISTING - minimal changes
│   ├── bookmark_service.py       # Update to use llm_router
│   └── tag_service.py            # Add: related tags, normalization
│
└── cli/                          # EXISTING - no changes
```

---

## Implementation Phases

### Phase 0: Foundation (Week 1)

**Goal:** Set up FastAPI, LangChain, infrastructure

**Tasks:**
1. Add dependencies (FastAPI, Uvicorn, Jinja2, HTMX, Tailwind, LangChain, luqum)
2. Create `LLMRouter` with multi-provider support
3. Refactor `OpenAIClient` → use `LLMRouter`
4. Update CLI to use new `LLMRouter` (verify no breakage)
5. Create FastAPI app structure (`api/main.py`)
6. Add health check endpoint (`GET /health`)
7. Set up Tailwind CSS build process
8. Create base HTML template

**TDD:**
- Test `LLMRouter` with mocked providers
- Test FastAPI app initialization
- Test health check endpoint

**Deliverable:** Working API server with no routes yet, LLM router tested

---

### Phase 1: View Bookmarks with Search/Filter (Week 2)

**Goal:** Display bookmarks, search, filter

**API Routes:**
```python
GET  /api/bookmarks?q=<lucene_query>&page=<n>&limit=<n>&sort=<order>
GET  /api/bookmarks/{display_id}
```

**UI Pages:**
- Homepage: bookmark list (paginated, 50/page)
- Search bar with Lucene query support
- Query builder UI (simple mode for beginners)
- Tag filter chips (clicks generate query)
- Bookmark cards (title, URL, tags, display_id)

**Features:**
- **Lucene query language** (powered by luqum library)
  - Field-specific: `title:neural`, `tags:python`
  - Boolean operators: `AND`, `OR`, `NOT`, `-`
  - Wildcards: `title:*neural*`
  - Phrases: `"machine learning"`
  - Grouping: `(title:neural OR title:network) AND tags:python`
- **Dual UI modes:**
  - Simple mode: Form fields that build query automatically
  - Advanced mode: Direct Lucene query input
- Pagination
- Click tag → adds to query (e.g., `tags:python`)

**TDD:**
- Test bookmark list API (pagination, Lucene queries)
- Test luqum query parsing and SQLAlchemy conversion
- Test query builder UI (form → query string)
- Test UI renders correctly with HTMX

**Deliverable:** Functional bookmark browser with powerful search

---

### Phase 2: Add New Bookmarks (Week 3)

**Goal:** Add bookmarks via web form

**API Routes:**
```python
POST /api/bookmarks
  Body: {url: required, title?: optional, description?: optional, tags?: optional}
  Returns: {bookmark} OR {conflict: true, existing: {id, display_id, ...}, new: {...}}
  # Note: Conflict response includes existing.id for easy reference
```

**UI Pages:**
- Add bookmark form (URL field + optional fields)
- LLM suggestions displayed inline
- Conflict resolution modal (if duplicate)

**Features:**
- URL required, all else optional
- Fetch metadata automatically (YouTube/webpage)
- LLM generates tags (via LangChain router)
- Show AI-generated content before submit
- Conflict resolution UI (side-by-side, radio buttons)

**TDD:**
- Test POST bookmark API
- Test conflict detection
- Test form validation
- Test HTMX partial updates

**Deliverable:** Working add bookmark flow with conflict handling

---

### Phase 3: Tag Management (Week 4)

**Goal:** View, search, merge tags

**API Routes:**
```python
GET  /api/tags?sort=count|date|similarity
GET  /api/tags/{name}
GET  /api/tags/related/{name}          # Vector similarity
GET  /api/tags/suggestions?q=<query>   # Same-TLD, context-aware
POST /api/tags/merge
  Body: {source_tags: [], target_tag: str}
```

**UI Pages:**
- Tag list (toggle sort: count | date | semantic similarity)
- Related tags panel (vector similarity)
- Tag merge interface

**Features:**
- Sort by count OR date OR semantically related (toggle)
- Alpha substring search
- Related tags via vector DB (use sentence-transformers)
- Same-TLD tag suggestions
- Tag normalization (lowercase except proper nouns)
- Merge tags (combine counts, update bookmarks)

**TDD:**
- Test tag list API (sort options)
- Test related tags (vector similarity)
- Test tag merge
- Test normalization rules

**Deliverable:** Tag management with smart suggestions

---

### Phase 4: Conflict Resolution UI (Week 5)

**Goal:** Visual conflict resolution

**Already designed in Phase 2, this is refinement:**
- Side-by-side comparison
- Per-field selection (n/o/s radio buttons)
- Tag diff (common, only current, only new)
- Visual indicators (green/red for changes)

**TDD:**
- Test all resolution codes (nnn, ooo, sss, nns, etc.)
- Test UI state management

**Deliverable:** Polished conflict resolution

---

### Phase 5: Interest Graph Over Time (Week 6)

**Goal:** Visualize bookmark/tag trends

**API Routes:**
```python
GET /api/analytics/timeline?granularity=day|week|month
  Returns: {dates: [], bookmark_counts: [], tag_trends: {}}

GET /api/analytics/top-tags?period=7d|30d|90d|all
  Returns: [{tag, count, trend}]
```

**UI Pages:**
- Graph page with time-series visualization
- Top tags by period
- Interest evolution chart

**Features:**
- Chart.js or Plotly for visualization
- Group by day/week/month
- Show tag trends (rising, stable, declining)
- Highlight evolving interests

**TDD:**
- Test analytics API
- Test data aggregation
- Test chart rendering

**Deliverable:** Interest graph visualization

---

## Technical Decisions

### 1. LangChain Multi-Provider Setup

**Provider Priority (cheapest first):**
1. Check spot pricing API (if available)
2. Fallback order: Anthropic → OpenAI → Google Gemini → Local

**Configuration:**
```python
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# LLMRouter uses LangChain to route
```

**Implementation:**
```python
class LLMRouter:
    def __init__(self):
        self.providers = [
            AnthropicProvider(),
            OpenAIProvider(),
            GeminiProvider()
        ]

    def generate_tags(self, title, description, url):
        # Try providers in order of spot pricing
        for provider in self.get_sorted_by_price():
            try:
                return provider.generate(...)
            except Exception:
                continue
        raise AllProvidersFailedError()
```

### 2. Tag Normalization Strategy

**Approach:** Use canonical downloadable list of tech terms

**Data Sources:**
- GitHub: awesome-tech-terms (community-curated)
- Wikipedia: List of programming languages
- Custom: Common tech brands/products

**Storage Strategy:**
- **Database Table**: `proper_nouns (term_lower VARCHAR PRIMARY KEY, term_proper VARCHAR)`
- **Service Cache**: In-memory dict loaded at startup
- **Update**: Manual refresh/sync from source (Phase 0 setup)

**Implementation:**
```python
class TagNormalizer:
    def __init__(self, db_session):
        # Load from DB into memory for fast lookups
        self.proper_nouns = {
            row.term_lower: row.term_proper
            for row in db_session.query(ProperNoun).all()
        }

    def normalize(self, tag: str) -> str:
        """Normalize to lowercase except proper nouns."""
        lower = tag.lower()
        return self.proper_nouns.get(lower, lower)

# Examples from canonical list:
# javascript → JavaScript
# typescript → TypeScript
# openai → OpenAI
# html → HTML
# css → CSS
```

**Migration:** Create `proper_nouns` table and seed with canonical data in Phase 0

### 3. Auth Placeholder Design

**Now (no auth):**
```python
# api/middleware/auth.py
def get_current_user():
    """Placeholder: returns default user. Future: JWT validation."""
    return {"id": 1, "username": "default"}

# api/routes/bookmarks.py
@router.get("/bookmarks")
async def list_bookmarks(user: dict = Depends(get_current_user)):
    # user is always {"id": 1} for now
    bookmarks = bookmark_service.list_all()
    return bookmarks
```

**Future (with auth):**
```python
# Just change get_current_user implementation:
def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate JWT, return user from DB."""
    payload = jwt.decode(token, SECRET_KEY)
    user = db.query(User).filter_by(id=payload["sub"]).first()
    if not user:
        raise HTTPException(401)
    return user

# Routes unchanged! Just swap middleware.
```

**Database preparation:**
```sql
-- migrations/versions/004_add_users_table.py (commented out initially)
-- Uncomment when ready for multi-user

-- CREATE TABLE users (
--     id INTEGER PRIMARY KEY,
--     username VARCHAR UNIQUE,
--     email VARCHAR UNIQUE,
--     hashed_password VARCHAR
-- );

-- ALTER TABLE bookmarks ADD COLUMN user_id INTEGER REFERENCES users(id);
-- ALTER TABLE tags ADD COLUMN user_id INTEGER REFERENCES users(id);
--
-- NOTE: Both bookmarks AND tags are user-specific
--       Tags are scoped per user (same tag name can exist for different users)
```

### 4. Containerization Prep

**Dockerfile (create but don't use yet):**
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev
COPY . .
EXPOSE 8000
CMD ["uvicorn", "diigo_tagger.api.main:app", "--host", "0.0.0.0"]
```

**docker-compose.yml (for later):**
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///data/diigo.db
```

### 5. Vector DB for Related Tags

**Use existing sentence-transformers:**
```python
# Already in dependencies
from sentence_transformers import SentenceTransformer

class TagService:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def find_related_tags(self, tag_name: str, limit: int = 10):
        """Find semantically similar tags using embeddings."""
        # Compute embeddings for all tags
        # Find cosine similarity
        # Return top N
```

---

## Dependencies to Add

```toml
[tool.poetry.dependencies]
# Web framework
fastapi = "^0.104"
uvicorn = {extras = ["standard"], version = "^0.24"}
jinja2 = "^3.1"
python-multipart = "^0.0.6"  # for form data

# Query parsing
luqum = "^0.13"  # Lucene query parser for search

# LLM routing
langchain = "^0.1"  # already have
langchain-openai = "^0.0.2"
langchain-anthropic = "^0.0.1"
langchain-google-genai = "^0.0.1"

# Already have for vector similarity
sentence-transformers = "^2.2"  # ✓ already installed

[tool.poetry.group.dev.dependencies]
httpx = "^0.25"  # for testing FastAPI
```

---

## Testing Strategy (TDD)

### Test Pyramid

```
       ┌─────────────┐
       │   E2E (5%)  │  Playwright/Selenium (HTMX flows)
       └─────────────┘
      ┌───────────────┐
      │ Integration   │  FastAPI TestClient (API routes)
      │   (20%)       │
      └───────────────┘
    ┌─────────────────────┐
    │   Unit Tests        │  Services, LLMRouter, utilities
    │     (75%)           │
    └─────────────────────┘
```

### Test Files (New)

```
tests/
├── unit/
│   ├── test_llm_router.py         # Multi-provider routing
│   ├── test_tag_normalization.py  # Proper noun handling
│   └── test_bookmark_service.py   # ✓ already exists
│
├── integration/
│   ├── test_api_bookmarks.py      # FastAPI bookmark routes
│   ├── test_api_tags.py           # FastAPI tag routes
│   └── test_api_analytics.py      # Analytics endpoints
│
└── e2e/
    ├── test_add_bookmark_flow.py  # Full add workflow
    └── test_conflict_resolution.py # Conflict UI flow
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LangChain breaking changes | High | Pin versions, test before upgrade |
| HTMX learning curve | Medium | Start simple, use docs heavily |
| Vector similarity performance | Medium | Cache embeddings, use FAISS if needed |
| Tag normalization edge cases | Low | Comprehensive proper noun list, user override |
| Multi-provider API failures | High | Robust fallback, retry logic, circuit breaker |

---

## Success Metrics

1. **Code Quality**
   - ✅ All tests passing (target: 80% coverage)
   - ✅ No business logic in API/UI layers
   - ✅ Clean separation of concerns

2. **Performance**
   - ✅ Bookmark list < 200ms
   - ✅ Search < 500ms
   - ✅ Add bookmark < 2s (including LLM)

3. **User Experience**
   - ✅ Works without JavaScript (progressive enhancement)
   - ✅ Responsive (mobile-friendly via Tailwind)
   - ✅ Accessible (ARIA labels, semantic HTML)

4. **Maintainability**
   - ✅ Auth easy to add (< 1 day)
   - ✅ Docker deployment ready
   - ✅ Multi-user extensible

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Pre-work: Test Coverage** | **2-3 days** | **>80% coverage, all tests passing** |
| Phase 0: Foundation | 1 week | FastAPI + LangChain setup |
| Phase 1: View/Search | 1 week | Bookmark browser |
| Phase 2: Add Bookmarks | 1 week | Add form + conflict UI |
| Phase 3: Tag Management | 1 week | Tag list, merge, suggestions |
| Phase 4: Conflict Polish | 1 week | Refined conflict UX |
| Phase 5: Interest Graph | 1 week | Analytics visualization |
| **Total** | **~6.5 weeks** | Full web UI |

---

## Next Steps

1. **Brooke approves this plan** ✋ (WAITING)
2. System Architect: Design API structure
3. Security Engineer: Review auth placeholders, CORS, input validation
4. Implementation: Phase 0 (Foundation)

---

**Questions for Brooke:**

1. ✅ Tailwind CSS - confirmed
2. ✅ LangChain multi-provider - confirmed
3. ✅ Auth placeholders - confirmed
4. ✅ Docker prep but not deploy yet - confirmed

**Anything else to adjust before I proceed to System Architect phase?**
