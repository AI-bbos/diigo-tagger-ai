# ABOUTME: Unit tests for settings_service module
# ABOUTME: Tests get/set, tag prefixes, defaults, and upsert behaviour using in-memory SQLite

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diigo_tagger.models import Base
from diigo_tagger.services.settings_service import SettingsService


@pytest.fixture
def session():
    """Create an in-memory SQLite session for testing.

    Yields:
        SQLAlchemy Session instance with all tables created.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


class TestSettingsServiceGetSet:
    """Tests for generic get/set operations."""

    def test_get_returns_none_for_missing_key(self, session):
        """Should return None when no default is given for a missing key."""
        service = SettingsService(session)
        assert service.get("nonexistent_key") is None

    def test_get_returns_default_for_missing_key(self, session):
        """Should return the supplied default for a missing key."""
        service = SettingsService(session)
        assert service.get("nonexistent_key", default="fallback") == "fallback"

    def test_set_and_get_round_trip(self, session):
        """Should persist a value and return it on subsequent get."""
        service = SettingsService(session)
        service.set("my_key", "my_value")
        assert service.get("my_key") == "my_value"

    def test_set_upserts_existing_key(self, session):
        """Should overwrite an existing value without creating a duplicate row."""
        service = SettingsService(session)
        service.set("my_key", "first_value")
        service.set("my_key", "second_value")
        assert service.get("my_key") == "second_value"

    def test_set_upsert_does_not_duplicate_rows(self, session):
        """Should keep exactly one row per key after multiple sets."""
        from diigo_tagger.models import Setting

        service = SettingsService(session)
        service.set("unique_key", "v1")
        service.set("unique_key", "v2")
        count = session.query(Setting).filter_by(key="unique_key").count()
        assert count == 1


class TestSettingsServiceTagPrefixes:
    """Tests for tag-prefix helpers."""

    def test_get_tag_prefixes_returns_default_when_not_configured(self, session):
        """Should return default prefixes when none have been stored."""
        service = SettingsService(session)
        assert service.get_tag_prefixes() == ["author:", "reference:"]

    def test_set_and_get_tag_prefixes_round_trip(self, session):
        """Should persist custom prefixes and return them unchanged."""
        service = SettingsService(session)
        prefixes = ["ref:", "type:", "lang:"]
        service.set_tag_prefixes(prefixes)
        assert service.get_tag_prefixes() == prefixes

    def test_set_tag_prefixes_replaces_previous_value(self, session):
        """Should overwrite previously stored prefixes."""
        service = SettingsService(session)
        service.set_tag_prefixes(["old:"])
        service.set_tag_prefixes(["new:", "other:"])
        assert service.get_tag_prefixes() == ["new:", "other:"]

    def test_set_tag_prefixes_stores_as_json(self, session):
        """Should store the prefixes as a JSON-encoded string in the database."""
        from diigo_tagger.models import Setting

        service = SettingsService(session)
        service.set_tag_prefixes(["a:", "b:"])
        row = session.query(Setting).filter_by(key="tag_prefixes").one()
        assert json.loads(row.value) == ["a:", "b:"]
