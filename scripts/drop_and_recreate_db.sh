#!/bin/bash
# ABOUTME: Drop and recreate database script - DANGEROUS!
# ABOUTME: Permanently deletes local database and reinitializes empty schema

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Database path
if [[ "$OSTYPE" =~ ^darwin ]]; then
    DB_DIR="$HOME/Library/Application Support/diigo-tagger"
else
    DB_DIR="$HOME/.local/share/diigo-tagger"
fi

DB_PATH="$DB_DIR/tags.db"
BACKUP_DIR="$HOME/Library/Application Support"

echo "=========================================="
echo "🚨 DATABASE DROP AND RECREATE SCRIPT 🚨"
echo "=========================================="
echo ""
echo -e "${RED}⚠️  WARNING: THIS WILL PERMANENTLY DELETE YOUR LOCAL DATABASE ⚠️${NC}"
echo ""
echo "This will:"
echo "  - Delete all bookmarks in the local database"
echo "  - Delete all tags and associations"
echo "  - Delete all user edits"
echo ""
echo "This will NOT affect:"
echo "  - Your bookmarks on Diigo.com (they're safe)"
echo "  - Your Diigo account"
echo ""
echo "Database location: $DB_PATH"
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo -e "${YELLOW}Database does not exist at: $DB_PATH${NC}"
    echo "Nothing to drop. Creating fresh database..."
    cd "$(dirname "$0")/.."
    poetry run python -c "from diigo_tagger.db import init_db; init_db(); print('✓ Database initialized')"
    exit 0
fi

# Confirm backup
echo "=========================================="
echo "STEP 1: BACKUP (MANDATORY)"
echo "=========================================="
echo ""

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_PATH="$BACKUP_DIR/diigo-tagger.backup-$TIMESTAMP"

echo "Creating backup at: $BACKUP_PATH"
cp -r "$DB_DIR" "$BACKUP_PATH"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    echo ""
else
    echo -e "${RED}✗ Backup failed! Aborting.${NC}"
    exit 1
fi

# Final confirmation
echo "=========================================="
echo "FINAL CONFIRMATION"
echo "=========================================="
echo ""
echo -e "${RED}Are you ABSOLUTELY SURE you want to drop the database?${NC}"
echo ""
echo "Type 'DROP DATABASE' (exactly) to confirm: "
read -r confirmation

if [ "$confirmation" != "DROP DATABASE" ]; then
    echo ""
    echo "Cancelled. Database not modified."
    echo "Backup kept at: $BACKUP_PATH"
    exit 0
fi

echo ""
echo "=========================================="
echo "STEP 2: DROPPING DATABASE"
echo "=========================================="
echo ""

# Check if app is running
if pgrep -f "uvicorn.*diigo_tagger" > /dev/null; then
    echo -e "${RED}⚠️  WARNING: Application appears to be running!${NC}"
    echo "Please stop the application (Ctrl+C in the terminal running uvicorn)"
    echo ""
    echo "Continue anyway? [y/N]: "
    read -r continue_anyway
    if [ "$continue_anyway" != "y" ]; then
        echo "Cancelled."
        exit 1
    fi
fi

# Drop database files
echo "Removing database files..."
rm -f "$DB_PATH"
rm -f "$DB_PATH-shm"
rm -f "$DB_PATH-wal"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database dropped${NC}"
    echo ""
else
    echo -e "${RED}✗ Failed to drop database${NC}"
    exit 1
fi

# Recreate database
echo "=========================================="
echo "STEP 3: RECREATING DATABASE"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."
poetry run python -c "from diigo_tagger.db import init_db; init_db(); print('✓ Database initialized')"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Database recreated successfully${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Failed to recreate database${NC}"
    echo "You can restore from backup at: $BACKUP_PATH"
    exit 1
fi

# Instructions
echo "=========================================="
echo "NEXT STEPS"
echo "=========================================="
echo ""
echo "1. Start the application:"
echo "   poetry run uvicorn diigo_tagger.api.main:app --reload"
echo ""
echo "2. Go to: http://localhost:8000/sync"
echo ""
echo "3. Select 'Full Sync (fetch all bookmarks)'"
echo ""
echo "4. Wait for completion (may take 15-30 minutes)"
echo ""
echo -e "${GREEN}Backup saved at: $BACKUP_PATH${NC}"
echo ""
