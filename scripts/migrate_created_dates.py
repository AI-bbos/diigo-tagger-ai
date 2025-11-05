#!/usr/bin/env python3
# ABOUTME: Migration script to backfill created_at from diigo_created_at
# ABOUTME: Fixes bookmarks synced with old code that used sync time instead of Diigo's creation date

"""
Migrate created_at dates for existing bookmarks.

This script copies diigo_created_at → created_at for all bookmarks where:
1. diigo_created_at is not NULL (we have Diigo's date)
2. created_at != diigo_created_at (they're different, meaning old sync code was used)

Run this once after upgrading to the new sync code.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from diigo_tagger.db import get_session
from diigo_tagger.models import Bookmark


def migrate_dates():
    """Copy diigo_created_at to created_at for existing bookmarks."""
    session = get_session()

    try:
        # Find bookmarks where we have Diigo's date but created_at is different
        bookmarks_to_fix = (
            session.query(Bookmark)
            .filter(
                Bookmark.diigo_created_at.isnot(None),
                Bookmark.diigo_created_at != Bookmark.created_at
            )
            .all()
        )

        if not bookmarks_to_fix:
            print("✓ No bookmarks need migration - all dates already correct!")
            return

        print(f"Found {len(bookmarks_to_fix)} bookmarks to migrate")
        print(f"Example: Bookmark '{bookmarks_to_fix[0].title[:50]}'")
        print(f"  Current created_at: {bookmarks_to_fix[0].created_at}")
        print(f"  Diigo created_at:   {bookmarks_to_fix[0].diigo_created_at}")
        print()

        response = input(f"Migrate {len(bookmarks_to_fix)} bookmarks? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled")
            return

        # Perform migration
        migrated_count = 0
        for bookmark in bookmarks_to_fix:
            bookmark.created_at = bookmark.diigo_created_at
            migrated_count += 1

            if migrated_count % 1000 == 0:
                print(f"  Migrated {migrated_count}/{len(bookmarks_to_fix)}...")
                session.commit()

        # Final commit
        session.commit()
        print(f"✓ Successfully migrated {migrated_count} bookmarks!")
        print(f"  created_at now reflects Diigo's original creation date")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Bookmark Date Migration Script")
    print("=" * 60)
    print()
    print("This script will copy diigo_created_at → created_at")
    print("for bookmarks that were synced with the old code.")
    print()

    migrate_dates()
