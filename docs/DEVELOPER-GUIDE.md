# Developer Guide

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
│   └── main.py       # All CLI commands
├── clients/          # External service integrations
│   ├── diigo_client.py       # Diigo API
│   ├── llm_router.py         # Multi-provider LLM routing
│   ├── metadata_fetcher.py   # URL/YouTube metadata extraction
│   └── openai_client.py      # OpenAI wrapper (uses llm_router)
├── services/         # Business logic (thick layer)
│   ├── bookmark_service.py   # Bookmark CRUD, sync, conflict resolution
│   ├── tag_service.py         # Tag operations
│   ├── tag_reconciliation.py  # Tag dedup/merge
│   └── query_parser.py        # Lucene query parsing
├── web/
│   └── templates/    # Jinja2 HTML templates (HTMX + Tailwind)
├── constants.py      # Shared constants
├── db.py             # Database initialization (SQLite + WAL)
├── models.py         # SQLAlchemy ORM models
└── security.py       # Validation, redaction, injection detection
```

### Key principle: thin UI, thick services

CLI and web UI are thin wrappers around the service layer. Business logic never goes in routes, templates, or CLI commands. If a function has branches unrelated to the UI (type conversions, validation, orchestration), it belongs in a service.

### LLM integration

The `LLMRouter` (`clients/llm_router.py`) provides multi-provider support:

- OpenAI (GPT-4o-mini)
- Anthropic (Claude)
- Google (Gemini)

Configured via environment variables. The router handles provider selection and fallback.

### Database

SQLite with:
- **FTS5** for full-text search on bookmarks
- **WAL mode** for concurrent reads
- **Alembic** for schema migrations

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
```

### Test structure

```
tests/
├── unit/                    # Unit tests (mocked dependencies)
│   ├── test_cli.py          # CLI command tests
│   ├── test_cli_help.py     # Grouped help output tests
│   ├── test_cli_server.py   # Server command tests (dev, build, deploy, promote)
│   ├── test_bookmark_service.py
│   ├── test_tag_service.py
│   └── ...
├── integration/             # Integration tests (real HTTP via TestClient)
│   ├── test_api_bookmarks.py
│   └── test_api_health.py
├── e2e/                     # End-to-end tests
├── security/                # Security-focused tests
└── performance/             # Performance benchmarks
```

### Testing conventions

- CLI tests use `click.testing.CliRunner`
- API tests use `httpx.AsyncClient` with FastAPI's `TestClient`
- External calls (Diigo API, LLMs) are mocked in unit tests
- Coverage target: 80%+

## CLI Wrapper

The `bin/diigo` wrapper template and `scripts/install.sh` installer let users run `diigo` from anywhere:

1. `scripts/install.sh` prompts for a bin directory (default `~/bin`)
2. Copies `bin/diigo` with the `__DIIGO_HOME__` placeholder replaced with the repo path
3. The wrapper `cd`s to the repo and runs `poetry run diigo`

### Server commands

| Command | Purpose |
|---------|---------|
| `diigo dev` | Start uvicorn with `--reload` (default port 8000) |
| `diigo build` | Export `requirements.txt`, create `api/index.py` and `vercel.json` |
| `diigo deploy` | Deploy to Vercel (not yet configured) |
| `diigo promote` | Promote Vercel preview to production (not yet configured) |

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
