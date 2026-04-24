# Diigo Tagger AI — Project Instructions

## Project Overview

AI-powered bookmark management tool for Diigo. CLI + web UI for tagging, searching, and managing bookmarks with multi-provider LLM support.

**Stack:** Python 3.10+, SQLAlchemy 2.0, FastAPI, HTMX, Tailwind CSS, SQLite (FTS5), Alembic, Click, LangChain  
**Repo:** GitHub — AI-bbos/diigo-tagger-ai  
**Default branch:** main

## Package & Commands

- **Package manager:** Poetry
- **Run tests:** `poetry run pytest`
- **Run app (CLI):** `poetry run diigo <command>`
- **Run web server:** `poetry run uvicorn diigo_tagger.api.main:app --reload`
- **Migrations:** `poetry run alembic upgrade head`
- **Lint:** `poetry run ruff check .`
- **Format:** `poetry run black .`
- **Type check:** `poetry run mypy diigo_tagger/`

## Architecture

- **Thin UI layers** — CLI and web UI are wrappers around services
- **Services** (`diigo_tagger/services/`) — all business logic lives here
- **Clients** (`diigo_tagger/clients/`) — external API integrations (Diigo, LLM providers, metadata)
- **API** (`diigo_tagger/api/`) — FastAPI REST endpoints
- **Web** (`diigo_tagger/web/`) — Jinja2 templates with HTMX
- **CLI** (`diigo_tagger/cli/`) — Click commands

## Key Design Decisions

- SQLite + FTS5 over PostgreSQL (simplicity, zero config)
- sentence-transformers for embeddings (local, no API cost)
- Multi-provider LLM via LLMRouter (OpenAI, Anthropic, Google)
- HTMX over React/Vue (server-rendered, minimal JS)
- Lucene-style query syntax via luqum

## Development Status

See `docs/plans/WEB_UI_PLAN.md` for the phased web UI plan.

## Testing

- Target: ≥80% coverage
- Framework: pytest
- Integration tests use httpx TestClient for FastAPI
- See `docs/plans/PRE_WORK_TEST_COVERAGE.md` for coverage gaps
