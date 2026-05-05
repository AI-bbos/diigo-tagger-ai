# ABOUTME: Unit tests for metadata_tag_detector service
# ABOUTME: Tests source detection, format detection, and full detect() return format

import pytest

from diigo_tagger.services.metadata_tag_detector import MetadataTagDetector


class TestSourceDetection:
    """Test _detect_source URL parsing."""

    def setup_method(self):
        """Create detector instance for each test."""
        self.detector = MetadataTagDetector()

    def test_simple_domain(self):
        """Should extract registered domain from simple URL."""
        result = self.detector._detect_source("https://youtube.com/watch?v=abc123")
        assert result == {"tag": "source:youtube.com", "type": "source"}

    def test_strips_www_subdomain(self):
        """Should strip www prefix, returning registered domain only."""
        result = self.detector._detect_source("https://www.github.com/user/repo")
        assert result == {"tag": "source:github.com", "type": "source"}

    def test_strips_arbitrary_subdomain(self):
        """Should strip non-www subdomains like blog.example.com."""
        result = self.detector._detect_source("https://blog.example.com/post/1")
        assert result == {"tag": "source:example.com", "type": "source"}

    def test_country_tld_co_uk(self):
        """Should preserve .co.uk as the TLD, stripping www."""
        result = self.detector._detect_source("https://www.bbc.co.uk/news")
        assert result == {"tag": "source:bbc.co.uk", "type": "source"}

    def test_country_tld_com_au(self):
        """Should preserve .com.au as the TLD."""
        result = self.detector._detect_source("https://www.abc.net.au/news")
        assert result == {"tag": "source:abc.net.au", "type": "source"}

    def test_github_url(self):
        """Should return github.com as source."""
        result = self.detector._detect_source("https://github.com/user/repo")
        assert result == {"tag": "source:github.com", "type": "source"}

    def test_youtu_be_shortlink(self):
        """Should handle youtu.be short domain correctly."""
        result = self.detector._detect_source("https://youtu.be/abc123")
        assert result == {"tag": "source:youtu.be", "type": "source"}

    def test_subdomain_with_country_tld(self):
        """Should strip subdomains but preserve 2LD + ccTLD."""
        result = self.detector._detect_source("https://blog.bbc.co.uk/article")
        assert result == {"tag": "source:bbc.co.uk", "type": "source"}


class TestFormatDetection:
    """Test _detect_format URL and metadata parsing."""

    def setup_method(self):
        """Create detector instance for each test."""
        self.detector = MetadataTagDetector()

    def test_youtube_is_video(self):
        """Should detect youtube.com as video format."""
        result = self.detector._detect_format("https://www.youtube.com/watch?v=abc", {})
        assert result == {"tag": "format:video", "type": "format"}

    def test_youtu_be_is_video(self):
        """Should detect youtu.be short link as video format."""
        result = self.detector._detect_format("https://youtu.be/abc123", {})
        assert result == {"tag": "format:video", "type": "format"}

    def test_vimeo_is_video(self):
        """Should detect vimeo.com as video format."""
        result = self.detector._detect_format("https://vimeo.com/123456789", {})
        assert result == {"tag": "format:video", "type": "format"}

    def test_dailymotion_is_video(self):
        """Should detect dailymotion.com as video format."""
        result = self.detector._detect_format("https://www.dailymotion.com/video/x7abc", {})
        assert result == {"tag": "format:video", "type": "format"}

    def test_twitch_is_video(self):
        """Should detect twitch.tv as video format."""
        result = self.detector._detect_format("https://www.twitch.tv/channel/clip/abc", {})
        assert result == {"tag": "format:video", "type": "format"}

    def test_rumble_is_video(self):
        """Should detect rumble.com as video format."""
        result = self.detector._detect_format("https://rumble.com/v12345-title.html", {})
        assert result == {"tag": "format:video", "type": "format"}

    def test_pdf_url_extension(self):
        """Should detect URL ending in .pdf as PDF format."""
        result = self.detector._detect_format("https://example.com/document.pdf", {})
        assert result == {"tag": "format:pdf", "type": "format"}

    def test_pdf_url_case_insensitive(self):
        """Should detect .PDF uppercase extension as PDF format."""
        result = self.detector._detect_format("https://example.com/document.PDF", {})
        assert result == {"tag": "format:pdf", "type": "format"}

    def test_github_user_repo_is_repository(self):
        """Should detect github.com with 2 path segments as repository."""
        result = self.detector._detect_format("https://github.com/user/repo", {})
        assert result == {"tag": "format:repository", "type": "format"}

    def test_gitlab_user_repo_is_repository(self):
        """Should detect gitlab.com with 2 path segments as repository."""
        result = self.detector._detect_format("https://gitlab.com/user/repo", {})
        assert result == {"tag": "format:repository", "type": "format"}

    def test_github_blob_is_not_repository(self):
        """Should NOT detect github.com blob view as repository."""
        result = self.detector._detect_format(
            "https://github.com/user/repo/blob/main/README.md", {}
        )
        assert result is None

    def test_github_tree_is_not_repository(self):
        """Should NOT detect github.com tree view as repository."""
        result = self.detector._detect_format(
            "https://github.com/user/repo/tree/main", {}
        )
        assert result is None

    def test_github_issues_is_not_repository(self):
        """Should NOT detect github.com issues page as repository."""
        result = self.detector._detect_format(
            "https://github.com/user/repo/issues/42", {}
        )
        assert result is None

    def test_github_pull_is_not_repository(self):
        """Should NOT detect github.com pull request as repository."""
        result = self.detector._detect_format(
            "https://github.com/user/repo/pull/1", {}
        )
        assert result is None

    def test_article_from_has_article_tag(self):
        """Should detect article format when metadata has has_article_tag=True."""
        result = self.detector._detect_format(
            "https://example.com/post", {"has_article_tag": True}
        )
        assert result == {"tag": "format:article", "type": "format"}

    def test_article_from_content_type(self):
        """Should detect article format when metadata content_type is 'article'."""
        result = self.detector._detect_format(
            "https://example.com/post", {"content_type": "article"}
        )
        assert result == {"tag": "format:article", "type": "format"}

    def test_plain_url_no_format(self):
        """Should return None for a plain URL with no detectable format."""
        result = self.detector._detect_format("https://example.com/page", {})
        assert result is None

    def test_github_no_path_is_not_repository(self):
        """Should NOT detect github.com root URL as repository."""
        result = self.detector._detect_format("https://github.com/", {})
        assert result is None

    def test_github_single_segment_is_not_repository(self):
        """Should NOT detect github.com with 1 path segment (user profile) as repository."""
        result = self.detector._detect_format("https://github.com/user", {})
        assert result is None


class TestDetectReturnFormat:
    """Test full detect() method return structure."""

    def setup_method(self):
        """Create detector instance for each test."""
        self.detector = MetadataTagDetector()

    def test_returns_list(self):
        """Should return a list."""
        result = self.detector.detect("https://youtube.com/watch?v=abc", {})
        assert isinstance(result, list)

    def test_each_item_has_tag_and_type_keys(self):
        """Each item in the list must have 'tag' and 'type' keys."""
        result = self.detector.detect("https://youtube.com/watch?v=abc", {})
        for item in result:
            assert "tag" in item
            assert "type" in item

    def test_video_url_returns_source_and_format(self):
        """A YouTube URL should return both source and format tags."""
        result = self.detector.detect("https://youtube.com/watch?v=abc", {})
        tags = {item["tag"] for item in result}
        assert "source:youtube.com" in tags
        assert "format:video" in tags
        assert len(result) == 2

    def test_plain_url_returns_only_source(self):
        """A plain URL with no detectable format returns only the source tag."""
        result = self.detector.detect("https://example.com/page", {})
        assert len(result) == 1
        assert result[0]["type"] == "source"
        assert result[0]["tag"] == "source:example.com"

    def test_pdf_url_returns_source_and_format(self):
        """A PDF URL should return both source and format tags."""
        result = self.detector.detect("https://example.com/document.pdf", {})
        types = {item["type"] for item in result}
        assert "source" in types
        assert "format" in types

    def test_github_repo_url_returns_source_and_format(self):
        """A GitHub repo URL should return source:github.com and format:repository."""
        result = self.detector.detect("https://github.com/user/repo", {})
        tags = {item["tag"] for item in result}
        assert "source:github.com" in tags
        assert "format:repository" in tags

    def test_article_metadata_returns_source_and_format(self):
        """Article metadata should produce source and format:article tags."""
        result = self.detector.detect(
            "https://example.com/post", {"has_article_tag": True}
        )
        tags = {item["tag"] for item in result}
        assert "source:example.com" in tags
        assert "format:article" in tags
