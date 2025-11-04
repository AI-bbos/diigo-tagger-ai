# ABOUTME: Pydantic schemas for bookmark API endpoints
# ABOUTME: Request/response models for creating, listing, and searching bookmarks

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class BookmarkResponse(BaseModel):
    """Standard bookmark response."""
    model_config = ConfigDict(from_attributes=True)  # SQLAlchemy model compatibility

    id: int
    display_id: str
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class PaginationInfo(BaseModel):
    """Pagination metadata."""
    page: int
    limit: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class BookmarkListResponse(BaseModel):
    """Paginated bookmark list response."""
    bookmarks: List[BookmarkResponse]
    pagination: PaginationInfo
    query: Optional[str] = None  # The Lucene query that was executed
