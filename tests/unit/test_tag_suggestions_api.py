# ABOUTME: Unit tests for the GET /api/v1/tags/suggestions endpoint
# ABOUTME: Verifies near-duplicate, orphaned, inconsistent-case, and single-use tag detection

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from diigo_tagger.models import Base, Tag, Bookmark, bookmark_tags


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with all tables.

    Uses StaticPool so every connection shares the same in-memory database.
    """
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session_factory(engine):
    """Create a session factory bound to the test engine."""
    return sessionmaker(bind=engine)


@pytest.fixture
def session(session_factory):
    """Create a session for direct test data setup."""
    sess = session_factory()
    yield sess
    sess.close()


@pytest.fixture
def client(session_factory, monkeypatch):
    """Create a test client with get_session returning sessions from test engine.

    Each get_session call returns a fresh session from the same in-memory
    engine, so the endpoint's session.close() in its finally block does
    not destroy the test data.
    """
    factory = lambda db_path=None: session_factory()  # noqa: E731

    import diigo_tagger.api.main as main_mod
    import diigo_tagger.api.routes.bookmarks as bookmarks_mod

    monkeypatch.setattr(main_mod, "get_session", factory)
    monkeypatch.setattr(bookmarks_mod, "get_session", factory)

    from diigo_tagger.api.main import app
    return TestClient(app)


@pytest.fixture
def populated_session(session):
    """Populate the database with data that triggers all four categories."""
    # Near-duplicate pair: "javascript" and "java-script"
    tag_js = Tag(name="javascript", count=5, source="diigo")
    tag_js2 = Tag(name="java-script", count=2, source="user")

    # Inconsistent case: "Python" and "python"
    tag_py_upper = Tag(name="Python", count=8, source="diigo")
    tag_py_lower = Tag(name="python", count=3, source="user")

    # Orphaned tag (no bookmarks)
    tag_orphan = Tag(name="abandoned", count=0, source="user")

    # Normal tag used by many bookmarks
    tag_web = Tag(name="web", count=10, source="diigo")

    # Single-use tag
    tag_niche = Tag(name="very-specific-topic", count=1, source="user")

    session.add_all([
        tag_js, tag_js2, tag_py_upper, tag_py_lower,
        tag_orphan, tag_web, tag_niche,
    ])
    session.flush()

    # Create bookmarks
    bm1 = Bookmark(
        url="https://example.com/1", title="JS Guide",
        display_id=Bookmark.generate_display_id("https://example.com/1"),
    )
    bm2 = Bookmark(
        url="https://example.com/2", title="Python Tutorial",
        display_id=Bookmark.generate_display_id("https://example.com/2"),
    )
    bm3 = Bookmark(
        url="https://example.com/3", title="Web Basics",
        display_id=Bookmark.generate_display_id("https://example.com/3"),
    )
    session.add_all([bm1, bm2, bm3])
    session.flush()

    # Associations
    session.execute(bookmark_tags.insert().values(bookmark_id=bm1.id, tag_id=tag_js.id))
    session.execute(bookmark_tags.insert().values(bookmark_id=bm2.id, tag_id=tag_js.id))
    session.execute(bookmark_tags.insert().values(bookmark_id=bm1.id, tag_id=tag_js2.id))
    session.execute(bookmark_tags.insert().values(bookmark_id=bm2.id, tag_id=tag_py_upper.id))
    session.execute(bookmark_tags.insert().values(bookmark_id=bm3.id, tag_id=tag_py_upper.id))
    session.execute(bookmark_tags.insert().values(bookmark_id=bm1.id, tag_id=tag_py_lower.id))
    session.execute(bookmark_tags.insert().values(bookmark_id=bm1.id, tag_id=tag_web.id))
    session.execute(bookmark_tags.insert().values(bookmark_id=bm2.id, tag_id=tag_web.id))
    session.execute(bookmark_tags.insert().values(bookmark_id=bm3.id, tag_id=tag_web.id))
    session.execute(bookmark_tags.insert().values(bookmark_id=bm3.id, tag_id=tag_niche.id))
    session.commit()

    return session


class TestTagSuggestionsEndpoint:
    """Test the GET /api/v1/tags/suggestions endpoint."""

    def test_returns_all_four_categories(self, client, populated_session):
        """Response should contain all four suggestion categories."""
        resp = client.get("/api/v1/tags/suggestions")
        assert resp.status_code == 200
        data = resp.json()
        assert "near_duplicates" in data
        assert "orphaned_tags" in data
        assert "inconsistent_case" in data
        assert "single_use_tags" in data

    def test_near_duplicates_detected(self, client, populated_session):
        """Should detect 'javascript' and 'java-script' as near duplicates."""
        resp = client.get("/api/v1/tags/suggestions")
        data = resp.json()
        pairs = data["near_duplicates"]
        tag_pair_names = set()
        for p in pairs:
            tag_pair_names.add(frozenset([p["tag1"], p["tag2"]]))
        assert frozenset(["javascript", "java-script"]) in tag_pair_names

    def test_near_duplicates_have_required_fields(self, client, populated_session):
        """Each near-duplicate entry should have all required fields."""
        resp = client.get("/api/v1/tags/suggestions")
        pairs = resp.json()["near_duplicates"]
        if pairs:
            entry = pairs[0]
            assert "tag1" in entry
            assert "tag2" in entry
            assert "similarity" in entry
            assert "count1" in entry
            assert "count2" in entry
            assert 0.0 <= entry["similarity"] <= 1.0

    def test_orphaned_tags_detected(self, client, populated_session):
        """Should detect 'abandoned' as orphaned (no bookmarks)."""
        resp = client.get("/api/v1/tags/suggestions")
        orphaned = resp.json()["orphaned_tags"]
        orphaned_names = [t["name"] for t in orphaned]
        assert "abandoned" in orphaned_names

    def test_orphaned_excludes_used_tags(self, client, populated_session):
        """Should not list tags that have bookmarks as orphaned."""
        resp = client.get("/api/v1/tags/suggestions")
        orphaned_names = [t["name"] for t in resp.json()["orphaned_tags"]]
        assert "javascript" not in orphaned_names
        assert "web" not in orphaned_names

    def test_inconsistent_case_detected(self, client, populated_session):
        """Should detect 'Python' and 'python' as inconsistent case variants."""
        resp = client.get("/api/v1/tags/suggestions")
        cases = resp.json()["inconsistent_case"]
        found = False
        for entry in cases:
            lower_variants = [v.lower() for v in entry["variants"]]
            if "python" in lower_variants and len(entry["variants"]) > 1:
                found = True
                assert "suggested" in entry
                assert "total_count" in entry
                break
        assert found, "Should find Python/python case inconsistency"

    def test_inconsistent_case_suggests_most_used(self, client, populated_session):
        """Suggested variant should be the one with the most bookmarks."""
        resp = client.get("/api/v1/tags/suggestions")
        cases = resp.json()["inconsistent_case"]
        for entry in cases:
            if "python" in [v.lower() for v in entry["variants"]]:
                # "Python" has 2 bookmarks, "python" has 1
                assert entry["suggested"] == "Python"
                break

    def test_single_use_tags_detected(self, client, populated_session):
        """Should detect tags used by exactly one bookmark."""
        resp = client.get("/api/v1/tags/suggestions")
        single = resp.json()["single_use_tags"]
        single_names = [t["name"] for t in single]
        assert "very-specific-topic" in single_names

    def test_single_use_includes_bookmark_title(self, client, populated_session):
        """Single-use tag entries should include the bookmark title."""
        resp = client.get("/api/v1/tags/suggestions")
        single = resp.json()["single_use_tags"]
        for entry in single:
            if entry["name"] == "very-specific-topic":
                assert entry["bookmark_title"] == "Web Basics"
                break

    def test_empty_database_returns_empty_lists(self, client):
        """Should return empty lists for all categories on empty database."""
        resp = client.get("/api/v1/tags/suggestions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["near_duplicates"] == []
        assert data["orphaned_tags"] == []
        assert data["inconsistent_case"] == []
        assert data["single_use_tags"] == []
