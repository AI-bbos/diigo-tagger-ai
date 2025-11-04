# ABOUTME: Bookmark API endpoints for listing and searching
# ABOUTME: Thin layer that calls bookmark service for business logic

import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from ...db import get_session
from ...models import Bookmark as BookmarkModel
from ...services.bookmark_service import BookmarkService
from ..schemas.bookmark import BookmarkResponse, BookmarkListResponse, PaginationInfo

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
