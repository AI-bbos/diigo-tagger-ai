# ABOUTME: Bookmark API endpoints for listing, searching, and adding bookmarks
# ABOUTME: Thin layer that calls bookmark service for business logic

import difflib
import logging
import os
from typing import Optional, Union

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ...db import get_session
from ...models import Bookmark as BookmarkModel, Tag as TagModel
from ...services.bookmark_service import BookmarkService
from ...clients.diigo_client import DiigoClient
from ...clients.openai_client import OpenAIClient
from ..schemas.bookmark import (
    BookmarkResponse,
    BookmarkListResponse,
    PaginationInfo,
    AddBookmarkRequest,
    AddBookmarkSuccessResponse,
    ConflictResponse,
    ResolveConflictRequest,
    PrepareBookmarkResponse,
    SubmitBookmarkRequest,
    LLMSuggestions,
    ExistingBookmark,
    NewBookmark
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/bookmarks", response_model=BookmarkListResponse)
async def list_bookmarks(
    q: Optional[str] = Query(None, description="Lucene query syntax"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    sort: str = Query("created_desc", description="Sort order: created_desc, created_asc, title_asc")
):
    """
    List bookmarks with optional Lucene query search.

    Supports Lucene query syntax:
    - Field search: title:python, tags:tutorial
    - Boolean: AND, OR, NOT, -
    - Wildcards: title:*python*
    - Phrases: "machine learning"
    - Grouping: (title:python OR title:javascript) AND tags:tutorial

    Example queries:
    - title:python
    - tags:tutorial AND tags:python
    - title:*neural* OR title:*network*
    """
    session = get_session()

    try:
        # Create service (no Diigo client needed for search)
        service = BookmarkService(session=session)

        # Call service layer
        try:
            result = service.search_bookmarks(
                query=q,
                page=page,
                limit=limit,
                sort=sort
            )
        except ValueError as e:
            # Invalid query syntax
            raise HTTPException(
                status_code=400,
                detail={
                    "detail": str(e),
                    "error_code": "INVALID_QUERY_SYNTAX",
                    "query": q
                }
            )

        # Convert service result to API response
        bookmark_responses = [
            BookmarkResponse(**bm) for bm in result["bookmarks"]
        ]

        pagination = PaginationInfo(**result["pagination"])

        return BookmarkListResponse(
            bookmarks=bookmark_responses,
            pagination=pagination,
            query=result["query"]
        )

    finally:
        session.close()


@router.get("/bookmarks/{display_id}", response_model=BookmarkResponse)
async def get_bookmark(display_id: str):
    """
    Get a single bookmark by display ID.
    """
    session = get_session()

    try:
        bookmark = session.query(BookmarkModel).filter_by(display_id=display_id).first()

        if not bookmark:
            raise HTTPException(
                status_code=404,
                detail={
                    "detail": "Bookmark not found",
                    "error_code": "BOOKMARK_NOT_FOUND",
                    "display_id": display_id
                }
            )

        tags = [tag.name for tag in bookmark.tags]

        return BookmarkResponse(
            id=bookmark.id,
            display_id=bookmark.display_id,
            url=bookmark.url,
            title=bookmark.title,
            description=bookmark.description,
            tags=tags,
            created_at=bookmark.created_at,
            updated_at=bookmark.updated_at
        )

    finally:
        session.close()


@router.post("/bookmarks", response_model=Union[AddBookmarkSuccessResponse, ConflictResponse])
async def add_bookmark(request: AddBookmarkRequest):
    """
    Add a new bookmark to Diigo.

    If bookmark already exists, returns conflict information for user to decide.
    Otherwise, creates bookmark with LLM-powered defaults.

    Returns:
        - AddBookmarkSuccessResponse: Bookmark created successfully
        - ConflictResponse: Bookmark already exists (conflict detected)
    """
    session = get_session()

    try:
        # Get credentials from environment
        api_key = os.getenv("DIIGO_API_KEY")
        username = os.getenv("DIIGO_USERNAME")
        password = os.getenv("DIIGO_PASSWORD")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not all([api_key, username, password]):
            raise HTTPException(
                status_code=500,
                detail={
                    "detail": "Missing Diigo credentials. Please configure DIIGO_API_KEY, DIIGO_USERNAME, and DIIGO_PASSWORD",
                    "error_code": "MISSING_CREDENTIALS"
                }
            )

        # Create clients
        diigo_client = DiigoClient(api_key=api_key, username=username, password=password)
        openai_client = OpenAIClient(api_key=openai_api_key) if openai_api_key else None

        # Create service
        service = BookmarkService(
            session=session,
            diigo_client=diigo_client,
            openai_client=openai_client
        )

        # Call service layer
        try:
            result = service.add_bookmark(
                url=request.url,
                title=request.title,
                description=request.description,
                tags=request.tags,
                shared=request.shared
            )
        except ValueError as e:
            # Diigo API error
            raise HTTPException(
                status_code=500,
                detail={
                    "detail": str(e),
                    "error_code": "DIIGO_API_ERROR"
                }
            )

        # Check if conflict detected
        if result.get("conflict"):
            return ConflictResponse(
                conflict=True,
                url=result["url"],
                existing=ExistingBookmark(**result["existing"]),
                new=NewBookmark(**result["new"]),
                llm_suggestions=LLMSuggestions(**result["llm_suggestions"])
            )

        # Check if no changes needed
        if result.get("no_changes"):
            return AddBookmarkSuccessResponse(
                url=result["url"],
                title=result["title"],
                description=result["description"],
                tags=result["tags"],
                display_id=result["display_id"],
                action="no_changes"
            )

        # Success - bookmark created
        llm_suggestions = None
        if result.get("llm_suggestions"):
            llm_suggestions = LLMSuggestions(**result["llm_suggestions"])

        return AddBookmarkSuccessResponse(
            url=result["url"],
            title=result["title"],
            description=result["description"],
            tags=result["tags"],
            display_id=result["display_id"],
            llm_suggestions=llm_suggestions,
            action=result.get("action")
        )

    finally:
        session.close()


@router.post("/bookmarks/prepare", response_model=PrepareBookmarkResponse)
async def prepare_bookmark(request: AddBookmarkRequest):
    """
    Prepare a bookmark without submitting to Diigo.

    Fetches metadata, generates LLM suggestions, checks for conflicts.
    Returns preview data for the user to review before final submission.
    """
    session = get_session()

    try:
        api_key = os.getenv("DIIGO_API_KEY")
        username = os.getenv("DIIGO_USERNAME")
        password = os.getenv("DIIGO_PASSWORD")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not all([api_key, username, password]):
            raise HTTPException(
                status_code=500,
                detail={
                    "detail": "Missing Diigo credentials",
                    "error_code": "MISSING_CREDENTIALS"
                }
            )

        diigo_client = DiigoClient(api_key=api_key, username=username, password=password)
        openai_client = OpenAIClient(api_key=openai_api_key) if openai_api_key else None

        service = BookmarkService(
            session=session,
            diigo_client=diigo_client,
            openai_client=openai_client
        )

        result = service.prepare_bookmark(
            url=request.url,
            title=request.title,
            description=request.description,
            tags=request.tags,
            force_retag=request.force_retag,
        )

        llm_suggestions = None
        if result.get("llm_suggestions"):
            llm_suggestions = LLMSuggestions(**result["llm_suggestions"])

        return PrepareBookmarkResponse(
            url=result["url"],
            title=result["title"],
            description=result["description"],
            tags=result["tags"],
            tag_counts=result.get("tag_counts", {}),
            title_missing=result.get("title_missing", False),
            llm_suggestions=llm_suggestions,
            conflict=result.get("conflict"),
            display_id=result["display_id"],
            detected_tags=result.get("detected_tags", []),
            tag_matches=result.get("tag_matches", []),
            author=result.get("author", ""),
            related_bookmarks=result.get("related_bookmarks", []),
            parent_categories=result.get("parent_categories", []),
        )

    finally:
        session.close()


@router.post("/bookmarks/submit", response_model=AddBookmarkSuccessResponse)
async def submit_bookmark(request: SubmitBookmarkRequest):
    """
    Submit a prepared bookmark to Diigo and save to database.

    Call this after reviewing the preview from /bookmarks/prepare.
    """
    session = get_session()

    try:
        api_key = os.getenv("DIIGO_API_KEY")
        username = os.getenv("DIIGO_USERNAME")
        password = os.getenv("DIIGO_PASSWORD")

        if not all([api_key, username, password]):
            raise HTTPException(
                status_code=500,
                detail={
                    "detail": "Missing Diigo credentials",
                    "error_code": "MISSING_CREDENTIALS"
                }
            )

        diigo_client = DiigoClient(api_key=api_key, username=username, password=password)

        service = BookmarkService(
            session=session,
            diigo_client=diigo_client,
        )

        try:
            result = service.submit_bookmark(
                url=request.url,
                title=request.title,
                description=request.description or "",
                tags=request.tags,
                shared=request.shared,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "detail": str(e),
                    "error_code": "DIIGO_API_ERROR"
                }
            )

        return AddBookmarkSuccessResponse(
            url=result["url"],
            title=result["title"],
            description=result["description"],
            tags=result["tags"],
            display_id=result["display_id"],
        )

    finally:
        session.close()


@router.get("/tags/statistics")
async def tag_statistics():
    """Return tag usage statistics and analytics."""
    from ...services.tag_service import TagService

    session = get_session()
    try:
        service = TagService(session=session)
        stats = service.get_statistics()
        return stats
    finally:
        session.close()


@router.get("/tags/autocomplete")
async def tag_autocomplete(
    prefix: str = Query("", description="Tag prefix to filter by (optional)"),
    q: str = Query("", description="Optional query to further filter"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
):
    """Return tags matching a prefix for autocomplete.

    Args:
        prefix: Required tag prefix (e.g. "reference:").
        q: Optional additional fragment to filter within the prefix.
        limit: Maximum number of results to return (1–100, default 20).

    Returns:
        A dict with ``tags`` (list of matching tag names) and ``prefix``
        (the prefix used for the query).
    """
    from sqlalchemy import func
    from ...models import bookmark_tags

    session = get_session()

    try:
        pattern = f"{prefix}{q}%"
        tags = (
            session.query(TagModel)
            .filter(TagModel.name.like(pattern))
            .limit(limit)
            .all()
        )
        # Include bookmark count per tag
        tag_counts = {}
        for tag in tags:
            count = (
                session.query(func.count())
                .select_from(bookmark_tags)
                .filter(bookmark_tags.c.tag_id == tag.id)
                .scalar()
            )
            tag_counts[tag.name] = count

        return {"tags": [tag.name for tag in tags], "tag_counts": tag_counts, "prefix": prefix}

    finally:
        session.close()


class MergeTagsRequest(BaseModel):
    """Request body for tag merge endpoint."""

    source_tags: list[str]
    target_tag: str
    preview: bool = False


@router.post("/tags/merge")
async def merge_tags(request: MergeTagsRequest):
    """Merge source tags into a target tag.

    Moves all bookmarks from source tags to the target tag, then deletes
    source tags. If preview=True, returns affected counts without merging.

    Args:
        request: MergeTagsRequest with source_tags, target_tag, preview flag.

    Returns:
        Dict with merged_count, target_tag, and affected_bookmarks.
    """
    from sqlalchemy import func
    from ...models import bookmark_tags
    from ...services.tag_reconciliation import TagReconciliationService

    session = get_session()
    try:
        service = TagReconciliationService(session=session)

        # Count affected bookmarks (bookmarks that have any of the source tags)
        source_tag_objs = (
            session.query(TagModel)
            .filter(TagModel.name.in_([s.strip().lower() for s in request.source_tags]))
            .all()
        )
        source_tag_ids = [t.id for t in source_tag_objs]

        affected_bookmarks = 0
        if source_tag_ids:
            affected_bookmarks = (
                session.query(func.count(func.distinct(bookmark_tags.c.bookmark_id)))
                .filter(bookmark_tags.c.tag_id.in_(source_tag_ids))
                .scalar()
            ) or 0

        if request.preview:
            return {
                "merged_count": len(source_tag_objs),
                "target_tag": request.target_tag.strip().lower(),
                "affected_bookmarks": affected_bookmarks,
            }

        # Perform merge
        service.merge_tags(
            source_tags=request.source_tags,
            target_tag=request.target_tag,
        )

        return {
            "merged_count": len(source_tag_objs),
            "target_tag": request.target_tag.strip().lower(),
            "affected_bookmarks": affected_bookmarks,
        }
    finally:
        session.close()


@router.get("/tags/similar")
async def similar_tags(
    threshold: float = Query(0.8, ge=0.5, le=1.0),
    limit: int = Query(20, ge=1, le=500),
    min_count: int = Query(5, ge=0, le=1000, description="Minimum bookmark count per tag"),
):
    """Find similar tag pairs that are merge candidates.

    Uses string similarity (SequenceMatcher) to identify tags that may be
    duplicates or near-duplicates. Pre-filters by minimum bookmark count
    and tag length similarity to keep response times fast.

    Args:
        threshold: Minimum similarity score (0.5-1.0).
        limit: Maximum number of pairs to return (1-100).
        min_count: Minimum bookmarks a tag must have to be included (default 2).

    Returns:
        Dict with pairs list sorted by similarity descending.
    """
    from sqlalchemy import func
    from ...models import bookmark_tags

    session = get_session()
    try:
        # Single query to get all tags with their bookmark counts
        tag_rows = (
            session.query(TagModel.name, func.count(bookmark_tags.c.bookmark_id).label('cnt'))
            .join(bookmark_tags, TagModel.id == bookmark_tags.c.tag_id)
            .group_by(TagModel.id)
            .having(func.count(bookmark_tags.c.bookmark_id) >= min_count)
            .all()
        )

        tag_counts = {name: cnt for name, cnt in tag_rows}
        tag_names = list(tag_counts.keys())

        # Find similar pairs with length pre-filter
        # Tags with very different lengths can't have high similarity
        pairs = []
        for i in range(len(tag_names)):
            len_i = len(tag_names[i])
            for j in range(i + 1, len(tag_names)):
                len_j = len(tag_names[j])
                # Length ratio filter: if lengths differ by >2x, similarity can't exceed ~0.67
                if len_i > 0 and len_j > 0:
                    ratio = min(len_i, len_j) / max(len_i, len_j)
                    if ratio < threshold:
                        continue

                similarity = difflib.SequenceMatcher(
                    None, tag_names[i], tag_names[j]
                ).ratio()
                if similarity >= threshold:
                    pairs.append({
                        "tag1": tag_names[i],
                        "tag2": tag_names[j],
                        "similarity": round(similarity, 3),
                        "count1": tag_counts[tag_names[i]],
                        "count2": tag_counts[tag_names[j]],
                    })

        # Sort by similarity descending
        pairs.sort(key=lambda p: p["similarity"], reverse=True)
        return {"pairs": pairs[:limit]}
    finally:
        session.close()


@router.get("/tags/cloud")
async def tag_cloud(
    limit: int = Query(100, ge=10, le=500, description="Max tags to return"),
):
    """Return tags with bookmark counts for cloud visualization.

    Queries the bookmark_tags association table for accurate counts rather
    than relying on the potentially stale Tag.count column.

    Args:
        limit: Maximum number of tags to return (10-500, default 100).

    Returns:
        Dict with ``tags`` list, each containing ``name`` and ``count``,
        sorted by count descending.
    """
    from sqlalchemy import func, desc
    from ...models import bookmark_tags

    session = get_session()

    try:
        results = (
            session.query(
                TagModel.name,
                func.count(bookmark_tags.c.bookmark_id).label("bookmark_count"),
            )
            .join(bookmark_tags, TagModel.id == bookmark_tags.c.tag_id)
            .group_by(TagModel.id)
            .order_by(desc("bookmark_count"))
            .limit(limit)
            .all()
        )

        tags = [{"name": row[0], "count": row[1]} for row in results]
        return {"tags": tags}

    finally:
        session.close()


class SetParentRequest(BaseModel):
    """Request body for setting a tag's parent."""

    tag_name: str
    parent_name: Optional[str] = None


@router.post("/bookmarks/resolve", response_model=AddBookmarkSuccessResponse)
async def resolve_bookmark_conflict(request: ResolveConflictRequest):
    """
    Resolve bookmark conflict with 3-character resolution code.

    Resolution code format (3 characters):
    - Position 0 (title): n=new, o=original, s=smart
    - Position 1 (description): n=new, o=original, s=smart
    - Position 2 (tags): n=new, o=original, s=smart

    Examples:
    - 'nns': new title, new description, smart merge tags
    - 'ooo': keep all original
    - 'nnn': replace all with new
    - 'sss': smart merge all (prefer user input, else keep original)
    """
    session = get_session()

    try:
        # Validate resolution code format
        if len(request.resolution) != 3:
            raise HTTPException(
                status_code=400,
                detail={
                    "detail": "Resolution code must be exactly 3 characters",
                    "error_code": "INVALID_RESOLUTION_CODE",
                    "resolution": request.resolution
                }
            )

        # Validate characters
        valid_chars = {'n', 'o', 's'}
        for char in request.resolution:
            if char not in valid_chars:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "detail": f"Invalid character '{char}' in resolution code. Must be one of: n, o, s",
                        "error_code": "INVALID_RESOLUTION_CHAR",
                        "resolution": request.resolution
                    }
                )

        # Get credentials from environment
        api_key = os.getenv("DIIGO_API_KEY")
        username = os.getenv("DIIGO_USERNAME")
        password = os.getenv("DIIGO_PASSWORD")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not all([api_key, username, password]):
            raise HTTPException(
                status_code=500,
                detail={
                    "detail": "Missing Diigo credentials",
                    "error_code": "MISSING_CREDENTIALS"
                }
            )

        # Create clients
        diigo_client = DiigoClient(api_key=api_key, username=username, password=password)
        openai_client = OpenAIClient(api_key=openai_api_key) if openai_api_key else None

        # Create service
        service = BookmarkService(
            session=session,
            diigo_client=diigo_client,
            openai_client=openai_client
        )

        # Call service layer with conflict resolution
        try:
            result = service.add_bookmark(
                url=request.url,
                title=request.title,
                description=request.description,
                tags=request.tags,
                shared=request.shared,
                conflict_resolution=request.resolution
            )
        except ValueError as e:
            # Diigo API error
            raise HTTPException(
                status_code=500,
                detail={
                    "detail": str(e),
                    "error_code": "DIIGO_API_ERROR"
                }
            )

        # Should not get conflict response when resolution provided
        if result.get("conflict"):
            logger.error(f"Unexpected conflict response with resolution: {request.resolution}")
            raise HTTPException(
                status_code=500,
                detail={
                    "detail": "Unexpected conflict after resolution",
                    "error_code": "UNEXPECTED_CONFLICT"
                }
            )

        # Success
        llm_suggestions = None
        if result.get("llm_suggestions"):
            llm_suggestions = LLMSuggestions(**result["llm_suggestions"])

        return AddBookmarkSuccessResponse(
            url=result["url"],
            title=result["title"],
            description=result["description"],
            tags=result["tags"],
            display_id=result["display_id"],
            llm_suggestions=llm_suggestions,
            action=result.get("action")
        )

    finally:
        session.close()


@router.get("/tags/hierarchy")
async def get_tag_hierarchy():
    """Return tag tree with parent-child relationships and bookmark counts.

    Returns top-level tags (parent_id is null) with nested children.
    Each node includes the tag's bookmark count from the association table.

    Returns:
        Dict with ``tags`` list of tree nodes, each containing ``id``,
        ``name``, ``parent_id``, ``count``, and ``children``.
    """
    from sqlalchemy import func
    from ...models import bookmark_tags

    session = get_session()

    try:
        # Get all tags with their bookmark counts
        results = (
            session.query(
                TagModel.id,
                TagModel.name,
                TagModel.parent_id,
                func.count(bookmark_tags.c.bookmark_id).label("bookmark_count"),
            )
            .outerjoin(bookmark_tags, TagModel.id == bookmark_tags.c.tag_id)
            .group_by(TagModel.id)
            .order_by(TagModel.name)
            .all()
        )

        # Build lookup of id -> node
        nodes = {}
        for row in results:
            nodes[row[0]] = {
                "id": row[0],
                "name": row[1],
                "parent_id": row[2],
                "count": row[3],
                "children": [],
            }

        # Assemble tree: attach children to parents
        root_tags = []
        for node in nodes.values():
            pid = node["parent_id"]
            if pid is not None and pid in nodes:
                nodes[pid]["children"].append(node)
            else:
                root_tags.append(node)

        # Sort root tags by count descending
        root_tags.sort(key=lambda t: t["count"], reverse=True)

        return {"tags": root_tags}

    finally:
        session.close()


@router.post("/tags/hierarchy")
async def set_tag_parent(request: SetParentRequest):
    """Set or remove the parent of a tag.

    Args:
        request: Contains ``tag_name`` and optional ``parent_name``.
            Set ``parent_name`` to null to make the tag top-level.

    Returns:
        Dict confirming the tag name and its new parent_id.

    Raises:
        HTTPException: 404 if tag or parent not found, 400 if circular.
    """
    session = get_session()

    try:
        tag = session.query(TagModel).filter_by(name=request.tag_name).first()
        if not tag:
            raise HTTPException(
                status_code=404,
                detail={
                    "detail": f"Tag '{request.tag_name}' not found",
                    "error_code": "TAG_NOT_FOUND",
                },
            )

        if request.parent_name is None:
            tag.parent_id = None
            session.commit()
            return {"tag": tag.name, "parent_id": None}

        parent = session.query(TagModel).filter_by(name=request.parent_name).first()
        if not parent:
            raise HTTPException(
                status_code=404,
                detail={
                    "detail": f"Parent tag '{request.parent_name}' not found",
                    "error_code": "PARENT_TAG_NOT_FOUND",
                },
            )

        # Prevent self-reference
        if parent.id == tag.id:
            raise HTTPException(
                status_code=400,
                detail={
                    "detail": "A tag cannot be its own parent",
                    "error_code": "CIRCULAR_HIERARCHY",
                },
            )

        # Prevent circular references: walk up from parent to root
        current = parent
        while current.parent_id is not None:
            if current.parent_id == tag.id:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "detail": "Setting this parent would create a circular hierarchy",
                        "error_code": "CIRCULAR_HIERARCHY",
                    },
                )
            current = session.query(TagModel).get(current.parent_id)
            if current is None:
                break

        tag.parent_id = parent.id
        session.commit()
        return {"tag": tag.name, "parent_id": parent.id}

    finally:
        session.close()


class SetClusterParentRequest(BaseModel):
    """Request to set parent for a cluster of child tags."""
    parent_tag: str
    child_tags: list


@router.post("/tags/hierarchy/cluster")
async def set_cluster_parent(request: SetClusterParentRequest):
    """Set parent_id on multiple child tags at once.

    Used when user accepts a suggested category from LCA inference.
    Creates the parent tag if it doesn't exist.

    Args:
        request: Contains parent_tag name and list of child_tag names.

    Returns:
        Dict with parent tag and count of children updated.
    """
    session = get_session()

    try:
        # Get or create the parent tag
        parent = session.query(TagModel).filter_by(name=request.parent_tag).first()
        if not parent:
            parent = TagModel(name=request.parent_tag, count=0, source="user")
            session.add(parent)
            session.flush()

        # Set parent_id on each child (skip if child == parent or doesn't exist)
        updated = 0
        for child_name in request.child_tags:
            child = session.query(TagModel).filter_by(name=child_name).first()
            if child and child.id != parent.id:
                child.parent_id = parent.id
                updated += 1

        session.commit()
        return {"parent_tag": parent.name, "children_updated": updated}

    finally:
        session.close()
