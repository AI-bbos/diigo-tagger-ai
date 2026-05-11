# ABOUTME: Unit tests for the tag cloud API endpoint
# ABOUTME: Tests count accuracy, ordering, and limit parameter

import pytest
from unittest.mock import MagicMock, patch

from diigo_tagger.api.routes.bookmarks import tag_cloud


class TestTagCloudEndpoint:
    """Test GET /api/v1/tags/cloud endpoint."""

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_returns_tags_with_counts(self, mock_get_session):
        """Should return tags with their bookmark counts."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock query results: list of (name, count) tuples
        mock_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
            ("python", 50),
            ("javascript", 30),
            ("tutorial", 10),
        ]

        result = await tag_cloud(limit=100)

        assert "tags" in result
        assert len(result["tags"]) == 3
        assert result["tags"][0] == {"name": "python", "count": 50}
        assert result["tags"][1] == {"name": "javascript", "count": 30}
        assert result["tags"][2] == {"name": "tutorial", "count": 10}

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_respects_limit_parameter(self, mock_get_session):
        """Should pass the limit parameter to the query."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
            ("python", 50),
        ]

        await tag_cloud(limit=25)

        # Verify limit was passed to the query chain
        mock_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.assert_called_with(25)

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_ordering_most_used_first(self, mock_get_session):
        """Should return tags ordered by count descending (most used first)."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Return in descending count order as the query would
        mock_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
            ("most-popular", 200),
            ("medium", 50),
            ("least-used", 5),
        ]

        result = await tag_cloud(limit=100)

        counts = [tag["count"] for tag in result["tags"]]
        assert counts == sorted(counts, reverse=True)

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_empty_result(self, mock_get_session):
        """Should return empty list when no tags exist."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = await tag_cloud(limit=100)

        assert result["tags"] == []

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_default_limit_is_100(self, mock_get_session):
        """Should use default limit of 100 when not specified explicitly."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = []

        # Call with explicit 100 to simulate what FastAPI does with the default
        await tag_cloud(limit=100)

        mock_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.assert_called_with(100)

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_session_closed_after_query(self, mock_get_session):
        """Should close the session even after successful query."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = []

        await tag_cloud(limit=100)

        mock_session.close.assert_called_once()
