"""add parent_id to tags table

Revision ID: 111605f46b18
Revises: 3f8f2267e2d3
Create Date: 2026-05-12 22:01:28.299435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '111605f46b18'
down_revision: Union[str, Sequence[str], None] = '3f8f2267e2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add parent_id column to tags for hierarchy support."""
    with op.batch_alter_table('tags') as batch_op:
        batch_op.add_column(sa.Column('parent_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_tags_parent_id', 'tags', ['parent_id'], ['id'])


def downgrade() -> None:
    """Remove parent_id column from tags."""
    with op.batch_alter_table('tags') as batch_op:
        batch_op.drop_constraint('fk_tags_parent_id', type_='foreignkey')
        batch_op.drop_column('parent_id')
