# ABOUTME: Bookmark service for Diigo bookmark operations
# ABOUTME: Handles sync, add, lookup with LLM-powered defaults and domain matching

from typing import List, Dict, Optional, Tuple, Callable
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import Tag, Bookmark
from ..api.diigo_client import DiigoClient
from ..api.openai_client import OpenAIClient


class BookmarkService:
    """
    Service for bookmark operations.

    Handles syncing from Diigo, adding bookmarks with LLM defaults,
    and looking up bookmarks with smart domain/path matching.
    """

    def __init__(self, session: Session, diigo_client: DiigoClient, openai_client: Optional[OpenAIClient] = None):
        """
        Initialize bookmark service.

        Args:
            session: SQLAlchemy session for database operations
            diigo_client: Diigo API client for bookmark operations
            openai_client: Optional OpenAI client for LLM-powered features
        """
        self.session = session
        self.diigo_client = diigo_client
        self.openai_client = openai_client

    def sync(
        self,
        target_new_tags: int,
        fetch_all: bool = False,
        progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> Tuple[int, int, int]:
        """
        Sync bookmarks from Diigo and update tag database.

        Fetches bookmarks in batches and extracts tags. Stops when target
        number of NEW tags found or all bookmarks fetched.

        Args:
            target_new_tags: Number of new unique tags to find
            fetch_all: If True, fetch all bookmarks regardless of tag count
            progress_callback: Optional callback(bookmarks_processed, tags_added, tags_updated)
                             called after each batch

        Returns:
            Tuple of (bookmarks_processed, tags_added, tags_updated)
        """
        start = 0
        batch_size = 100  # API max per request

        bookmarks_processed = 0
        tags_added = 0
        tags_updated = 0

        while True:
            # Fetch next batch
            batch = self.diigo_client.fetch_bookmarks(count=batch_size, start=start)
            if not batch:
                break

            bookmarks_processed += len(batch)

            # Process tags from this batch
            for bookmark in batch:
                for tag_name in bookmark.tags:
                    # Normalize tag name
                    tag_name = tag_name.strip().lower()
                    if not tag_name:
                        continue

                    # Get or create tag
                    tag = self.session.query(Tag).filter_by(name=tag_name).first()
                    if tag:
                        tag.count += 1
                        tags_updated += 1
                    else:
                        tag = Tag(name=tag_name, count=1, source="user")
                        self.session.add(tag)
                        tags_added += 1

            # Commit this batch
            self.session.commit()

            # Call progress callback if provided
            if progress_callback:
                progress_callback(bookmarks_processed, tags_added, tags_updated)

            # Check stopping conditions
            if not fetch_all and tags_added >= target_new_tags:
                break

            # If we got less than batch_size, we've reached the end
            if len(batch) < batch_size:
                break

            start += batch_size

        return bookmarks_processed, tags_added, tags_updated

    def add_bookmark(
        self,
        url: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        outline: Optional[str] = None,
        groups: Optional[str] = None,
        shared: bool = True
    ) -> Dict:
        """
        Add bookmark to Diigo with LLM-powered defaults.

        If title/description not provided, uses LLM to generate them.
        If user provides title/description, formats as "User Title (LLM Title)".
        Checks tag similarity and confirms with user if very close.

        Args:
            url: Bookmark URL (required)
            title: Optional user-provided title
            description: Optional user-provided description
            tags: Optional list of user-provided tags
            outline: Optional Diigo outliner content
            groups: Optional comma-separated group names
            shared: Whether bookmark is public (default: True)

        Returns:
            Dict with bookmark details and LLM suggestions:
            {
                "url": str,
                "title": str,  # Final title
                "description": str,  # Final description
                "tags": List[str],  # Final tags
                "llm_suggestions": {
                    "title": str,
                    "description": str,
                    "tags": List[str]
                },
                "display_id": str  # CRC32 hash for lookups
            }

        Raises:
            ValueError: If OpenAI client not configured when LLM features needed
        """
        # Generate LLM suggestions if client available
        llm_title = None
        llm_description = None
        llm_tags = []

        if self.openai_client:
            # TODO: Fetch URL content for better LLM suggestions
            llm_tags = self.openai_client.generate_tags(
                title=title or "",
                description=description or "",
                url=url,
                max_tags=8
            )
            # TODO: Generate title/description using LLM
            llm_title = title or "LLM Title Placeholder"
            llm_description = description or "LLM Description Placeholder"

        # Format final title/description
        final_title = title
        final_description = description

        if title and llm_title and title != llm_title:
            # User provided, add LLM in parentheses: "User Title (LLM Title)"
            final_title = f"{title} ({llm_title})"
        elif not title and llm_title:
            # No user title, use LLM
            final_title = llm_title

        if description and llm_description and description != llm_description:
            final_description = f"{description} ({llm_description})"
        elif not description and llm_description:
            final_description = llm_description

        # Combine user tags and LLM tags
        final_tags = list(tags) if tags else []
        if llm_tags:
            # TODO: Check similarity between user tags and LLM tags
            # For now, just combine them
            final_tags.extend(llm_tags)

        # TODO: Call Diigo API to create bookmark
        # bookmark_response = self.diigo_client.create_bookmark(...)

        # Create bookmark in our database
        display_id = Bookmark.generate_display_id(url)
        bookmark = Bookmark(
            display_id=display_id,
            url=url,
            title=final_title,
            description=final_description,
            shared=shared,
            outline=outline,
            groups=groups
        )
        self.session.add(bookmark)

        # Add tags to bookmark
        for tag_name in final_tags:
            tag_name = tag_name.strip().lower()
            if not tag_name:
                continue

            tag = self.session.query(Tag).filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name, count=0, source="user")
                self.session.add(tag)
                self.session.flush()  # Get ID

            bookmark.tags.append(tag)

        self.session.commit()

        return {
            "url": url,
            "title": final_title,
            "description": final_description,
            "tags": final_tags,
            "llm_suggestions": {
                "title": llm_title,
                "description": llm_description,
                "tags": llm_tags
            },
            "display_id": display_id
        }

    def lookup_by_url(self, url: str, include_similar: bool = True) -> Dict:
        """
        Look up bookmark by URL with smart domain/path matching.

        Returns exact match if found, otherwise searches for bookmarks
        on the same top-level domain and sorts by path similarity.

        Args:
            url: URL to look up
            include_similar: If True, include similar domain matches

        Returns:
            Dict with:
            {
                "exact_match": Optional[Bookmark],  # Exact URL match
                "similar_matches": List[Bookmark],  # Same domain, sorted by path similarity
                "similar_count": int  # Number of similar matches found
            }
        """
        # Try exact match first
        exact_match = self.session.query(Bookmark).filter_by(url=url).first()

        result = {
            "exact_match": exact_match,
            "similar_matches": [],
            "similar_count": 0
        }

        if exact_match or not include_similar:
            return result

        # No exact match, find similar domain matches
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        if not domain:
            return result

        # Extract top-level domain (e.g., "example.com" from "www.example.com")
        domain_parts = domain.split('.')
        if len(domain_parts) >= 2:
            tld = '.'.join(domain_parts[-2:])
        else:
            tld = domain

        # Find all bookmarks with matching top-level domain
        similar_bookmarks = (
            self.session.query(Bookmark)
            .filter(Bookmark.url.like(f'%{tld}%'))
            .all()
        )

        # Sort by path similarity (simple approach: count matching path segments)
        def path_similarity(bookmark_url: str) -> int:
            """Count matching path segments between URLs."""
            parsed_bookmark = urlparse(bookmark_url)

            # Split paths into segments
            query_segments = parsed_url.path.strip('/').split('/')
            bookmark_segments = parsed_bookmark.path.strip('/').split('/')

            # Count matching segments from start
            matches = 0
            for q, b in zip(query_segments, bookmark_segments):
                if q == b:
                    matches += 1
                else:
                    break

            return matches

        # Sort by path similarity (highest first)
        similar_bookmarks_sorted = sorted(
            similar_bookmarks,
            key=lambda b: path_similarity(b.url),
            reverse=True
        )

        result["similar_matches"] = similar_bookmarks_sorted
        result["similar_count"] = len(similar_bookmarks_sorted)

        return result

    def lookup_by_display_id(self, display_id: str) -> Optional[Bookmark]:
        """
        Look up bookmark by display ID.

        Args:
            display_id: 8-character hex display ID (e.g., "a3f2b8c1")

        Returns:
            Bookmark if found, None otherwise
        """
        return self.session.query(Bookmark).filter_by(display_id=display_id).first()

    def lookup_by_display_ids(self, display_ids: List[str]) -> List[Bookmark]:
        """
        Look up multiple bookmarks by display IDs.

        Args:
            display_ids: List of display IDs

        Returns:
            List of found bookmarks (may be fewer than requested if some not found)
        """
        return (
            self.session.query(Bookmark)
            .filter(Bookmark.display_id.in_(display_ids))
            .all()
        )

    def lookup_by_identifiers(self, identifiers: List[str]) -> List[Dict]:
        """
        Look up bookmarks by mixed identifiers (URLs or display IDs).

        Automatically detects whether each identifier is a URL or display ID
        and performs appropriate lookup.

        Args:
            identifiers: List of URLs or display IDs

        Returns:
            List of dicts with lookup results:
            {
                "identifier": str,  # Original identifier
                "type": str,  # "url" or "display_id"
                "exact_match": Optional[Bookmark],
                "similar_matches": List[Bookmark],  # Only for URLs
                "similar_count": int  # Only for URLs
            }
        """
        results = []

        for identifier in identifiers:
            if identifier.startswith('http://') or identifier.startswith('https://'):
                # It's a URL
                lookup_result = self.lookup_by_url(identifier, include_similar=True)
                results.append({
                    "identifier": identifier,
                    "type": "url",
                    "exact_match": lookup_result["exact_match"],
                    "similar_matches": lookup_result["similar_matches"],
                    "similar_count": lookup_result["similar_count"]
                })
            else:
                # It's a display ID
                bookmark = self.lookup_by_display_id(identifier)
                results.append({
                    "identifier": identifier,
                    "type": "display_id",
                    "exact_match": bookmark,
                    "similar_matches": [],
                    "similar_count": 0
                })

        return results
