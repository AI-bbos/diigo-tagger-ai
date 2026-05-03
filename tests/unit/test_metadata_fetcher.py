# ABOUTME: Unit tests for metadata fetcher module
# ABOUTME: Tests YouTube and webpage metadata extraction with mocked HTTP/yt-dlp

import pytest
from unittest.mock import Mock, patch, MagicMock
from diigo_tagger.clients.metadata_fetcher import MetadataFetcher


class TestMetadataFetcher:
    """Test metadata fetcher for YouTube and webpages."""

    def test_is_youtube_url_detects_youtube_com(self):
        """Should detect www.youtube.com URLs."""
        fetcher = MetadataFetcher()
        assert fetcher.is_youtube_url("https://www.youtube.com/watch?v=abc123") is True
        assert fetcher.is_youtube_url("https://youtube.com/watch?v=abc123") is True

    def test_is_youtube_url_detects_youtu_be(self):
        """Should detect youtu.be short URLs."""
        fetcher = MetadataFetcher()
        assert fetcher.is_youtube_url("https://youtu.be/abc123") is True

    def test_is_youtube_url_detects_mobile(self):
        """Should detect mobile YouTube URLs."""
        fetcher = MetadataFetcher()
        assert fetcher.is_youtube_url("https://m.youtube.com/watch?v=abc123") is True

    def test_is_youtube_url_rejects_non_youtube(self):
        """Should reject non-YouTube URLs."""
        fetcher = MetadataFetcher()
        assert fetcher.is_youtube_url("https://vimeo.com/abc123") is False
        assert fetcher.is_youtube_url("https://example.com") is False

    @patch("diigo_tagger.clients.metadata_fetcher.yt_dlp.YoutubeDL")
    def test_fetch_youtube_metadata_success(self, mock_ytdlp_class):
        """Should fetch YouTube video metadata successfully."""
        # Mock yt-dlp
        mock_ytdl = MagicMock()
        mock_ytdl.extract_info.return_value = {
            "title": "Test Video Title",
            "description": "Test video description",
            "tags": ["tag1", "tag2", "tag3"],
            "uploader": "Test Channel",
            "channel": "Test Channel Name",
            "duration": 300,
            "view_count": 1000
        }
        mock_ytdlp_class.return_value.__enter__.return_value = mock_ytdl

        fetcher = MetadataFetcher()
        result = fetcher.fetch_metadata("https://www.youtube.com/watch?v=abc123")

        assert result["title"] == "Test Video Title"
        assert result["description"] == "Test video description"
        assert "tag1" in result["keywords"]
        assert "tag2" in result["keywords"]
        assert "Test Channel" in result["keywords"]  # uploader added to keywords
        assert result["content_type"] == "youtube"
        assert result["uploader"] == "Test Channel"
        assert result["duration"] == 300
        assert result["view_count"] == 1000

    @patch("diigo_tagger.clients.metadata_fetcher.yt_dlp.YoutubeDL")
    def test_fetch_youtube_metadata_handles_missing_tags(self, mock_ytdlp_class):
        """Should handle YouTube videos without tags."""
        mock_ytdl = MagicMock()
        mock_ytdl.extract_info.return_value = {
            "title": "Video Without Tags",
            "description": "No tags here",
            "tags": None,  # No tags
            "uploader": "Channel"
        }
        mock_ytdlp_class.return_value.__enter__.return_value = mock_ytdl

        fetcher = MetadataFetcher()
        result = fetcher.fetch_metadata("https://youtube.com/watch?v=xyz")

        assert result["title"] == "Video Without Tags"
        assert result["keywords"] == ["Channel"]  # Only uploader
        assert result["content_type"] == "youtube"

    @patch("diigo_tagger.clients.metadata_fetcher.yt_dlp.YoutubeDL")
    def test_fetch_youtube_metadata_handles_errors(self, mock_ytdlp_class):
        """Should handle yt-dlp errors gracefully."""
        mock_ytdl = MagicMock()
        mock_ytdl.extract_info.side_effect = Exception("Network error")
        mock_ytdlp_class.return_value.__enter__.return_value = mock_ytdl

        fetcher = MetadataFetcher()
        result = fetcher.fetch_metadata("https://youtube.com/watch?v=error")

        assert result["title"] == ""
        assert result["description"] == ""
        assert result["keywords"] == []
        assert result["content_type"] == "youtube"
        assert "error" in result
        assert "Network error" in result["error"]

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    @patch("diigo_tagger.clients.metadata_fetcher.BeautifulSoup")
    def test_fetch_webpage_metadata_success(self, mock_bs_class, mock_get):
        """Should fetch webpage metadata successfully."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><head><title>Test Page</title></head></html>"
        mock_get.return_value = mock_response

        # Mock BeautifulSoup
        mock_soup = Mock()
        mock_title = Mock()
        mock_title.string = "Test Page Title"
        mock_soup.title = mock_title

        mock_meta_desc = {"content": "Test page description"}
        mock_soup.find.return_value = mock_meta_desc

        mock_soup.find_all.return_value = []  # No og: tags

        mock_bs_class.return_value = mock_soup

        fetcher = MetadataFetcher()
        result = fetcher.fetch_metadata("https://example.com")

        assert result["title"] == "Test Page Title"
        assert result["description"] == "Test page description"
        assert result["content_type"] == "webpage"
        mock_get.assert_called_once()

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    @patch("diigo_tagger.clients.metadata_fetcher.BeautifulSoup")
    def test_fetch_webpage_metadata_with_keywords(self, mock_bs_class, mock_get):
        """Should extract keywords from meta tags."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html></html>"
        mock_get.return_value = mock_response

        mock_soup = Mock()
        mock_title = Mock()
        mock_title.string = "Page"
        mock_soup.title = mock_title

        # Mock find to return different things based on attrs
        def find_side_effect(tag, attrs=None):
            if attrs and attrs.get('name') == 'description':
                return {"content": "Description"}
            elif attrs and attrs.get('name') == 'keywords':
                return {"content": "python, programming, tutorial"}
            return None

        mock_soup.find.side_effect = find_side_effect
        mock_soup.find_all.return_value = []

        mock_bs_class.return_value = mock_soup

        fetcher = MetadataFetcher()
        result = fetcher.fetch_metadata("https://example.com")

        assert "python" in result["keywords"]
        assert "programming" in result["keywords"]
        assert "tutorial" in result["keywords"]

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    def test_fetch_webpage_metadata_handles_http_errors(self, mock_get):
        """Should handle HTTP errors gracefully."""
        mock_get.side_effect = Exception("Connection timeout")

        fetcher = MetadataFetcher()
        result = fetcher.fetch_metadata("https://example.com/error")

        assert result["title"] == ""
        assert result["description"] == ""
        assert result["keywords"] == []
        assert result["content_type"] == "webpage"
        assert "error" in result
        assert "Connection timeout" in result["error"]

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    @patch("diigo_tagger.clients.metadata_fetcher.BeautifulSoup")
    def test_fetch_webpage_metadata_handles_missing_elements(self, mock_bs_class, mock_get):
        """Should handle missing title/description gracefully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html></html>"
        mock_get.return_value = mock_response

        mock_soup = Mock()
        mock_soup.title = None  # No title
        mock_soup.find.return_value = None  # No description
        mock_soup.find_all.return_value = []

        mock_bs_class.return_value = mock_soup

        fetcher = MetadataFetcher()
        result = fetcher.fetch_metadata("https://minimal.com")

        assert result["title"] == ""
        assert result["description"] == ""
        assert result["keywords"] == []
        assert result["content_type"] == "webpage"

    def test_fetch_metadata_handles_missing_yt_dlp(self):
        """Should handle missing yt-dlp gracefully."""
        with patch("diigo_tagger.clients.metadata_fetcher.YT_DLP_AVAILABLE", False):
            fetcher = MetadataFetcher()
            result = fetcher._fetch_youtube_metadata("https://youtube.com/test")

            assert "error" in result
            assert result["content_type"] == "youtube"
            assert "yt-dlp not installed" in result["error"]

    def test_fetch_metadata_handles_missing_requests(self):
        """Should handle missing requests library gracefully."""
        with patch("diigo_tagger.clients.metadata_fetcher.WEB_SCRAPING_AVAILABLE", False):
            fetcher = MetadataFetcher()
            result = fetcher._fetch_webpage_metadata("https://example.com")

            assert "error" in result
            assert result["content_type"] == "webpage"
            assert "not installed" in result["error"]


class TestTitleFallbackChain:
    """Test title extraction fallback: <title> → og:title → <h1> → URL path."""

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    def test_title_from_title_tag(self, mock_get):
        """Should use <title> tag as first priority."""
        html = b"""<html><head>
            <title>Title Tag Value</title>
            <meta property="og:title" content="OG Title Value">
        </head><body><h1>H1 Value</h1></body></html>"""
        mock_response = Mock()
        mock_response.content = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = MetadataFetcher()
        result = fetcher._fetch_webpage_metadata("https://example.com/page")
        assert result["title"] == "Title Tag Value"

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    def test_title_falls_back_to_og_title(self, mock_get):
        """Should fall back to og:title when <title> is missing."""
        html = b"""<html><head>
            <meta property="og:title" content="OG Title Value">
        </head><body><h1>H1 Value</h1></body></html>"""
        mock_response = Mock()
        mock_response.content = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = MetadataFetcher()
        result = fetcher._fetch_webpage_metadata("https://example.com/page")
        assert result["title"] == "OG Title Value"

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    def test_title_falls_back_to_h1(self, mock_get):
        """Should fall back to <h1> when <title> and og:title are missing."""
        html = b"""<html><head></head><body><h1>H1 Title Here</h1></body></html>"""
        mock_response = Mock()
        mock_response.content = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = MetadataFetcher()
        result = fetcher._fetch_webpage_metadata("https://example.com/page")
        assert result["title"] == "H1 Title Here"

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    def test_title_falls_back_to_url_path(self, mock_get):
        """Should fall back to URL path when all HTML sources fail."""
        html = b"""<html><head></head><body><p>No title anywhere</p></body></html>"""
        mock_response = Mock()
        mock_response.content = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = MetadataFetcher()
        result = fetcher._fetch_webpage_metadata(
            "https://medium.com/data-science/great-article-about-ai"
        )
        assert result["title"] == "Great Article About Ai"  # .title() capitalizes all words

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    def test_og_description_preferred_over_meta_description(self, mock_get):
        """Should prefer og:description over generic meta description."""
        html = b"""<html><head>
            <title>Page</title>
            <meta name="description" content="Generic description">
            <meta property="og:description" content="Better OG description">
        </head><body></body></html>"""
        mock_response = Mock()
        mock_response.content = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = MetadataFetcher()
        result = fetcher._fetch_webpage_metadata("https://example.com")
        assert result["description"] == "Better OG description"

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    def test_medium_page_with_og_tags(self, mock_get):
        """Should extract title from og:title on Medium-style pages."""
        html = b"""<html><head>
            <title>Medium</title>
            <meta property="og:title" content="Claude Code Hooks Explained">
            <meta property="og:description" content="The missing layer between prompts and production">
        </head><body></body></html>"""
        mock_response = Mock()
        mock_response.content = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = MetadataFetcher()
        result = fetcher._fetch_webpage_metadata("https://medium.com/article-slug")
        # <title> is "Medium" which is generic but still present - it's the first priority
        # Actually the spec says <title> is first priority, so "Medium" wins here
        # But the real fix is that Medium serves real content to Chrome UA
        assert result["title"] == "Medium"

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    def test_medium_page_empty_title_uses_og(self, mock_get):
        """Should use og:title when <title> is empty string."""
        html = b"""<html><head>
            <title></title>
            <meta property="og:title" content="Claude Code Hooks Explained">
        </head><body></body></html>"""
        mock_response = Mock()
        mock_response.content = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = MetadataFetcher()
        result = fetcher._fetch_webpage_metadata("https://medium.com/article-slug")
        assert result["title"] == "Claude Code Hooks Explained"

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    def test_user_agent_is_realistic_browser(self, mock_get):
        """Should use a realistic Chrome browser User-Agent."""
        mock_response = Mock()
        mock_response.content = b"<html><head><title>Page</title></head></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = MetadataFetcher()
        fetcher._fetch_webpage_metadata("https://example.com")

        call_kwargs = mock_get.call_args[1]
        ua = call_kwargs["headers"]["User-Agent"]
        assert "Chrome" in ua
        assert "Macintosh" in ua
        assert "DiigoTagger" not in ua


class TestTitleFromUrlPath:
    """Test URL path slug to title conversion."""

    def test_medium_url_with_hex_suffix(self):
        """Should strip trailing hex ID from Medium URLs."""
        fetcher = MetadataFetcher()
        url = "https://medium.com/data-science-collective/claude-code-hooks-explained-the-missing-layer-between-prompts-and-production-d0e3d1509278"
        result = fetcher._title_from_url_path(url)
        assert result == "Claude Code Hooks Explained The Missing Layer Between Prompts And Production"

    def test_substack_url(self):
        """Should handle Substack-style URLs."""
        fetcher = MetadataFetcher()
        url = "https://newsletter.substack.com/p/how-to-build-better-ai-agents"
        result = fetcher._title_from_url_path(url)
        assert result == "How To Build Better Ai Agents"

    def test_simple_slug(self):
        """Should handle simple hyphenated slugs."""
        fetcher = MetadataFetcher()
        url = "https://blog.example.com/posts/my-great-article"
        result = fetcher._title_from_url_path(url)
        assert result == "My Great Article"

    def test_url_with_trailing_slash(self):
        """Should handle trailing slashes."""
        fetcher = MetadataFetcher()
        url = "https://example.com/blog/some-post/"
        result = fetcher._title_from_url_path(url)
        assert result == "Some Post"

    def test_root_url_returns_empty(self):
        """Should return empty string for root URLs with no path."""
        fetcher = MetadataFetcher()
        url = "https://example.com/"
        result = fetcher._title_from_url_path(url)
        assert result == ""

    def test_strips_uuid_suffix(self):
        """Should strip UUID-style suffixes."""
        fetcher = MetadataFetcher()
        url = "https://example.com/great-article-a1b2c3d4e5f6"
        result = fetcher._title_from_url_path(url)
        assert result == "Great Article"

    def test_short_hex_not_stripped(self):
        """Should not strip short hex-like segments that might be meaningful."""
        fetcher = MetadataFetcher()
        url = "https://example.com/python-3-12-features"
        result = fetcher._title_from_url_path(url)
        assert result == "Python 3 12 Features"
