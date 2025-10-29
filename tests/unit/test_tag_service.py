# ABOUTME: Unit tests for tag_service module
# ABOUTME: Tests tag listing, filtering, sorting, AI generation, and statistics

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from diigo_tagger.services.tag_service import TagService
from diigo_tagger.models import Tag


class TestTagServiceList:
    """Test list_tags functionality."""

    def test_list_tags_default_sorting(self):
        """Should return tags sorted by count descending by default."""
        mock_session = Mock()

        # Create mock tags with different counts
        tag1 = Tag(name="python", count=100, source="user")
        tag2 = Tag(name="javascript", count=50, source="user")
        tag3 = Tag(name="ruby", count=75, source="user")

        # Mock query chain
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [tag1, tag3, tag2]
        mock_session.query.return_value = mock_query

        service = TagService(mock_session)
        result = service.list_tags()

        # Verify query chain
        mock_session.query.assert_called_once_with(Tag)
        mock_query.order_by.assert_called_once()
        mock_query.order_by.return_value.limit.assert_called_once_with(50)

        # Should return tags sorted by count
        assert len(result) == 3
        assert result[0].name == "python"
        assert result[1].name == "ruby"
        assert result[2].name == "javascript"

    def test_list_tags_sort_by_name(self):
        """Should sort tags alphabetically when sort_by='name'."""
        mock_session = Mock()

        tag1 = Tag(name="zebra", count=10, source="user")
        tag2 = Tag(name="alpha", count=20, source="user")
        tag3 = Tag(name="beta", count=15, source="user")

        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [tag2, tag3, tag1]
        mock_session.query.return_value = mock_query

        service = TagService(mock_session)
        result = service.list_tags(sort_by='name')

        # Should return tags alphabetically
        assert result[0].name == "alpha"
        assert result[1].name == "beta"
        assert result[2].name == "zebra"

    def test_list_tags_sort_by_created(self):
        """Should sort tags by creation date when sort_by='created'."""
        mock_session = Mock()

        tag1 = Tag(name="old", count=10, source="user", created_at=datetime(2024, 1, 1))
        tag2 = Tag(name="new", count=20, source="user", created_at=datetime(2024, 3, 1))
        tag3 = Tag(name="mid", count=15, source="user", created_at=datetime(2024, 2, 1))

        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [tag2, tag3, tag1]
        mock_session.query.return_value = mock_query

        service = TagService(mock_session)
        result = service.list_tags(sort_by='created')

        # Should return newest first
        assert result[0].name == "new"
        assert result[1].name == "mid"
        assert result[2].name == "old"

    def test_list_tags_with_source_filter(self):
        """Should filter tags by source when provided."""
        mock_session = Mock()

        tag1 = Tag(name="user-tag", count=10, source="user")
        tag2 = Tag(name="system-tag", count=20, source="system")

        mock_query = MagicMock()
        mock_query.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = [tag1]
        mock_session.query.return_value = mock_query

        service = TagService(mock_session)
        result = service.list_tags(source="user")

        # Should filter by source
        mock_query.filter_by.assert_called_once_with(source="user")
        assert len(result) == 1
        assert result[0].source == "user"

    def test_list_tags_with_limit(self):
        """Should respect limit parameter."""
        mock_session = Mock()

        # Create 100 mock tags
        tags = [Tag(name=f"tag{i}", count=i, source="user") for i in range(100)]

        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = tags[:10]
        mock_session.query.return_value = mock_query

        service = TagService(mock_session)
        result = service.list_tags(limit=10)

        # Should only return 10 tags
        mock_query.order_by.return_value.limit.assert_called_once_with(10)
        assert len(result) == 10

    def test_list_tags_invalid_sort_defaults_to_count(self):
        """Should default to count sorting when invalid sort_by provided."""
        mock_session = Mock()

        tag1 = Tag(name="high", count=100, source="user")
        tag2 = Tag(name="low", count=50, source="user")

        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [tag1, tag2]
        mock_session.query.return_value = mock_query

        service = TagService(mock_session)
        result = service.list_tags(sort_by='invalid_option')

        # Should fall back to count sorting
        assert result[0].count > result[1].count


class TestTagServiceGenerate:
    """Test generate_tags functionality."""

    def test_generate_tags_with_client(self):
        """Should call OpenAI client to generate tags."""
        mock_session = Mock()
        mock_openai_client = Mock()
        mock_openai_client.generate_tags.return_value = [
            "python", "programming", "tutorial", "beginner"
        ]

        service = TagService(mock_session, mock_openai_client)
        result = service.generate_tags(
            title="Python Tutorial",
            description="Learn Python basics",
            url="https://python.org",
            max_tags=8
        )

        # Should call OpenAI client with correct parameters
        mock_openai_client.generate_tags.assert_called_once_with(
            title="Python Tutorial",
            description="Learn Python basics",
            url="https://python.org",
            max_tags=8
        )

        assert len(result) == 4
        assert "python" in result
        assert "programming" in result

    def test_generate_tags_without_client_raises_error(self):
        """Should raise ValueError when OpenAI client not configured."""
        mock_session = Mock()

        service = TagService(mock_session, openai_client=None)

        with pytest.raises(ValueError, match="OpenAI client not configured"):
            service.generate_tags(
                title="Some Title",
                description="Some Description"
            )

    def test_generate_tags_minimal_input(self):
        """Should work with only title provided."""
        mock_session = Mock()
        mock_openai_client = Mock()
        mock_openai_client.generate_tags.return_value = ["tag1", "tag2"]

        service = TagService(mock_session, mock_openai_client)
        result = service.generate_tags(title="Just a Title")

        # Should call with empty description and url
        mock_openai_client.generate_tags.assert_called_once_with(
            title="Just a Title",
            description="",
            url="",
            max_tags=8
        )

        assert len(result) == 2


class TestTagServiceGetByName:
    """Test get_tag_by_name functionality."""

    def test_get_tag_by_name_exact_match(self):
        """Should return tag when exact match found."""
        mock_session = Mock()

        expected_tag = Tag(name="python", count=50, source="user")
        mock_session.query.return_value.filter_by.return_value.first.return_value = expected_tag

        service = TagService(mock_session)
        result = service.get_tag_by_name("python")

        # Should query with normalized name
        mock_session.query.return_value.filter_by.assert_called_once_with(name="python")
        assert result == expected_tag
        assert result.name == "python"

    def test_get_tag_by_name_normalizes_case(self):
        """Should normalize tag name to lowercase."""
        mock_session = Mock()

        expected_tag = Tag(name="python", count=50, source="user")
        mock_session.query.return_value.filter_by.return_value.first.return_value = expected_tag

        service = TagService(mock_session)
        result = service.get_tag_by_name("PYTHON")

        # Should normalize to lowercase
        mock_session.query.return_value.filter_by.assert_called_once_with(name="python")
        assert result.name == "python"

    def test_get_tag_by_name_strips_whitespace(self):
        """Should strip whitespace from tag name."""
        mock_session = Mock()

        expected_tag = Tag(name="python", count=50, source="user")
        mock_session.query.return_value.filter_by.return_value.first.return_value = expected_tag

        service = TagService(mock_session)
        result = service.get_tag_by_name("  python  ")

        # Should strip whitespace and normalize
        mock_session.query.return_value.filter_by.assert_called_once_with(name="python")
        assert result.name == "python"

    def test_get_tag_by_name_not_found(self):
        """Should return None when tag not found."""
        mock_session = Mock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        service = TagService(mock_session)
        result = service.get_tag_by_name("nonexistent")

        assert result is None


class TestTagServiceStats:
    """Test get_tag_stats functionality."""

    def test_get_tag_stats_with_data(self):
        """Should return comprehensive statistics."""
        mock_session = Mock()

        # Create separate mocks for different query chains
        total_query = Mock()
        total_query.scalar.return_value = 100

        sum_query = Mock()
        sum_query.scalar.return_value = 500

        # Mock filter_by chain for each source
        user_query = Mock()
        user_query.scalar.return_value = 60

        master_query = Mock()
        master_query.scalar.return_value = 30

        system_query = Mock()
        system_query.scalar.return_value = 10

        # Set up query to return different chains
        mock_session.query.side_effect = [
            total_query,   # First call: total tags count
            sum_query,     # Second call: total usage sum
            user_query,    # Third call: user source count
            master_query,  # Fourth call: master source count
            system_query   # Fifth call: system source count
        ]

        # Mock filter_by to return the appropriate query
        user_query.filter_by.return_value = user_query
        master_query.filter_by.return_value = master_query
        system_query.filter_by.return_value = system_query

        service = TagService(mock_session)
        result = service.get_tag_stats()

        assert result["total_tags"] == 100
        assert result["total_usage"] == 500
        assert result["by_source"]["user"] == 60
        assert result["by_source"]["master"] == 30
        assert result["by_source"]["system"] == 10

    def test_get_tag_stats_empty_database(self):
        """Should handle empty database gracefully."""
        mock_session = Mock()

        # Create separate mocks for different query chains
        total_query = Mock()
        total_query.scalar.return_value = 0

        sum_query = Mock()
        sum_query.scalar.return_value = None  # sum returns None on empty

        # Mock filter_by chain for each source
        user_query = Mock()
        user_query.scalar.return_value = 0

        master_query = Mock()
        master_query.scalar.return_value = 0

        system_query = Mock()
        system_query.scalar.return_value = 0

        # Set up query to return different chains
        mock_session.query.side_effect = [
            total_query,   # First call: total tags count
            sum_query,     # Second call: total usage sum
            user_query,    # Third call: user source count
            master_query,  # Fourth call: master source count
            system_query   # Fifth call: system source count
        ]

        # Mock filter_by to return the appropriate query
        user_query.filter_by.return_value = user_query
        master_query.filter_by.return_value = master_query
        system_query.filter_by.return_value = system_query

        service = TagService(mock_session)
        result = service.get_tag_stats()

        assert result["total_tags"] == 0
        assert result["total_usage"] == 0  # Should convert None to 0
        assert result["by_source"]["user"] == 0
        assert result["by_source"]["master"] == 0
        assert result["by_source"]["system"] == 0

    def test_get_tag_stats_queries_all_sources(self):
        """Should query for all three source types."""
        mock_session = Mock()

        mock_session.query.return_value.scalar.side_effect = [10, 50, 5, 3, 2]

        # Create a mock for filter_by to track calls
        filter_by_mock = Mock()
        filter_by_mock.scalar.side_effect = [5, 3, 2]
        mock_session.query.return_value.filter_by.return_value = filter_by_mock

        service = TagService(mock_session)
        result = service.get_tag_stats()

        # Should have queried for user, master, and system
        assert "user" in result["by_source"]
        assert "master" in result["by_source"]
        assert "system" in result["by_source"]
