# ABOUTME: Lucene query parser service for bookmark search
# ABOUTME: Converts Lucene syntax to SQLAlchemy filters, used by API and CLI

import logging
from typing import Optional, Any
from sqlalchemy import and_, or_, not_, func
from sqlalchemy.orm import Query
from luqum.parser import parser as lucene_parser
from luqum.tree import (
    SearchField, Word, Phrase, Group, Term,
    AndOperation, OrOperation, Not, Prohibit,
    UnknownOperation
)

from ..models import Bookmark, Tag

logger = logging.getLogger(__name__)


class LuceneQueryParser:
    """
    Parse Lucene query syntax and convert to SQLAlchemy filters.

    Supported fields:
    - title: Bookmark title
    - description: Bookmark description
    - url: Bookmark URL
    - tags: Bookmark tags (joins with Tag table)

    Supported operators:
    - AND: Boolean AND
    - OR: Boolean OR
    - NOT: Boolean negation
    - *: Wildcard (converted to SQL LIKE)
    - "...": Phrase search (exact match)
    - (...): Grouping

    Example queries:
    - title:python
    - tags:tutorial AND tags:python
    - title:*neural* OR title:*network*
    - (title:python OR title:javascript) AND tags:tutorial
    """

    SUPPORTED_FIELDS = {"title", "description", "url", "tags"}

    def parse(self, query: Optional[str]) -> Optional[Any]:
        """
        Parse Lucene query and return SQLAlchemy filter expression.

        Args:
            query: Lucene query string (e.g., "title:python AND tags:tutorial")

        Returns:
            SQLAlchemy filter expression or None if empty query

        Raises:
            ValueError: If query contains unsupported fields or syntax errors
        """
        if not query or not query.strip():
            return None

        try:
            # Parse Lucene syntax using luqum
            tree = lucene_parser.parse(query)
            logger.debug(f"Parsed query tree: {tree}")

            # Convert to SQLAlchemy filter
            return self._convert_tree(tree)

        except Exception as e:
            logger.error(f"Failed to parse query '{query}': {e}")
            raise ValueError(f"Invalid query syntax: {e}")

    def _convert_tree(self, node: Any) -> Any:
        """
        Recursively convert luqum parse tree to SQLAlchemy filter.

        Args:
            node: luqum tree node

        Returns:
            SQLAlchemy filter expression
        """
        # SearchField: field:value
        if isinstance(node, SearchField):
            return self._convert_search_field(node)

        # Boolean AND
        elif isinstance(node, (AndOperation, UnknownOperation)):
            # UnknownOperation defaults to AND in Lucene
            left = self._convert_tree(node.children[0])
            right = self._convert_tree(node.children[1])
            return and_(left, right)

        # Boolean OR
        elif isinstance(node, OrOperation):
            left = self._convert_tree(node.children[0])
            right = self._convert_tree(node.children[1])
            return or_(left, right)

        # Boolean NOT (NOT keyword or - prefix)
        elif isinstance(node, (Not, Prohibit)):
            child = self._convert_tree(node.children[0])
            return not_(child)

        # Group: (...)
        elif isinstance(node, Group):
            return self._convert_tree(node.children[0])

        # Word, Term or Phrase without field (default field search)
        elif isinstance(node, (Word, Phrase, Term)):
            # Default to searching in title
            return self._create_filter("title", self._get_value(node))

        else:
            raise ValueError(f"Unsupported query node type: {type(node).__name__}")

    def _convert_search_field(self, node: SearchField) -> Any:
        """
        Convert SearchField node to SQLAlchemy filter.

        Args:
            node: SearchField node with field name and value

        Returns:
            SQLAlchemy filter expression
        """
        field_name = node.name.lower()
        value = self._get_value(node.children[0])

        # Validate field
        if field_name not in self.SUPPORTED_FIELDS:
            raise ValueError(
                f"Unsupported field: {field_name}. "
                f"Supported fields: {', '.join(sorted(self.SUPPORTED_FIELDS))}"
            )

        return self._create_filter(field_name, value)

    def _get_value(self, node: Any) -> str:
        """
        Extract value from Word, Term, or Phrase node.

        Args:
            node: Word, Term, or Phrase node

        Returns:
            String value
        """
        if isinstance(node, (Word, Term)):
            return node.value
        elif isinstance(node, Phrase):
            # Remove quotes from phrase
            return node.value.strip('"')
        elif isinstance(node, Group):
            return self._get_value(node.children[0])
        else:
            return str(node)

    def _create_filter(self, field: str, value: str) -> Any:
        """
        Create SQLAlchemy filter for field and value.

        Args:
            field: Field name (title, description, url, tags)
            value: Search value (may contain wildcards)

        Returns:
            SQLAlchemy filter expression
        """
        # Convert wildcards to SQL LIKE
        if "*" in value:
            pattern = value.replace("*", "%")
            use_like = True
        else:
            # Default: substring search
            pattern = f"%{value}%"
            use_like = True

        # Special handling for tags (requires join)
        if field == "tags":
            # Tag search: bookmark must have a tag matching the pattern
            return Bookmark.tags.any(
                func.lower(Tag.name).like(func.lower(pattern))
            )

        # Standard fields: title, description, url
        column = getattr(Bookmark, field)
        return func.lower(column).like(func.lower(pattern))
