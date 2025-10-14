# Repository Guidelines

## Project Structure & Module Organization
- `src/`: application code (e.g., `src/diigo_tagger/` or `src/diigo_tagger.ts`).
- `tests/`: unit/integration tests and fixtures.
- `scripts/`: local tooling (data import, maintenance tasks).
- `config/`: static configs; include `config/sample.env` for required env vars.
- `docs/`: design notes and ADRs; brief architecture overviews.
- `assets/`: images and test data that are safe to commit.
Group modules by domain (e.g., `api/`, `tagging/`, `cli/`) and keep files small and cohesive.

## Build, Test, and Development Commands
Standardize with a Makefile (recommended targets below). If you prefer npm or poetry, map commands accordingly.
- `make setup`: install dependencies.
- `make run`: run the app locally.
- `make test`: run the test suite.
- `make lint`: static checks.
- `make format`: auto-format code.
Examples:
- Python: `pip install -r requirements.txt` or `uv sync`; `pytest -q`; `ruff check`; `black .`; `python -m diigo_tagger`.
- Node/TS: `npm ci`; `npm test`; `npm run lint`; `npm run format`; `npm start`.

## Coding Style & Naming Conventions
- Python: PEP 8; 4-space indent; snake_case for modules/functions; PascalCase for classes. Use `ruff` + `black`.
- TypeScript/JS: 2-space indent; camelCase for vars/functions; PascalCase for classes. Use `eslint` + `prettier`.
Prefer pure functions and dependency injection; avoid heavy side effects at module import time.

## Testing Guidelines
- Frameworks: `pytest` (Python) or `vitest/jest` (TS/JS).
- Naming: `tests/test_*.py` or `**/*.spec.ts`.
- Coverage: target ≥80% for core modules. Add at least one integration test for the Diigo API client (mock HTTP or record with VCR).
- Run locally: `make test` and ensure repeatability.

## Commit & Pull Request Guidelines
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `build:`, `chore:`.
- PRs include: purpose, approach, linked issue (e.g., `Closes #123`), screenshots/logs for UX/CLI changes, and testing notes.
- Keep diffs focused; update docs/config samples when behavior changes.

## Security & Configuration Tips
- Do not commit secrets. Use `.env` (ignored) or your secret manager; provide `config/sample.env` (e.g., `DIIGO_API_TOKEN=`).
- Prefer environment variables over hardcoded paths; document defaults in `README.md`.
- Validate inputs for any external API calls and rate-limit where applicable.

