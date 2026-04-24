# Diigo Tagger AI

AI-powered bookmark management tool with CLI and web UI. Automatically generates tags using LLMs, provides full-text and semantic search, and syncs with your Diigo account.

## Features

- **AI-powered tagging** — generate tags using OpenAI, Anthropic, or Google LLMs
- **Full-text search** — Lucene query syntax powered by SQLite FTS5
- **Semantic search** — find similar tags using sentence-transformer embeddings
- **Web UI** — browse, search, add bookmarks with HTMX-powered interface
- **Diigo sync** — import bookmarks with real-time progress streaming
- **Conflict resolution** — detect duplicates and merge intelligently
- **URL metadata extraction** — auto-fetch titles and descriptions (including YouTube)
- **Security hardened** — API key redaction, prompt injection detection, rate limiting

## Quick Start

### 1. Install dependencies

```bash
git clone https://github.com/AI-bbos/diigo-tagger-ai.git
cd diigo-tagger-ai
poetry install
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys:
#   DIIGO_API_KEY, DIIGO_USERNAME, DIIGO_PASSWORD
#   OPENAI_API_KEY (or ANTHROPIC_API_KEY, GOOGLE_API_KEY)
```

### 3. Initialize database

```bash
poetry run diigo init
```

### 4. Install CLI wrapper (optional)

```bash
./scripts/install.sh
# Installs `diigo` command to ~/bin (or custom directory)
```

After installing, use `diigo` directly instead of `poetry run diigo`.

### 5. Start the web UI

```bash
diigo dev
# Opens at http://localhost:8000
```

Or use the CLI directly:

```bash
diigo sync --count 100        # Import bookmarks from Diigo
diigo search "*python*"       # Search tags
diigo add --url https://...   # Add a bookmark with AI tagging
```

## Commands

```
Bookmarks:
  add               Add bookmark with LLM-powered tagging and conflict resolution
  lookup            Look up bookmarks by URL or display ID
  search            Search tags (wildcard or semantic similarity)
  search-bookmarks  Search bookmarks using Lucene query syntax
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
  deploy            Deploy preview to Vercel (not yet configured)
  promote           Promote latest preview to production (not yet configured)
```

Run `diigo <command> --help` for detailed options on any command.

## Web UI

The web interface provides:

- **Bookmark search** — full-text search with Lucene syntax (`title:python AND tags:tutorial`)
- **Add bookmarks** — form with URL metadata auto-fetch, LLM tag suggestions, and conflict resolution
- **Diigo sync** — import bookmarks with real-time SSE progress streaming
- **Help pages** — search syntax reference, database operations guide

Start with `diigo dev` (default port 8000) or `diigo dev --port 3000`.

## Documentation

- [User Guide](docs/USER-GUIDE.md)
- [Developer Guide](docs/DEVELOPER-GUIDE.md)
- [Architecture Design](docs/features/diigo-tagger-ai/02-architecture-design.md)
- [REST API Design](docs/plans/REST_API_DESIGN.md)
- [Security Audit](docs/features/diigo-tagger-ai/04-security-audit.md)

## License

MIT
