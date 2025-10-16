# ABOUTME: Database initialization and connection management
# ABOUTME: Handles engine creation, WAL mode setup, SQLite version checks, and session factory

import sqlite3
from pathlib import Path
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker
from platformdirs import user_config_dir

from .models import Base

# Module-level engine cache to avoid creating multiple connection pools
_engine_cache: dict[Path, Engine] = {}


def check_sqlite_version() -> None:
    """
    Ensure SQLite version supports FTS5.

    Raises:
        RuntimeError: If SQLite version < 3.35.0
    """
    version = sqlite3.sqlite_version_info
    if version < (3, 35, 0):
        raise RuntimeError(
            f"SQLite {sqlite3.sqlite_version} is too old. "
            f"FTS5 requires SQLite >= 3.35.0. Please upgrade Python or sqlite3."
        )


def get_db_path(db_path: Path | None = None) -> Path:
    """
    Get database path, using default if not provided.

    Args:
        db_path: Path to SQLite database file. If None, uses default location
                 from platformdirs (~/Library/Application Support/diigo-tagger on macOS)

    Returns:
        Path to database file
    """
    if db_path is None:
        config_dir = Path(user_config_dir("diigo-tagger"))
        config_dir.mkdir(parents=True, exist_ok=True)
        db_path = config_dir / "tags.db"
    else:
        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

    return db_path


def create_db_engine(db_path: Path | None = None) -> Engine:
    """
    Get or create SQLAlchemy engine with SQLite pragmas configured.

    Uses module-level cache to avoid creating multiple connection pools
    for the same database path.

    Args:
        db_path: Path to SQLite database file. If None, uses default location

    Returns:
        SQLAlchemy engine instance (cached)

    Raises:
        RuntimeError: If SQLite version is too old for FTS5
    """
    # Check SQLite version
    check_sqlite_version()

    # Get database path
    db_path = get_db_path(db_path)

    # Return cached engine if it exists
    if db_path in _engine_cache:
        return _engine_cache[db_path]

    # Create new engine
    engine = create_engine(f"sqlite:///{db_path}")

    # Enable WAL mode and foreign keys
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Cache the engine
    _engine_cache[db_path] = engine

    return engine


def init_db(db_path: Path | None = None) -> Engine:
    """
    Initialize database with schema.

    Args:
        db_path: Path to SQLite database file. If None, uses default location
                 from platformdirs (~/Library/Application Support/diigo-tagger on macOS)

    Returns:
        SQLAlchemy engine instance (cached)

    Raises:
        RuntimeError: If SQLite version is too old for FTS5
    """
    engine = create_db_engine(db_path)

    # Create all tables
    Base.metadata.create_all(engine)

    return engine


def get_session(db_path: Path | None = None):
    """
    Get SQLAlchemy session.

    Args:
        db_path: Path to SQLite database file. If None, uses default location

    Returns:
        SQLAlchemy Session instance
    """
    engine = create_db_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()
