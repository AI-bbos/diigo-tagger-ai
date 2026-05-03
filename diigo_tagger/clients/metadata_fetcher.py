# ABOUTME: Webpage and video metadata fetcher for URL content extraction
# ABOUTME: Uses yt-dlp for YouTube, BeautifulSoup for other URLs

import re
from typing import Optional, Dict, List
from urllib.parse import urlparse
import logging

# Optional dependencies - may not be installed
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    yt_dlp = None
    YT_DLP_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    WEB_SCRAPING_AVAILABLE = True
except ImportError:
    requests = None
    BeautifulSoup = None
    WEB_SCRAPING_AVAILABLE = False

logger = logging.getLogger(__name__)


class MetadataFetcher:
    """
    Fetches metadata from URLs for enhanced tag generation.

    Handles:
    - YouTube videos: title, description, tags, uploader via yt-dlp
    - Regular webpages: title, description, keywords via BeautifulSoup
    """

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """
        Check if URL is a YouTube video.

        Args:
            url: URL to check

        Returns:
            True if YouTube URL, False otherwise
        """
        parsed = urlparse(url)
        return parsed.netloc in [
            'www.youtube.com', 'youtube.com',
            'youtu.be', 'm.youtube.com'
        ]

    def fetch_metadata(self, url: str) -> Dict[str, any]:
        """
        Fetch metadata from URL.

        Args:
            url: URL to fetch metadata from

        Returns:
            Dict with keys:
            - title: Page/video title
            - description: Page/video description
            - keywords: List of keywords/tags
            - content_type: 'youtube' or 'webpage'
            - error: Error message if fetch failed

        Examples:
            >>> fetcher = MetadataFetcher()
            >>> meta = fetcher.fetch_metadata("https://youtube.com/watch?v=...")
            >>> meta['title']
            'Swimming Freestyle Tutorial'
        """
        try:
            if self.is_youtube_url(url):
                return self._fetch_youtube_metadata(url)
            else:
                return self._fetch_webpage_metadata(url)
        except Exception as e:
            logger.warning(f"Failed to fetch metadata from {url}: {e}")
            return {
                "title": "",
                "description": "",
                "keywords": [],
                "content_type": "unknown",
                "error": str(e)
            }

    def _fetch_youtube_metadata(self, url: str) -> Dict[str, any]:
        """
        Fetch YouTube video metadata using yt-dlp.

        Args:
            url: YouTube video URL

        Returns:
            Dict with video metadata
        """
        if not YT_DLP_AVAILABLE:
            logger.error("yt-dlp not installed. Install with: pip install yt-dlp")
            return {
                "title": "",
                "description": "",
                "keywords": [],
                "content_type": "youtube",
                "error": "yt-dlp not installed"
            }

        try:
            # Configure yt-dlp to extract metadata only (no download)
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'format': 'best',
                'ignore_no_formats_error': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Extract relevant metadata
            title = info.get('title', '')
            description = info.get('description', '')

            # YouTube tags (if available)
            tags = info.get('tags', [])

            # Also consider categories, uploader as potential keywords
            keywords = list(tags) if tags else []
            if info.get('uploader'):
                keywords.append(info['uploader'])
            if info.get('channel'):
                keywords.append(info['channel'])

            return {
                "title": title,
                "description": description,
                "keywords": keywords,
                "content_type": "youtube",
                "uploader": info.get('uploader'),
                "duration": info.get('duration'),
                "view_count": info.get('view_count')
            }

        except Exception as e:
            logger.warning(f"Failed to fetch YouTube metadata: {e}")
            return {
                "title": "",
                "description": "",
                "keywords": [],
                "content_type": "youtube",
                "error": str(e)
            }

    def _title_from_url_path(self, url: str) -> str:
        """Extract a human-readable title from the URL path slug.

        Takes the last meaningful path segment, strips trailing hex/UUID
        suffixes, replaces hyphens with spaces, and title-cases the result.

        Args:
            url: Full URL to extract title from.

        Returns:
            Title-cased string derived from the URL path, or empty string
            if no meaningful path segment exists.
        """
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            return ""

        # Take the last path segment
        segment = path.split("/")[-1]

        # Strip trailing hex/UUID suffixes (12+ hex chars at end, preceded by hyphen)
        segment = re.sub(r"-[0-9a-f]{12,}$", "", segment)

        if not segment:
            return ""

        # Replace hyphens with spaces and title-case
        title = segment.replace("-", " ").title()
        return title

    def _fetch_webpage_metadata(self, url: str) -> Dict[str, any]:
        """Fetch webpage metadata using requests + BeautifulSoup.

        Extracts title using fallback chain: <title> → og:title → <h1> → URL path.
        Prefers og:description over generic meta description.

        Args:
            url: Webpage URL.

        Returns:
            Dict with webpage metadata.
        """
        if not WEB_SCRAPING_AVAILABLE:
            logger.error("requests or beautifulsoup4 not installed")
            return {
                "title": "",
                "description": "",
                "keywords": [],
                "content_type": "webpage",
                "error": "requests or beautifulsoup4 not installed"
            }

        try:
            # Fetch page with realistic browser User-Agent
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                )
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title with fallback chain:
            # <title> → og:title → <h1> → URL path slug
            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            if not title:
                og_title = soup.find('meta', attrs={'property': 'og:title'})
                if og_title and og_title.get('content'):
                    title = og_title['content'].strip()

            if not title:
                h1 = soup.find('h1')
                if h1 and h1.get_text(strip=True):
                    title = h1.get_text(strip=True)

            if not title:
                title = self._title_from_url_path(url)

            # Extract description — prefer og:description over meta description
            description = ""
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                description = og_desc['content'].strip()
            else:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    description = meta_desc['content'].strip()

            # Extract keywords
            keywords = []
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords and meta_keywords.get('content'):
                keywords = [k.strip() for k in meta_keywords['content'].split(',')]

            # Also check Open Graph tags
            og_tags = soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')})
            for tag in og_tags:
                if tag.get('property') == 'og:type':
                    keywords.append(tag.get('content', ''))

            return {
                "title": title,
                "description": description,
                "keywords": [k for k in keywords if k],  # Filter empty
                "content_type": "webpage"
            }

        except Exception as e:
            logger.warning(f"Failed to fetch webpage metadata: {e}")
            return {
                "title": "",
                "description": "",
                "keywords": [],
                "content_type": "webpage",
                "error": str(e)
            }
