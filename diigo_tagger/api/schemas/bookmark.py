# ABOUTME: Pydantic schemas for bookmark API endpoints
# ABOUTME: Request/response models for creating, listing, and searching bookmarks

from datetime import datetime
from typing import Dict, List, Optional
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


class AddBookmarkRequest(BaseModel):
    """Request to add a new bookmark."""
    url: str = Field(..., min_length=1, description="Bookmark URL (required)")
    title: Optional[str] = Field(None, description="Optional title (auto-fetched if not provided)")
    description: Optional[str] = Field(None, description="Optional description (auto-fetched if not provided)")
    tags: Optional[List[str]] = Field(None, description="Optional tags (LLM-suggested if not provided)")
    shared: bool = Field(True, description="Whether bookmark is public (default: True)")


class LLMSuggestions(BaseModel):
    """LLM-generated suggestions for bookmark metadata."""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ExistingBookmark(BaseModel):
    """Existing bookmark data in conflict response."""
    title: Optional[str]
    description: Optional[str]
    tags: List[str]
    display_id: str


class NewBookmark(BaseModel):
    """New bookmark data in conflict response."""
    title: Optional[str]
    description: Optional[str]
    tags: List[str]


class ConflictResponse(BaseModel):
    """Response when bookmark already exists (conflict detected)."""
    conflict: bool = True
    url: str
    existing: ExistingBookmark
    new: NewBookmark
    llm_suggestions: LLMSuggestions


class AddBookmarkSuccessResponse(BaseModel):
    """Successful bookmark creation response."""
    url: str
    title: Optional[str]
    description: Optional[str]
    tags: List[str]
    display_id: str
    llm_suggestions: Optional[LLMSuggestions] = None
    action: Optional[str] = None  # "kept_original" or None


class PrepareBookmarkResponse(BaseModel):
    """Preview of prepared bookmark data before submission."""
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    tag_counts: Dict[str, int] = Field(default_factory=dict, description="Bookmark count per tag name")
    title_missing: bool = False
    llm_suggestions: Optional[LLMSuggestions] = None
    conflict: Optional[dict] = None
    display_id: str


class SubmitBookmarkRequest(BaseModel):
    """Request to submit a prepared bookmark."""
    url: str = Field(..., min_length=1, description="Bookmark URL")
    title: str = Field(..., description="Resolved title to submit")
    description: Optional[str] = Field(None, description="Resolved description")
    tags: List[str] = Field(default_factory=list, description="Final tags to submit")
    shared: bool = Field(True, description="Whether bookmark is public")


class ResolveConflictRequest(BaseModel):
    """Request to resolve bookmark conflict with 3-character code."""
    url: str = Field(..., min_length=1, description="Bookmark URL")
    resolution: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="3-character resolution code (position 0=title, 1=description, 2=tags). Each char: n=new, o=original, s=smart. Example: 'nns'"
    )
    title: Optional[str] = Field(None, description="New title value (if using 'n' or 's' for title)")
    description: Optional[str] = Field(None, description="New description value (if using 'n' or 's' for description)")
    tags: Optional[List[str]] = Field(None, description="New tags (if using 'n' or 's' for tags)")
    shared: bool = Field(True, description="Whether bookmark is public")
