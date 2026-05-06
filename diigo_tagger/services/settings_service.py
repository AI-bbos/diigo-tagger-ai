# ABOUTME: Service for reading and writing application settings from the database
# ABOUTME: Provides typed helpers for tag-prefix config on top of a generic key-value store

import json
from typing import List, Optional

from sqlalchemy.orm import Session

from ..models import Setting

_TAG_PREFIXES_KEY = "tag_prefixes"
_DEFAULT_TAG_PREFIXES = ["author:", "reference:"]


class SettingsService:
    """Service for managing application settings stored in the database.

    Wraps the ``settings`` key-value table with typed helpers for common
    configuration values.  All writes are committed immediately so callers do
    not need to manage the transaction themselves.
    """

    def __init__(self, session: Session) -> None:
        """Initialise the service with a database session.

        Args:
            session: SQLAlchemy session used for all database operations.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Generic key-value API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Return the stored value for *key*, or *default* if absent.

        Args:
            key: Setting name.
            default: Value returned when the key does not exist.

        Returns:
            The stored string value, or *default*.
        """
        row = self.session.query(Setting).filter_by(key=key).first()
        if row is None:
            return default
        return row.value

    def set(self, key: str, value: str) -> None:
        """Persist *value* under *key*, creating or updating the row.

        Args:
            key: Setting name.
            value: String value to store.
        """
        row = self.session.query(Setting).filter_by(key=key).first()
        if row is None:
            row = Setting(key=key, value=value)
            self.session.add(row)
        else:
            row.value = value
        self.session.commit()

    # ------------------------------------------------------------------
    # Tag-prefix helpers
    # ------------------------------------------------------------------

    def get_tag_prefixes(self) -> List[str]:
        """Return the configured tag prefixes.

        When no prefixes have been stored the default ``["reference:"]`` is
        returned so callers always receive a non-empty list.

        Returns:
            List of prefix strings (e.g. ``["reference:", "type:"]``).
        """
        raw = self.get(_TAG_PREFIXES_KEY)
        if raw is None:
            return list(_DEFAULT_TAG_PREFIXES)
        return json.loads(raw)

    def set_tag_prefixes(self, prefixes: List[str]) -> None:
        """Store the tag prefixes, replacing any previously saved value.

        Args:
            prefixes: List of prefix strings to persist.
        """
        self.set(_TAG_PREFIXES_KEY, json.dumps(prefixes))
