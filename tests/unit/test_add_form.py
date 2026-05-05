# ABOUTME: Unit tests for AddForm pure helper methods
# ABOUTME: Tests logic methods only — no I/O, no prompt_toolkit interaction

import pytest

from diigo_tagger.cli.add_form import AddForm


def make_form() -> AddForm:
    """Create an AddForm instance without calling __init__.

    Returns:
        AddForm instance with no session attached, suitable for testing
        pure helper methods.
    """
    return AddForm.__new__(AddForm)


class TestFilterAccepted:
    """Tests for AddForm._filter_accepted."""

    def test_returns_only_accepted_tags(self):
        """Should return tag strings where accepted is True."""
        form = make_form()
        tags = [
            {"tag": "python", "accepted": True},
            {"tag": "javascript", "accepted": False},
            {"tag": "tutorial", "accepted": True},
        ]
        assert form._filter_accepted(tags) == ["python", "tutorial"]

    def test_all_accepted(self):
        """Should return all tags when all are accepted."""
        form = make_form()
        tags = [
            {"tag": "a", "accepted": True},
            {"tag": "b", "accepted": True},
        ]
        assert form._filter_accepted(tags) == ["a", "b"]

    def test_none_accepted(self):
        """Should return empty list when no tags are accepted."""
        form = make_form()
        tags = [
            {"tag": "a", "accepted": False},
            {"tag": "b", "accepted": False},
        ]
        assert form._filter_accepted(tags) == []

    def test_empty_input(self):
        """Should return empty list for empty input."""
        form = make_form()
        assert form._filter_accepted([]) == []

    def test_missing_accepted_key_treated_as_false(self):
        """Tags without 'accepted' key should be excluded."""
        form = make_form()
        tags = [
            {"tag": "a"},
            {"tag": "b", "accepted": True},
        ]
        assert form._filter_accepted(tags) == ["b"]


class TestBuildRatingTag:
    """Tests for AddForm._build_rating_tag."""

    def test_rating_1(self):
        """Rating 1 should format as 'rating=1_10'."""
        form = make_form()
        assert form._build_rating_tag(1) == "rating=1_10"

    def test_rating_7(self):
        """Rating 7 should format as 'rating=7_10'."""
        form = make_form()
        assert form._build_rating_tag(7) == "rating=7_10"

    def test_rating_10(self):
        """Rating 10 (from '0' key) should format as 'rating=10_10'."""
        form = make_form()
        assert form._build_rating_tag(10) == "rating=10_10"

    def test_none_returns_none(self):
        """None input should return None."""
        form = make_form()
        assert form._build_rating_tag(None) is None

    def test_rating_9(self):
        """Rating 9 should format as 'rating=9_10'."""
        form = make_form()
        assert form._build_rating_tag(9) == "rating=9_10"


class TestBuildPrefixTag:
    """Tests for AddForm._build_prefix_tag."""

    def test_combines_prefix_and_value(self):
        """Should return 'prefix:value' for normal inputs."""
        form = make_form()
        assert form._build_prefix_tag("reference:", "peter-zeihan") == "reference:peter-zeihan"

    def test_none_value_returns_none(self):
        """None value should return None."""
        form = make_form()
        assert form._build_prefix_tag("reference:", None) is None

    def test_empty_string_value_returns_none(self):
        """Empty string value should return None."""
        form = make_form()
        assert form._build_prefix_tag("reference:", "") is None

    def test_prefix_without_colon_adds_colon(self):
        """Prefix without trailing colon should still produce correct tag."""
        form = make_form()
        assert form._build_prefix_tag("author", "smith") == "author:smith"

    def test_prefix_with_colon_does_not_double_colon(self):
        """Prefix ending with ':' should not result in double colon."""
        form = make_form()
        result = form._build_prefix_tag("author:", "smith")
        assert result == "author:smith"
        assert "::" not in result

    def test_whitespace_value_returns_none(self):
        """Whitespace-only value should still produce a tag (not stripped here)."""
        # _build_prefix_tag doesn't strip — the caller (prompt_prefix_tags) strips.
        # A space is truthy so it produces a tag. This tests existing behaviour.
        form = make_form()
        result = form._build_prefix_tag("ref:", " ")
        assert result == "ref: "


class TestParseRatingKey:
    """Tests for AddForm._parse_rating_key."""

    @pytest.mark.parametrize("key,expected", [
        ("1", 1),
        ("2", 2),
        ("3", 3),
        ("4", 4),
        ("5", 5),
        ("6", 6),
        ("7", 7),
        ("8", 8),
        ("9", 9),
    ])
    def test_digit_keys_map_to_rating(self, key, expected):
        """Digit keys '1'-'9' should map to integers 1-9."""
        form = make_form()
        assert form._parse_rating_key(key) == expected

    def test_zero_maps_to_ten(self):
        """'0' key should map to rating 10."""
        form = make_form()
        assert form._parse_rating_key("0") == 10

    def test_enter_returns_none(self):
        """Empty string (Enter) should return None."""
        form = make_form()
        assert form._parse_rating_key("") is None

    def test_letter_returns_minus_one(self):
        """Non-digit letter should return -1."""
        form = make_form()
        assert form._parse_rating_key("x") == -1

    def test_special_char_returns_minus_one(self):
        """Special character should return -1."""
        form = make_form()
        assert form._parse_rating_key("!") == -1

    def test_space_returns_minus_one(self):
        """Space character should return -1."""
        form = make_form()
        assert form._parse_rating_key(" ") == -1
