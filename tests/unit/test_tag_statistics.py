# ABOUTME: Unit tests for TagService.get_statistics() method
# ABOUTME: Tests analytics including top tags, orphaned tags, source breakdown, and edge cases

import pytest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diigo_tagger.models import Base, Tag, Bookmark, bookmark_tags
from diigo_tagger.services.tag_service import TagService


@pytest.fixture
def session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


class TestGetStatisticsEmptyDatabase:
    """Test get_statistics with an empty database."""

    def test_returns_all_expected_keys(self, session):
        """Should return a dict with all expected keys even when empty."""
        service = TagService(session=session)
        stats = service.get_statistics()

        expected_keys = {
            "total_tags",
            "total_bookmarks",
            "tags_per_bookmark_avg",
            "top_tags",
            "orphaned_tags",
            "orphaned_count",
            "recent_tags",
            "source_breakdown",
            "single_use_tags",
        }
        assert set(stats.keys()) == expected_keys

    def test_empty_database_zeroes(self, session):
        """Should return zero counts for empty database."""
        service = TagService(session=session)
        stats = service.get_statistics()

        assert stats["total_tags"] == 0
        assert stats["total_bookmarks"] == 0
        assert stats["tags_per_bookmark_avg"] == 0.0
        assert stats["top_tags"] == []
        assert stats["orphaned_tags"] == []
        assert stats["orphaned_count"] == 0
        assert stats["recent_tags"] == []
        assert stats["source_breakdown"] == {}
        assert stats["single_use_tags"] == 0


class TestGetStatisticsWithData:
    """Test get_statistics with populated database."""

    @pytest.fixture
    def populated_session(self, session):
        """Create a session with tags and bookmarks."""
        # Create tags
        tag_python = Tag(name="python", count=10, source="diigo")
        tag_web = Tag(name="web", count=5, source="diigo")
        tag_tutorial = Tag(name="tutorial", count=3, source="user")
        tag_orphan = Tag(name="orphaned-tag", count=0, source="user")
        tag_single = Tag(name="single-use", count=1, source="system")

        session.add_all([tag_python, tag_web, tag_tutorial, tag_orphan, tag_single])
        session.flush()

        # Create bookmarks
        bm1 = Bookmark(
            url="https://example.com/1",
            title="Python Tutorial",
            display_id=Bookmark.generate_display_id("https://example.com/1"),
        )
        bm2 = Bookmark(
            url="https://example.com/2",
            title="Web Development",
            display_id=Bookmark.generate_display_id("https://example.com/2"),
        )
        bm3 = Bookmark(
            url="https://example.com/3",
            title="Another Article",
            display_id=Bookmark.generate_display_id("https://example.com/3"),
        )
        session.add_all([bm1, bm2, bm3])
        session.flush()

        # Associate tags with bookmarks via the association table
        # python -> bm1, bm2, bm3 (3 bookmarks)
        # web -> bm1, bm2 (2 bookmarks)
        # tutorial -> bm1 (1 bookmark - single use)
        # single-use -> bm3 (1 bookmark - single use)
        # orphan -> no bookmarks
        session.execute(bookmark_tags.insert().values(bookmark_id=bm1.id, tag_id=tag_python.id))
        session.execute(bookmark_tags.insert().values(bookmark_id=bm2.id, tag_id=tag_python.id))
        session.execute(bookmark_tags.insert().values(bookmark_id=bm3.id, tag_id=tag_python.id))
        session.execute(bookmark_tags.insert().values(bookmark_id=bm1.id, tag_id=tag_web.id))
        session.execute(bookmark_tags.insert().values(bookmark_id=bm2.id, tag_id=tag_web.id))
        session.execute(bookmark_tags.insert().values(bookmark_id=bm1.id, tag_id=tag_tutorial.id))
        session.execute(bookmark_tags.insert().values(bookmark_id=bm3.id, tag_id=tag_single.id))
        session.commit()

        return session

    def test_total_counts(self, populated_session):
        """Should return correct total counts."""
        service = TagService(populated_session)
        stats = service.get_statistics()

        assert stats["total_tags"] == 5
        assert stats["total_bookmarks"] == 3

    def test_tags_per_bookmark_avg(self, populated_session):
        """Should calculate average tags per bookmark from association table."""
        service = TagService(populated_session)
        stats = service.get_statistics()

        # 7 associations / 3 bookmarks = 2.33
        assert stats["tags_per_bookmark_avg"] == 2.33

    def test_top_tags_ordering(self, populated_session):
        """Should return top tags ordered by bookmark count descending."""
        service = TagService(populated_session)
        stats = service.get_statistics()

        top_tags = stats["top_tags"]
        assert len(top_tags) >= 2
        # python has 3 bookmarks, web has 2
        assert top_tags[0]["name"] == "python"
        assert top_tags[0]["count"] == 3
        assert top_tags[1]["name"] == "web"
        assert top_tags[1]["count"] == 2

    def test_orphaned_tag_detection(self, populated_session):
        """Should detect tags with no bookmark associations."""
        service = TagService(populated_session)
        stats = service.get_statistics()

        orphaned_names = [t["name"] for t in stats["orphaned_tags"]]
        assert "orphaned-tag" in orphaned_names
        assert stats["orphaned_count"] == 1

    def test_orphaned_excludes_used_tags(self, populated_session):
        """Should not include tags that have bookmark associations."""
        service = TagService(populated_session)
        stats = service.get_statistics()

        orphaned_names = [t["name"] for t in stats["orphaned_tags"]]
        assert "python" not in orphaned_names
        assert "web" not in orphaned_names

    def test_source_breakdown(self, populated_session):
        """Should count tags by source correctly."""
        service = TagService(populated_session)
        stats = service.get_statistics()

        source = stats["source_breakdown"]
        assert source["diigo"] == 2  # python, web
        assert source["user"] == 2  # tutorial, orphaned-tag
        assert source["system"] == 1  # single-use

    def test_single_use_tags(self, populated_session):
        """Should count tags used by exactly one bookmark."""
        service = TagService(populated_session)
        stats = service.get_statistics()

        # tutorial and single-use each have exactly 1 bookmark
        assert stats["single_use_tags"] == 2

    def test_recent_tags_returns_data(self, populated_session):
        """Should return recent tags with counts."""
        service = TagService(populated_session)
        stats = service.get_statistics()

        assert len(stats["recent_tags"]) == 5  # All 5 tags
        # Each entry should have name and count
        for entry in stats["recent_tags"]:
            assert "name" in entry
            assert "count" in entry
