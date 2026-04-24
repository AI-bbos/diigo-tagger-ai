# User Guide

## Installation

### Prerequisites

- Python 3.10+
- Poetry package manager
- Diigo account with API key
- At least one LLM API key (OpenAI, Anthropic, or Google)

### Setup

```bash
git clone https://github.com/AI-bbos/diigo-tagger-ai.git
cd diigo-tagger-ai
poetry install
```

### Configuration

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Required variables:

| Variable | Purpose |
|----------|---------|
| `DIIGO_API_KEY` | Diigo API key |
| `DIIGO_USERNAME` | Diigo username |
| `DIIGO_PASSWORD` | Diigo password |

At least one LLM provider:

| Variable | Provider |
|----------|----------|
| `OPENAI_API_KEY` | OpenAI (GPT-4o-mini) |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) |
| `GOOGLE_API_KEY` | Google (Gemini) |

### Installing the CLI wrapper

The CLI wrapper lets you run `diigo` from anywhere instead of `poetry run diigo`:

```bash
./scripts/install.sh
```

The installer prompts for a directory (default `~/bin`), creates the `diigo` command, and warns if the directory isn't in your `PATH`.

### Initialize the database

```bash
diigo init
```

This creates the SQLite database with FTS5 full-text search indexes. The database location is platform-specific (managed by `platformdirs`).

## Web UI

### Starting the server

```bash
diigo dev
```

Opens at `http://localhost:8000`. Use `--port` to change the port:

```bash
diigo dev --port 3000
```

The server runs with auto-reload — code changes take effect immediately.

### Browsing bookmarks

The homepage shows all bookmarks with pagination. Use the search bar with Lucene query syntax:

```
title:python                          # Search by title
tags:tutorial                         # Search by tag
title:python AND tags:tutorial        # Boolean AND
title:python OR title:javascript      # Boolean OR
title:python NOT tags:beginner        # Exclude results
title:*neural*                        # Wildcard
title:"machine learning"              # Exact phrase
(title:python OR title:js) AND tags:tutorial  # Grouping
```

### Adding bookmarks

Click "Add Bookmark" on the bookmarks page. The form:

1. Enter a URL — metadata (title, description) is fetched automatically
2. Edit title and description if needed
3. Click "Suggest Tags" for LLM-generated tag suggestions
4. Add or remove tags manually
5. Submit

If the URL already exists, you'll see a conflict resolution dialog with options to keep the original, replace with new data, smart merge, or customize per field.

### Syncing from Diigo

Navigate to the Sync page to import bookmarks from your Diigo account. Options:

- **Incremental** — fetch until 50 new tags found (default)
- **Full** — fetch all bookmarks
- **Custom** — specify target number of new tags

Progress updates stream in real time.

## CLI Commands

### Bookmark Management

**`diigo add --url URL`** — Add a bookmark with LLM-powered tagging.

```bash
diigo add --url https://example.com/article
diigo add --url https://example.com --title "My Title" --tags "python,web"
diigo add --url https://example.com --private  # Private bookmark
```

Options: `--title`, `--description`, `--tags` (comma-separated), `--outline`, `--groups`, `--shared/--private`

**`diigo sync`** — Import bookmarks from Diigo.

```bash
diigo sync --count 100    # Stop after 100 new tags
diigo sync --all          # Fetch everything
```

**`diigo lookup`** — Look up bookmarks by URL or display ID.

```bash
diigo lookup https://example.com
diigo lookup a3f2b8c1
diigo lookup -v a3f2b8c1  # Verbose (full JSON)
```

**`diigo search-bookmarks`** — Search bookmarks with Lucene syntax.

```bash
diigo search-bookmarks "title:python AND tags:tutorial"
diigo search-bookmarks --page 2 --limit 20 --sort title_asc
```

### Tag Operations

**`diigo search`** — Search tags by name or semantic similarity.

```bash
diigo search "*python*"                    # Wildcard
diigo search "machine learning" --semantic # Semantic similarity
diigo search "web" --threshold 0.7 --limit 50
```

**`diigo generate`** — Generate tag suggestions for content.

```bash
diigo generate --title "Article Title" --url https://example.com
diigo generate --title "Title" --description "Description" --max-tags 10
```

**`diigo list`** — List tags in the database.

```bash
diigo list                    # Top 50 by count
diigo list --sort name        # Alphabetical
diigo list --source user      # Filter by source
diigo list --limit 100        # More results
```

**`diigo merge`** — Merge duplicate tags.

```bash
diigo merge --source "python3" --source "py3" --target "python"
```

### Server Commands

**`diigo dev`** — Start the local development server.

```bash
diigo dev              # Default port 8000
diigo dev --port 3000  # Custom port
```

**`diigo build`** — Prepare for Vercel deployment. Exports `requirements.txt` and creates Vercel config files.

**`diigo deploy`** / **`diigo promote`** — Vercel deployment (not yet configured, pending database migration to Turso).

### Database

**`diigo init`** — Initialize or reset the database schema.

```bash
diigo init
diigo init --db-path /custom/path/db.sqlite
```
