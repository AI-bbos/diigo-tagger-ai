# ABOUTME: Tag hierarchy service for LLM-based parent category inference (LCA approach)
# ABOUTME: Clusters content tags and finds broader parent categories, checking against existing tags

import logging
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from ..clients.openai_client import OpenAIClient
from .tag_reconciliation import TagReconciliationService

logger = logging.getLogger(__name__)


class TagHierarchyService:
    """Infer parent category tags using LLM-based LCA and existing tag matching.

    Uses LLM's ontological knowledge to group content tags into clusters
    and identify their most specific shared parent categories. Checks
    suggestions against existing tags via similarity matching.
    """

    def __init__(self, session: Session, openai_client: Optional[OpenAIClient] = None):
        """Initialize tag hierarchy service.

        Args:
            session: SQLAlchemy session for database operations.
            openai_client: Optional OpenAI client for LLM category inference.
        """
        self.session = session
        self.openai_client = openai_client

    def infer_parent_categories(
        self, tags: List[str], title: str = "", description: str = ""
    ) -> List[Dict]:
        """Infer parent categories and check against existing tags.

        Args:
            tags: Content tags to find parent categories for.
            title: Bookmark title for context.
            description: Bookmark description for context.

        Returns:
            List of dicts with keys:
                - tag: Final tag name to use (matched existing or suggested).
                - original_suggestion: What the LLM suggested.
                - cluster: Tags this category covers.
                - matched_existing: Existing tag name if found, None otherwise.
                - similarity: Similarity score (0.0-1.0).
                - is_new: True if no existing match found.
        """
        if not self.openai_client or len(tags) < 2:
            return []

        try:
            categories = self.openai_client.generate_categories(
                tags=tags, title=title, description=description
            )
        except Exception as e:
            logger.warning(f"Failed to generate categories: {e}")
            return []

        if not categories or not isinstance(categories, list):
            return []

        # Check each suggested parent against existing tags
        results = []
        try:
            reconciler = TagReconciliationService(self.session)
            parent_names = [cat["parent"] for cat in categories]
            matches = reconciler.match_existing_tags(parent_names, threshold=0.5)
        except (TypeError, AttributeError) as e:
            logger.debug(f"Tag reconciliation unavailable: {e}")
            matches = [None] * len(categories)

        for i, cat in enumerate(categories):
            parent = cat.get("parent", "")
            cluster = cat.get("cluster", [])

            match = matches[i] if i < len(matches) else None
            matched_existing = None
            similarity = 0.0

            if match and match.get("action") in ("auto_accept", "confirm"):
                matched_existing = match["matched"]
                similarity = match["similarity"]

            results.append({
                "tag": matched_existing or parent,
                "original_suggestion": parent,
                "cluster": cluster,
                "matched_existing": matched_existing,
                "similarity": similarity,
                "is_new": matched_existing is None,
            })

        return results
