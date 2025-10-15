# User Documentation: Diigo Tagger AI

**Project**: diigo-tagger-ai
**Created**: October 15, 2025
**Tech Writer**: Claude
**Status**: Ready for QA Review
**Input**: `01-bsa-analysis.md`, `02-architecture-design.md`, `03-data-engineering-plan.md`, `04-security-audit.md`

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
poetry install
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
DIIGO_USER=your_username
DIIGO_PASS=your_password
DIIGO_API_KEY=your_diigo_api_key
OPENAI_API_KEY=sk-your_openai_key
```

**⚠️ SECURITY WARNING**:
- **NEVER commit `.env` to git!**
- Run `chmod 600 .env` to restrict file permissions (Unix/macOS)
- Add `.env` to your `.gitignore` file

### Step 3: Sync Your Existing Tags

```bash
diigo tags:sync --user your_username
```

**What this does**:
- Fetches all your existing bookmarks from Diigo
- Extracts unique tag names
- Stores them in local database (`~/.diigo/tags.db`)
- **Runtime**: 1-5 minutes for thousands of bookmarks

**Expected output**:
```
🔄 Syncing tags from Diigo...
   Fetching bookmarks: 1247/1247 [████████████] 100%
   Found 3,421 unique tags
✅ Tag database updated: ~/.diigo/tags.db
```

### Step 4: Save Your First Bookmark

```bash
diigo save "https://example.com/article"
```

**What happens**:
1. Tool fetches the webpage
2. Extracts title, author, description
3. Sends metadata to LLM for tag generation
4. Shows you a preview with proposed tags
5. Asks for confirmation before saving

**Example interaction**:
```
🌐 Fetching: https://example.com/article
📄 Extracted metadata:
   Title: How to Build CLI Tools with Python
   Author: Jane Doe

🤖 Generating tags with OpenAI (gpt-4o-mini)...

Proposed bookmark:

URL:    https://example.com/article
Title:  How to Build CLI Tools with Python
Author: Jane Doe
Desc:   A comprehensive guide to building command-line tools...

Tags:   python, cli-tools, command-line, development,
        source:example.com, author:jane-doe

Unknown tags (will be added):
  - cli-tools → Similar: cli, command-line-interface (0.82)

Save to Diigo? [Y/n/e]:
```

**Options**:
- `Y` or Enter: Save bookmark
- `n`: Cancel (don't save)
- `e`: Edit tags manually

### Step 5: Search Your Tags

**Wildcard search** (fast, uses FTS5):
```bash
diigo tags:search "*python*"
```

**Semantic search** (finds related tags):
```bash
diigo tags:similar "machine learning"
```

---

## Configuration

### Environment Variables

**Required**:
```bash
DIIGO_USER=your_username         # Diigo login username
DIIGO_PASS=your_password          # Diigo password (plain text, see security note)
DIIGO_API_KEY=abc123              # From Diigo Settings → API Key
OPENAI_API_KEY=sk-...             # From OpenAI dashboard
```

**Optional**:
```bash
ANTHROPIC_API_KEY=sk-ant-...      # For Anthropic Claude fallback
```

### Configuration File (Advanced)

Create `~/.diigo-tagger.yml` for advanced settings:

```yaml
# LLM Provider Configuration
llm_providers:
  - provider: openai
    model: gpt-4o-mini
    priority: 1
    temperature: 0.2
    max_tokens: 150

  - provider: anthropic
    model: claude-3-haiku-20240307
    priority: 2
    temperature: 0.2
    max_tokens: 150

  - provider: ollama
    model: llama3.2
    priority: 3
    temperature: 0.2
    endpoint: http://localhost:11434

# Tag Reconciliation Settings
reconciliation:
  fuzzy_max_distance: 2              # Levenshtein distance threshold
  semantic_threshold: 0.75           # Cosine similarity threshold (0-1)
  auto_merge: false                  # Manual merge by default

# Database Settings
database:
  path: ~/.diigo/tags.db            # SQLite database location
  enable_embeddings: true            # Enable semantic search

# UI Settings
ui:
  color_scheme: auto                 # auto | light | dark
  show_progress: true                # Progress bars for long operations
```

### Database Location

**Default**: `~/.diigo/tags.db`

**Custom location**:
```bash
export DIIGO_DB_PATH=/path/to/custom/tags.db
```

---

## Command Reference

### `diigo save <url>`

Save a bookmark to Diigo with AI-generated tags.

**Usage**:
```bash
diigo save <url> [options]
```

**Arguments**:
- `url` (required): URL to bookmark, or text content

**Options**:
- `--dry-run`: Show what would be saved without actually saving
- `--no-interactive`: Skip confirmation prompt (batch mode)
- `--allow-new-tags`: Allow tags not in database (default: warn)
- `--force`: Auto-approve (combine with `--no-interactive`)
- `--desc <text>`: Override LLM-generated description

**Examples**:

```bash
# Interactive save (default)
diigo save "https://example.com/article"

# Dry run (preview without saving)
diigo save "https://example.com/article" --dry-run

# Batch mode (no prompts)
diigo save "https://example.com/article" --no-interactive --force

# Custom description
diigo save "https://example.com/article" --desc "My custom description"
```

**Exit codes**:
- `0`: Success
- `1`: Network error (URL unreachable)
- `2`: LLM API error (all providers failed)
- `3`: User cancelled
- `4`: Diigo API error

---

### `diigo tags:sync --user <username>`

Sync tags from Diigo to local database (one-time setup).

**Usage**:
```bash
diigo tags:sync --user <username> [options]
```

**Arguments**:
- `--user` (required): Your Diigo username

**Options**:
- `--force`: Re-sync even if database exists
- `--clear`: Clear existing tags before syncing

**Examples**:

```bash
# Initial sync
diigo tags:sync --user brooke

# Force re-sync
diigo tags:sync --user brooke --force

# Clear and re-sync
diigo tags:sync --user brooke --clear
```

**What it does**:
1. Fetches all bookmarks via Diigo API (paginated)
2. Extracts unique tag names
3. Counts usage frequency for each tag
4. Stores in SQLite database with `source='master'`

**Performance**:
- ~100 bookmarks/second
- 2000 bookmarks ≈ 20 seconds
- Shows progress bar with ETA

---

### `diigo tags:search <pattern>`

Search tags using wildcard patterns (fast FTS5 search).

**Usage**:
```bash
diigo tags:search <pattern> [options]
```

**Arguments**:
- `pattern` (required): Wildcard pattern (e.g., `*python*`)

**Options**:
- `--limit <n>`: Max results to show (default: 50)
- `--sort <field>`: Sort by `count`, `name`, or `last_used` (default: `count`)

**Examples**:

```bash
# Find tags containing "python"
diigo tags:search "*python*"

# Find tags starting with "git"
diigo tags:search "git*"

# Show top 10 most-used tags
diigo tags:search "*" --limit 10 --sort count
```

**Output**:
```
Tag                    Count   Last Used
─────────────────────────────────────────
python                 247     2025-10-15
python-library         89      2025-10-12
python3                45      2025-10-10
micropython            12      2025-09-20
```

**Performance**: < 50ms for thousands of tags

---

### `diigo tags:similar <query>`

Find semantically similar tags using embeddings.

**Usage**:
```bash
diigo tags:similar <query> [options]
```

**Arguments**:
- `query` (required): Natural language query (e.g., "machine learning")

**Options**:
- `--threshold <n>`: Similarity threshold 0-1 (default: 0.75)
- `--limit <n>`: Max results (default: 10)

**Examples**:

```bash
# Find tags related to "machine learning"
diigo tags:similar "machine learning"

# Lower threshold for more results
diigo tags:similar "version control" --threshold 0.65
```

**Output**:
```
Tag                    Similarity   Count
──────────────────────────────────────────
machine-learning       0.95         156
ml                     0.89         78
deep-learning          0.83         45
neural-networks        0.79         34
ai                     0.76         89
```

**First-time setup**:
```
⚠️  Semantic search requires downloading 80MB embedding model.
   Model: sentence-transformers/all-MiniLM-L6-v2
   This is a one-time download.

   Proceed? [Y/n]:
```

**Performance**: < 500ms for 10,000 tags

---

### `diigo tags:show`

List all tags in database.

**Usage**:
```bash
diigo tags:show [options]
```

**Options**:
- `--source <type>`: Filter by source (`user`, `master`, `system`)
- `--limit <n>`: Max tags to show (default: 100)
- `--sort <field>`: Sort by `count`, `name`, `last_used` (default: `count`)

**Examples**:

```bash
# Show top 100 tags
diigo tags:show

# Show only user-created tags
diigo tags:show --source user

# Show all system tags
diigo tags:show --source system --limit 1000
```

---

### `diigo tags:merge <from> <to>`

Manually merge duplicate tags (v1.1 feature).

**Usage**:
```bash
diigo tags:merge <from> <to>
```

**Example**:
```bash
# Merge "gitworkflow" into "git-workflow"
diigo tags:merge gitworkflow git-workflow
```

**What it does**:
1. Updates all bookmarks using `<from>` to use `<to>`
2. Increments count for `<to>`
3. Deletes `<from>` tag from database

---

### `diigo tags:export`

Export tags to CSV for backup.

**Usage**:
```bash
diigo tags:export [options]
```

**Options**:
- `--output <path>`: Output file (default: `tags_export.csv`)

**Example**:
```bash
diigo tags:export --output ~/Dropbox/diigo_backup.csv
```

**Output format**:
```csv
name,count,last_used,source
python,247,2025-10-15T14:30:00,master
cli-tools,12,2025-10-15T10:15:00,user
source:github.com,156,2025-10-14T22:45:00,system
```

---

## Workflows

### Daily Workflow: Save Bookmarks

```bash
# 1. Save bookmark with interactive review
diigo save "https://news.ycombinator.com/item?id=12345"

# 2. Review proposed tags, edit if needed

# 3. Press 'Y' to save
```

**Time saved**: 2-3 minutes per bookmark (vs manual tagging)

---

### Weekly Workflow: Tag Maintenance

```bash
# 1. Search for potential duplicates
diigo tags:search "*workflow*"

# Example output shows:
# - git-workflow (count: 45)
# - gitworkflow (count: 3)
# - workflow (count: 120)

# 2. Merge duplicates
diigo tags:merge gitworkflow git-workflow

# 3. Backup tags
diigo tags:export --output ~/backups/tags_$(date +%Y%m%d).csv
```

---

### Batch Workflow: Import Multiple Bookmarks

```bash
# Create file with URLs (one per line)
cat > urls.txt <<EOF
https://example.com/article1
https://example.com/article2
https://example.com/article3
EOF

# Process all URLs in batch mode
while read url; do
  diigo save "$url" --no-interactive --force
  sleep 2  # Rate limiting
done < urls.txt
```

---

### Exploratory Workflow: Find Related Tags

```bash
# 1. Find tags related to topic
diigo tags:similar "kubernetes deployment"

# 2. Review similar tags:
# - kubernetes, docker, containers, devops, cloud-native

# 3. Use in searches
diigo tags:search "*kubernetes*"
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

**Q: Does this work with other bookmarking services?**
A: v1.0 supports only Diigo. Pinboard/Raindrop support planned for v1.1.

**Q: Can I use this without OpenAI?**
A: Yes, configure Anthropic or Ollama in `~/.diigo-tagger.yml`. Fallback uses keyword extraction.

**Q: Is my data sent to OpenAI?**
A: Only metadata (title, author, 2000-char excerpt) is sent for tag generation. Full HTML never sent.

---

### Privacy & Security

**Q: Are my credentials stored securely?**
A: Credentials stored in plain-text `.env` file. Use file permissions (600) to restrict access. OS keychain support planned for v1.1.

**Q: Can others access my tags?**
A: Tags stored locally in `~/.diigo/tags.db`. No cloud sync. Your data stays on your machine.

**Q: What data is logged?**
A: v1.0 has no logging. Optional audit logging planned for v1.1.

---

### Features

**Q: Can I edit tags before saving?**
A: Yes, press `e` at the confirmation prompt to manually edit tags.

**Q: Can I save bookmarks without AI?**
A: Use `--no-interactive --force` to skip review, but LLM still generates tags. Manual tagging not supported in v1.0.

**Q: Can I delete bookmarks?**
A: No, this tool only creates bookmarks. Use Diigo web UI to delete.

**Q: Does this update existing bookmarks?**
A: Diigo API is idempotent - if URL exists, it updates tags. Otherwise creates new bookmark.

---

### Troubleshooting

**Q: Why are some tags rejected?**
A: Tags must be lowercase, alphanumeric, and use hyphens only. Special characters are invalid.

**Q: Why is semantic search slow?**
A: First use downloads 80MB model (~10 seconds). Subsequent searches are < 500ms.

**Q: Can I use this offline?**
A: No, requires internet for Diigo API and LLM API. Local LLM (Ollama) works offline after model download.

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
# Diigo Configuration
DIIGO_USER=your_username_here
DIIGO_PASS=your_password_here
DIIGO_API_KEY=get_from_diigo_settings

# LLM Configuration
OPENAI_API_KEY=sk-get_from_openai_dashboard

# Optional: Anthropic (for fallback)
# ANTHROPIC_API_KEY=sk-ant-get_from_anthropic

# Optional: Database path (default: ~/.diigo/tags.db)
# DIIGO_DB_PATH=/custom/path/tags.db
```

---

**Documentation Status**: ✅ Complete
**Last Updated**: October 15, 2025
**Version**: 1.0.0

**Next Steps**:
- Handoff to QAS Agent for test planning
- QAS should validate all examples and commands
- RTE should create deployment guide
