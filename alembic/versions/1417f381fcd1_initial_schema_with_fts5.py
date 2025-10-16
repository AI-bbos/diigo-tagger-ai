"""initial_schema_with_fts5

Revision ID: 1417f381fcd1
Revises: 
Create Date: 2025-10-16 11:38:20.344841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1417f381fcd1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tags table with FTS5 support."""

    # Create tags table
    op.execute("""
        CREATE TABLE tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            count INTEGER DEFAULT 0 NOT NULL,
            last_used TIMESTAMP,
            source TEXT DEFAULT 'user' NOT NULL,
            embedding BLOB,
            embedding_version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT name_not_empty CHECK (length(name) > 0),
            CONSTRAINT count_non_negative CHECK (count >= 0),
            CONSTRAINT valid_source CHECK (source IN ('user', 'master', 'system'))
        )
    """)

    # Create indexes for performance
    op.execute("CREATE INDEX idx_tags_count ON tags(count DESC)")
    op.execute("CREATE INDEX idx_tags_last_used ON tags(last_used DESC)")
    op.execute("CREATE INDEX idx_tags_source ON tags(source)")
    op.execute("CREATE INDEX idx_tags_embedding_version ON tags(embedding_version)")

    # Create FTS5 virtual table for wildcard search
    op.execute("""
        CREATE VIRTUAL TABLE tags_fts USING fts5(
            name,
            content=tags,
            content_rowid=id
        )
    """)

    # Triggers to keep FTS5 in sync with tags table
    op.execute("""
        CREATE TRIGGER tags_ai AFTER INSERT ON tags BEGIN
            INSERT INTO tags_fts(rowid, name) VALUES (new.id, new.name);
        END
    """)

    op.execute("""
        CREATE TRIGGER tags_ad AFTER DELETE ON tags BEGIN
            DELETE FROM tags_fts WHERE rowid = old.id;
        END
    """)

    op.execute("""
        CREATE TRIGGER tags_au AFTER UPDATE ON tags BEGIN
            UPDATE tags_fts SET name = new.name WHERE rowid = old.id;
        END
    """)

    # Trigger to update updated_at timestamp
    op.execute("""
        CREATE TRIGGER tags_updated_at AFTER UPDATE ON tags BEGIN
            UPDATE tags SET updated_at = CURRENT_TIMESTAMP WHERE id = old.id;
        END
    """)


def downgrade() -> None:
    """Drop tags table and FTS5."""

    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS tags_updated_at")
    op.execute("DROP TRIGGER IF EXISTS tags_au")
    op.execute("DROP TRIGGER IF EXISTS tags_ad")
    op.execute("DROP TRIGGER IF EXISTS tags_ai")

    # Drop FTS5 virtual table
    op.execute("DROP TABLE IF EXISTS tags_fts")

    # Drop indexes (automatically dropped with table, but explicit for clarity)
    op.execute("DROP INDEX IF EXISTS idx_tags_embedding_version")
    op.execute("DROP INDEX IF EXISTS idx_tags_source")
    op.execute("DROP INDEX IF EXISTS idx_tags_last_used")
    op.execute("DROP INDEX IF EXISTS idx_tags_count")

    # Drop tags table
    op.execute("DROP TABLE IF EXISTS tags")
