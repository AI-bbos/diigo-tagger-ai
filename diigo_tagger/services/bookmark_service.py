# ABOUTME: Bookmark service for Diigo bookmark operations
# ABOUTME: Handles sync, add, lookup, search with LLM-powered defaults and domain matching

from typing import List, Dict, Optional, Tuple, Callable
from urllib.parse import urlparse
import math
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import Tag, Bookmark
from ..clients.diigo_client import DiigoClient
from ..clients.openai_client import OpenAIClient
from ..clients.metadata_fetcher import MetadataFetcher
from .query_parser import LuceneQueryParser


class BookmarkService:
    """
    Service for bookmark operations.

    Handles syncing from Diigo, adding bookmarks with LLM defaults,
    and looking up bookmarks with smart domain/path matching.
    """

    def __init__(
        self,
        session: Session,
        diigo_client: Optional[DiigoClient] = None,
        openai_client: Optional[OpenAIClient] = None
    ):
        """
        Initialize bookmark service.

        Args:
            session: SQLAlchemy session for database operations
            diigo_client: Optional Diigo API client (required for sync/add operations)
            openai_client: Optional OpenAI client for LLM-powered features
        """
        self.session = session
        self.diigo_client = diigo_client
        self.openai_client = openai_client
        self.metadata_fetcher = MetadataFetcher()
        self.query_parser = LuceneQueryParser()

    def sync(
        self,
        target_new_tags: int,
        fetch_all: bool = False,
        progress_callback: Optional[Callable[[int, int, int, int, int], None]] = None
    ) -> Tuple[int, int, int, int, int]:
        """
        Sync bookmarks from Diigo and save to database.

        Fetches bookmarks in batches and saves them along with their tags.
        Stops when target number of NEW tags found or all bookmarks fetched.

        Args:
            target_new_tags: Number of new unique tags to find
            fetch_all: If True, fetch all bookmarks regardless of tag count
            progress_callback: Optional callback(downloaded, new_bookmarks, updated_bookmarks, new_tags, updated_tags)
                             called after each batch

        Returns:
            Tuple of (downloaded, new_bookmarks, updated_bookmarks, new_tags, updated_tags)
        """
        import logging
        logger = logging.getLogger(__name__)

        start = 0
        batch_size = 100  # API max per request

        downloaded = 0
        new_bookmarks = 0
        updated_bookmarks = 0
        new_tags = 0
        updated_tags = 0

        logger.info(f"Starting sync: target_new_tags={target_new_tags}, fetch_all={fetch_all}")

        # Track tags created in this sync to prevent duplicates across batches
        batch_tag_cache = {}  # tag_name -> Tag object

        while True:
            # Fetch next batch
            logger.info(f"Fetching batch: start={start}, count={batch_size}")
            batch = self.diigo_client.fetch_bookmarks(count=batch_size, start=start)

            if not batch:
                logger.info(f"No more bookmarks to fetch (batch empty at start={start})")
                break

            logger.info(f"Fetched {len(batch)} bookmarks from Diigo")
            downloaded += len(batch)

            # Process each bookmark
            for bookmark_data in batch:
                # Check if bookmark exists by URL (disable autoflush to prevent premature flushes)
                with self.session.no_autoflush:
                    existing = self.session.query(Bookmark).filter_by(url=bookmark_data.url).first()

                # Parse created_at string to datetime if needed
                from datetime import datetime, timezone
                diigo_created_at = None
                if bookmark_data.created_at:
                    try:
                        # Parse Diigo format: "2015/05/04 05:40:36 +0000"
                        diigo_created_at = datetime.strptime(bookmark_data.created_at, "%Y/%m/%d %H:%M:%S %z")
                    except Exception as e:
                        logger.warning(f"Failed to parse created_at '{bookmark_data.created_at}': {e}")

                if existing:
                    # Update existing bookmark
                    existing.title = bookmark_data.title
                    existing.description = bookmark_data.description
                    # Manually set updated_at to track when our tool modified this bookmark
                    existing.updated_at = datetime.now(timezone.utc)
                    # Note: Don't change created_at - it should remain fixed from initial creation
                    # Don't update tags for existing bookmarks to preserve user modifications
                    updated_bookmarks += 1
                    bookmark_obj = existing
                    logger.debug(f"Updated bookmark: {bookmark_data.url}")
                else:
                    # Create new bookmark
                    # Set created_at from Diigo's timestamp (not auto-generated)
                    bookmark_obj = Bookmark(
                        display_id=Bookmark.generate_display_id(bookmark_data.url),
                        url=bookmark_data.url,
                        title=bookmark_data.title,
                        description=bookmark_data.description,
                        created_at=diigo_created_at or datetime.now(timezone.utc),  # Use Diigo date, fallback to now
                        diigo_created_at=diigo_created_at  # Keep copy for reference
                    )
                    self.session.add(bookmark_obj)
                    new_bookmarks += 1
                    logger.debug(f"Created new bookmark: {bookmark_data.url}")

                    # Process tags for NEW bookmarks only
                    bookmark_tags = []
                    seen_tag_names = set()

                    for tag_name in bookmark_data.tags:
                        # Normalize tag name
                        tag_name = tag_name.strip().lower()
                        if not tag_name:
                            continue

                        # Skip duplicate tags in the same bookmark
                        if tag_name in seen_tag_names:
                            logger.debug(f"Skipping duplicate tag '{tag_name}' for bookmark")
                            continue
                        seen_tag_names.add(tag_name)

                        # Check cache first (tags created in this sync)
                        if tag_name in batch_tag_cache:
                            tag = batch_tag_cache[tag_name]
                            updated_tags += 1
                        else:
                            # Get or create tag
                            with self.session.no_autoflush:
                                tag = self.session.query(Tag).filter_by(name=tag_name).first()

                            if tag:
                                updated_tags += 1
                            else:
                                tag = Tag(name=tag_name, count=0, source="diigo")
                                self.session.add(tag)
                                new_tags += 1

                            # Add to cache for subsequent bookmarks
                            batch_tag_cache[tag_name] = tag

                        bookmark_tags.append(tag)

                    # Associate tags with bookmark
                    bookmark_obj.tags = bookmark_tags

            # Commit this batch
            self.session.commit()
            logger.info(f"Committed batch: downloaded={downloaded}, new={new_bookmarks}, updated={updated_bookmarks}, new_tags={new_tags}, updated_tags={updated_tags}")

            # Call progress callback if provided
            if progress_callback:
                progress_callback(downloaded, new_bookmarks, updated_bookmarks, new_tags, updated_tags)

            # Check stopping conditions
            if not fetch_all and new_tags >= target_new_tags:
                logger.info(f"Reached target of {target_new_tags} new tags, stopping")
                break

            # If we got less than batch_size, we've reached the end
            if len(batch) < batch_size:
                logger.info(f"Reached end of bookmarks (batch size {len(batch)} < {batch_size})")
                break

            start += batch_size

        logger.info(f"Sync complete: downloaded={downloaded}, new={new_bookmarks}, updated={updated_bookmarks}, new_tags={new_tags}, updated_tags={updated_tags}")
        return downloaded, new_bookmarks, updated_bookmarks, new_tags, updated_tags

    def add_bookmark(
        self,
        url: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        outline: Optional[str] = None,
        groups: Optional[str] = None,
        shared: bool = True,
        conflict_resolution: Optional[str] = None  # 3-char code: 'nnn', 'ooo', 'nns', etc.
    ) -> Dict:
        """
        Add bookmark to Diigo with LLM-powered defaults and conflict resolution.

        If title/description not provided, uses LLM to generate them.
        If bookmark already exists and no conflict_resolution provided, returns
        conflict info for user to decide.

        Args:
            url: Bookmark URL (required)
            title: Optional user-provided title
            description: Optional user-provided description
            tags: Optional list of user-provided tags
            outline: Optional Diigo outliner content
            groups: Optional comma-separated group names
            shared: Whether bookmark is public (default: True)
            conflict_resolution: Optional 3-character resolution code when conflict exists
                Position 0 (title):       n=new, o=original, s=smart
                Position 1 (description): n=new, o=original, s=smart
                Position 2 (tags):        n=new, o=original, s=smart
                Examples: 'nns' = new title, new description, smart merge tags
                          'ooo' = keep all original
                          'nnn' = replace all with new

        Returns:
            Dict with bookmark details or conflict information:

            If no conflict or conflict resolved:
            {
                "url": str,
                "title": str,
                "description": str,
                "tags": List[str],
                "display_id": str,
                "llm_suggestions": {...}  # Optional
            }

            If conflict detected (no resolution provided):
            {
                "conflict": True,
                "url": str,
                "existing": {"title": str, "description": str, "tags": List[str], "display_id": str},
                "new": {"title": str, "description": str, "tags": List[str]},
                "llm_suggestions": {...}
            }

        Raises:
            ValueError: If Diigo API fails to create/update bookmark
        """
        # Check if bookmark already exists FIRST (before expensive LLM calls)
        display_id = Bookmark.generate_display_id(url)
        existing_bookmark = self.session.query(Bookmark).filter_by(url=url).first()

        # If bookmark exists and user didn't provide any overrides, no changes needed
        if existing_bookmark and not (title or description or tags) and not conflict_resolution:
            existing_tags = [tag.name for tag in existing_bookmark.tags]
            return {
                "no_changes": True,
                "url": url,
                "title": existing_bookmark.title,
                "description": existing_bookmark.description,
                "tags": existing_tags,
                "display_id": existing_bookmark.display_id
            }

        # Fetch webpage/video metadata (only if needed)
        metadata = self.metadata_fetcher.fetch_metadata(url)
        fetched_title = metadata.get('title', '')
        fetched_description = metadata.get('description', '')
        fetched_keywords = metadata.get('keywords', [])

        # Generate LLM suggestions if client available
        llm_title = None
        llm_description = None
        llm_tags = []

        if self.openai_client:
            # Use fetched metadata if user didn't provide title/description
            llm_input_title = title or fetched_title or ""
            llm_input_description = description or fetched_description or ""

            # Generate tags from LLM with full context
            llm_tags = self.openai_client.generate_tags(
                title=llm_input_title,
                description=llm_input_description,
                url=url,
                max_tags=8
            )

            # Use fetched title as fallback if no user title
            llm_title = title or fetched_title or urlparse(url).netloc
            llm_description = description or fetched_description

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

        # If bookmark exists and no conflict resolution specified, return conflict info
        if existing_bookmark and not conflict_resolution:
            existing_tags = [tag.name for tag in existing_bookmark.tags]

            # Return conflict information for CLI to handle
            return {
                "conflict": True,
                "url": url,
                "existing": {
                    "title": existing_bookmark.title,
                    "description": existing_bookmark.description,
                    "tags": existing_tags,
                    "display_id": existing_bookmark.display_id
                },
                "new": {
                    "title": final_title,
                    "description": final_description,
                    "tags": final_tags
                },
                "llm_suggestions": {
                    "title": llm_title,
                    "description": llm_description,
                    "tags": llm_tags
                }
            }

        # Determine final values based on conflict resolution strategy
        if existing_bookmark and conflict_resolution:
            # Parse 3-character resolution code: position 0=title, 1=description, 2=tags
            # Each char can be: n=new, o=original, s=smart
            if len(conflict_resolution) == 3:
                title_res, desc_res, tags_res = conflict_resolution[0], conflict_resolution[1], conflict_resolution[2]
            else:
                # Backward compatibility with old single-word codes
                if conflict_resolution == 'keep':
                    title_res, desc_res, tags_res = 'o', 'o', 'o'
                elif conflict_resolution == 'replace':
                    title_res, desc_res, tags_res = 'n', 'n', 'n'
                elif conflict_resolution == 'merge':
                    title_res, desc_res, tags_res = 's', 's', 's'
                else:
                    title_res, desc_res, tags_res = 'o', 'o', 'o'

            existing_tags = [tag.name for tag in existing_bookmark.tags]

            # Resolve title
            if title_res == 'o':
                final_title = existing_bookmark.title
            elif title_res == 'n':
                final_title = final_title  # Already set
            elif title_res == 's':
                # Smart: prefer user-provided, else keep existing
                final_title = title or existing_bookmark.title

            # Resolve description
            if desc_res == 'o':
                final_description = existing_bookmark.description
            elif desc_res == 'n':
                final_description = final_description  # Already set
            elif desc_res == 's':
                # Smart: prefer user-provided, else keep existing
                final_description = description or existing_bookmark.description

            # Resolve tags
            if tags_res == 'o':
                final_tags = existing_tags
            elif tags_res == 'n':
                final_tags = final_tags  # Already set
            elif tags_res == 's':
                # Smart: combine tags (unique union)
                final_tags = list(set(existing_tags + final_tags))

            # Check if keeping everything original
            if conflict_resolution == 'ooo':
                return {
                    "url": url,
                    "title": existing_bookmark.title,
                    "description": existing_bookmark.description,
                    "tags": existing_tags,
                    "display_id": existing_bookmark.display_id,
                    "action": "kept_original"
                }

        # Call Diigo API to create/update bookmark
        # Use merge=False to replace existing bookmark data (not merge with it)
        try:
            diigo_response = self.diigo_client.create_bookmark(
                url=url,
                title=final_title or "Untitled",
                description=final_description or "",
                tags=final_tags,
                shared=shared,
                merge=False  # Replace existing bookmark, don't merge
            )
        except Exception as e:
            raise ValueError(f"Failed to create bookmark in Diigo: {e}")

        # Create or update bookmark in our database
        if existing_bookmark:
            # Update existing bookmark
            from datetime import datetime, timezone
            bookmark = existing_bookmark
            bookmark.title = final_title
            bookmark.description = final_description
            bookmark.shared = shared
            bookmark.outline = outline
            bookmark.groups = groups
            # Manually set updated_at to track when our tool modified this bookmark
            bookmark.updated_at = datetime.now(timezone.utc)
            # Note: Don't change created_at - it should remain fixed from initial creation
            # Clear existing tags and re-add
            bookmark.tags.clear()
        else:
            # Create new bookmark
            # created_at will use model default (func.now()) since we're adding "now"
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

    def search_bookmarks(
        self,
        query: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        sort: str = "created_desc"
    ) -> Dict:
        """
        Search bookmarks with optional Lucene query syntax.

        Args:
            query: Optional Lucene query string (e.g., "title:python AND tags:tutorial")
            page: Page number (1-indexed)
            limit: Items per page (max 100)
            sort: Sort order - "created_desc", "created_asc", or "title_asc"

        Returns:
            Dictionary with:
            {
                "bookmarks": [
                    {
                        "id": int,
                        "display_id": str,
                        "url": str,
                        "title": str,
                        "description": str,
                        "tags": [str],
                        "created_at": datetime,
                        "updated_at": datetime
                    },
                    ...
                ],
                "pagination": {
                    "page": int,
                    "limit": int,
                    "total_items": int,
                    "total_pages": int,
                    "has_next": bool,
                    "has_prev": bool
                },
                "query": str (the query that was executed)
            }

        Raises:
            ValueError: If query has invalid syntax or unsupported fields
        """
        # Start with base query
        db_query = self.session.query(Bookmark)

        # Apply Lucene query filter if provided
        if query:
            filter_expr = self.query_parser.parse(query)
            if filter_expr is not None:
                db_query = db_query.filter(filter_expr)

        # Apply sorting
        if sort == "created_asc":
            db_query = db_query.order_by(Bookmark.created_at.asc())
        elif sort == "title_asc":
            db_query = db_query.order_by(Bookmark.title.asc())
        else:  # default: created_desc
            db_query = db_query.order_by(Bookmark.created_at.desc())

        # Count total for pagination
        total_items = db_query.count()
        total_pages = math.ceil(total_items / limit) if total_items > 0 else 0

        # Apply pagination
        offset = (page - 1) * limit
        bookmarks = db_query.offset(offset).limit(limit).all()

        # Convert to dictionaries
        bookmark_dicts = []
        for bm in bookmarks:
            tags = [tag.name for tag in bm.tags]
            bookmark_dicts.append({
                "id": bm.id,
                "display_id": bm.display_id,
                "url": bm.url,
                "title": bm.title,
                "description": bm.description,
                "tags": tags,
                "created_at": bm.created_at,
                "updated_at": bm.updated_at
            })

        return {
            "bookmarks": bookmark_dicts,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "query": query
        }
