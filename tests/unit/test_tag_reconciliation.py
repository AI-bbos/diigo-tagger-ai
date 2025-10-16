# ABOUTME: Unit tests for tag reconciliation service
# ABOUTME: Tests tag merging, deduplication, wildcard search, and semantic similarity

import pytest
import numpy as np
from pathlib import Path
from diigo_tagger.services.tag_reconciliation import TagReconciliationService
from diigo_tagger.models import Tag
from diigo_tagger.db import init_db, get_session


@pytest.fixture
def db_session(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test_tags.db"
    init_db(db_path)
    session = get_session(db_path)
    yield session
    session.close()


@pytest.fixture
def reconciliation_service(db_session):
    """Create reconciliation service with test database."""
    return TagReconciliationService(db_session)


class TestTagDeduplication:
    """Test tag deduplication and normalization."""

    def test_normalize_tag_lowercases(self, reconciliation_service):
        """Should normalize tags to lowercase."""
        assert reconciliation_service.normalize_tag("Python") == "python"
        assert reconciliation_service.normalize_tag("WEB-DEV") == "web-dev"

    def test_normalize_tag_strips_whitespace(self, reconciliation_service):
        """Should strip leading/trailing whitespace."""
        assert reconciliation_service.normalize_tag("  python  ") == "python"

    def test_normalize_tag_handles_empty(self, reconciliation_service):
        """Should handle empty strings."""
        assert reconciliation_service.normalize_tag("") == ""
        assert reconciliation_service.normalize_tag("   ") == ""

    def test_deduplicate_tags(self, reconciliation_service):
        """Should deduplicate tags (case-insensitive)."""
        tags = ["Python", "python", "PYTHON", "web-dev", "Web-Dev"]
        result = reconciliation_service.deduplicate_tags(tags)
        assert len(result) == 2
        assert "python" in result
        assert "web-dev" in result

    def test_deduplicate_preserves_order(self, reconciliation_service):
        """Should preserve first occurrence order."""
        tags = ["z-tag", "a-tag", "Z-TAG"]
        result = reconciliation_service.deduplicate_tags(tags)
        assert result == ["z-tag", "a-tag"]


class TestWildcardSearch:
    """Test wildcard tag search using FTS5."""

    def test_wildcard_search_prefix(self, reconciliation_service, db_session):
        """Should find tags matching prefix wildcards."""
        # Create test tags
        db_session.add(Tag(name="python", count=5, source="user"))
        db_session.add(Tag(name="python-web", count=3, source="user"))
        db_session.add(Tag(name="javascript", count=2, source="user"))
        db_session.commit()

        results = reconciliation_service.wildcard_search("python*")
        assert len(results) == 2
        assert "python" in [t.name for t in results]
        assert "python-web" in [t.name for t in results]

    def test_wildcard_search_infix(self, reconciliation_service, db_session):
        """Should find tags with infix matches (via multiple prefix queries)."""
        db_session.add(Tag(name="web-development", count=5, source="user"))
        db_session.add(Tag(name="mobile-web", count=3, source="user"))
        db_session.add(Tag(name="webinar", count=2, source="user"))
        db_session.commit()

        # FTS5 supports prefix wildcards
        results = reconciliation_service.wildcard_search("web*")
        assert len(results) >= 2  # Should find web-development, mobile-web, webinar

    def test_wildcard_search_empty_query(self, reconciliation_service):
        """Should handle empty query strings."""
        results = reconciliation_service.wildcard_search("")
        assert len(results) == 0

    def test_wildcard_search_no_matches(self, reconciliation_service, db_session):
        """Should return empty list when no matches."""
        db_session.add(Tag(name="python", count=5, source="user"))
        db_session.commit()

        results = reconciliation_service.wildcard_search("ruby*")
        assert len(results) == 0


class TestTagMerging:
    """Test merging multiple tags into one."""

    def test_merge_tags_combines_counts(self, reconciliation_service, db_session):
        """Should combine usage counts when merging."""
        db_session.add(Tag(name="python", count=5, source="user"))
        db_session.add(Tag(name="Python", count=3, source="user"))
        db_session.add(Tag(name="PYTHON", count=2, source="user"))
        db_session.commit()

        reconciliation_service.merge_tags(
            source_tags=["Python", "PYTHON"], target_tag="python"
        )

        # Should have one tag with combined count
        result = db_session.query(Tag).filter_by(name="python").first()
        assert result is not None
        assert result.count == 10  # 5 + 3 + 2

        # Source tags should be deleted
        assert db_session.query(Tag).count() == 1

    def test_merge_tags_preserves_latest_timestamp(self, reconciliation_service, db_session):
        """Should keep the most recent last_used timestamp."""
        from datetime import datetime

        old_time = datetime(2025, 1, 1)
        new_time = datetime(2025, 1, 15)

        db_session.add(Tag(name="python", count=5, source="user", last_used=old_time))
        db_session.add(Tag(name="Python", count=3, source="user", last_used=new_time))
        db_session.commit()

        reconciliation_service.merge_tags(source_tags=["Python"], target_tag="python")

        result = db_session.query(Tag).filter_by(name="python").first()
        assert result.last_used == new_time

    def test_merge_tags_creates_target_if_missing(self, reconciliation_service, db_session):
        """Should create target tag if it doesn't exist."""
        db_session.add(Tag(name="py", count=5, source="user"))
        db_session.commit()

        reconciliation_service.merge_tags(source_tags=["py"], target_tag="python")

        result = db_session.query(Tag).filter_by(name="python").first()
        assert result is not None
        assert result.count == 5

        # Source should be deleted
        assert db_session.query(Tag).filter_by(name="py").first() is None


class TestSemanticSimilarity:
    """Test semantic tag similarity using embeddings."""

    def test_find_similar_tags_with_embeddings(self, reconciliation_service, db_session):
        """Should find semantically similar tags using embeddings."""
        # Create tags with mock embeddings
        tag1 = Tag(name="python", count=5, source="user")
        tag1.set_embedding(np.random.rand(384).astype(np.float32))

        tag2 = Tag(name="javascript", count=3, source="user")
        tag2.set_embedding(np.random.rand(384).astype(np.float32))

        tag3 = Tag(name="python-programming", count=2, source="user")
        # Similar to tag1 (simulate high similarity by copying embedding)
        tag3.set_embedding(tag1.get_embedding())

        db_session.add_all([tag1, tag2, tag3])
        db_session.commit()

        results = reconciliation_service.find_similar_tags("python", threshold=0.8, limit=5)

        # Should find python-programming as similar (same embedding)
        assert len(results) > 0
        assert any(r.name == "python-programming" for r in results)

    def test_find_similar_tags_no_embeddings(self, reconciliation_service, db_session):
        """Should return empty list if query tag has no embedding."""
        db_session.add(Tag(name="python", count=5, source="user"))
        db_session.commit()

        results = reconciliation_service.find_similar_tags("python", threshold=0.8)
        assert len(results) == 0

    def test_find_similar_tags_nonexistent(self, reconciliation_service, db_session):
        """Should return empty list if query tag doesn't exist."""
        results = reconciliation_service.find_similar_tags("nonexistent", threshold=0.8)
        assert len(results) == 0
