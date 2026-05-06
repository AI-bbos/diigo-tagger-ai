# ABOUTME: Unit tests for TagHierarchyService
# ABOUTME: Verifies LCA-based parent category inference with mocked LLM and DB

from unittest.mock import MagicMock, patch
import pytest

from diigo_tagger.services.tag_hierarchy import TagHierarchyService


class TestTagHierarchyService:
    """Tests for TagHierarchyService.infer_parent_categories()."""

    def test_returns_empty_when_no_openai_client(self):
        """Service returns empty list when no LLM client is provided."""
        session = MagicMock()
        service = TagHierarchyService(session=session, openai_client=None)

        result = service.infer_parent_categories(
            tags=["python", "flask", "django"], title="Web Frameworks"
        )

        assert result == []

    def test_returns_empty_when_fewer_than_two_tags(self):
        """Service returns empty list with fewer than 2 tags."""
        session = MagicMock()
        openai_client = MagicMock()
        service = TagHierarchyService(session=session, openai_client=openai_client)

        result = service.infer_parent_categories(tags=["python"], title="Single tag")

        assert result == []
        openai_client.generate_categories.assert_not_called()

    def test_valid_llm_response_returns_categories(self):
        """Service correctly processes valid LLM category suggestions."""
        session = MagicMock()
        openai_client = MagicMock()
        openai_client.generate_categories.return_value = [
            {"parent": "web-development", "cluster": ["flask", "django", "html"]},
            {"parent": "data-science", "cluster": ["pandas", "numpy"]},
        ]

        # Mock TagReconciliationService.match_existing_tags to return "new" for all
        with patch(
            "diigo_tagger.services.tag_hierarchy.TagReconciliationService"
        ) as mock_reconciler_cls:
            mock_reconciler = MagicMock()
            mock_reconciler.match_existing_tags.return_value = [
                {"suggested": "web-development", "matched": None, "similarity": 0.0, "candidates": [], "action": "new"},
                {"suggested": "data-science", "matched": None, "similarity": 0.0, "candidates": [], "action": "new"},
            ]
            mock_reconciler_cls.return_value = mock_reconciler

            service = TagHierarchyService(session=session, openai_client=openai_client)
            result = service.infer_parent_categories(
                tags=["flask", "django", "html", "pandas", "numpy"],
                title="Python Libraries",
            )

        assert len(result) == 2
        assert result[0]["tag"] == "web-development"
        assert result[0]["original_suggestion"] == "web-development"
        assert result[0]["cluster"] == ["flask", "django", "html"]
        assert result[0]["is_new"] is True
        assert result[0]["matched_existing"] is None

        assert result[1]["tag"] == "data-science"
        assert result[1]["cluster"] == ["pandas", "numpy"]

    def test_matched_existing_tag_used_when_found(self):
        """Service uses existing tag name when similarity match found."""
        session = MagicMock()
        openai_client = MagicMock()
        openai_client.generate_categories.return_value = [
            {"parent": "web-dev", "cluster": ["flask", "django"]},
        ]

        with patch(
            "diigo_tagger.services.tag_hierarchy.TagReconciliationService"
        ) as mock_reconciler_cls:
            mock_reconciler = MagicMock()
            mock_reconciler.match_existing_tags.return_value = [
                {
                    "suggested": "web-dev",
                    "matched": "web-development",
                    "similarity": 0.85,
                    "candidates": [{"name": "web-development", "similarity": 0.85}],
                    "action": "auto_accept",
                },
            ]
            mock_reconciler_cls.return_value = mock_reconciler

            service = TagHierarchyService(session=session, openai_client=openai_client)
            result = service.infer_parent_categories(
                tags=["flask", "django"], title="Frameworks"
            )

        assert len(result) == 1
        assert result[0]["tag"] == "web-development"
        assert result[0]["original_suggestion"] == "web-dev"
        assert result[0]["matched_existing"] == "web-development"
        assert result[0]["similarity"] == 0.85
        assert result[0]["is_new"] is False

    def test_llm_returning_invalid_json_returns_empty(self):
        """Service gracefully handles LLM errors."""
        session = MagicMock()
        openai_client = MagicMock()
        openai_client.generate_categories.side_effect = Exception("JSON parse error")

        service = TagHierarchyService(session=session, openai_client=openai_client)
        result = service.infer_parent_categories(
            tags=["python", "flask"], title="Test"
        )

        assert result == []

    def test_llm_returning_empty_list(self):
        """Service handles LLM returning no categories."""
        session = MagicMock()
        openai_client = MagicMock()
        openai_client.generate_categories.return_value = []

        service = TagHierarchyService(session=session, openai_client=openai_client)
        result = service.infer_parent_categories(
            tags=["python", "flask"], title="Test"
        )

        assert result == []
