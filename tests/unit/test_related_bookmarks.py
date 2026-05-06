# ABOUTME: Unit tests for _find_related_bookmarks method on BookmarkService
# ABOUTME: Tests domain+path matching, sorting, filtering, and limit behavior

import pytest
from unittest.mock import Mock, patch
from diigo_tagger.services.bookmark_service import BookmarkService
from diigo_tagger.models import Bookmark, Tag


def _make_bookmark(url, title="Test", tags=None):
    """Create a mock Bookmark with the given URL and tags."""
    bm = Mock(spec=Bookmark)
    bm.url = url
    bm.title = title
    bm.display_id = "abc12345"
    tag_objs = []
    for t in (tags or []):
        tag_obj = Mock(spec=Tag)
        tag_obj.name = t
        tag_objs.append(tag_obj)
    bm.tags = tag_objs
    return bm


class TestFindRelatedBookmarks:
    """Tests for BookmarkService._find_related_bookmarks."""

    def test_matching_domain_and_path_segments(self):
        """Should return bookmarks sharing domain and path prefix."""
        session = Mock()
        # Existing bookmark shares domain and first path segment
        existing = _make_bookmark(
            "https://docs.example.com/python/basics",
            title="Python Basics",
            tags=["python", "tutorial"]
        )
        session.query.return_value.filter.return_value.filter.return_value.all.return_value = [existing]

        service = BookmarkService(session=session)
        results = service._find_related_bookmarks("https://docs.example.com/python/advanced")

        assert len(results) == 1
        assert results[0]["url"] == "https://docs.example.com/python/basics"
        assert results[0]["tags"] == ["python", "tutorial"]
        assert results[0]["path_match_segments"] == 1

    def test_matching_domain_no_path_overlap(self):
        """Should exclude bookmarks with same domain but different path."""
        session = Mock()
        existing = _make_bookmark(
            "https://example.com/javascript/intro",
            title="JS Intro",
            tags=["javascript"]
        )
        session.query.return_value.filter.return_value.filter.return_value.all.return_value = [existing]

        service = BookmarkService(session=session)
        results = service._find_related_bookmarks("https://example.com/python/advanced")

        assert len(results) == 0

    def test_no_matches_different_domain(self):
        """Should return empty list when no bookmarks match domain."""
        session = Mock()
        session.query.return_value.filter.return_value.filter.return_value.all.return_value = []

        service = BookmarkService(session=session)
        results = service._find_related_bookmarks("https://newsite.com/article/123")

        assert results == []

    def test_sorting_most_segments_first(self):
        """Should sort results by path_match_segments descending."""
        session = Mock()
        shallow = _make_bookmark(
            "https://example.com/docs/other",
            title="Shallow",
            tags=["docs"]
        )
        deep = _make_bookmark(
            "https://example.com/docs/api/other-endpoint",
            title="Deep",
            tags=["api"]
        )
        session.query.return_value.filter.return_value.filter.return_value.all.return_value = [shallow, deep]

        service = BookmarkService(session=session)
        results = service._find_related_bookmarks("https://example.com/docs/api/users")

        assert len(results) == 2
        assert results[0]["title"] == "Deep"
        assert results[0]["path_match_segments"] == 2
        assert results[1]["title"] == "Shallow"
        assert results[1]["path_match_segments"] == 1

    def test_limit_parameter(self):
        """Should respect the limit parameter."""
        session = Mock()
        bookmarks = [
            _make_bookmark(f"https://example.com/docs/page{i}", title=f"Page {i}", tags=["docs"])
            for i in range(10)
        ]
        session.query.return_value.filter.return_value.filter.return_value.all.return_value = bookmarks

        service = BookmarkService(session=session)
        results = service._find_related_bookmarks("https://example.com/docs/new-page", limit=3)

        assert len(results) == 3

    def test_empty_path_returns_empty(self):
        """Should return empty list when URL has no path segments."""
        session = Mock()
        service = BookmarkService(session=session)
        results = service._find_related_bookmarks("https://example.com/")

        assert results == []

    def test_invalid_url_returns_empty(self):
        """Should return empty list for URLs without a domain."""
        session = Mock()
        service = BookmarkService(session=session)
        results = service._find_related_bookmarks("not-a-url")

        assert results == []
