# ABOUTME: Unit tests for the bulk tag operations API endpoint
# ABOUTME: Tests rename, delete, lowercase, and merge operations using in-memory SQLite

import asyncio

import pytest
from fastapi import HTTPException

from diigo_tagger.api.routes.bookmarks import bulk_tag_operations, BulkTagRequest
from diigo_tagger.models import Tag, Bookmark, bookmark_tags
from diigo_tagger.db import init_db, get_session


def run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def db_session(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test_bulk.db"
    init_db(db_path)
    session = get_session(db_path)
    yield session
    session.close()


@pytest.fixture
def seeded_db(db_session):
    """Seed database with tags and bookmarks for bulk operation tests."""
    tag_python = Tag(name="Python", count=0, source="diigo")
    tag_js = Tag(name="JavaScript", count=0, source="diigo")
    tag_web = Tag(name="web-dev", count=0, source="diigo")
    tag_py_lower = Tag(name="python", count=0, source="user")
    db_session.add_all([tag_python, tag_js, tag_web, tag_py_lower])
    db_session.flush()

    bm1 = Bookmark(display_id="aaaa0001", url="https://example.com/1", title="BM1")
    bm2 = Bookmark(display_id="aaaa0002", url="https://example.com/2", title="BM2")
    bm3 = Bookmark(display_id="aaaa0003", url="https://example.com/3", title="BM3")
    db_session.add_all([bm1, bm2, bm3])
    db_session.flush()

    db_session.execute(bookmark_tags.insert().values(bookmark_id=bm1.id, tag_id=tag_python.id))
    db_session.execute(bookmark_tags.insert().values(bookmark_id=bm2.id, tag_id=tag_python.id))
    db_session.execute(bookmark_tags.insert().values(bookmark_id=bm1.id, tag_id=tag_js.id))
    db_session.execute(bookmark_tags.insert().values(bookmark_id=bm3.id, tag_id=tag_web.id))
    db_session.execute(bookmark_tags.insert().values(bookmark_id=bm3.id, tag_id=tag_py_lower.id))
    db_session.commit()

    return db_session


class TestBulkDelete:
    """Test bulk delete operation."""

    def test_delete_single_tag(self, seeded_db, monkeypatch):
        """Should delete a tag and remove it from bookmarks."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="delete", tags=["JavaScript"])
        result = run(bulk_tag_operations(request))

        assert result.operation == "delete"
        assert result.affected_tags == 1
        assert result.affected_bookmarks == 1

        tag = seeded_db.query(Tag).filter_by(name="JavaScript").first()
        assert tag is None

    def test_delete_multiple_tags(self, seeded_db, monkeypatch):
        """Should delete multiple tags."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="delete", tags=["JavaScript", "web-dev"])
        result = run(bulk_tag_operations(request))

        assert result.affected_tags == 2
        assert result.affected_bookmarks == 2

    def test_delete_nonexistent_tag(self, seeded_db, monkeypatch):
        """Should gracefully handle nonexistent tags."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="delete", tags=["nonexistent"])
        result = run(bulk_tag_operations(request))

        assert result.affected_tags == 0
        assert result.affected_bookmarks == 0


class TestBulkRename:
    """Test bulk rename operation."""

    def test_rename_tag(self, seeded_db, monkeypatch):
        """Should rename a tag and preserve bookmark associations."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="rename", tags=["web-dev"], new_name="webdev")
        result = run(bulk_tag_operations(request))

        assert result.operation == "rename"
        assert result.affected_tags == 1
        assert result.affected_bookmarks == 1

        old = seeded_db.query(Tag).filter_by(name="web-dev").first()
        new = seeded_db.query(Tag).filter_by(name="webdev").first()
        assert old is None
        assert new is not None

    def test_rename_nonexistent_tag(self, seeded_db, monkeypatch):
        """Should raise 404 for nonexistent tag."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="rename", tags=["ghost"], new_name="new")
        with pytest.raises(HTTPException) as exc_info:
            run(bulk_tag_operations(request))
        assert exc_info.value.status_code == 404

    def test_rename_to_existing_tag(self, seeded_db, monkeypatch):
        """Should raise 400 if target name already exists."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="rename", tags=["Python"], new_name="python")
        with pytest.raises(HTTPException) as exc_info:
            run(bulk_tag_operations(request))
        assert exc_info.value.status_code == 400


class TestBulkLowercase:
    """Test bulk lowercase operation."""

    def test_lowercase_tag(self, seeded_db, monkeypatch):
        """Should lowercase a tag name."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="lowercase", tags=["JavaScript"])
        result = run(bulk_tag_operations(request))

        assert result.operation == "lowercase"
        assert result.affected_tags == 1

        tag = seeded_db.query(Tag).filter_by(name="javascript").first()
        assert tag is not None

    def test_lowercase_merges_with_existing(self, seeded_db, monkeypatch):
        """Should merge into existing lowercase tag when collision occurs."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="lowercase", tags=["Python"])
        result = run(bulk_tag_operations(request))

        assert result.affected_tags == 1
        upper = seeded_db.query(Tag).filter_by(name="Python").first()
        lower = seeded_db.query(Tag).filter_by(name="python").first()
        assert upper is None
        assert lower is not None

    def test_lowercase_already_lowercase(self, seeded_db, monkeypatch):
        """Should skip tags that are already lowercase."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="lowercase", tags=["web-dev"])
        result = run(bulk_tag_operations(request))

        assert result.affected_tags == 0


class TestBulkMerge:
    """Test bulk merge operation."""

    def test_merge_tags(self, seeded_db, monkeypatch):
        """Should merge tags into the one with highest bookmark count."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="merge", tags=["Python", "JavaScript"])
        result = run(bulk_tag_operations(request))

        assert result.operation == "merge"
        assert result.affected_tags == 2

        js_tag = seeded_db.query(Tag).filter_by(name="JavaScript").first()
        assert js_tag is None

        py_tag = seeded_db.query(Tag).filter_by(name="Python").first()
        assert py_tag is not None

    def test_merge_requires_two_tags(self, seeded_db, monkeypatch):
        """Should raise 400 if fewer than 2 tags provided."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="merge", tags=["Python"])
        with pytest.raises(HTTPException) as exc_info:
            run(bulk_tag_operations(request))
        assert exc_info.value.status_code == 400


class TestBulkValidation:
    """Test request validation for bulk operations."""

    def test_invalid_operation(self, seeded_db, monkeypatch):
        """Should reject invalid operation names."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="nuke", tags=["Python"])
        with pytest.raises(HTTPException) as exc_info:
            run(bulk_tag_operations(request))
        assert exc_info.value.status_code == 400

    def test_rename_without_new_name(self, seeded_db, monkeypatch):
        """Should reject rename without new_name."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="rename", tags=["Python"])
        with pytest.raises(HTTPException) as exc_info:
            run(bulk_tag_operations(request))
        assert exc_info.value.status_code == 400

    def test_empty_tags_list(self, seeded_db, monkeypatch):
        """Should reject empty tags list."""
        monkeypatch.setattr("diigo_tagger.api.routes.bookmarks.get_session", lambda: seeded_db)

        request = BulkTagRequest(operation="delete", tags=[])
        with pytest.raises(HTTPException) as exc_info:
            run(bulk_tag_operations(request))
        assert exc_info.value.status_code == 400
