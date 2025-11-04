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
        with patch("diigo_tagger.clients.metadata_fetcher.yt_dlp", None):
            # This would normally fail import, but we can test the error path
            # by mocking the import to raise ImportError
            with patch.dict('sys.modules', {'yt_dlp': None}):
                fetcher = MetadataFetcher()
                # The _fetch_youtube_metadata method has try/except for ImportError
                result = fetcher._fetch_youtube_metadata("https://youtube.com/test")

                assert "error" in result
                assert result["content_type"] == "youtube"

    def test_fetch_metadata_handles_missing_requests(self):
        """Should handle missing requests library gracefully."""
        with patch.dict('sys.modules', {'requests': None}):
            fetcher = MetadataFetcher()
            result = fetcher._fetch_webpage_metadata("https://example.com")

            assert "error" in result
            assert result["content_type"] == "webpage"
