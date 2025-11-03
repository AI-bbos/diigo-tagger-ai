# ABOUTME: Webpage and video metadata fetcher for URL content extraction
# ABOUTME: Uses yt-dlp for YouTube, BeautifulSoup for other URLs

from typing import Optional, Dict, List
from urllib.parse import urlparse
import logging

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
        try:
            import yt_dlp
        except ImportError:
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

    def _fetch_webpage_metadata(self, url: str) -> Dict[str, any]:
        """
        Fetch webpage metadata using requests + BeautifulSoup.

        Args:
            url: Webpage URL

        Returns:
            Dict with webpage metadata
        """
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("requests or beautifulsoup4 not installed")
            return {
                "title": "",
                "description": "",
                "keywords": [],
                "content_type": "webpage",
                "error": "requests or beautifulsoup4 not installed"
            }

        try:
            # Fetch page with reasonable timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; DiigoTagger/1.0)'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title = ""
            if soup.title:
                title = soup.title.string.strip() if soup.title.string else ""

            # Extract meta description
            description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'}) or \
                       soup.find('meta', attrs={'property': 'og:description'})
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
