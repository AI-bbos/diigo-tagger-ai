# User Documentation: Diigo Tagger AI

**Project**: diigo-tagger-ai
**Created**: October 15, 2025
**Tech Writer**: Claude
**Status**: Updated October 16, 2025 to match v1.0.0 implementation
**Input**: `01-bsa-analysis.md`, `02-architecture-design.md`, `03-data-engineering-plan.md`, `04-security-audit.md`, actual CLI code

---

## Documentation Summary

This document provides comprehensive user documentation for the Diigo Tagger AI CLI tool, including:
- Installation guide
- Quick start tutorial
- Command reference
- Configuration guide
- Security best practices
- Troubleshooting

**Target Audience**: Command-line users comfortable with Python, pip/poetry, and environment variables.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Command Reference](#command-reference)
5. [Workflows](#workflows)
6. [Security Best Practices](#security-best-practices)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## Installation

### Prerequisites

**Required**:
- Python 3.10 or higher
- pip or Poetry package manager
- Diigo account with API key
- OpenAI API key (or Anthropic/Ollama)

**Recommended**:
- Git (for installing from source)
- 200MB free disk space (for embedding model, optional)
- macOS, Linux, or Windows with WSL

### Check Python Version

```bash
python --version
# Expected: Python 3.10.0 or higher

python -c "import sqlite3; print(sqlite3.sqlite_version)"
# Expected: 3.35.0 or higher (for FTS5 support)
```

### Install with pip (Recommended)

```bash
pip install diigo-tagger-ai
```

### Install with Poetry (Development)

```bash
git clone https://github.com/yourusername/diigo-tagger-ai.git
cd diigo-tagger-ai
poetry install'
poetry shell
```

### Verify Installation

```bash
diigo --version
# Expected: diigo-tagger-ai 1.0.0
```

---

## Quick Start

### Step 1: Get API Keys

**Diigo API Key**:
1. Log in to Diigo: https://www.diigo.com
2. Go to Settings → API Key
3. Copy your API key (format: `abc123def456`)

**OpenAI API Key**:
1. Sign up at https://platform.openai.com
2. Go to API Keys → Create new secret key
3. Copy your key (format: `sk-...`)

### Step 2: Create Configuration File

Create `.env` file in your project directory:

```bash
# .env
DIIGO_API_KEY=your_diigo_api_key
OPENAI_API_KEY=sk-your_openai_key
```

**⚠️ SECURITY WARNING**:
- **NEVER commit `.env` to git!**
- Run `chmod 600 .env` to restrict file permissions (Unix/macOS)
- Add `.env` to your `.gitignore` file

### Step 3: Initialize Database

```bash
diigo init
```

**What this does**:
- Creates SQLite database with FTS5 schema
- Default location varies by platform:
  - **macOS**: `~/Library/Application Support/diigo-tagger/tags.db`
  - **Linux**: `~/.config/diigo-tagger/tags.db`
  - **Windows**: `%APPDATA%\diigo-tagger\tags.db`
- Custom location: `diigo init --db-path /path/to/tags.db`

### Step 4: Sync Your Existing Tags

```bash
diigo sync --count 100
```

**What this does**:
- Fetches bookmarks from Diigo API
- Extracts unique tag names
- Stores them in local database
- `--count`: Number of bookmarks to fetch (default: 100)
- **Runtime**: ~10-30 seconds for 100 bookmarks

**Expected output**:
```
Fetching 100 bookmarks from Diigo...
✓ Fetched 100 bookmarks
✓ Added 247 new tags, updated 89 existing tags
```

### Step 5: Generate Tags with AI

```bash
diigo generate --title "How to Build CLI Tools" --url "https://example.com/article"
```

**What happens**:
1. Sends metadata to OpenAI (GPT-4o-mini)
2. AI generates relevant tags based on title, URL, and description
3. Returns list of suggested tags
4. **v1.0 Note**: Tags are NOT automatically saved to Diigo - use this for preview only

**Example output**:
```
Generating tags for: How to Build CLI Tools

✓ Generated 6 tags:

  python
  cli-tools
  command-line
  development
  tutorial
  programming
```

**Optional parameters**:
- `--description "Article summary"`: Add context for better tag generation
- `--max-tags 5`: Limit number of tags (default: 8)

### Step 6: Search Your Tags

**Wildcard search** (fast, uses FTS5):
```bash
diigo search "*python*"
```

**Semantic search** (finds related tags using embeddings):
```bash
diigo search "machine learning" --semantic --threshold 0.75
```

**⚠️ v1.0 Limitation**: Semantic search requires embeddings to be pre-stored in the database. Embeddings are not automatically generated during sync in v1.0.

---

## Configuration

### Environment Variables

**Required**:
```bash
DIIGO_API_KEY=abc123              # From Diigo Settings → API Key
OPENAI_API_KEY=sk-...             # From OpenAI dashboard
```

**Optional**:
```bash
DIIGO_DB_PATH=/custom/path/tags.db  # Override default database location
```

### Database Location

**Default locations** (cross-platform using platformdirs):
- **macOS**: `~/Library/Application Support/diigo-tagger/tags.db`
- **Linux**: `~/.config/diigo-tagger/tags.db`
- **Windows**: `%APPDATA%\diigo-tagger\tags.db`

**Custom location**:
```bash
# Option 1: Environment variable
export DIIGO_DB_PATH=/path/to/custom/tags.db

# Option 2: CLI parameter (any command)
diigo init --db-path /path/to/custom/tags.db
diigo sync --db-path /path/to/custom/tags.db
diigo search "query" --db-path /path/to/custom/tags.db
```

---

## Command Reference

### `diigo init`

Initialize database with schema (one-time setup).

**Usage**:
```bash
diigo init [options]
```

**Options**:
- `--db-path PATH`: Custom database location (default: platform-specific)

**Examples**:

```bash
# Initialize with default location
diigo init

# Custom location
diigo init --db-path /path/to/tags.db
```

**What it does**:
1. Creates SQLite database file
2. Creates tables for tags with FTS5 full-text search
3. Sets up indexes for performance

**Default locations**:
- **macOS**: `~/Library/Application Support/diigo-tagger/tags.db`
- **Linux**: `~/.config/diigo-tagger/tags.db`
- **Windows**: `%APPDATA%\diigo-tagger\tags.db`

**Expected output**:
```
✓ Database initialized successfully
  Location: ~/Library/Application Support/diigo-tagger/tags.db
```

---

### `diigo sync`

Sync bookmarks from Diigo and update tag database.

**Usage**:
```bash
diigo sync [options]
```

**Options**:
- `--count N`: Number of bookmarks to fetch (default: 100)
- `--db-path PATH`: Database location (default: platform-specific)

**Examples**:

```bash
# Sync 100 bookmarks (default)
diigo sync

# Sync 500 bookmarks
diigo sync --count 500

# Custom database location
diigo sync --count 100 --db-path /path/to/tags.db
```

**Requirements**:
- Environment variable: `DIIGO_API_KEY`

**What it does**:
1. Fetches bookmarks via Diigo API (paginated)
2. Extracts unique tag names from each bookmark
3. Updates or creates tag records with usage counts
4. Tags are stored with `source='user'`

**Performance**:
- ~100 bookmarks in 10-30 seconds (depends on API response time)
- Shows progress during fetch

**Expected output**:
```
Fetching 100 bookmarks from Diigo...
✓ Fetched 100 bookmarks
✓ Added 247 new tags, updated 89 existing tags
```

---

### `diigo search`

Search for tags using wildcard or semantic similarity.

**Usage**:
```bash
diigo search QUERY [options]
```

**Arguments**:
- `QUERY` (required): Search query or wildcard pattern

**Options**:
- `--semantic`: Use semantic similarity search (requires embeddings)
- `--threshold N`: Similarity threshold for semantic search (default: 0.8)
- `--limit N`: Maximum results to return (default: 20)
- `--db-path PATH`: Database location (default: platform-specific)

**Examples**:

```bash
# Wildcard search (FTS5)
diigo search "*python*"
diigo search "cli*"

# Semantic search (embeddings)
diigo search "machine learning" --semantic
diigo search "version control" --semantic --threshold 0.7 --limit 10
```

**Wildcard search** (default):
- Uses SQLite FTS5 full-text search
- Fast (< 50ms for thousands of tags)
- Supports `*` wildcard for pattern matching
- No additional setup required

**Semantic search** (`--semantic` flag):
- Uses cosine similarity with embeddings
- Finds conceptually related tags
- **⚠️ v1.0 Limitation**: Requires embeddings to be pre-stored in database
- Embeddings are NOT auto-generated during sync in v1.0

**Expected output**:
```
Searching for tags matching '*python*'...

Found 4 tags:

  python                        (used 247 times)
  python-library                (used 89 times)
  python3                       (used 45 times)
  micropython                   (used 12 times)
```

---

### `diigo merge`

Merge multiple tags into a single canonical tag.

**Usage**:
```bash
diigo merge --source TAG1 --source TAG2 --target TAG [options]
```

**Options**:
- `--source TAG`: Source tag to merge (can specify multiple)
- `--target TAG`: Target tag to merge into (required)
- `--db-path PATH`: Database location (default: platform-specific)

**Examples**:

```bash
# Merge single tag
diigo merge --source gitworkflow --target git-workflow

# Merge multiple tags
diigo merge --source ml --source ML --source machine_learning --target machine-learning
```

**What it does**:
1. Combines usage counts from source tags into target tag
2. Removes source tags from database
3. **⚠️ v1.0 Note**: Only updates local database, does NOT update bookmarks in Diigo

**Expected output**:
```
Merging ['gitworkflow', 'git-workflow-old'] → 'git-workflow'...
✓ Tags merged successfully
```

---

### `diigo generate`

Generate tag suggestions using AI (GPT-4o-mini).

**Usage**:
```bash
diigo generate --title TITLE --url URL [options]
```

**Options**:
- `--title TEXT`: Bookmark title (required)
- `--url URL`: Bookmark URL (required)
- `--description TEXT`: Optional description for better context
- `--max-tags N`: Maximum number of tags to generate (default: 8)

**Examples**:

```bash
# Basic tag generation
diigo generate --title "How to Build CLI Tools" --url "https://example.com/article"

# With description and tag limit
diigo generate \
  --title "Python CLI Tutorial" \
  --url "https://example.com/python-cli" \
  --description "Comprehensive guide to building command-line tools with Python" \
  --max-tags 5
```

**Requirements**:
- Environment variable: `OPENAI_API_KEY`

**What it does**:
1. Sends metadata to OpenAI GPT-4o-mini
2. AI analyzes title, URL, and description
3. Returns list of relevant tags
4. **⚠️ v1.0 Note**: Tags are NOT saved to Diigo - this is a preview-only feature

**Security**:
- Includes prompt injection detection
- API keys are never logged or displayed
- All requests use HTTPS only

**Expected output**:
```
Generating tags for: How to Build CLI Tools

✓ Generated 6 tags:

  python
  cli-tools
  command-line
  development
  tutorial
  programming
```

---

### `diigo list`

List all tags in the database.

**Usage**:
```bash
diigo list [options]
```

**Options**:
- `--limit N`: Maximum number of tags to display (default: 50)
- `--source TYPE`: Filter by source (`user`, `master`, `system`)
- `--db-path PATH`: Database location (default: platform-specific)

**Examples**:

```bash
# Show top 50 tags (default)
diigo list

# Show top 100 tags
diigo list --limit 100

# Show only user-created tags
diigo list --source user

# Show all system tags
diigo list --source system --limit 1000
```

**What it does**:
- Displays tags sorted by usage count (descending)
- Shows tag name, count, and source
- Helps identify popular tags and tag sources

**Expected output**:
```
Showing 50 tags:

Tag                            Count      Source
--------------------------------------------------
python                         247        user
cli-tools                      89         user
development                    156        user
tutorial                       78         user
programming                    145        user
```

---

## Workflows

### Initial Setup Workflow

```bash
# 1. Initialize database
diigo init

# 2. Sync existing bookmarks from Diigo
diigo sync --count 500

# 3. List tags to verify sync
diigo list --limit 20
```

---

### Tag Generation Workflow (Preview Tags for New Bookmarks)

```bash
# Generate tag suggestions for a URL
diigo generate \
  --title "How to Build CLI Tools with Python" \
  --url "https://example.com/python-cli" \
  --description "A comprehensive tutorial"

# Review suggested tags, then manually add to bookmark in Diigo web UI
# (v1.0 does not auto-save bookmarks)
```

**v1.0 Note**: Tag generation is preview-only. You must manually copy tags to Diigo.

---

### Tag Search Workflow

```bash
# 1. Find tags with wildcard pattern
diigo search "*python*"

# 2. See usage statistics
diigo list --source user --limit 50

# 3. Search semantically (if embeddings available)
diigo search "machine learning" --semantic --threshold 0.75
```

---

### Tag Maintenance Workflow

```bash
# 1. Search for potential duplicates
diigo search "*workflow*"

# Example output shows:
# - git-workflow (count: 45)
# - gitworkflow (count: 3)
# - workflow (count: 120)

# 2. Merge duplicates
diigo merge --source gitworkflow --target git-workflow

# 3. Verify merge
diigo search "*workflow*"
```

**v1.0 Note**: Merge only updates local database. Does not update bookmarks in Diigo.

---

### Bulk Sync Workflow

```bash
# Sync large number of bookmarks in batches
diigo sync --count 1000

# Check database size
diigo list --limit 10

# Re-sync to update counts
diigo sync --count 1000
```

---

## Security Best Practices

### Credential Protection

**DO**:
- ✅ Store credentials in `.env` file
- ✅ Run `chmod 600 .env` (Unix/macOS)
- ✅ Add `.env` to `.gitignore`
- ✅ Use different API keys for dev/prod
- ✅ Rotate API keys every 90 days

**DON'T**:
- ❌ Commit `.env` to git
- ❌ Share `.env` file via email/chat
- ❌ Store credentials in code
- ❌ Use same password for Diigo and other services

### Pre-commit Hook (Prevent Accidental Commits)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Prevent committing .env file

if git diff --cached --name-only | grep -q "^\.env$"; then
    echo "❌ ERROR: Attempting to commit .env file!"
    echo "   This file contains secrets and should NEVER be committed."
    echo "   To bypass (NOT RECOMMENDED): git commit --no-verify"
    exit 1
fi
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

### File Permissions

**Unix/macOS**:
```bash
# Restrict .env to owner only (600)
chmod 600 .env

# Verify
ls -la .env
# Expected: -rw------- (owner read/write only)
```

**Windows**:
```powershell
# Remove inheritance and grant access only to current user
icacls .env /inheritance:r
icacls .env /grant:r "%USERNAME%:F"
```

### API Key Rotation

**Every 90 days**:
1. Generate new API key in OpenAI/Diigo dashboard
2. Update `.env` file
3. Test with `diigo save --dry-run`
4. Revoke old API key

### Network Security

**HTTPS-only** (enforced by tool):
- All API calls use HTTPS
- Tool rejects HTTP endpoints
- Certificates validated (no MITM attacks)

### Backup Security

**Encrypted backups**:
```bash
# Export tags
diigo tags:export --output tags.csv

# Encrypt with GPG
gpg --symmetric --cipher-algo AES256 tags.csv
# Creates tags.csv.gpg

# Upload to secure cloud storage
mv tags.csv.gpg ~/Dropbox/Backups/
```

---

## Troubleshooting

### Installation Issues

#### Python Version Too Old

**Symptom**:
```
ERROR: Python 3.10+ required, found 3.9.0
```

**Solution**:
```bash
# macOS with Homebrew
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# Windows
Download from https://www.python.org/downloads/
```

#### SQLite Too Old (No FTS5)

**Symptom**:
```
ERROR: SQLite 3.35.0+ required for FTS5 support
```

**Solution**:
```bash
# Check version
python -c "import sqlite3; print(sqlite3.sqlite_version)"

# macOS: Update Python (includes newer SQLite)
brew install python@3.11

# Linux: Compile from source or use pyenv
# https://www.sqlite.org/download.html
```

---

### Configuration Issues

#### Missing .env File

**Symptom**:
```
ERROR: .env file not found
```

**Solution**:
```bash
# Create .env in current directory
cat > .env <<EOF
DIIGO_USER=your_username
DIIGO_PASS=your_password
DIIGO_API_KEY=your_api_key
OPENAI_API_KEY=sk-your_key
EOF

chmod 600 .env
```

#### Invalid API Keys

**Symptom**:
```
ERROR: OpenAI API authentication failed (401)
```

**Solution**:
1. Verify key in `.env` matches OpenAI dashboard
2. Check for extra spaces or newlines
3. Regenerate API key if needed

---

### Runtime Issues

#### Diigo API Rate Limit

**Symptom**:
```
ERROR: Diigo API returned 429 Too Many Requests
```

**Solution**:
- Wait 60 seconds before retrying
- Use `--dry-run` to test without API calls
- Diigo rate limits unknown, be conservative

#### LLM API Timeout

**Symptom**:
```
⚠️  OpenAI API timeout, trying Anthropic...
⚠️  Anthropic API timeout, using fallback...
```

**Solution**:
- Network connectivity issue, check internet
- OpenAI/Anthropic may be down, check status pages
- Fallback uses keyword extraction (lower quality)

#### Tag Reconciliation Conflict

**Symptom**:
```
⚠️  Unknown tag: cli-tools
   Similar: cli (0.82), command-line-interface (0.78)
   Allow this new tag? [y/N]:
```

**Solution**:
- Press `e` to edit tags manually
- Choose existing tag from suggestions
- Or press `y` to add as new tag

---

### Performance Issues

#### Slow Tag Sync

**Symptom**: `tags:sync` takes > 5 minutes

**Solution**:
- Normal for 5000+ bookmarks
- Uses pagination (100 bookmarks/page)
- Check network speed (Diigo API may be slow)

#### Slow Semantic Search

**Symptom**: `tags:similar` takes > 2 seconds

**Solution**:
- O(n) cosine similarity for all tags
- Acceptable for < 10,000 tags
- For > 100,000 tags, consider ChromaDB/Weaviate

---

### Database Issues

#### Corrupted Database

**Symptom**:
```
ERROR: SQLite database is corrupted
```

**Solution**:
```bash
# Restore from backup
cp ~/.diigo/tags.db.backup ~/.diigo/tags.db

# Or re-sync from Diigo
rm ~/.diigo/tags.db
diigo tags:sync --user your_username
```

#### Database Locked

**Symptom**:
```
ERROR: Database is locked
```

**Solution**:
- Another `diigo` process is running
- Check: `ps aux | grep diigo`
- Kill stale process: `kill <pid>`

---

## FAQ

### General

**Q: Is this tool official from Diigo?**
A: No, this is an independent CLI tool using Diigo's public API.

**Q: What can v1.0 do?**
A: v1.0 focuses on tag management and AI-powered tag generation. It can:
- Sync bookmarks from Diigo to extract tags
- Generate tag suggestions using AI (preview only)
- Search tags with wildcard or semantic search
- Merge duplicate tags locally
- List and analyze tag usage

**Q: Can v1.0 save bookmarks to Diigo?**
A: No. v1.0 generates tag suggestions only. You must manually copy tags to Diigo web UI. Bookmark saving planned for v1.1.

**Q: Does this work with other bookmarking services?**
A: v1.0 supports only Diigo. Pinboard/Raindrop support planned for future versions.

**Q: Is my data sent to OpenAI?**
A: Only when using `diigo generate`. The tool sends title, URL, and optional description for tag generation. No full HTML content is sent.

---

### Privacy & Security

**Q: Are my credentials stored securely?**
A: API keys stored in plain-text `.env` file. Use file permissions (chmod 600) to restrict access. Store `.env` outside version control.

**Q: Can others access my tags?**
A: Tags stored locally in platform-specific database location. No cloud sync. Your data stays on your machine.

**Q: What data is logged?**
A: v1.0 has minimal logging. Error messages are displayed to console but not persisted.

**Q: Does this tool validate inputs for security?**
A: Yes. Includes prompt injection detection, API key redaction from logs, and HTTPS-only API calls.

---

### Features & Limitations

**Q: Why doesn't `diigo generate` save bookmarks?**
A: v1.0 is a tag preview tool. It helps you see what tags AI would suggest before manually adding the bookmark via Diigo web UI. Auto-save planned for v1.1.

**Q: Can I use semantic search?**
A: Yes, with `--semantic` flag, but only if embeddings are pre-stored in database. v1.0 does NOT auto-generate embeddings during sync.

**Q: Does `diigo merge` update bookmarks in Diigo?**
A: No. v1.0 merge only updates local database counts. It does NOT modify bookmarks stored in Diigo. Full sync planned for v1.1.

**Q: Can I delete bookmarks?**
A: No, this tool is read-only for bookmarks. Use Diigo web UI to delete bookmarks.

**Q: Can I export tags?**
A: Not in v1.0. You can query tags with `diigo list` but CSV export not implemented. Planned for future version.

---

### Troubleshooting

**Q: Why are some tags rejected?**
A: Tag validation depends on Diigo's rules. Generally, tags should be lowercase, alphanumeric, and use hyphens.

**Q: Why is semantic search not working?**
A: Semantic search requires embeddings to be stored in database. v1.0 does not auto-generate embeddings. Ensure embeddings exist or use wildcard search instead.

**Q: Can I use this offline?**
A: No. Requires internet for Diigo API (`sync` command) and OpenAI API (`generate` command). Search and list work offline once database is synced.

---

## Getting Help

**Documentation**: https://github.com/yourusername/diigo-tagger-ai/docs
**Issues**: https://github.com/yourusername/diigo-tagger-ai/issues
**Discussions**: https://github.com/yourusername/diigo-tagger-ai/discussions

**Before filing an issue**:
1. Check troubleshooting section above
2. Search existing issues
3. Include error messages and `diigo --version` output

---

## Appendix: Example .gitignore

Add to your `.gitignore`:

```gitignore
# Diigo Tagger AI
.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Database (optional - remove if you want to commit)
# *.db
# *.db-wal
# *.db-shm
```

---

## Appendix: Example .env.example

Create `.env.example` for documentation (safe to commit):

```bash
# Diigo API Configuration
DIIGO_API_KEY=get_from_diigo_settings

# OpenAI API Configuration
OPENAI_API_KEY=sk-get_from_openai_dashboard

# Optional: Custom database path
# DIIGO_DB_PATH=/custom/path/tags.db
```

---

**Documentation Status**: ✅ Updated for v1.0.0 Implementation
**Last Updated**: October 16, 2025
**Version**: 1.0.0
**Changes**: Updated all commands to match actual CLI implementation
