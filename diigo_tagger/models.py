# ABOUTME: SQLAlchemy ORM models for Diigo Tagger AI database
# ABOUTME: Defines Tag and Bookmark models with FTS5 support and optional embeddings

from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, CheckConstraint, Index, Table, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime
import numpy as np
import zlib

Base = declarative_base()

# Association table for many-to-many relationship between bookmarks and tags
bookmark_tags = Table(
    'bookmark_tags',
    Base.metadata,
    Column('bookmark_id', Integer, ForeignKey('bookmarks.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, nullable=False, default=func.now())
)


class Tag(Base):
    """
    Tag model with FTS5 support and optional embeddings.

    Stores tag names from Diigo bookmarks with usage statistics and optional
    semantic embeddings for similarity search.
    """

    __tablename__ = "tags"

    # Columns
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    count = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime, nullable=True)
    source = Column(String, nullable=False, default="user")
    embedding = Column(LargeBinary, nullable=True)
    embedding_version = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey('tags.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship("Tag", remote_side=[id], backref="children")

    # Constraints
    __table_args__ = (
        CheckConstraint("length(name) > 0", name="name_not_empty"),
        CheckConstraint("count >= 0", name="count_non_negative"),
        CheckConstraint("source IN ('user', 'master', 'system', 'diigo')", name="valid_source"),
        Index("idx_tags_count", "count"),
        Index("idx_tags_last_used", "last_used"),
        Index("idx_tags_source", "source"),
        Index("idx_tags_embedding_version", "embedding_version"),
    )

    def set_embedding(self, vector: np.ndarray) -> None:
        """
        Store numpy array as BLOB.

        Args:
            vector: 384-dimensional float32 numpy array

        Raises:
            AssertionError: If vector is not 384-dim float32
        """
        assert vector.shape == (384,), f"Embedding must be 384-dimensional, got {vector.shape}"
        assert vector.dtype == np.float32, f"Embedding must be float32, got {vector.dtype}"
        self.embedding = vector.tobytes()

    def get_embedding(self) -> np.ndarray | None:
        """
        Load BLOB as numpy array.

        Returns:
            384-dimensional float32 numpy array, or None if not set
        """
        if self.embedding is None:
            return None
        return np.frombuffer(self.embedding, dtype=np.float32)

    def __repr__(self):
        return f"<Tag(name='{self.name}', count={self.count}, source='{self.source}')>"


class Bookmark(Base):
    """
    Bookmark model storing Diigo bookmarks with metadata.

    Stores full bookmark details from Diigo including URL, title, description,
    and Diigo-specific features like outlines, groups, and sharing status.
    Uses CRC32 hash of URL for short, human-friendly display IDs.
    """

    __tablename__ = "bookmarks"

    # Columns
    id = Column(Integer, primary_key=True, autoincrement=True)
    display_id = Column(String(8), nullable=False, unique=True, index=True)  # CRC32 hash for easy typing
    url = Column(Text, nullable=False, unique=True)  # Full URL
    title = Column(Text, nullable=True)  # Can be LLM-generated or user-provided
    description = Column(Text, nullable=True)  # Can be LLM-generated or user-provided

    # Diigo-specific fields
    shared = Column(Boolean, nullable=False, default=True)  # Public/private
    outline = Column(Text, nullable=True)  # Diigo outliner content
    groups = Column(Text, nullable=True)  # Comma-separated group names

    # Metadata
    diigo_created_at = Column(DateTime, nullable=True)  # When created in Diigo
    diigo_updated_at = Column(DateTime, nullable=True)  # When last updated in Diigo
    created_at = Column(DateTime, nullable=False, default=func.now())  # When added to our DB
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    tags = relationship("Tag", secondary=bookmark_tags, backref="bookmarks")

    # Constraints
    __table_args__ = (
        CheckConstraint("length(url) > 0", name="url_not_empty"),
        Index("idx_bookmarks_display_id", "display_id"),
        Index("idx_bookmarks_url", "url"),
        Index("idx_bookmarks_created_at", "created_at"),
    )

    @staticmethod
    def generate_display_id(url: str) -> str:
        """
        Generate a short, human-friendly display ID from URL using CRC32 hash.

        Uses CRC32 (fast, non-cryptographic hash) and converts to hex.
        Result is 8 characters, easy to type for CLI lookups.

        Args:
            url: The bookmark URL

        Returns:
            8-character hexadecimal string (e.g., "a3f2b8c1")
        """
        # CRC32 returns unsigned 32-bit integer
        crc = zlib.crc32(url.encode('utf-8')) & 0xffffffff
        # Convert to 8-character hex string (32 bits = 8 hex chars)
        return f"{crc:08x}"

    def __repr__(self):
        return f"<Bookmark(display_id='{self.display_id}', url='{self.url[:50]}...', title='{self.title}')>"


class Setting(Base):
    """Key-value settings stored in the database.

    Provides a simple persistence layer for application configuration such as
    tag prefixes and other user-adjustable options.  The primary key is the
    setting name (``key``), so each name is unique and upserts are trivial.
    """

    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value[:40]}')>"
