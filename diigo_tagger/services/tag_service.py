# ABOUTME: Tag service for tag listing and generation operations
# ABOUTME: Handles querying tags with filters/sorting and AI-powered tag generation

from typing import List, Optional
from sqlalchemy.orm import Session

from ..models import Tag
from ..clients.openai_client import OpenAIClient


class TagService:
    """
    Service for tag operations.

    Handles listing tags with various filters and sorting options,
    and generating tag suggestions using AI.
    """

    def __init__(self, session: Session, openai_client: Optional[OpenAIClient] = None):
        """
        Initialize tag service.

        Args:
            session: SQLAlchemy session for database operations
            openai_client: Optional OpenAI client for tag generation
        """
        self.session = session
        self.openai_client = openai_client

    def list_tags(
        self,
        limit: int = 50,
        source: Optional[str] = None,
        sort_by: str = 'count'
    ) -> List[Tag]:
        """
        List tags from database with filtering and sorting.

        Args:
            limit: Maximum number of tags to return (1-10000)
            source: Optional filter by source ('user', 'master', 'system')
            sort_by: Sort order ('count', 'name', 'created')

        Returns:
            List of Tag objects matching criteria

        Examples:
            >>> list_tags(limit=10, sort_by='count')
            [Tag(name='python', count=50), Tag(name='web', count=30), ...]
        """
        # Build query
        query = self.session.query(Tag)

        # Apply source filter
        if source:
            query = query.filter_by(source=source)

        # Apply sorting
        if sort_by == 'count':
            query = query.order_by(Tag.count.desc())
        elif sort_by == 'name':
            query = query.order_by(Tag.name.asc())
        elif sort_by == 'created':
            query = query.order_by(Tag.created_at.desc())
        else:
            # Default to count if invalid
            query = query.order_by(Tag.count.desc())

        # Apply limit and fetch
        tags = query.limit(limit).all()

        return tags

    def generate_tags(
        self,
        title: str,
        description: str = "",
        url: str = "",
        max_tags: int = 8
    ) -> List[str]:
        """
        Generate tag suggestions using AI (GPT-4o-mini).

        Args:
            title: Bookmark title
            description: Bookmark description (optional)
            url: Bookmark URL (optional)
            max_tags: Maximum number of tags to generate (1-20)

        Returns:
            List of suggested tag strings

        Raises:
            ValueError: If OpenAI client not configured

        Examples:
            >>> generate_tags("Python Tutorial", url="https://python.org")
            ['python', 'programming', 'tutorial', 'beginner']
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not configured. Set OPENAI_API_KEY environment variable.")

        tags = self.openai_client.generate_tags(
            title=title,
            description=description,
            url=url,
            max_tags=max_tags
        )

        return tags

    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """
        Get a single tag by exact name match.

        Args:
            name: Tag name (will be normalized to lowercase)

        Returns:
            Tag if found, None otherwise
        """
        normalized_name = name.strip().lower()
        return self.session.query(Tag).filter_by(name=normalized_name).first()

    def get_tag_stats(self) -> dict:
        """
        Get statistics about tags in the database.

        Returns:
            Dict with tag statistics:
            {
                "total_tags": int,
                "total_usage": int,
                "by_source": {
                    "user": int,
                    "master": int,
                    "system": int
                }
            }
        """
        from sqlalchemy import func

        total_tags = self.session.query(func.count(Tag.id)).scalar()
        total_usage = self.session.query(func.sum(Tag.count)).scalar() or 0

        # Count by source
        by_source = {}
        for source in ['user', 'master', 'system']:
            count = (
                self.session.query(func.count(Tag.id))
                .filter_by(source=source)
                .scalar()
            )
            by_source[source] = count

        return {
            "total_tags": total_tags,
            "total_usage": total_usage,
            "by_source": by_source
        }
