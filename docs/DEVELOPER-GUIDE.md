# Developer Guide

## Architecture Philosophy

This is a **local-first** application. The web UI runs on `localhost`, the database is a local SQLite file, and no data leaves the user's machine except explicit API calls to Diigo and their chosen LLM provider. There is no server-side hosting, no user accounts, no cloud database.

This architecture was a deliberate choice:
- **SQLite over PostgreSQL** — zero config, single file, no database server to manage
- **Local web server over SaaS** — user owns their data, no subscription model
- **API keys in `.env`** — user provides their own LLM keys, no proxy or shared quota
- **Designed for self-hosting** — install from git, run locally, works on any machine with Python 3.10+

## Setup

### Prerequisites

- Python 3.10+
- Poetry
- SQLite 3.35+ (for FTS5 support)

### Getting started

```bash
git clone https://github.com/AI-bbos/diigo-tagger-ai.git
cd diigo-tagger-ai
poetry install
cp .env.example .env  # Add your API keys
poetry run diigo init  # Initialize database
```

### Running the app

```bash
# CLI
poetry run diigo --help

# Web UI (with auto-reload)
poetry run diigo dev

# Or install the wrapper for convenience
./scripts/install.sh
diigo dev
```

## Architecture

```
diigo_tagger/
├── api/              # FastAPI REST API (thin layer)
│   ├── main.py       # App setup, middleware, web routes
│   ├── routes/       # API endpoint handlers
│   └── schemas/      # Pydantic request/response models
├── cli/              # Click CLI (thin layer)
│   ├── main.py       # All CLI commands + helper functions
│   └── add_form.py   # prompt_toolkit interactive bookmark form
├── clients/          # External service integrations
│   ├── diigo_client.py       # Diigo API
│   ├── llm_router.py         # Multi-provider LLM routing (tag generation + category inference)
│   ├── metadata_fetcher.py   # URL/YouTube metadata extraction (title, description, author)
│   └── openai_client.py      # OpenAI wrapper (uses llm_router)
├── services/         # Business logic (thick layer)
│   ├── bookmark_service.py       # Bookmark CRUD, sync, conflict resolution, prepare/submit
│   ├── tag_service.py            # Tag operations
│   ├── tag_reconciliation.py     # Tag dedup/merge + similarity matching with confidence tiers
│   ├── tag_hierarchy.py          # LCA-based parent category inference
│   ├── metadata_tag_detector.py  # Auto-detect format: and source: tags
│   ├── settings_service.py       # Key-value settings (tag prefixes, etc.)
│   └── query_parser.py           # Lucene query parsing
├── web/
│   └── templates/    # Jinja2 HTML templates (HTMX + Tailwind)
├── constants.py      # Shared constants
├── db.py             # Database initialization (SQLite + WAL)
├── models.py         # SQLAlchemy ORM models (Bookmark, Tag, Setting)
└── security.py       # Validation, redaction, injection detection
```

### Key principle: thin UI, thick services

CLI and web UI are thin wrappers around the service layer. Business logic never goes in routes, templates, or CLI commands. If a function has branches unrelated to the UI (type conversions, validation, orchestration), it belongs in a service.

### Bookmark add flow (prepare/submit)

The bookmark add process is split into two phases:

1. **`prepare_bookmark()`** — Fetches metadata, generates LLM tags, runs similarity matching, detects metadata tags, infers parent categories, finds related bookmarks. Returns a preview dict without side effects.

2. **`submit_bookmark()`** — Takes reviewed data and submits to Diigo API + saves to local DB.

The CLI and web UI both use this flow with their own confirmation UX between the two steps.

### LLM integration

The `LLMRouter` (`clients/llm_router.py`) provides multi-provider support:

- OpenAI (GPT-4o-mini)
- Anthropic (Claude Haiku)
- Google (Gemini Pro)

Two LLM calls per bookmark:
1. **`generate_tags()`** — Produces 8 content tags from title, description, and URL
2. **`generate_categories()`** — Clusters content tags and infers parent categories (LCA approach)

Configured via environment variables. The router handles provider selection and automatic fallback.

### Tag similarity matching

`TagReconciliationService.match_existing_tags()` compares suggested tags against all existing database tags using `difflib.SequenceMatcher`. Returns confidence tiers:

| Similarity | Action | UI Behavior |
|-----------|--------|-------------|
| >= 80% | `auto_accept` | Auto-swap to existing tag name |
| 50-80% | `confirm` | Show similarity % with dropdown of alternatives |
| < 50% | `new` | Use as-is (new tag) |

Tags with multiple candidates above 65% show a ranked dropdown sorted by usage count then similarity.

### Metadata tag detection

`MetadataTagDetector` auto-detects tags from URL patterns:

| Pattern | Tag |
|---------|-----|
| YouTube, Vimeo, etc. | `format:video` |
| `.pdf` URLs | `format:pdf` |
| GitHub/GitLab repos | `format:repository` |
| Pages with `<article>` | `format:article` |
| Any URL | `source:{domain}` |

### Parent category inference (LCA)

`TagHierarchyService` uses a second LLM call to cluster content tags and find their Lowest Common Ancestor categories. Results are checked against existing tags via similarity matching:

- **Existing users:** Categories match existing tags (reinforces user's taxonomy)
- **New users:** Categories suggested directly (bootstraps hierarchy)

### Settings

`SettingsService` provides key-value storage in the `settings` table. Used for:
- Tag prefixes (`author:`, `reference:`) — configurable at runtime

### Database

SQLite with:
- **FTS5** for full-text search on bookmarks
- **WAL mode** for concurrent reads
- **Alembic** for schema migrations

Models:
- `Bookmark` — URL, title, description, display_id, timestamps
- `Tag` — name, count, source, embeddings (optional)
- `Setting` — key-value pairs for app configuration
- `bookmark_tags` — many-to-many association

Migrations live in `alembic/versions/`. Run with:

```bash
poetry run alembic upgrade head    # Apply all migrations
poetry run alembic revision -m "description"  # Create new migration
```

## Testing

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/unit/test_cli_help.py -v

# Run with coverage report
poetry run pytest --cov=diigo_tagger --cov-report=html

# Skip pre-existing sync failures
poetry run pytest -k "not sync"
```

### Test structure

```
tests/
├── unit/                          # Unit tests (mocked dependencies)
│   ├── test_cli.py                # CLI command tests
│   ├── test_cli_help.py           # Grouped help output tests
│   ├── test_cli_server.py         # Server command tests
│   ├── test_add_form.py           # Interactive CLI form logic
│   ├── test_bookmark_service.py   # Bookmark CRUD + prepare/submit
│   ├── test_tag_service.py        # Tag operations
│   ├── test_tag_similarity.py     # Similarity matching + confidence tiers
│   ├── test_tag_hierarchy.py      # Parent category inference
│   ├── test_metadata_fetcher.py   # URL metadata extraction
│   ├── test_metadata_tag_detector.py  # format:/source: detection
│   ├── test_settings_service.py   # Settings CRUD
│   ├── test_related_bookmarks.py  # URL path matching
│   └── ...
├── integration/                   # Integration tests (real HTTP via TestClient)
│   ├── test_api_bookmarks.py
│   ├── test_api_autocomplete.py
│   └── test_api_health.py
├── e2e/                           # End-to-end tests
├── security/                      # Security-focused tests
└── performance/                   # Performance benchmarks
```

### Testing conventions

- CLI tests use `click.testing.CliRunner`
- API tests use `httpx.AsyncClient` with FastAPI's `TestClient`
- External calls (Diigo API, LLMs) are mocked in unit tests
- Coverage target: 80%+

### API endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/bookmarks` | List/search bookmarks (Lucene syntax) |
| GET | `/api/v1/bookmarks/{id}` | Get bookmark by display ID |
| POST | `/api/v1/bookmarks` | Add bookmark (legacy one-step) |
| POST | `/api/v1/bookmarks/prepare` | Preview bookmark (no side effects) |
| POST | `/api/v1/bookmarks/submit` | Submit reviewed bookmark to Diigo |
| POST | `/api/v1/bookmarks/resolve` | Resolve bookmark conflict |
| GET | `/api/v1/tags/autocomplete` | Tag autocomplete (prefix + query) |

## CLI Wrapper

The `bin/diigo` wrapper template and `scripts/install.sh` installer let users run `diigo` from anywhere:

1. `scripts/install.sh` prompts for a bin directory (default `~/bin`)
2. Copies `bin/diigo` with the `__DIIGO_HOME__` placeholder replaced with the repo path
3. The wrapper `cd`s to the repo and runs `poetry run diigo`

## Deployment

Vercel deployment is scaffolded but not functional. The blocker is database: SQLite requires a persistent filesystem, which Vercel serverless doesn't provide. The planned solution is Turso (hosted SQLite-compatible).

`diigo build` generates the Vercel deployment files:
- `requirements.txt` — exported from Poetry
- `api/index.py` — serverless function entry point
- `vercel.json` — build and routing config

## Contributing

### Branch workflow

- Branch from `main` with prefix: `feat/`, `fix/`, `refactor/`, `docs/`, `test/`
- Commit messages follow Conventional Commits
- Create a PR for all changes (never commit directly to main)

### Code style

- **Formatter:** Black (line length 100)
- **Linter:** Ruff
- **Type checker:** mypy

```bash
poetry run black .
poetry run ruff check .
poetry run mypy diigo_tagger/
```

### File headers

All code files must start with two ABOUTME comment lines:

```python
# ABOUTME: What this file does
# ABOUTME: How it fits into the system
```

### Docstrings

All functions and methods must have Google-style docstrings with Args, Returns, and Raises sections.
