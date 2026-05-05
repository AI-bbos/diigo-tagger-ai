# ABOUTME: Unit tests for tag similarity matching with confidence tiers
# ABOUTME: Tests match_existing_tags against exact, close, moderate, and no-match scenarios

import pytest
from diigo_tagger.services.tag_reconciliation import TagReconciliationService
from diigo_tagger.models import Tag
from diigo_tagger.db import init_db, get_session


@pytest.fixture
def db_session(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test_tags.db"
    init_db(db_path)
    session = get_session(db_path)
    yield session
    session.close()


@pytest.fixture
def reconciliation_service(db_session):
    """Create reconciliation service with test database."""
    return TagReconciliationService(db_session)


@pytest.fixture
def populated_db(db_session):
    """Populate DB with a known set of existing tags."""
    db_session.add_all([
        Tag(name="python", count=10, source="user"),
        Tag(name="javascript", count=8, source="user"),
        Tag(name="web-development", count=6, source="user"),
        Tag(name="machine-learning", count=5, source="user"),
        Tag(name="database", count=4, source="user"),
    ])
    db_session.commit()
    return db_session


class TestMatchExistingTagsReturnFormat:
    """Test that return values always contain all required keys."""

    def test_returns_list(self, reconciliation_service, populated_db):
        """Should return a list."""
        result = reconciliation_service.match_existing_tags(["python"])
        assert isinstance(result, list)

    def test_result_has_required_keys(self, reconciliation_service, populated_db):
        """Each result dict must contain all required keys."""
        result = reconciliation_service.match_existing_tags(["python"])
        assert len(result) == 1
        item = result[0]
        assert "suggested" in item
        assert "matched" in item
        assert "similarity" in item
        assert "candidates" in item
        assert "action" in item

    def test_suggested_key_contains_original_tag(self, reconciliation_service, populated_db):
        """Suggested key should hold the original input tag."""
        result = reconciliation_service.match_existing_tags(["Python"])
        assert result[0]["suggested"] == "Python"

    def test_candidates_is_list(self, reconciliation_service, populated_db):
        """Candidates must always be a list."""
        result = reconciliation_service.match_existing_tags(["python"])
        assert isinstance(result[0]["candidates"], list)

    def test_action_is_valid_value(self, reconciliation_service, populated_db):
        """Action must be one of the three valid tiers."""
        result = reconciliation_service.match_existing_tags(["python"])
        assert result[0]["action"] in ("auto_accept", "confirm", "new")


class TestMatchExistingTagsExactMatch:
    """Test exact match → auto_accept."""

    def test_exact_match_action(self, reconciliation_service, populated_db):
        """Exact match should return action=auto_accept."""
        result = reconciliation_service.match_existing_tags(["python"])
        assert result[0]["action"] == "auto_accept"

    def test_exact_match_similarity(self, reconciliation_service, populated_db):
        """Exact match should have similarity=1.0."""
        result = reconciliation_service.match_existing_tags(["python"])
        assert result[0]["similarity"] == 1.0

    def test_exact_match_matched_name(self, reconciliation_service, populated_db):
        """Exact match should set matched to the existing tag name."""
        result = reconciliation_service.match_existing_tags(["python"])
        assert result[0]["matched"] == "python"

    def test_exact_match_case_insensitive(self, reconciliation_service, populated_db):
        """Exact match after normalization should also be auto_accept."""
        result = reconciliation_service.match_existing_tags(["Python"])
        assert result[0]["action"] == "auto_accept"
        assert result[0]["similarity"] == 1.0


class TestMatchExistingTagsCloseMatch:
    """Test close (>=0.8) match → auto_accept."""

    def test_close_match_auto_accepts(self, reconciliation_service, populated_db):
        """Close match (>=0.8) should return action=auto_accept."""
        # "java-script" vs "javascript" is a close but not exact match
        result = reconciliation_service.match_existing_tags(["java-script"])
        assert result[0]["action"] == "auto_accept"
        assert result[0]["similarity"] >= 0.8

    def test_close_match_sets_matched(self, reconciliation_service, populated_db):
        """Close match should populate matched with the best existing tag."""
        result = reconciliation_service.match_existing_tags(["java-script"])
        assert result[0]["matched"] == "javascript"


class TestMatchExistingTagsModerateMatch:
    """Test moderate (0.5–<0.8) match → confirm."""

    def test_moderate_match_action(self, reconciliation_service, db_session):
        """Moderate match should return action=confirm."""
        # "database" vs "datab" — similar but not close enough for auto_accept
        db_session.add(Tag(name="database", count=10, source="user"))
        db_session.commit()

        result = reconciliation_service.match_existing_tags(["data"])
        assert result[0]["action"] == "confirm"
        assert 0.5 <= result[0]["similarity"] < 0.8

    def test_moderate_match_has_matched(self, reconciliation_service, db_session):
        """Moderate match should set matched to best existing tag."""
        db_session.add(Tag(name="database", count=10, source="user"))
        db_session.commit()

        result = reconciliation_service.match_existing_tags(["data"])
        assert result[0]["matched"] == "database"


class TestMatchExistingTagsNoMatch:
    """Test below-threshold (<0.5) → new tag."""

    def test_no_match_action(self, reconciliation_service, populated_db):
        """Tag with no similar existing tags should return action=new."""
        result = reconciliation_service.match_existing_tags(["kubernetes"])
        assert result[0]["action"] == "new"

    def test_no_match_similarity(self, reconciliation_service, populated_db):
        """Below-threshold result should have similarity < 0.5."""
        result = reconciliation_service.match_existing_tags(["kubernetes"])
        assert result[0]["similarity"] < 0.5

    def test_no_match_matched_is_none(self, reconciliation_service, populated_db):
        """Below-threshold result should have matched=None."""
        result = reconciliation_service.match_existing_tags(["kubernetes"])
        assert result[0]["matched"] is None

    def test_empty_db_returns_new(self, reconciliation_service, db_session):
        """With no existing tags, all suggestions should be new."""
        result = reconciliation_service.match_existing_tags(["python"])
        assert result[0]["action"] == "new"
        assert result[0]["matched"] is None


class TestMatchExistingTagsCandidates:
    """Test candidates list for multiple matches above 0.65."""

    def test_multiple_candidates_populated(self, reconciliation_service, db_session):
        """When multiple tags score >0.65, candidates list should be populated."""
        # "pythonic" is similar enough to both "python" and "pythons"
        db_session.add_all([
            Tag(name="python", count=10, source="user"),
            Tag(name="pythons", count=5, source="user"),
        ])
        db_session.commit()

        result = reconciliation_service.match_existing_tags(["pythonic"])
        candidates = result[0]["candidates"]
        # Both "python" and "pythons" should appear as candidates (>0.65 similarity)
        assert len(candidates) >= 2

    def test_candidates_are_ranked_by_score(self, reconciliation_service, db_session):
        """Candidates should be ordered highest similarity first."""
        db_session.add_all([
            Tag(name="python", count=10, source="user"),
            Tag(name="pythons", count=5, source="user"),
        ])
        db_session.commit()

        result = reconciliation_service.match_existing_tags(["pythonic"])
        candidates = result[0]["candidates"]
        if len(candidates) >= 2:
            scores = [c["similarity"] for c in candidates]
            assert scores == sorted(scores, reverse=True)

    def test_candidates_have_name_and_similarity(self, reconciliation_service, db_session):
        """Each candidate dict must contain name and similarity keys."""
        db_session.add_all([
            Tag(name="python", count=10, source="user"),
            Tag(name="pythons", count=5, source="user"),
        ])
        db_session.commit()

        result = reconciliation_service.match_existing_tags(["pythonic"])
        for candidate in result[0]["candidates"]:
            assert "name" in candidate
            assert "similarity" in candidate

    def test_single_best_match_no_extra_candidates(self, reconciliation_service, db_session):
        """When only one tag passes 0.65, candidates has just that one entry."""
        db_session.add_all([
            Tag(name="python", count=10, source="user"),
            Tag(name="kubernetes", count=5, source="user"),
        ])
        db_session.commit()

        # "python" is similar to "python", "kubernetes" is not
        result = reconciliation_service.match_existing_tags(["python"])
        candidates = result[0]["candidates"]
        names = [c["name"] for c in candidates]
        assert "kubernetes" not in names


class TestMatchExistingTagsThreshold:
    """Test custom threshold parameter."""

    def test_high_threshold_treats_moderate_as_new(self, reconciliation_service, db_session):
        """With threshold=0.9, a moderate match should become action=new."""
        db_session.add(Tag(name="database", count=10, source="user"))
        db_session.commit()

        # "data" vs "database" scores ~0.67, so threshold=0.9 should make it new
        result = reconciliation_service.match_existing_tags(["data"], threshold=0.9)
        assert result[0]["action"] == "new"

    def test_low_threshold_allows_weak_matches(self, reconciliation_service, db_session):
        """With very low threshold, weaker matches surface as confirm or auto_accept."""
        db_session.add(Tag(name="database", count=10, source="user"))
        db_session.commit()

        result = reconciliation_service.match_existing_tags(["data"], threshold=0.1)
        # Should not be 'new' since similarity is well above 0.1
        assert result[0]["action"] != "new"


class TestMatchExistingTagsMultipleSuggestions:
    """Test processing of multiple suggested tags in one call."""

    def test_multiple_suggestions_all_returned(self, reconciliation_service, populated_db):
        """All suggested tags should appear in the result."""
        suggestions = ["python", "kubernetes", "java-script"]
        result = reconciliation_service.match_existing_tags(suggestions)
        assert len(result) == len(suggestions)

    def test_multiple_suggestions_order_preserved(self, reconciliation_service, populated_db):
        """Results should appear in the same order as suggestions."""
        suggestions = ["python", "kubernetes", "java-script"]
        result = reconciliation_service.match_existing_tags(suggestions)
        for i, suggestion in enumerate(suggestions):
            assert result[i]["suggested"] == suggestion

    def test_multiple_suggestions_independent_results(self, reconciliation_service, populated_db):
        """Each suggestion should be evaluated independently."""
        result = reconciliation_service.match_existing_tags(["python", "kubernetes"])
        python_result = next(r for r in result if r["suggested"] == "python")
        k8s_result = next(r for r in result if r["suggested"] == "kubernetes")
        assert python_result["action"] == "auto_accept"
        assert k8s_result["action"] == "new"
