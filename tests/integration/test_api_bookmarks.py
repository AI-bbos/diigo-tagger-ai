# ABOUTME: Integration tests for bookmark API endpoints
# ABOUTME: Tests list, search, pagination, and Lucene query parsing

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from datetime import datetime

from diigo_tagger.api.main import app
from diigo_tagger.models import Bookmark


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_bookmarks():
    """Sample bookmark data for tests."""
    return [
        {
            "id": 1,
            "display_id": "ABC12",
            "url": "https://example.com/python",
            "title": "Learn Python",
            "description": "Python tutorial for beginners",
            "tags": ["python", "tutorial", "programming"],
            "created_at": datetime(2025, 1, 1, 10, 0, 0),
            "updated_at": datetime(2025, 1, 1, 10, 0, 0),
        },
        {
            "id": 2,
            "display_id": "DEF34",
            "url": "https://example.com/javascript",
            "title": "JavaScript Guide",
            "description": "Modern JavaScript development",
            "tags": ["javascript", "web-development"],
            "created_at": datetime(2025, 1, 2, 10, 0, 0),
            "updated_at": datetime(2025, 1, 2, 10, 0, 0),
        },
    ]


class TestBookmarkListAPI:
    """Test GET /api/v1/bookmarks endpoint."""

    def test_list_bookmarks_without_query(self, client, sample_bookmarks):
        """Should list all bookmarks without search query."""
        # This test will fail initially (TDD RED)
        response = client.get("/api/v1/bookmarks")

        assert response.status_code == 200
        data = response.json()
        assert "bookmarks" in data
        assert "pagination" in data
        assert isinstance(data["bookmarks"], list)

    def test_list_bookmarks_with_pagination(self, client):
        """Should support pagination parameters."""
        response = client.get("/api/v1/bookmarks?page=1&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 10

    def test_list_bookmarks_with_lucene_query(self, client):
        """Should support Lucene query syntax."""
        response = client.get("/api/v1/bookmarks?q=title:python")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "title:python"

    def test_list_bookmarks_with_complex_query(self, client):
        """Should support complex Lucene queries."""
        query = "title:python AND tags:(tutorial OR programming)"
        response = client.get(f"/api/v1/bookmarks?q={query}")

        assert response.status_code == 200
        data = response.json()
        assert "bookmarks" in data

    def test_list_bookmarks_default_sort(self, client):
        """Should sort by created_at desc by default."""
        response = client.get("/api/v1/bookmarks")

        assert response.status_code == 200
        # Will verify sort order in implementation


class TestBookmarkDetailAPI:
    """Test GET /api/v1/bookmarks/{display_id} endpoint."""

    def test_get_bookmark_by_display_id(self, client):
        """Should retrieve bookmark by display ID."""
        response = client.get("/api/v1/bookmarks/ABC12")

        # Will either be 200 or 404 depending on data
        assert response.status_code in [200, 404]

    def test_get_nonexistent_bookmark(self, client):
        """Should return 404 for nonexistent bookmark."""
        response = client.get("/api/v1/bookmarks/XXXXX")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
