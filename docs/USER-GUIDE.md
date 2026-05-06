# User Guide

## Features at a Glance

| Feature | Description |
|---------|-------------|
| **AI-Powered Tagging** | LLM generates 8 content tags per bookmark using OpenAI, Anthropic, or Google |
| **Smart Tag Matching** | Suggested tags checked against your existing tags — duplicates auto-merged, similar tags shown with alternatives |
| **Metadata Detection** | Auto-detects `source:{domain}` (e.g., `source:medium.com`) for any URL, plus `format:video`, `format:pdf`, `format:repository`, `format:article` |
| **Category Inference** | Clusters content tags and suggests broader parent categories (e.g., "software-development") |
| **Related Bookmarks** | Shows existing bookmarks with matching URL paths — click to inherit their tags |
| **Rating System** | Rate bookmarks 1-10 with one click, stored as `rating=7_10` tag |
| **Prefix Tags** | `author:` and `reference:` prefix tags with autocomplete from existing values |
| **Tag Similarity** | Dropdown showing alternative existing tags ranked by usage count and similarity % |
| **Preview & Confirm** | Review title, description, and all tags before submitting to Diigo |
| **Conflict Resolution** | Side-by-side comparison when bookmark exists, with keep/replace/merge options |
| **Lucene Search** | Full-text search with boolean operators, wildcards, phrases, and field filtering |
| **Multi-Provider LLM** | Automatic fallback between OpenAI, Anthropic, and Google providers |
| **Diigo Sync** | Import bookmarks from Diigo with progress tracking |

### Suggested Screenshots

<!-- TODO: Add screenshots -->
<!-- 1. Web UI preview page showing all sections: AI tags, detected tags, categories, related bookmarks, rating, prefix inputs -->
<!-- 2. Tag similarity dropdown showing ranked alternatives with counts -->
<!-- 3. Related bookmarks section with clickable tags from matching URL paths -->
<!-- 4. Conflict resolution side-by-side comparison -->
<!-- 5. Search results page with Lucene query -->
<!-- 6. Bookmark list homepage with tag chips -->

## Installation

### Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/). Verify with `python3 --version`.
- **Poetry** — Python package manager. [Install guide](https://python-poetry.org/docs/#installation). Verify with `poetry --version`.
- **Diigo account + API key** — Sign up at [diigo.com](https://www.diigo.com), then get your API key from [Diigo API console](https://www.diigo.com/api_dev).
- **At least one LLM API key:**
  - [OpenAI](https://platform.openai.com/api-keys) — uses GPT-4o-mini (cheapest, recommended to start)
  - [Anthropic](https://console.anthropic.com/settings/keys) — uses Claude Haiku
  - [Google](https://aistudio.google.com/app/apikey) — uses Gemini Pro
  - You can configure multiple — the system falls back automatically if one fails

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

### Adding Bookmarks (Web UI)

The bookmark add flow is a two-phase process: **Preview** then **Confirm**.

#### Phase 1: Enter URL

Click "Add Bookmark" and enter a URL. Click **Preview** to fetch metadata and generate tags.

#### Phase 2: Review & Edit

The preview shows everything that will be submitted, organized in sections:

**Title & Description** — Auto-fetched from the page metadata. Editable. Falls back to URL path slug if the site blocks metadata fetching (e.g., Medium).

**Tags (manual)** — Type to search existing tags with typeahead autocomplete, or press Enter to create new tags. Usage counts shown on each tag.

**AI-generated tags** (green section) — LLM-suggested tags, already added. Each shows:
- Usage count: how many bookmarks already use this tag
- Similarity %: how closely it matched an existing tag
- Dropdown (click %): ranked alternatives from your existing tags, sorted by usage count

Click × to remove. Removed tags move to a "Removed suggestions" section where you can re-add them.

**Detected metadata tags** (blue section) — Auto-detected from the URL:
- `source:medium.com` — extracted from the domain
- `format:video` — YouTube, Vimeo, etc.
- `format:pdf` — PDF links
- `format:repository` — GitHub/GitLab repos
- `format:article` — pages with `<article>` HTML element

Click × to remove.

**Suggested categories** (amber section) — Broader parent categories inferred by clustering the content tags:
- e.g., tags [java, spring-boot, api] → category **software-development**
- Shows which content tags each category covers
- Dropdown with alternative existing tags ranked by count
- Click + to add

**Related bookmarks** (purple section) — Existing bookmarks with matching URL paths. Shows their tags as clickable chips — click to inherit a tag from a related bookmark.

**Rating** — Click 1-10 or Skip. Stored as `rating=7_10` tag.

**Prefix tags** — `author:` and `reference:` fields. Enter just the value (prefix auto-prepended). Use `,` or `;` for multiple entries. Author auto-populated from page metadata when available.

Click **Confirm & Submit** to save to both the local database and Diigo.

#### Conflict Resolution

If the bookmark URL already exists, a side-by-side comparison shows current vs. new data with resolution options:
- **Keep Original** — discard new data
- **Replace All** — overwrite with new data
- **Smart Merge** — keep original where new is empty, combine tags
- **Update Title & Description, Merge Tags** — replace text, combine tags

### Browsing Bookmarks

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

### Syncing from Diigo

Navigate to the Sync page to import bookmarks from your Diigo account. Options:

- **Incremental** — fetch until 50 new tags found (default)
- **Full** — fetch all bookmarks
- **Custom** — specify target number of new tags

Progress updates stream in real time.

## CLI Commands

### Bookmark Management

**`diigo add --url URL`** — Add a bookmark with AI-powered tagging.

Shows a preview of the resolved title, description, and tags before submitting. Use `--yes` to skip confirmation (for scripting).

```bash
diigo add --url https://example.com/article
diigo add --url https://example.com --title "My Title" --tags "python,web"
diigo add --url https://example.com --private  # Private bookmark
diigo add --url https://example.com --yes      # Skip confirmation
```

Options: `--title`, `--description`, `--tags` (comma-separated), `--outline`, `--groups`, `--shared/--private`, `--yes/-y`

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
