# Diigo Tagger AI

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

AI-powered bookmark management for [Diigo](https://www.diigo.com). Smart tagging with similarity matching, metadata detection, category inference, and a web UI for reviewing everything before it hits your Diigo library.

## What It Does

You paste a URL. The system fetches the page, generates tags with an LLM, matches them against your existing tags, detects metadata (source, format, author), infers broader categories, finds related bookmarks you've already saved, and presents it all for review before submitting.

**The key insight:** LLM-generated tags are generic. This system makes them specific to *your* vocabulary by checking every suggestion against your existing tags (the author's library has 9,600+), showing alternatives ranked by usage, and letting you decide.

### Feature Highlights

| Feature | What It Does |
|---------|-------------|
| **AI Tagging** | 8 content tags per bookmark via OpenAI, Anthropic, or Google (automatic fallback) |
| **Tag Matching** | Every suggestion checked against your tags — >80% auto-merges, 50-80% shows ranked alternatives |
| **Metadata Detection** | Auto-detects `source:medium.com`, `format:video`, `format:pdf`, `format:article` |
| **Category Inference** | Clusters tags and suggests parent categories (e.g., java + spring-boot → software-development) |
| **Related Bookmarks** | Shows existing bookmarks with matching URL paths — click to inherit their tags |
| **Preview & Confirm** | Review everything before submitting — edit title, remove/swap tags, add rating |
| **Rating** | One-click 1-10 rating stored as `rating=7_10` tag |
| **Prefix Tags** | `author:` and `reference:` with autocomplete from existing values |
| **Lucene Search** | `title:python AND tags:tutorial`, wildcards, phrases, boolean operators |
| **Diigo Sync** | Import your entire Diigo library with progress tracking |

<!-- TODO: Add screenshot of the full preview page -->

## Quick Start

### 1. Install

```bash
git clone https://github.com/AI-bbos/diigo-tagger-ai.git
cd diigo-tagger-ai
poetry install
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys:
#   DIIGO_API_KEY, DIIGO_USERNAME, DIIGO_PASSWORD
#   OPENAI_API_KEY (or ANTHROPIC_API_KEY, GOOGLE_API_KEY)
```

### 3. Initialize & Run

```bash
poetry run diigo init    # Create database
poetry run diigo dev     # Start web UI at http://localhost:8000
```

### 4. Optional: Install CLI wrapper

```bash
./scripts/install.sh     # Installs `diigo` command to ~/bin
diigo dev                # Now works without `poetry run`
```

## CLI Commands

```
Bookmarks:
  add               Add bookmark with AI tagging, preview, and conflict resolution
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
```

Run `diigo <command> --help` for detailed options.

## Tech Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy 2.0, SQLite (FTS5)
- **Frontend:** HTMX, Tailwind CSS, Jinja2 templates
- **AI:** LangChain with OpenAI, Anthropic, Google providers
- **CLI:** Click with prompt_toolkit for interactive forms
- **Testing:** pytest, 340+ tests

## Documentation

- [User Guide](docs/USER-GUIDE.md) — features overview, web UI walkthrough, CLI reference
- [Developer Guide](docs/DEVELOPER-GUIDE.md) — architecture, API endpoints, testing, contributing

## License

[AGPL-3.0](LICENSE) — free to use and modify. If you host a modified version as a service, you must share your source code.

Copyright (c) 2026 Brooke Smith
