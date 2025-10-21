# ABOUTME: Diigo API client for fetching bookmarks
# ABOUTME: Handles authentication, pagination, and bookmark parsing

import requests
from dataclasses import dataclass
from datetime import datetime
from typing import List

from ..security import is_valid_https_url, redact_api_key


@dataclass
class DiigoBookmark:
    """
    Represents a Diigo bookmark.

    Attributes:
        title: Bookmark title
        url: Bookmark URL
        description: Bookmark description/notes
        tags: List of tag strings
        created_at: Creation timestamp
    """

    title: str
    url: str
    description: str
    tags: List[str]
    created_at: str


class DiigoClient:
    """
    Client for Diigo API v2.

    Fetches bookmarks with authentication and handles API errors.
    """

    def __init__(
        self,
        api_key: str | None,
        username: str | None = None,
        base_url: str = "https://secure.diigo.com/api/v2",
    ):
        """
        Initialize Diigo API client.

        Args:
            api_key: Diigo API key for authentication
            username: Diigo username (required for API calls)
            base_url: Base URL for Diigo API (must be HTTPS)

        Raises:
            ValueError: If API key/username is missing or base_url is not HTTPS
        """
        if not api_key:
            raise ValueError("API key is required for Diigo client")

        if not username:
            raise ValueError("Username is required for Diigo client")

        if not is_valid_https_url(base_url):
            raise ValueError(f"Base URL must use HTTPS: {base_url}")

        self.api_key = api_key
        self.username = username
        self.base_url = base_url

    def fetch_bookmarks(
        self, count: int = 100, start: int = 0
    ) -> List[DiigoBookmark]:
        """
        Fetch bookmarks from Diigo API.

        Args:
            count: Number of bookmarks to fetch (max 100 per request)
            start: Offset for pagination (0-based)

        Returns:
            List of DiigoBookmark objects

        Raises:
            Exception: On API errors (rate limit, auth failure, network errors)
        """
        url = f"{self.base_url}/bookmarks"
        # Diigo API v2 uses API key as query parameter (not Authorization header)
        params = {
            "key": self.api_key,
            "user": self.username,
            "count": count,
            "start": start,
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 401:
                raise Exception(
                    f"Authentication failed with Diigo API. "
                    f"Check API key: {redact_api_key(self.api_key)}"
                )

            if response.status_code == 429:
                raise Exception("Rate limit exceeded for Diigo API. Please retry later.")

            if response.status_code != 200:
                raise Exception(
                    f"Diigo API error: {response.status_code} - {response.text}"
                )

            # Parse JSON response
            data = response.json()
            bookmarks = []

            for item in data:
                # Parse tags (comma-separated string to list)
                tags_str = item.get("tags", "")
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]

                bookmark = DiigoBookmark(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("desc", ""),
                    tags=tags,
                    created_at=item.get("created_at", ""),
                )
                bookmarks.append(bookmark)

            return bookmarks

        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error fetching bookmarks from Diigo: {e}")
