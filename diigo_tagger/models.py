# ABOUTME: SQLAlchemy ORM models for Diigo Tagger AI database
# ABOUTME: Defines Tag model with FTS5 support and optional embeddings

from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, CheckConstraint, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import numpy as np

Base = declarative_base()


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
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("length(name) > 0", name="name_not_empty"),
        CheckConstraint("count >= 0", name="count_non_negative"),
        CheckConstraint("source IN ('user', 'master', 'system')", name="valid_source"),
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
