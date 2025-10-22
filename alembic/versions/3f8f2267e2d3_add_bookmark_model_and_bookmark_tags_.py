"""add bookmark model and bookmark_tags association table

Revision ID: 3f8f2267e2d3
Revises: 1417f381fcd1
Create Date: 2025-10-22 18:37:20.802763

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f8f2267e2d3'
down_revision: Union[str, Sequence[str], None] = '1417f381fcd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add bookmarks table and bookmark_tags association table."""
    # Create bookmarks table
    op.create_table('bookmarks',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('display_id', sa.String(length=8), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('shared', sa.Boolean(), nullable=False),
    sa.Column('outline', sa.Text(), nullable=True),
    sa.Column('groups', sa.Text(), nullable=True),
    sa.Column('diigo_created_at', sa.DateTime(), nullable=True),
    sa.Column('diigo_updated_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('length(url) > 0', name='url_not_empty'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('display_id'),
    sa.UniqueConstraint('url')
    )

    # Create indexes for bookmarks
    op.create_index('idx_bookmarks_created_at', 'bookmarks', ['created_at'], unique=False)
    op.create_index('idx_bookmarks_display_id', 'bookmarks', ['display_id'], unique=False)
    op.create_index('idx_bookmarks_url', 'bookmarks', ['url'], unique=False)

    # Create bookmark_tags association table
    op.create_table('bookmark_tags',
    sa.Column('bookmark_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['bookmark_id'], ['bookmarks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('bookmark_id', 'tag_id')
    )

    # Trigger to update updated_at timestamp on bookmarks
    op.execute("""
        CREATE TRIGGER bookmarks_updated_at AFTER UPDATE ON bookmarks BEGIN
            UPDATE bookmarks SET updated_at = CURRENT_TIMESTAMP WHERE id = old.id;
        END
    """)


def downgrade() -> None:
    """Remove bookmarks table and bookmark_tags association table."""
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS bookmarks_updated_at")

    # Drop bookmark_tags association table
    op.drop_table('bookmark_tags')

    # Drop indexes
    op.drop_index('idx_bookmarks_url', table_name='bookmarks')
    op.drop_index('idx_bookmarks_display_id', table_name='bookmarks')
    op.drop_index('idx_bookmarks_created_at', table_name='bookmarks')

    # Drop bookmarks table
    op.drop_table('bookmarks')
