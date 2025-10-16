# ABOUTME: Tag reconciliation service for deduplication and merging
# ABOUTME: Handles wildcard search (FTS5), semantic similarity, and tag normalization

from typing import List
from datetime import datetime
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models import Tag


class TagReconciliationService:
    """
    Service for tag reconciliation operations.

    Handles tag deduplication, merging, wildcard search (FTS5),
    and semantic similarity matching using embeddings.
    """

    def __init__(self, session: Session):
        """
        Initialize tag reconciliation service.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def normalize_tag(self, tag: str) -> str:
        """
        Normalize tag to canonical form.

        Converts to lowercase and strips whitespace for consistent comparison.

        Args:
            tag: Tag string to normalize

        Returns:
            Normalized tag string

        Examples:
            >>> normalize_tag("  Python  ")
            'python'
        """
        return tag.strip().lower()

    def deduplicate_tags(self, tags: List[str]) -> List[str]:
        """
        Deduplicate list of tags (case-insensitive).

        Preserves order of first occurrence.

        Args:
            tags: List of tag strings (possibly duplicates)

        Returns:
            Deduplicated list of normalized tags

        Examples:
            >>> deduplicate_tags(["Python", "python", "Web-Dev"])
            ['python', 'web-dev']
        """
        seen = set()
        result = []

        for tag in tags:
            normalized = self.normalize_tag(tag)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)

        return result

    def wildcard_search(self, query: str, limit: int = 50) -> List[Tag]:
        """
        Search tags using wildcard patterns (FTS5).

        Supports * as wildcard character for prefix/suffix/infix matching.

        Args:
            query: Search query with wildcards (e.g., "python*", "*dev")
            limit: Maximum number of results to return

        Returns:
            List of matching Tag objects, ordered by relevance

        Examples:
            >>> wildcard_search("python*")
            [Tag(name='python'), Tag(name='python-web')]
        """
        if not query or not query.strip():
            return []

        # FTS5 query - escape special chars except *
        # Convert * to FTS5 wildcard syntax
        fts_query = query.strip()

        try:
            # Query FTS5 table and join with tags table
            sql = text("""
                SELECT tags.* FROM tags
                JOIN tags_fts ON tags.id = tags_fts.rowid
                WHERE tags_fts MATCH :query
                ORDER BY tags.count DESC
                LIMIT :limit
            """)

            result = self.session.execute(
                sql, {"query": fts_query, "limit": limit}
            ).fetchall()

            # Convert rows to Tag objects
            tags = []
            for row in result:
                tag = self.session.query(Tag).filter_by(id=row[0]).first()
                if tag:
                    tags.append(tag)

            return tags

        except Exception:
            # If FTS5 query fails (invalid syntax), return empty list
            return []

    def merge_tags(self, source_tags: List[str], target_tag: str) -> None:
        """
        Merge multiple tags into a single target tag.

        Combines usage counts and preserves latest timestamp.
        Deletes source tags after merging.

        Args:
            source_tags: List of tag names to merge (will be deleted)
            target_tag: Target tag name to merge into (created if missing)

        Examples:
            >>> merge_tags(["py", "Python"], "python")
            # Creates/updates "python" with combined count, deletes "py" and "Python"
        """
        # Normalize target tag
        target_tag_normalized = self.normalize_tag(target_tag)

        # Get or create target tag
        target = self.session.query(Tag).filter_by(name=target_tag_normalized).first()
        if not target:
            target = Tag(name=target_tag_normalized, count=0, source="user")
            self.session.add(target)
            self.session.flush()  # Get ID assigned

        # Merge source tags into target
        total_count = target.count
        latest_used = target.last_used

        # Collect all tags to be merged (including any with same normalized name)
        tags_to_merge = []
        all_tags = self.session.query(Tag).all()

        for tag in all_tags:
            # Skip the target tag itself
            if tag.id == target.id:
                continue

            tag_normalized = self.normalize_tag(tag.name)

            # Check if this tag matches any of the source tags OR the target tag
            # (to handle case where DB has "Python" and we want to merge into "python")
            if tag_normalized in [self.normalize_tag(s) for s in source_tags]:
                tags_to_merge.append(tag)
            elif tag_normalized == target_tag_normalized:
                # Also merge any duplicates of target tag (different case)
                tags_to_merge.append(tag)

        # Merge all collected tags
        for tag in tags_to_merge:
            total_count += tag.count

            if tag.last_used:
                if latest_used is None or tag.last_used > latest_used:
                    latest_used = tag.last_used

            self.session.delete(tag)

        # Update target with merged data
        target.count = total_count
        target.last_used = latest_used

        self.session.commit()

    def find_similar_tags(
        self, query_tag: str, threshold: float = 0.8, limit: int = 10
    ) -> List[Tag]:
        """
        Find semantically similar tags using embeddings.

        Uses cosine similarity between tag embeddings.

        Args:
            query_tag: Tag name to find similar tags for
            threshold: Minimum similarity score (0.0-1.0)
            limit: Maximum number of results

        Returns:
            List of similar Tag objects, ordered by similarity (highest first)

        Examples:
            >>> find_similar_tags("python", threshold=0.8)
            [Tag(name='python-programming'), Tag(name='python-dev')]
        """
        # Get query tag
        query = self.session.query(Tag).filter_by(name=query_tag).first()
        if not query or query.embedding is None:
            return []

        # Get query embedding
        query_embedding = query.get_embedding()
        if query_embedding is None:
            return []

        # Get all tags with embeddings
        all_tags = self.session.query(Tag).filter(Tag.embedding.isnot(None)).all()

        # Calculate cosine similarity for each
        similarities = []
        for tag in all_tags:
            if tag.name == query_tag:
                continue  # Skip self

            tag_embedding = tag.get_embedding()
            if tag_embedding is None:
                continue

            # Cosine similarity
            similarity = np.dot(query_embedding, tag_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(tag_embedding)
            )

            if similarity >= threshold:
                similarities.append((tag, similarity))

        # Sort by similarity (highest first) and limit
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in similarities[:limit]]
