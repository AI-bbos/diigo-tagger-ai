# Database Operations

**⚠️ DANGER ZONE ⚠️**

This document contains **DESTRUCTIVE** operations that can **PERMANENTLY DELETE** your data.

Read carefully and make backups before proceeding.

---

## Table of Contents

1. [Database Location](#database-location)
2. [Backup Operations](#backup-operations)
3. [Drop and Recreate Database](#drop-and-recreate-database)
4. [Migration Scripts](#migration-scripts)
5. [Manual SQL Operations](#manual-sql-operations)
6. [Recovery Procedures](#recovery-procedures)

---

## Database Location

The SQLite database is stored at:

**macOS/Linux:**
```bash
~/Library/Application Support/diigo-tagger/tags.db
```

**Related files:**
- `tags.db` - Main database
- `tags.db-shm` - Shared memory (WAL mode)
- `tags.db-wal` - Write-Ahead Log (WAL mode)

---

## Backup Operations

### Create Backup

**Always backup before dangerous operations!**

```bash
# macOS/Linux
cp -r "$HOME/Library/Application Support/diigo-tagger" "$HOME/Library/Application Support/diigo-tagger.backup-$(date +%Y%m%d-%H%M%S)"
```

### Restore from Backup

```bash
# macOS/Linux
# 1. Stop the application first!
# 2. Remove current database
rm -rf "$HOME/Library/Application Support/diigo-tagger"
# 3. Restore from backup
cp -r "$HOME/Library/Application Support/diigo-tagger.backup-YYYYMMDD-HHMMSS" "$HOME/Library/Application Support/diigo-tagger"
```

---

## Drop and Recreate Database

### 🚨 NUCLEAR OPTION - READ THIS FIRST 🚨

**⚠️ THIS WILL PERMANENTLY DELETE:**
- All bookmarks in the local database
- All tags and tag associations
- All user edits and modifications
- **CANNOT BE UNDONE WITHOUT BACKUP**

**✓ This will NOT delete:**
- Bookmarks on Diigo.com (they're safe)
- Your Diigo account data

**When to use this:**
- You want to start fresh with a clean database
- Your database has corrupted date fields from old sync code
- You've verified backups exist and you're ready to lose local data

### Step 1: Backup (MANDATORY)

```bash
# Create timestamped backup
cp -r "$HOME/Library/Application Support/diigo-tagger" "$HOME/Library/Application Support/diigo-tagger.backup-$(date +%Y%m%d-%H%M%S)"

# Verify backup exists
ls -lh "$HOME/Library/Application Support/diigo-tagger.backup"*
```

### Step 2: Stop the Application

**CRITICAL:** Stop uvicorn/FastAPI server before dropping the database!

```bash
# Press Ctrl+C in the terminal running uvicorn
# OR find and kill the process
ps aux | grep uvicorn
kill <PID>
```

### Step 3: Drop the Database

```bash
# Remove all database files
rm -f "$HOME/Library/Application Support/diigo-tagger/tags.db"
rm -f "$HOME/Library/Application Support/diigo-tagger/tags.db-shm"
rm -f "$HOME/Library/Application Support/diigo-tagger/tags.db-wal"

# Verify deletion
ls -la "$HOME/Library/Application Support/diigo-tagger/"
```

### Step 4: Recreate Database

```bash
cd /path/to/diigo_tagger
poetry run python -c "from diigo_tagger.db import init_db; init_db(); print('Database initialized')"
```

### Step 5: Full Sync from Diigo

**Option A: Via Web UI**
1. Start the server: `poetry run uvicorn diigo_tagger.api.main:app --reload`
2. Go to: http://localhost:8000/sync
3. Select "Full Sync (fetch all bookmarks)"
4. Click "Start Sync"
5. Wait for completion (may take 15-30 minutes for large libraries)

**Option B: Via CLI**
```bash
poetry run diigo-tagger sync --all
```

### Step 6: Verify

```bash
# Check bookmark count
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "SELECT COUNT(*) FROM bookmarks;"

# Check date distribution
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "SELECT
    MIN(created_at) as oldest,
    MAX(created_at) as newest,
    COUNT(*) as total
FROM bookmarks;"
```

---

## Migration Scripts

Migration scripts fix data issues without dropping the database.

### Date Migration (Fix created_at from Diigo)

**What it does:** Copies `diigo_created_at` → `created_at` for bookmarks synced with old code.

**When to use:** After upgrading to new sync code that properly uses Diigo dates.

**How to run:**

```bash
cd /path/to/diigo_tagger
python scripts/migrate_created_dates.py
```

**What it shows:**
- Number of bookmarks needing migration
- Example of before/after dates
- Confirmation prompt before making changes

**Safe to run:** Yes - only updates dates, doesn't delete data. But backup first!

### Custom Migration Template

```python
#!/usr/bin/env python3
"""Template for custom migration scripts."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diigo_tagger.db import get_session
from diigo_tagger.models import Bookmark, Tag

def migrate():
    """Your migration logic here."""
    session = get_session()
    try:
        # 1. Find records to fix
        # 2. Make changes
        # 3. Commit
        session.commit()
        print("✓ Migration successful")
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    # Add confirmation prompt for safety
    response = input("Run migration? [y/N]: ")
    if response.lower() == 'y':
        migrate()
    else:
        print("Cancelled")
```

---

## Manual SQL Operations

### Read-Only Queries (Safe)

These queries **DO NOT** modify data:

#### Check Database Stats
```bash
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
SELECT 'Bookmarks:', COUNT(*) FROM bookmarks
UNION ALL
SELECT 'Tags:', COUNT(*) FROM tags
UNION ALL
SELECT 'Tag Associations:', COUNT(*) FROM bookmark_tags;
"
```

#### Find Bookmarks Missing Dates
```bash
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
SELECT
    display_id,
    substr(title, 1, 50) as title,
    created_at,
    diigo_created_at
FROM bookmarks
WHERE diigo_created_at IS NULL
LIMIT 10;
"
```

#### Date Distribution
```bash
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
SELECT
    strftime('%Y', created_at) as year,
    COUNT(*) as count
FROM bookmarks
GROUP BY year
ORDER BY year;
"
```

#### Most Popular Tags
```bash
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
SELECT
    t.name,
    COUNT(bt.bookmark_id) as usage_count
FROM tags t
LEFT JOIN bookmark_tags bt ON t.id = bt.tag_id
GROUP BY t.name
ORDER BY usage_count DESC
LIMIT 20;
"
```

#### Bookmarks Without Tags
```bash
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
SELECT
    display_id,
    substr(title, 1, 60) as title,
    url
FROM bookmarks b
WHERE NOT EXISTS (
    SELECT 1 FROM bookmark_tags bt WHERE bt.bookmark_id = b.id
)
LIMIT 10;
"
```

### Destructive Queries (DANGEROUS)

**⚠️ WARNING:** These modify or delete data. **BACKUP FIRST!**

#### Delete Specific Bookmark
```bash
# Find the bookmark first (safe)
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
SELECT id, display_id, title FROM bookmarks WHERE display_id = 'XXXXXXXX';
"

# Delete it (DESTRUCTIVE)
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
DELETE FROM bookmarks WHERE display_id = 'XXXXXXXX';
"
```

#### Delete Orphaned Tags
```bash
# Find orphaned tags first (safe)
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
SELECT id, name FROM tags t
WHERE NOT EXISTS (
    SELECT 1 FROM bookmark_tags bt WHERE bt.tag_id = t.id
);
"

# Delete them (DESTRUCTIVE)
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
DELETE FROM tags WHERE id IN (
    SELECT t.id FROM tags t
    WHERE NOT EXISTS (
        SELECT 1 FROM bookmark_tags bt WHERE bt.tag_id = t.id
    )
);
"
```

#### Reset All updated_at Timestamps
```bash
# DESTRUCTIVE - sets all updated_at to created_at
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
UPDATE bookmarks SET updated_at = created_at;
"
```

#### Vacuum Database (Reclaim Space)
```bash
# Safe but locks database during operation
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "VACUUM;"
```

---

## Recovery Procedures

### Database Corruption

**Symptoms:**
- `database disk image is malformed` errors
- Queries hang indefinitely
- Missing data that should exist

**Recovery Steps:**

1. **Stop the application**
2. **Create backup** (even corrupted DB might be partially recoverable)
   ```bash
   cp "$HOME/Library/Application Support/diigo-tagger/tags.db" "$HOME/Library/Application Support/diigo-tagger/tags.db.corrupted"
   ```

3. **Try SQLite recovery**
   ```bash
   # Dump to SQL
   sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db.corrupted" .dump > dump.sql

   # Recreate from dump
   sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db.recovered" < dump.sql

   # Replace original
   mv "$HOME/Library/Application Support/diigo-tagger/tags.db" "$HOME/Library/Application Support/diigo-tagger/tags.db.old"
   mv "$HOME/Library/Application Support/diigo-tagger/tags.db.recovered" "$HOME/Library/Application Support/diigo-tagger/tags.db"
   ```

4. **If recovery fails:** Drop and recreate (see above)

### Accidental Deletion

**If you deleted data but haven't closed the database:**

1. **DO NOT close the application!**
2. **DO NOT run any more queries!**
3. **Immediately restore from backup:**
   ```bash
   # In another terminal
   cp "$HOME/Library/Application Support/diigo-tagger.backup-LATEST/tags.db" "$HOME/Library/Application Support/diigo-tagger/tags.db.restore"
   ```
4. **Stop application**
5. **Replace database**
   ```bash
   mv "$HOME/Library/Application Support/diigo-tagger/tags.db.restore" "$HOME/Library/Application Support/diigo-tagger/tags.db"
   ```

**If you already closed/committed:**
- Restore from backup (if exists)
- Otherwise: Drop and full re-sync from Diigo

---

## Emergency Contacts

**If something goes wrong:**

1. **Check the logs** (if server is running):
   - Look for errors in terminal output
   - Check for SQLite error codes

2. **Don't panic:**
   - Your Diigo.com bookmarks are safe (separate from local DB)
   - If you have backups, you can restore
   - If no backups, you can re-sync from Diigo

3. **Recovery priority:**
   1. Restore from backup (fastest, preserves local edits)
   2. Drop and re-sync from Diigo (slower, loses local edits)

---

## Best Practices

### Regular Backups

Create a backup script and run it regularly:

```bash
#!/bin/bash
# backup-diigo-db.sh

BACKUP_DIR="$HOME/backups/diigo-tagger"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SOURCE="$HOME/Library/Application Support/diigo-tagger"

mkdir -p "$BACKUP_DIR"
cp -r "$SOURCE" "$BACKUP_DIR/diigo-tagger-$TIMESTAMP"

# Keep only last 7 backups
cd "$BACKUP_DIR"
ls -t | tail -n +8 | xargs rm -rf

echo "Backup created: diigo-tagger-$TIMESTAMP"
```

### Before Dangerous Operations

**Checklist:**
- [ ] Created backup with timestamp
- [ ] Verified backup exists and has files
- [ ] Stopped the application
- [ ] Tested restoration procedure (optional but recommended)
- [ ] Have time to wait for re-sync if needed (15-30 min for large libraries)

### Testing Changes

Use a test database:

```bash
# Export test data
sqlite3 "$HOME/Library/Application Support/diigo-tagger/tags.db" "
.output test-export.sql
.dump
.quit
"

# Create test database
mkdir -p /tmp/diigo-test
sqlite3 /tmp/diigo-test/tags.db < test-export.sql

# Test your dangerous operation on test DB
# ...

# If successful, apply to production
```

---

## Help Resources

- **Main Documentation:** [README.md](../README.md)
- **Help Pages:** http://localhost:8000/help (when server running)
- **Issues:** https://github.com/yourusername/diigo-tagger/issues

---

**Last Updated:** 2025-11-05
**Database Schema Version:** 1.0.0
