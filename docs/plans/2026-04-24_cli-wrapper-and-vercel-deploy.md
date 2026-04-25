# CLI Wrapper, Server Commands & Vercel Deployment Scaffolding

**Created**: 2026-04-24  
**Status**: Approved  
**Branch**: TBD (will be created during implementation)

---

## Summary

Add an installable CLI wrapper (`bin/diigo` + `scripts/install.sh`) following the same pattern as the home-auto (`ha`) project, plus four new server/deployment commands (`dev`, `build`, `deploy`, `promote`). The `--help` output is reorganized into logical command groups.

Vercel deployment is scaffolded but not functional — the database story (likely Turso) is deferred. `deploy` and `promote` print a "not yet configured" message for now.

---

## 1. Wrapper & Install

### `bin/diigo` (template)

Bash wrapper with a `__DIIGO_HOME__` placeholder replaced at install time.

```bash
#!/bin/bash
export DIIGO_HOME="__DIIGO_HOME__"
cd "$DIIGO_HOME"
poetry run diigo "$@"
```

Responsibilities:
- Export `DIIGO_HOME` environment variable
- `cd` to the project directory (so Poetry finds `pyproject.toml`)
- Delegate all arguments to `poetry run diigo`

### `scripts/install.sh`

No dev/prod split — single install.

1. Detect repo root from script location
2. Prompt for install directory (default `~/bin`)
3. `sed` replaces `__DIIGO_HOME__` in the wrapper template
4. Copy to install dir, `chmod +x`
5. Warn if install dir is not in `$PATH`

---

## 2. Grouped Help Output

Extend the existing `HelpfulGroup` Click subclass to support command grouping in `--help`. Each command gets a `help_group` attribute. Groups display in a defined order.

Target output:

```
Usage: diigo [OPTIONS] COMMAND [ARGS]...

  Diigo Tagger AI - AI-powered bookmark tagging tool.

Bookmarks:
  add               Add bookmark with LLM-powered tagging
  lookup            Look up bookmarks by URL or display ID
  search            Search tags (wildcard or semantic)
  search-bookmarks  Search bookmarks (Lucene syntax)
  sync              Sync bookmarks from Diigo

Database:
  init              Initialize database with schema

Tags:
  generate          Generate tag suggestions using AI
  list              List all tags in the database
  merge             Merge multiple tags into one

Server:
  dev               Start local development server
  build             Prepare project for Vercel deployment
  deploy            Deploy preview to Vercel
  promote           Promote latest preview to production
```

Group ordering: Bookmarks, Database, Tags, Server.
Commands within each group: alphabetical.

---

## 3. New CLI Commands

### `diigo dev`

Start the local development web server.

```
diigo dev [--port PORT]
```

- Runs `uvicorn diigo_tagger.api.main:app --reload --port <port>`
- Default port: 8000
- Runs in foreground (ctrl-C to stop)
- Uses `--reload` for auto-restart on code changes

### `diigo build`

Prepare the project for Vercel deployment.

```
diigo build
```

- Export `requirements.txt` from Poetry: `poetry export -f requirements.txt --output requirements.txt --without-hashes`
- Verify or create `api/index.py` (Vercel serverless entry point)
- Verify or create `vercel.json` (routing config)
- Print summary of generated/verified files

Generated `api/index.py`:
```python
from diigo_tagger.api.main import app
```

Generated `vercel.json`:
```json
{
  "builds": [{"src": "api/index.py", "use": "@vercel/python"}],
  "routes": [{"src": "/(.*)", "dest": "api/index.py"}]
}
```

### `diigo deploy`

Deploy a preview to Vercel. **Currently scaffolded only.**

```
diigo deploy
```

- Prints: "Vercel deployment not yet configured. Database migration to Turso required first."
- Future: will run `vercel` to create a preview deployment

### `diigo promote`

Promote the latest preview deployment to production. **Currently scaffolded only.**

```
diigo promote
```

- Prints: "Vercel deployment not yet configured. Database migration to Turso required first."
- Future: will run `vercel promote` to push latest preview to production

---

## 4. File Changes

### New Files

| File | Purpose |
|------|---------|
| `bin/diigo` | Bash wrapper template with `__DIIGO_HOME__` placeholder |
| `scripts/install.sh` | Installer that copies wrapper to user's bin directory |

### Modified Files

| File | Changes |
|------|---------|
| `diigo_tagger/cli/main.py` | Add `dev`, `build`, `deploy`, `promote` commands; extend `HelpfulGroup` for grouped `--help` |

### Files Created by `diigo build`

| File | Purpose |
|------|---------|
| `api/index.py` | Vercel serverless function entry point |
| `vercel.json` | Vercel build and routing configuration |
| `requirements.txt` | Dependencies exported from Poetry for Vercel |

---

## 5. Deferred Work

- **Vercel database**: Turso (hosted SQLite-compatible) is the likely choice. Free tier: 100 DBs, 5 GB storage, 500M reads/mo, 10M writes/mo. More than sufficient for this app.
- **SSE sync progress**: The in-memory `sync_progress` dict in `api/main.py` won't work in serverless. Will need a different approach (e.g., Turso table or Redis) when deploying.
- **`deploy` and `promote`**: Will be implemented once Turso integration is complete.

---

## 6. Design Decisions

- **No dev/prod split**: Project is small enough that a single install is sufficient. Unlike ha, there's no need to run dev and prod side-by-side.
- **`poetry run` in wrapper**: Adds ~200ms startup overhead vs direct venv activation, but is simpler, always correct, and handles venv location automatically.
- **Grouped help via Click**: Custom `HelpfulGroup` subclass reads a `help_group` attribute from each command. Clean, no external dependencies.
- **`build` generates/updates files**: `build` creates or updates `api/index.py`, `vercel.json`, and `requirements.txt`. The entry point and config are stable and should be committed. `requirements.txt` changes when dependencies change and should be regenerated before each deploy.
