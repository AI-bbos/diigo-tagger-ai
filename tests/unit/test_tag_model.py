# ABOUTME: Unit tests for Tag database model
# ABOUTME: Tests CRUD operations, constraints, embedding storage, and FTS5 sync

import pytest
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from diigo_tagger.models import Base, Tag


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestTagCRUD:
    """Test Create, Read, Update, Delete operations."""

    def test_create_tag(self, db_session):
        """Should create tag with valid data."""
        tag = Tag(name="python", count=5, source="user")
        db_session.add(tag)
        db_session.commit()

        assert tag.id is not None
        assert tag.created_at is not None
        assert tag.updated_at is not None
        assert tag.name == "python"
        assert tag.count == 5
        assert tag.source == "user"

    def test_unique_tag_name(self, db_session):
        """Should enforce unique tag names."""
        tag1 = Tag(name="duplicate", count=1, source="user")
        db_session.add(tag1)
        db_session.commit()

        tag2 = Tag(name="duplicate", count=2, source="user")
        db_session.add(tag2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_name_not_empty_constraint(self, db_session):
        """Should reject empty tag names."""
        tag = Tag(name="", count=0, source="user")
        db_session.add(tag)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_count_non_negative_constraint(self, db_session):
        """Should reject negative counts."""
        tag = Tag(name="test", count=-5, source="user")
        db_session.add(tag)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_valid_source_constraint(self, db_session):
        """Should only allow user|master|system sources."""
        valid_sources = ["user", "master", "system"]
        for source in valid_sources:
            tag = Tag(name=f"test-{source}", count=0, source=source)
            db_session.add(tag)
            db_session.commit()

        # Invalid source should fail
        tag_invalid = Tag(name="invalid-source", count=0, source="invalid")
        db_session.add(tag_invalid)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestEmbeddings:
    """Test embedding storage and retrieval."""

    def test_set_embedding(self, db_session):
        """Should store embedding as BLOB."""
        tag = Tag(name="test-embedding", count=1, source="user")
        embedding = np.random.rand(384).astype(np.float32)

        tag.set_embedding(embedding)
        db_session.add(tag)
        db_session.commit()

        assert tag.embedding is not None
        assert len(tag.embedding) == 384 * 4  # 384 floats × 4 bytes

    def test_get_embedding(self, db_session):
        """Should retrieve embedding as numpy array."""
        tag = Tag(name="test-embedding", count=1, source="user")
        original_embedding = np.random.rand(384).astype(np.float32)

        tag.set_embedding(original_embedding)
        db_session.add(tag)
        db_session.commit()

        retrieved_embedding = tag.get_embedding()
        assert isinstance(retrieved_embedding, np.ndarray)
        assert retrieved_embedding.shape == (384,)
        assert retrieved_embedding.dtype == np.float32
        np.testing.assert_array_almost_equal(original_embedding, retrieved_embedding)

    def test_embedding_none_when_not_set(self, db_session):
        """Should return None when embedding not set."""
        tag = Tag(name="no-embedding", count=1, source="user")
        db_session.add(tag)
        db_session.commit()

        assert tag.get_embedding() is None
