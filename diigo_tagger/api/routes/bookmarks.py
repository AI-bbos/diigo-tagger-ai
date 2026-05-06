# ABOUTME: Bookmark API endpoints for listing, searching, and adding bookmarks
# ABOUTME: Thin layer that calls bookmark service for business logic

import logging
import os
from typing import Optional, Union

from fastapi import APIRouter, Query, HTTPException

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
    session = get_session()

    try:
        pattern = f"{prefix}{q}%"
        tags = (
            session.query(TagModel)
            .filter(TagModel.name.like(pattern))
            .limit(limit)
            .all()
        )
        return {"tags": [tag.name for tag in tags], "prefix": prefix}

    finally:
        session.close()


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
