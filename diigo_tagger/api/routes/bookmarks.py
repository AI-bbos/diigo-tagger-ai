# ABOUTME: Bookmark API endpoints for listing and searching
# ABOUTME: Supports Lucene query syntax via luqum, pagination, and sorting

import logging
import math
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import desc, or_

from ...db import get_session
from ...models import Bookmark as BookmarkModel, Tag as TagModel
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
        # Build query
        query = session.query(BookmarkModel)

        # TODO: Phase 1.2 - Add luqum query parsing
        # For now, just list all bookmarks
        if q:
            logger.warning(f"Query parsing not yet implemented: {q}")

        # Apply sorting
        if sort == "created_asc":
            query = query.order_by(BookmarkModel.created_at.asc())
        elif sort == "title_asc":
            query = query.order_by(BookmarkModel.title.asc())
        else:  # default: created_desc
            query = query.order_by(BookmarkModel.created_at.desc())

        # Count total for pagination
        total_items = query.count()
        total_pages = math.ceil(total_items / limit) if total_items > 0 else 0

        # Apply pagination
        offset = (page - 1) * limit
        bookmarks = query.offset(offset).limit(limit).all()

        # Convert to response format
        bookmark_responses = []
        for bm in bookmarks:
            tags = [tag.name for tag in bm.tags]
            bookmark_responses.append(BookmarkResponse(
                id=bm.id,
                display_id=bm.display_id,
                url=bm.url,
                title=bm.title,
                description=bm.description,
                tags=tags,
                created_at=bm.created_at,
                updated_at=bm.updated_at
            ))

        # Build pagination info
        pagination = PaginationInfo(
            page=page,
            limit=limit,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

        return BookmarkListResponse(
            bookmarks=bookmark_responses,
            pagination=pagination,
            query=q
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
