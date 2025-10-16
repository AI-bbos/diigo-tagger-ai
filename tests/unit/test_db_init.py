# ABOUTME: Unit tests for database initialization module
# ABOUTME: Tests engine creation, WAL mode, SQLite version checks, and session management

import pytest
import sqlite3
from pathlib import Path
from sqlalchemy import text

from diigo_tagger.db import init_db, get_session, check_sqlite_version


class TestSQLiteVersionCheck:
    """Test SQLite version validation."""

    def test_check_sqlite_version_passes_for_current(self):
        """Should pass for current SQLite version (>= 3.35)."""
        # This should not raise
        check_sqlite_version()

    def test_sqlite_version_is_sufficient(self):
        """Verify SQLite version supports FTS5."""
        version = sqlite3.sqlite_version_info
        assert version >= (3, 35, 0), f"SQLite {sqlite3.sqlite_version} too old for FTS5"


class TestDatabaseInitialization:
    """Test database engine initialization."""

    def test_init_db_creates_directory(self, tmp_path):
        """Should create parent directory if it doesn't exist."""
        db_path = tmp_path / "subdir" / "test.db"
        assert not db_path.parent.exists()

        engine = init_db(db_path)

        assert db_path.parent.exists()
        assert db_path.exists()
        engine.dispose()

    def test_init_db_returns_engine(self, tmp_path):
        """Should return SQLAlchemy engine."""
        db_path = tmp_path / "test.db"
        engine = init_db(db_path)

        assert engine is not None
        assert str(engine.url).startswith("sqlite:///")
        engine.dispose()

    def test_init_db_creates_tables(self, tmp_path):
        """Should create tables from models."""
        db_path = tmp_path / "test.db"
        engine = init_db(db_path)

        # Verify tags table exists
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tags'"
            ))
            assert result.fetchone() is not None

        engine.dispose()

    def test_init_db_enables_wal_mode(self, tmp_path):
        """Should enable WAL mode for better concurrency."""
        db_path = tmp_path / "test.db"
        engine = init_db(db_path)

        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode"))
            mode = result.fetchone()[0]
            assert mode.lower() == "wal"

        engine.dispose()

    def test_init_db_enables_foreign_keys(self, tmp_path):
        """Should enable foreign key constraints."""
        db_path = tmp_path / "test.db"
        engine = init_db(db_path)

        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys"))
            enabled = result.fetchone()[0]
            assert enabled == 1

        engine.dispose()


class TestSessionManagement:
    """Test session creation and management."""

    def test_get_session_returns_session(self, tmp_path):
        """Should return SQLAlchemy session."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        session = get_session(db_path)

        assert session is not None
        session.close()

    def test_session_can_query_database(self, tmp_path):
        """Should be able to execute queries."""
        from diigo_tagger.models import Tag

        db_path = tmp_path / "test.db"
        init_db(db_path)
        session = get_session(db_path)

        # Create a tag
        tag = Tag(name="test-tag", count=1, source="user")
        session.add(tag)
        session.commit()

        # Query it back
        result = session.query(Tag).filter(Tag.name == "test-tag").first()
        assert result is not None
        assert result.name == "test-tag"

        session.close()
