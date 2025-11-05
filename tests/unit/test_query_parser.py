# ABOUTME: Unit tests for Lucene query parser using luqum
# ABOUTME: Tests parsing and conversion to SQLAlchemy filters

import pytest
from sqlalchemy import and_, or_, not_
from luqum.parser import parser as lucene_parser

from diigo_tagger.services.query_parser import LuceneQueryParser
from diigo_tagger.models import Bookmark, Tag


class TestLuceneQueryParser:
    """Test Lucene query parsing and SQLAlchemy conversion."""

    def setup_method(self):
        """Setup test instance."""
        self.parser = LuceneQueryParser()

    def test_simple_title_search(self):
        """Test simple field search: title:python"""
        query = "title:python"
        filter_expr = self.parser.parse(query)

        # Should create a filter for title LIKE '%python%'
        assert filter_expr is not None
        # The expression should involve Bookmark.title
        assert "title" in str(filter_expr).lower()

    def test_simple_tag_search(self):
        """Test tag search: tags:tutorial"""
        query = "tags:tutorial"
        filter_expr = self.parser.parse(query)

        # Should join with Tag table and filter
        assert filter_expr is not None
        assert "tag" in str(filter_expr).lower()

    def test_boolean_and_query(self):
        """Test AND operator: title:python AND tags:tutorial"""
        query = "title:python AND tags:tutorial"
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        # Should have both conditions
        filter_str = str(filter_expr).lower()
        assert "title" in filter_str
        assert "tag" in filter_str

    def test_boolean_or_query(self):
        """Test OR operator: title:python OR title:javascript"""
        query = "title:python OR title:javascript"
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        filter_str = str(filter_expr).lower()
        assert "title" in filter_str

    def test_boolean_not_query(self):
        """Test NOT operator: title:python NOT tags:beginner"""
        query = "title:python NOT tags:beginner"
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        # Should include negation
        filter_str = str(filter_expr).lower()
        assert "not" in filter_str or "not_" in filter_str

    def test_wildcard_search(self):
        """Test wildcard: title:*neural*"""
        query = "title:*neural*"
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        # Should use LIKE or ilike
        filter_str = str(filter_expr).lower()
        assert "like" in filter_str or "ilike" in filter_str

    def test_phrase_search(self):
        """Test phrase search: title:"machine learning" """
        query = 'title:"machine learning"'
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        filter_str = str(filter_expr).lower()
        assert "title" in filter_str

    def test_complex_grouped_query(self):
        """Test complex query with grouping: (title:python OR title:javascript) AND tags:tutorial"""
        query = "(title:python OR title:javascript) AND tags:tutorial"
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        filter_str = str(filter_expr).lower()
        assert "title" in filter_str
        assert "tag" in filter_str

    def test_description_search(self):
        """Test description field: description:api"""
        query = "description:api"
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        filter_str = str(filter_expr).lower()
        assert "description" in filter_str

    def test_url_search(self):
        """Test URL field: url:github.com"""
        query = "url:github.com"
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        filter_str = str(filter_expr).lower()
        assert "url" in filter_str

    def test_multiple_tags_and(self):
        """Test multiple tag search with AND: tags:python AND tags:tutorial"""
        query = "tags:python AND tags:tutorial"
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        # Should require both tags
        filter_str = str(filter_expr).lower()
        assert "tag" in filter_str

    def test_multiple_tags_or(self):
        """Test multiple tag search with OR: tags:python OR tags:javascript"""
        query = "tags:python OR tags:javascript"
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        filter_str = str(filter_expr).lower()
        assert "tag" in filter_str

    def test_invalid_field_raises_error(self):
        """Test that invalid field raises error"""
        query = "invalid_field:value"

        with pytest.raises(ValueError, match="Unsupported field"):
            self.parser.parse(query)

    def test_empty_query_returns_none(self):
        """Test that empty query returns None (no filter)"""
        filter_expr = self.parser.parse("")
        assert filter_expr is None

        filter_expr = self.parser.parse(None)
        assert filter_expr is None

    def test_case_insensitive_search(self):
        """Test that searches are case-insensitive"""
        query = "title:Python"
        filter_expr = self.parser.parse(query)

        assert filter_expr is not None
        # Should use ilike for case-insensitive search
        filter_str = str(filter_expr).lower()
        assert "ilike" in filter_str or "lower" in filter_str
