# ABOUTME: Integration tests for tag autocomplete API endpoint
# ABOUTME: Tests prefix filtering, empty query, and missing prefix validation

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from diigo_tagger.api.main import app
from diigo_tagger.models import Tag


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


def _make_tag(name: str) -> Tag:
    """Create a Tag ORM object with the given name.

    Args:
        name: The tag name string.

    Returns:
        A Tag instance with only the name attribute set.
    """
    tag = Tag()
    tag.name = name
    return tag


class TestTagAutocomplete:
    """Test GET /api/v1/tags/autocomplete endpoint."""

    def test_autocomplete_returns_matching_tags(self, client):
        """Should return tags matching both prefix and query fragment."""
        mock_tags = [
            _make_tag("reference:peter-zeihan"),
            _make_tag("reference:peter-attia"),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_tags

        with patch("diigo_tagger.api.routes.bookmarks.get_session", return_value=mock_session):
            response = client.get("/api/v1/tags/autocomplete?prefix=reference:&q=peter")

        assert response.status_code == 200
        data = response.json()
        assert data["prefix"] == "reference:"
        assert set(data["tags"]) == {"reference:peter-zeihan", "reference:peter-attia"}

    def test_autocomplete_empty_query(self, client):
        """Should return all tags matching prefix when q is omitted."""
        mock_tags = [
            _make_tag("reference:peter-zeihan"),
            _make_tag("reference:paul-graham"),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_tags

        with patch("diigo_tagger.api.routes.bookmarks.get_session", return_value=mock_session):
            response = client.get("/api/v1/tags/autocomplete?prefix=reference:")

        assert response.status_code == 200
        data = response.json()
        assert data["prefix"] == "reference:"
        assert len(data["tags"]) == 2

    def test_autocomplete_requires_prefix(self, client):
        """Should return 422 when prefix parameter is missing."""
        response = client.get("/api/v1/tags/autocomplete")

        assert response.status_code == 422
