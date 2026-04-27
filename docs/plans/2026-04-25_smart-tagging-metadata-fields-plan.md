# Smart Tagging and Metadata Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add auto-detected metadata tags, rating, configurable prefix tag autocomplete, and tag similarity matching to the bookmark add flow (CLI + web UI).

**Architecture:** New `MetadataTagDetector` service detects `format:` and `source:` tags from URLs. Tag similarity matching in `TagReconciliationService` deduplicates LLM suggestions against existing tags. A `settings` table stores configurable tag prefixes. CLI uses `prompt_toolkit` for interactive form. Web UI extends existing HTMX templates.

**Tech Stack:** Python 3.10+, SQLAlchemy, Alembic, prompt_toolkit, Click, FastAPI, HTMX, difflib

**Spec:** `docs/plans/2026-04-25_smart-tagging-metadata-fields.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `diigo_tagger/models.py` | Add `Setting` ORM model |
| `alembic/versions/003_add_settings_table.py` | Migration for settings table |
| `diigo_tagger/services/metadata_tag_detector.py` | Detect `format:` and `source:` tags from URL/metadata |
| `diigo_tagger/services/tag_reconciliation.py` | Add `match_existing_tags()` for similarity dedup |
| `diigo_tagger/services/settings_service.py` | CRUD for settings table (tag prefixes) |
| `diigo_tagger/cli/add_form.py` | prompt_toolkit interactive add-bookmark form |
| `diigo_tagger/cli/main.py` | Wire `add` command to new form |
| `diigo_tagger/api/routes/bookmarks.py` | Tag autocomplete endpoint |
| `diigo_tagger/api/routes/settings.py` | Settings API endpoints |
| `diigo_tagger/web/templates/add_bookmark.html` | Detected tags, rating widget, prefix inputs |
| `tests/unit/test_metadata_tag_detector.py` | Detector tests |
| `tests/unit/test_tag_similarity.py` | Similarity matching tests |
| `tests/unit/test_settings_service.py` | Settings CRUD tests |
| `tests/unit/test_add_form.py` | CLI form tests |
| `pyproject.toml` | Add prompt_toolkit dependency |

---

### Task 1: Add Settings Model and Migration

**Files:**
- Modify: `diigo_tagger/models.py`
- Create: `alembic/versions/003_add_settings_table.py`
- Create: `diigo_tagger/services/settings_service.py`
- Create: `tests/unit/test_settings_service.py`

- [ ] **Step 1: Write failing tests for SettingsService**

Create `tests/unit/test_settings_service.py`:

```python
# ABOUTME: Tests for settings service CRUD operations
# ABOUTME: Verifies tag prefix storage and retrieval from database

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from diigo_tagger.models import Base, Setting
from diigo_tagger.services.settings_service import SettingsService


@pytest.fixture
def db_session():
    """Create in-memory database with settings table."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


class TestSettingsService:
    """Test settings CRUD operations."""

    def test_get_tag_prefixes_default(self, db_session):
        """Should return default prefixes when none configured."""
        service = SettingsService(db_session)
        prefixes = service.get_tag_prefixes()
        assert prefixes == ["reference:"]

    def test_set_tag_prefixes(self, db_session):
        """Should store and retrieve custom prefixes."""
        service = SettingsService(db_session)
        service.set_tag_prefixes(["reference:", "project:", "topic:"])
        prefixes = service.get_tag_prefixes()
        assert prefixes == ["reference:", "project:", "topic:"]

    def test_get_setting(self, db_session):
        """Should get a setting by key."""
        service = SettingsService(db_session)
        service.set("test_key", "test_value")
        assert service.get("test_key") == "test_value"

    def test_get_setting_default(self, db_session):
        """Should return default when key not found."""
        service = SettingsService(db_session)
        assert service.get("nonexistent", "fallback") == "fallback"

    def test_set_setting_upsert(self, db_session):
        """Should update existing setting."""
        service = SettingsService(db_session)
        service.set("key", "value1")
        service.set("key", "value2")
        assert service.get("key") == "value2"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/unit/test_settings_service.py -v`
Expected: FAIL — `Setting` model and `SettingsService` don't exist

- [ ] **Step 3: Add Setting model to models.py**

Add to `diigo_tagger/models.py` after the `Bookmark` class:

```python
class Setting(Base):
    """
    Key-value settings stored in the database.

    Stores application configuration like tag prefixes, user preferences,
    and other persistent settings.
    """

    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value[:50]}')>"
```

- [ ] **Step 4: Create SettingsService**

Create `diigo_tagger/services/settings_service.py`:

```python
# ABOUTME: Settings service for reading and writing application configuration
# ABOUTME: Manages tag prefixes and other persistent settings stored in SQLite

import json
from typing import Optional, List
from sqlalchemy.orm import Session

from ..models import Setting


DEFAULT_TAG_PREFIXES = ["reference:"]


class SettingsService:
    """
    Service for application settings stored in the database.

    Provides typed accessors for known settings (like tag prefixes)
    and generic get/set for arbitrary key-value pairs.
    """

    def __init__(self, session: Session):
        """
        Initialize settings service.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a setting value by key.

        Args:
            key: Setting key
            default: Value to return if key not found

        Returns:
            Setting value, or default if not found
        """
        setting = self.session.query(Setting).filter_by(key=key).first()
        if setting is None:
            return default
        return setting.value

    def set(self, key: str, value: str) -> None:
        """
        Set a setting value, creating or updating as needed.

        Args:
            key: Setting key
            value: Setting value
        """
        setting = self.session.query(Setting).filter_by(key=key).first()
        if setting is None:
            setting = Setting(key=key, value=value)
            self.session.add(setting)
        else:
            setting.value = value
        self.session.flush()

    def get_tag_prefixes(self) -> List[str]:
        """
        Get configured tag prefixes for autocomplete prompts.

        Returns:
            List of prefix strings (e.g., ["reference:", "project:"])
        """
        raw = self.get("tag_prefixes")
        if raw is None:
            return list(DEFAULT_TAG_PREFIXES)
        return json.loads(raw)

    def set_tag_prefixes(self, prefixes: List[str]) -> None:
        """
        Set tag prefixes for autocomplete prompts.

        Args:
            prefixes: List of prefix strings
        """
        self.set("tag_prefixes", json.dumps(prefixes))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_settings_service.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Create Alembic migration**

Run: `poetry run alembic revision -m "add settings table"`

Then edit the generated migration file to contain:

```python
def upgrade():
    op.create_table(
        'settings',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('key')
    )
    # Insert default tag prefixes
    op.execute("INSERT INTO settings (key, value) VALUES ('tag_prefixes', '[\"reference:\"]')")


def downgrade():
    op.drop_table('settings')
```

- [ ] **Step 7: Commit**

```bash
git add diigo_tagger/models.py diigo_tagger/services/settings_service.py tests/unit/test_settings_service.py alembic/versions/
git commit -m "feat: add settings table and service for tag prefix config

Stores configurable tag prefixes in SQLite settings table.
Default prefix: reference:

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: MetadataTagDetector Service

**Files:**
- Create: `diigo_tagger/services/metadata_tag_detector.py`
- Create: `tests/unit/test_metadata_tag_detector.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_metadata_tag_detector.py`:

```python
# ABOUTME: Tests for auto-detection of format: and source: tags from URLs
# ABOUTME: Verifies URL pattern matching and metadata-based content type detection

import pytest
from diigo_tagger.services.metadata_tag_detector import MetadataTagDetector


class TestSourceDetection:
    """Test source: tag detection from URL domains."""

    def test_youtube_source(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://www.youtube.com/watch?v=abc123", {})
        source_tags = [t for t in tags if t["type"] == "source"]
        assert len(source_tags) == 1
        assert source_tags[0]["tag"] == "source:youtube.com"

    def test_github_source(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://github.com/user/repo", {})
        source_tags = [t for t in tags if t["type"] == "source"]
        assert source_tags[0]["tag"] == "source:github.com"

    def test_subdomain_stripped(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://blog.example.com/post", {})
        source_tags = [t for t in tags if t["type"] == "source"]
        assert source_tags[0]["tag"] == "source:example.com"

    def test_country_tld_preserved(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://www.bbc.co.uk/news", {})
        source_tags = [t for t in tags if t["type"] == "source"]
        assert source_tags[0]["tag"] == "source:bbc.co.uk"


class TestFormatDetection:
    """Test format: tag detection from URL patterns and metadata."""

    def test_youtube_video(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://www.youtube.com/watch?v=abc", {"content_type": "youtube"})
        format_tags = [t for t in tags if t["type"] == "format"]
        assert any(t["tag"] == "format:video" for t in format_tags)

    def test_vimeo_video(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://vimeo.com/123456", {})
        format_tags = [t for t in tags if t["type"] == "format"]
        assert any(t["tag"] == "format:video" for t in format_tags)

    def test_pdf_format(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://example.com/paper.pdf", {})
        format_tags = [t for t in tags if t["type"] == "format"]
        assert any(t["tag"] == "format:pdf" for t in format_tags)

    def test_github_repo(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://github.com/user/repo", {})
        format_tags = [t for t in tags if t["type"] == "format"]
        assert any(t["tag"] == "format:repository" for t in format_tags)

    def test_github_blob_not_repo(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://github.com/user/repo/blob/main/README.md", {})
        format_tags = [t for t in tags if t["type"] == "format"]
        assert not any(t["tag"] == "format:repository" for t in format_tags)

    def test_article_from_metadata(self):
        detector = MetadataTagDetector()
        metadata = {"content_type": "webpage", "has_article_tag": True}
        tags = detector.detect("https://example.com/blog/post", metadata)
        format_tags = [t for t in tags if t["type"] == "format"]
        assert any(t["tag"] == "format:article" for t in format_tags)

    def test_plain_url_no_format(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://example.com/", {})
        format_tags = [t for t in tags if t["type"] == "format"]
        assert len(format_tags) == 0


class TestDetectReturnFormat:
    """Test the return format of detect()."""

    def test_returns_list_of_dicts(self):
        detector = MetadataTagDetector()
        tags = detector.detect("https://www.youtube.com/watch?v=abc", {"content_type": "youtube"})
        assert isinstance(tags, list)
        for tag in tags:
            assert "tag" in tag
            assert "type" in tag
            assert tag["type"] in ("format", "source")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/unit/test_metadata_tag_detector.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement MetadataTagDetector**

Create `diigo_tagger/services/metadata_tag_detector.py`:

```python
# ABOUTME: Detects format: and source: tags from URL patterns and page metadata
# ABOUTME: Used during bookmark creation to suggest metadata tags separately from LLM tags

import re
from urllib.parse import urlparse
from typing import List, Dict


# Video hosting domains
VIDEO_DOMAINS = {
    "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
    "twitch.tv", "rumble.com",
}

# Known country-code second-level domains (e.g., .co.uk, .com.au)
COUNTRY_SLDS = {"co", "com", "org", "net", "ac", "gov", "edu"}

# GitHub/GitLab repo URL pattern: /<user>/<repo> with no deeper path segments
# that indicate a file view (blob, tree, raw, etc.)
REPO_FILE_SEGMENTS = {"blob", "tree", "raw", "commit", "commits", "issues", "pull", "actions", "wiki"}


class MetadataTagDetector:
    """
    Detect format: and source: tags from a URL and its fetched metadata.

    Returns a list of detected tag dicts, each with 'tag' and 'type' keys.
    These are presented separately from LLM-generated content tags.
    """

    def detect(self, url: str, metadata: dict) -> List[Dict[str, str]]:
        """
        Detect metadata tags from URL and fetched metadata.

        Args:
            url: Bookmark URL
            metadata: Dict from MetadataFetcher (may include content_type,
                      has_article_tag, etc.)

        Returns:
            List of dicts with keys:
            - tag: Full tag string (e.g., "format:video", "source:youtube.com")
            - type: Tag category ("format" or "source")
        """
        tags = []
        tags.extend(self._detect_source(url))
        tags.extend(self._detect_format(url, metadata))
        return tags

    def _detect_source(self, url: str) -> List[Dict[str, str]]:
        """Extract source: tag from URL domain."""
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return []

        domain = self._extract_registered_domain(hostname)
        if not domain:
            return []

        return [{"tag": f"source:{domain}", "type": "source"}]

    def _extract_registered_domain(self, hostname: str) -> str:
        """
        Extract the registered domain from a hostname.

        Handles country-code SLDs like .co.uk, .com.au.
        Strips www and other subdomains.

        Args:
            hostname: Full hostname (e.g., "www.bbc.co.uk")

        Returns:
            Registered domain (e.g., "bbc.co.uk")
        """
        parts = hostname.lower().split(".")
        if len(parts) <= 2:
            return hostname.lower()

        # Check for country-code SLD pattern (e.g., co.uk, com.au)
        if len(parts) >= 3 and parts[-2] in COUNTRY_SLDS and len(parts[-1]) == 2:
            return ".".join(parts[-3:])

        return ".".join(parts[-2:])

    def _detect_format(self, url: str, metadata: dict) -> List[Dict[str, str]]:
        """Detect format: tag from URL patterns and metadata."""
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        path = parsed.path.lower()
        domain = self._extract_registered_domain(hostname)

        # Video sites
        if domain in VIDEO_DOMAINS:
            return [{"tag": "format:video", "type": "format"}]

        # PDF
        if path.endswith(".pdf"):
            return [{"tag": "format:pdf", "type": "format"}]

        # GitHub/GitLab repository (but not file/blob views)
        if domain in ("github.com", "gitlab.com"):
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(path_parts) == 2 and path_parts[1] not in REPO_FILE_SEGMENTS:
                return [{"tag": "format:repository", "type": "format"}]
            if len(path_parts) > 2 and path_parts[2] in REPO_FILE_SEGMENTS:
                return []
            if len(path_parts) == 2:
                return [{"tag": "format:repository", "type": "format"}]

        # Article detection from metadata
        content_type = metadata.get("content_type", "")
        has_article = metadata.get("has_article_tag", False)
        if has_article or content_type == "article":
            return [{"tag": "format:article", "type": "format"}]

        return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_metadata_tag_detector.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add diigo_tagger/services/metadata_tag_detector.py tests/unit/test_metadata_tag_detector.py
git commit -m "feat: add MetadataTagDetector for format: and source: tags

Detects format:video, format:pdf, format:repository, format:article
from URL patterns. Extracts source: from registered domain.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Tag Similarity Matching

**Files:**
- Modify: `diigo_tagger/services/tag_reconciliation.py`
- Create: `tests/unit/test_tag_similarity.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_tag_similarity.py`:

```python
# ABOUTME: Tests for tag similarity matching against existing database tags
# ABOUTME: Verifies that near-duplicate LLM suggestions get mapped to existing tags

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from diigo_tagger.models import Base, Tag
from diigo_tagger.services.tag_reconciliation import TagReconciliationService


@pytest.fixture
def db_session():
    """Create in-memory database with some existing tags."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    # Add existing tags
    for name in ["javascript", "python", "machine-learning", "web-development", "react"]:
        session.add(Tag(name=name, count=10, source="user"))
    session.commit()

    yield session
    session.close()


class TestMatchExistingTags:
    """Test matching suggested tags against existing ones."""

    def test_exact_match(self, db_session):
        """Exact match should return the existing tag."""
        service = TagReconciliationService(db_session)
        results = service.match_existing_tags(["javascript"])
        assert results[0]["matched"] == "javascript"
        assert results[0]["similarity"] == 1.0

    def test_close_match(self, db_session):
        """Similar tag should map to existing one."""
        service = TagReconciliationService(db_session)
        results = service.match_existing_tags(["java-script"])
        assert results[0]["matched"] == "javascript"
        assert results[0]["similarity"] >= 0.8

    def test_no_match(self, db_session):
        """Dissimilar tag should not match."""
        service = TagReconciliationService(db_session)
        results = service.match_existing_tags(["kubernetes"])
        assert results[0]["matched"] is None
        assert results[0]["similarity"] < 0.8

    def test_multiple_suggestions(self, db_session):
        """Should process multiple suggestions."""
        service = TagReconciliationService(db_session)
        results = service.match_existing_tags(["javascript", "kubernetes", "python3"])
        assert len(results) == 3
        assert results[0]["matched"] == "javascript"
        assert results[1]["matched"] is None
        assert results[2]["suggested"] == "python3"

    def test_custom_threshold(self, db_session):
        """Should respect custom threshold."""
        service = TagReconciliationService(db_session)
        results_strict = service.match_existing_tags(["python3"], threshold=0.95)
        results_loose = service.match_existing_tags(["python3"], threshold=0.5)
        # Strict should not match, loose might
        assert results_strict[0]["matched"] is None

    def test_return_format(self, db_session):
        """Should return correct dict format."""
        service = TagReconciliationService(db_session)
        results = service.match_existing_tags(["javascript"])
        result = results[0]
        assert "suggested" in result
        assert "matched" in result
        assert "similarity" in result
        assert result["suggested"] == "javascript"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/unit/test_tag_similarity.py -v`
Expected: FAIL — `match_existing_tags` doesn't exist

- [ ] **Step 3: Add match_existing_tags to TagReconciliationService**

Add to `diigo_tagger/services/tag_reconciliation.py`, after the `search_tags` method:

```python
    def match_existing_tags(
        self, suggested_tags: List[str], threshold: float = 0.8
    ) -> List[dict]:
        """
        Match suggested tags against existing tags in the database.

        Uses string similarity to find near-duplicates. Tags above the
        threshold get mapped to the existing tag name.

        Args:
            suggested_tags: List of tag names to check
            threshold: Minimum similarity score (0.0-1.0) to count as a match

        Returns:
            List of dicts with keys:
            - suggested: Original suggested tag name
            - matched: Existing tag name if similar enough, None otherwise
            - similarity: Highest similarity score found (0.0-1.0)
        """
        from difflib import SequenceMatcher

        all_existing = [
            tag.name for tag in self.session.query(Tag).all()
        ]

        results = []
        for suggested in suggested_tags:
            best_match = None
            best_score = 0.0

            normalized = self.normalize_tag(suggested)

            for existing in all_existing:
                score = SequenceMatcher(None, normalized, existing).ratio()
                if score > best_score:
                    best_score = score
                    best_match = existing

            results.append({
                "suggested": suggested,
                "matched": best_match if best_score >= threshold else None,
                "similarity": best_score,
            })

        return results
```

Also add `List` to the typing imports if not already there (it should be).

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_tag_similarity.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add diigo_tagger/services/tag_reconciliation.py tests/unit/test_tag_similarity.py
git commit -m "feat: add tag similarity matching for LLM suggestion dedup

Matches suggested tags against existing DB tags using string similarity.
Tags >80% similar get mapped to existing names.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Add prompt_toolkit Dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add prompt_toolkit**

Run: `poetry add prompt_toolkit`

- [ ] **Step 2: Verify installation**

Run: `poetry run python -c "import prompt_toolkit; print(prompt_toolkit.__version__)"`
Expected: prints version number

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "build: add prompt_toolkit dependency for interactive CLI forms

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Interactive CLI Add Form

**Files:**
- Create: `diigo_tagger/cli/add_form.py`
- Create: `tests/unit/test_add_form.py`
- Modify: `diigo_tagger/cli/main.py`

- [ ] **Step 1: Write failing tests for AddForm**

Create `tests/unit/test_add_form.py`:

```python
# ABOUTME: Tests for the interactive CLI add-bookmark form
# ABOUTME: Tests tag acceptance, rating input, and prefix autocomplete logic

import pytest
from unittest.mock import Mock, patch, MagicMock
from diigo_tagger.cli.add_form import AddForm


class TestAddFormTagProcessing:
    """Test tag processing logic (not interactive prompts)."""

    def test_filter_accepted_tags(self):
        """Should return only accepted tags."""
        form = AddForm.__new__(AddForm)
        tags = [
            {"tag": "python", "accepted": True},
            {"tag": "java", "accepted": False},
            {"tag": "web", "accepted": True},
        ]
        result = form._filter_accepted(tags)
        assert result == ["python", "web"]

    def test_build_rating_tag(self):
        """Should format rating as rating=x_10."""
        form = AddForm.__new__(AddForm)
        assert form._build_rating_tag(7) == "rating=7_10"
        assert form._build_rating_tag(10) == "rating=10_10"
        assert form._build_rating_tag(None) is None

    def test_build_prefix_tag(self):
        """Should combine prefix with value."""
        form = AddForm.__new__(AddForm)
        assert form._build_prefix_tag("reference:", "peter-zeihan") == "reference:peter-zeihan"
        assert form._build_prefix_tag("reference:", "") is None
        assert form._build_prefix_tag("reference:", None) is None


class TestAddFormRatingParse:
    """Test rating input parsing."""

    def test_parse_digit_keys(self):
        """Should map digit keys to ratings."""
        form = AddForm.__new__(AddForm)
        assert form._parse_rating_key("1") == 1
        assert form._parse_rating_key("9") == 9
        assert form._parse_rating_key("0") == 10

    def test_parse_enter_skips(self):
        """Enter should return None (skip)."""
        form = AddForm.__new__(AddForm)
        assert form._parse_rating_key("\r") is None
        assert form._parse_rating_key("\n") is None

    def test_parse_invalid_ignored(self):
        """Non-digit keys should return sentinel for retry."""
        form = AddForm.__new__(AddForm)
        assert form._parse_rating_key("a") == -1
        assert form._parse_rating_key(" ") == -1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/unit/test_add_form.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement AddForm**

Create `diigo_tagger/cli/add_form.py`:

```python
# ABOUTME: Interactive CLI form for adding bookmarks with prompt_toolkit
# ABOUTME: Handles tag acceptance, rating input, and prefix tag autocomplete

from typing import List, Dict, Optional, Tuple
import click

from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.keys import Keys
from prompt_toolkit.key_binding import KeyBindings


class AddForm:
    """
    Interactive form for the CLI add-bookmark workflow.

    Manages the multi-step form flow:
    1. Title/description confirmation
    2. LLM tag suggestions (accept/reject)
    3. Detected metadata tags (accept/reject)
    4. Prefix tag prompts with autocomplete
    5. Rating (single keypress)
    """

    def __init__(self, session):
        """
        Initialize the form.

        Args:
            session: SQLAlchemy database session (for tag autocomplete lookups)
        """
        self.session = session

    def prompt_title(self, default: str) -> str:
        """
        Prompt for bookmark title with pre-filled default.

        Args:
            default: Pre-filled title from metadata

        Returns:
            Confirmed or edited title
        """
        click.echo(f"\nTitle: {default}")
        edited = pt_prompt("  Edit (enter to keep): ", default="")
        return edited.strip() if edited.strip() else default

    def prompt_description(self, default: str) -> str:
        """
        Prompt for bookmark description with pre-filled default.

        Args:
            default: Pre-filled description from metadata

        Returns:
            Confirmed or edited description
        """
        short = default[:80] + "..." if len(default) > 80 else default
        click.echo(f"\nDescription: {short}")
        edited = pt_prompt("  Edit (enter to keep): ", default="")
        return edited.strip() if edited.strip() else default

    def prompt_tag_list(self, tags: List[str], label: str) -> List[str]:
        """
        Present a list of tags for accept/reject.

        Args:
            tags: List of tag name strings
            label: Section label (e.g., "LLM Suggestions", "Detected Tags")

        Returns:
            List of accepted tag names
        """
        if not tags:
            return []

        click.echo(f"\n{label}:")
        accepted = []
        for tag in tags:
            response = pt_prompt(f"  {tag} — keep? (enter=yes, n=no): ", default="")
            if response.strip().lower() != "n":
                accepted.append(tag)
        return accepted

    def prompt_metadata_tags(self, detected: List[Dict[str, str]]) -> List[str]:
        """
        Present detected metadata tags for accept/reject.

        Args:
            detected: List of dicts from MetadataTagDetector with 'tag' and 'type' keys

        Returns:
            List of accepted tag strings
        """
        tag_names = [d["tag"] for d in detected]
        return self.prompt_tag_list(tag_names, "Detected metadata tags")

    def prompt_prefix_tags(self, prefixes: List[str]) -> List[str]:
        """
        Prompt for each configured prefix tag with autocomplete.

        Args:
            prefixes: List of prefix strings (e.g., ["reference:", "project:"])

        Returns:
            List of complete prefix tags (e.g., ["reference:peter-zeihan"])
        """
        from ..models import Tag

        result = []
        for prefix in prefixes:
            # Get existing tags with this prefix for autocomplete
            existing = (
                self.session.query(Tag.name)
                .filter(Tag.name.like(f"{prefix}%"))
                .all()
            )
            completions = [t[0] for t in existing]
            # Strip prefix for display in completer
            values = [t[0][len(prefix):] for t in existing]

            completer = WordCompleter(values, ignore_case=True) if values else None

            click.echo(f"\n{prefix}")
            if values:
                click.echo(f"  Existing: {', '.join(values[:10])}")

            value = pt_prompt(
                f"  Value (enter to skip): ",
                completer=completer,
                default="",
            )

            tag = self._build_prefix_tag(prefix, value.strip())
            if tag:
                result.append(tag)

        return result

    def prompt_rating(self) -> Optional[str]:
        """
        Prompt for rating with single keypress.

        Returns:
            Rating tag string (e.g., "rating=7_10") or None if skipped
        """
        click.echo("\nRate? (1-9, 0=10, enter to skip)")

        while True:
            key = pt_prompt("  Rating: ", default="")
            if not key:
                return None

            rating = self._parse_rating_key(key[0] if key else "\r")
            if rating == -1:
                click.echo("  Invalid — press 1-9, 0 for 10, or enter to skip")
                continue
            if rating is None:
                return None
            return self._build_rating_tag(rating)

    def _filter_accepted(self, tags: List[Dict]) -> List[str]:
        """
        Filter tag dicts to only accepted ones.

        Args:
            tags: List of dicts with 'tag' and 'accepted' keys

        Returns:
            List of accepted tag name strings
        """
        return [t["tag"] for t in tags if t.get("accepted")]

    def _build_rating_tag(self, rating: Optional[int]) -> Optional[str]:
        """
        Build rating tag string.

        Args:
            rating: Rating value 1-10, or None

        Returns:
            Tag string like "rating=7_10", or None
        """
        if rating is None:
            return None
        return f"rating={rating}_10"

    def _build_prefix_tag(self, prefix: str, value: Optional[str]) -> Optional[str]:
        """
        Combine prefix with value to form a complete tag.

        Args:
            prefix: Tag prefix (e.g., "reference:")
            value: User input value

        Returns:
            Complete tag (e.g., "reference:peter-zeihan"), or None if empty
        """
        if not value:
            return None
        return f"{prefix}{value}"

    def _parse_rating_key(self, key: str) -> int:
        """
        Parse a rating keypress.

        Args:
            key: Single character from keypress

        Returns:
            1-10 for valid rating, None for enter/skip, -1 for invalid
        """
        if key in ("\r", "\n"):
            return None
        if key == "0":
            return 10
        if key.isdigit() and key != "0":
            return int(key)
        return -1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_add_form.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Wire AddForm into the add command**

Modify `diigo_tagger/cli/main.py`. In the `add` command function, after the bookmark service is created and metadata is fetched, add the interactive form flow. Add this import inside the `add` function body (lazy import):

```python
from .add_form import AddForm
from ..services.metadata_tag_detector import MetadataTagDetector
from ..services.settings_service import SettingsService
```

Then after the existing `click.echo(f"Adding bookmark: {url}")` line, before calling `service.add_bookmark()`, insert the interactive form logic:

```python
        # Interactive form for tag enrichment
        form = AddForm(session)
        detector = MetadataTagDetector()
        settings = SettingsService(session)

        # Fetch metadata
        metadata = service.metadata_fetcher.fetch_metadata(url)

        # Prompt for title/description
        resolved_title = form.prompt_title(title or metadata.get("title", ""))
        resolved_desc = form.prompt_description(description or metadata.get("description", ""))

        # Get LLM suggestions and match against existing
        llm_tags = []
        if openai_client:
            raw_suggestions = service.openai_client.generate_tags(
                title=resolved_title,
                description=resolved_desc,
                url=url,
            )
            from ..services.tag_reconciliation import TagReconciliationService
            reconciler = TagReconciliationService(session)
            matched = reconciler.match_existing_tags(raw_suggestions)
            llm_tags = [m["matched"] or m["suggested"] for m in matched]

        accepted_llm = form.prompt_tag_list(llm_tags, "Tag suggestions")

        # Detected metadata tags
        detected = detector.detect(url, metadata)
        accepted_meta = form.prompt_metadata_tags(detected)

        # Prefix tags
        prefixes = settings.get_tag_prefixes()
        prefix_tags = form.prompt_prefix_tags(prefixes)

        # Rating
        rating_tag = form.prompt_rating()

        # Combine all tags
        all_tags = list(tag_list or []) + accepted_llm + accepted_meta + prefix_tags
        if rating_tag:
            all_tags.append(rating_tag)
```

Then pass `all_tags` as the `tags` parameter and `resolved_title`/`resolved_desc` as `title`/`description` to `service.add_bookmark()`.

**Note:** This is a significant modification to the existing `add` command. The implementer should read the full current `add` function in `main.py` and integrate carefully, preserving the conflict resolution flow.

- [ ] **Step 6: Run all CLI tests**

Run: `poetry run pytest tests/unit/test_cli.py tests/unit/test_cli_help.py tests/unit/test_cli_server.py tests/unit/test_add_form.py -v`
Expected: All tests pass (pre-existing failures excepted)

- [ ] **Step 7: Commit**

```bash
git add diigo_tagger/cli/add_form.py diigo_tagger/cli/main.py tests/unit/test_add_form.py
git commit -m "feat: add interactive CLI form with prompt_toolkit

Multi-step form for adding bookmarks: title/description editing,
tag accept/reject, metadata tags, prefix autocomplete, rating.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Tag Autocomplete API Endpoint

**Files:**
- Modify: `diigo_tagger/api/routes/bookmarks.py`
- Create: `tests/integration/test_api_autocomplete.py`

- [ ] **Step 1: Write failing test**

Create `tests/integration/test_api_autocomplete.py`:

```python
# ABOUTME: Integration tests for tag autocomplete API endpoint
# ABOUTME: Tests prefix-filtered tag search for autocomplete dropdowns

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from diigo_tagger.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestTagAutocomplete:
    """Test GET /api/v1/tags/autocomplete endpoint."""

    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    def test_autocomplete_returns_matching_tags(self, mock_get_session, client):
        """Should return tags matching prefix and query."""
        mock_session = MagicMock()
        mock_query = MagicMock()

        # Mock tag results
        mock_tag1 = MagicMock()
        mock_tag1.name = "reference:peter-zeihan"
        mock_tag2 = MagicMock()
        mock_tag2.name = "reference:peter-attia"
        mock_query.filter.return_value.limit.return_value.all.return_value = [mock_tag1, mock_tag2]
        mock_session.query.return_value = mock_query
        mock_get_session.return_value = mock_session

        response = client.get("/api/v1/tags/autocomplete?prefix=reference:&q=peter")
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        assert "prefix" in data
        assert data["prefix"] == "reference:"

    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    def test_autocomplete_empty_query(self, mock_get_session, client):
        """Should return all tags with prefix when query is empty."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.limit.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_get_session.return_value = mock_session

        response = client.get("/api/v1/tags/autocomplete?prefix=reference:")
        assert response.status_code == 200

    def test_autocomplete_requires_prefix(self, client):
        """Should return 422 when prefix is missing."""
        response = client.get("/api/v1/tags/autocomplete")
        assert response.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/integration/test_api_autocomplete.py -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Add autocomplete endpoint**

Add to `diigo_tagger/api/routes/bookmarks.py`:

```python
@router.get("/tags/autocomplete")
async def tag_autocomplete(prefix: str, q: str = "", limit: int = 20):
    """
    Return tags matching a prefix for autocomplete.

    Args:
        prefix: Tag prefix to filter by (e.g., "reference:")
        q: Optional query to further filter results
        limit: Maximum number of results (default 20)

    Returns:
        JSON with matching tags and the prefix used
    """
    from ...db import get_session
    from ...models import Tag

    session = get_session()
    try:
        search = f"{prefix}{q}%"
        tags = (
            session.query(Tag)
            .filter(Tag.name.like(search))
            .limit(limit)
            .all()
        )
        return {
            "tags": [tag.name for tag in tags],
            "prefix": prefix,
        }
    finally:
        session.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/integration/test_api_autocomplete.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add diigo_tagger/api/routes/bookmarks.py tests/integration/test_api_autocomplete.py
git commit -m "feat: add tag autocomplete API endpoint

GET /api/v1/tags/autocomplete?prefix=reference:&q=peter
Returns matching tags for prefix-based autocomplete.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: Web UI — Detected Tags, Rating, and Prefix Inputs

**Files:**
- Modify: `diigo_tagger/web/templates/add_bookmark.html`
- Modify: `diigo_tagger/api/routes/bookmarks.py` (add metadata tags to POST response)

- [ ] **Step 1: Add detected tags section to add_bookmark.html**

After the existing LLM tag suggestions section, add a new "Detected Tags" section. This should be visually distinct (different border color, e.g., blue instead of green).

```html
<!-- Detected Metadata Tags -->
<div id="detected-tags" class="mt-4 p-4 border border-blue-200 rounded-lg bg-blue-50 hidden">
    <h3 class="text-sm font-medium text-blue-800 mb-2">Detected Metadata Tags</h3>
    <div id="detected-tag-chips" class="flex flex-wrap gap-2">
        <!-- Chips inserted by JS/HTMX -->
    </div>
</div>
```

Each chip has an accept/reject toggle (same pattern as existing LLM tag chips but with blue styling).

- [ ] **Step 2: Add rating widget**

After the tags sections, add a rating widget:

```html
<!-- Rating -->
<div class="mt-4">
    <label class="block text-sm font-medium text-gray-700 mb-2">Rating (optional)</label>
    <div class="flex gap-1" id="rating-widget">
        <button type="button" onclick="setRating(0)" class="rating-btn px-3 py-1 border rounded text-sm hover:bg-yellow-100">Skip</button>
        <template x-for="n in [1,2,3,4,5,6,7,8,9,10]">
            <button type="button" :onclick="'setRating('+n+')'" class="rating-btn px-3 py-1 border rounded text-sm hover:bg-yellow-100" x-text="n"></button>
        </template>
    </div>
    <input type="hidden" name="rating" id="rating-input" value="">
</div>

<script>
function setRating(value) {
    document.getElementById('rating-input').value = value === 0 ? '' : value;
    document.querySelectorAll('.rating-btn').forEach(btn => btn.classList.remove('bg-yellow-200', 'border-yellow-400'));
    if (value > 0) {
        event.target.classList.add('bg-yellow-200', 'border-yellow-400');
    }
}
</script>
```

- [ ] **Step 3: Add prefix tag inputs**

After the rating widget, add dynamically generated prefix tag inputs. These are loaded from the settings API:

```html
<!-- Prefix Tags -->
<div id="prefix-tags" class="mt-4 space-y-3">
    <!-- Loaded via HTMX from settings -->
</div>
```

Each prefix input uses HTMX to fetch autocomplete suggestions:

```html
<div class="flex items-center gap-2">
    <label class="text-sm font-medium text-gray-700 w-24">reference:</label>
    <input type="text" name="prefix_reference" 
           class="flex-1 border rounded px-2 py-1 text-sm"
           placeholder="Type to search or create..."
           hx-get="/api/v1/tags/autocomplete?prefix=reference:"
           hx-trigger="keyup changed delay:300ms"
           hx-target="#reference-suggestions"
           hx-swap="innerHTML"
           hx-include="this"
           autocomplete="off">
    <div id="reference-suggestions" class="absolute bg-white border rounded shadow-lg z-10"></div>
</div>
```

- [ ] **Step 4: Update POST /api/v1/bookmarks to include metadata tags**

Modify the bookmark creation endpoint in `bookmarks.py` to:
1. Run `MetadataTagDetector.detect()` on the URL
2. Include detected tags in the response so the frontend can display them
3. Accept `rating` and prefix tag fields from the form submission

- [ ] **Step 5: Test manually**

Run: `poetry run diigo dev`
Navigate to `http://localhost:8000/add`, enter a YouTube URL, and verify:
- Detected tags section appears with `format:video` and `source:youtube.com`
- Rating widget displays and sets value
- Prefix tag input shows with autocomplete

- [ ] **Step 6: Commit**

```bash
git add diigo_tagger/web/templates/add_bookmark.html diigo_tagger/api/routes/bookmarks.py
git commit -m "feat: add detected tags, rating widget, and prefix inputs to web UI

Detected metadata tags shown in separate blue section.
Rating widget with 1-10 buttons. Prefix tag inputs with
HTMX autocomplete from existing tags.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: Update MetadataFetcher to Detect Article Tags

**Files:**
- Modify: `diigo_tagger/clients/metadata_fetcher.py`
- Modify: `tests/unit/test_metadata_fetcher.py`

- [ ] **Step 1: Write failing test**

Add to `tests/unit/test_metadata_fetcher.py`:

```python
class TestArticleDetection:
    """Test that webpage metadata includes article tag detection."""

    @patch("diigo_tagger.clients.metadata_fetcher.requests.get")
    def test_detects_article_element(self, mock_get):
        """Should set has_article_tag when <article> element found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body><article><h1>Title</h1></article></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = MetadataFetcher()
        result = fetcher.fetch_metadata("https://example.com/blog/post")

        assert result.get("has_article_tag") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/test_metadata_fetcher.py::TestArticleDetection -v`
Expected: FAIL — `has_article_tag` not in result

- [ ] **Step 3: Add article detection to _fetch_webpage_metadata**

In `diigo_tagger/clients/metadata_fetcher.py`, in the `_fetch_webpage_metadata` method, after the keywords extraction and before the return statement, add:

```python
            # Detect article element
            has_article_tag = soup.find('article') is not None
```

Then include it in the return dict:

```python
            return {
                "title": title,
                "description": description,
                "keywords": [k for k in keywords if k],
                "content_type": "webpage",
                "has_article_tag": has_article_tag,
            }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_metadata_fetcher.py -v`
Expected: PASS (all tests including new one)

- [ ] **Step 5: Commit**

```bash
git add diigo_tagger/clients/metadata_fetcher.py tests/unit/test_metadata_fetcher.py
git commit -m "feat: detect <article> element in webpage metadata

Sets has_article_tag=True when HTML contains an <article> element,
used by MetadataTagDetector for format:article detection.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: Integration — Wire Everything into BookmarkService

**Files:**
- Modify: `diigo_tagger/services/bookmark_service.py`

- [ ] **Step 1: Import new services in add_bookmark method**

In `BookmarkService.add_bookmark()`, add lazy imports:

```python
from .metadata_tag_detector import MetadataTagDetector
from .tag_reconciliation import TagReconciliationService
from .settings_service import SettingsService
```

- [ ] **Step 2: Add metadata tag detection to the add flow**

After metadata is fetched and before tags are saved, run the detector:

```python
detector = MetadataTagDetector()
detected_tags = detector.detect(url, metadata)
```

Include detected tag names in the response so both CLI and web UI can display them in the "Detected metadata tags" section.

- [ ] **Step 3: Add tag similarity matching**

After LLM generates tag suggestions, run similarity matching:

```python
reconciler = TagReconciliationService(self.session)
matched = reconciler.match_existing_tags(raw_tags)
deduped_tags = [m["matched"] or m["suggested"] for m in matched]
```

- [ ] **Step 4: Run full test suite**

Run: `poetry run pytest -v`
Expected: All new tests pass, no regressions

- [ ] **Step 5: Commit**

```bash
git add diigo_tagger/services/bookmark_service.py
git commit -m "feat: integrate metadata detection and tag similarity into add flow

BookmarkService.add_bookmark() now runs MetadataTagDetector and
tag similarity matching before presenting tags to user.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: Documentation Updates

**Files:**
- Modify: `docs/USER-GUIDE.md`
- Modify: `docs/DEVELOPER-GUIDE.md`
- Modify: `README.md`

- [ ] **Step 1: Update USER-GUIDE.md**

Add sections for:
- Detected metadata tags (format: and source:)
- Rating (`rating=x_10`)
- Prefix tags with autocomplete
- Interactive CLI form flow description

- [ ] **Step 2: Update DEVELOPER-GUIDE.md**

Add:
- `MetadataTagDetector` in architecture section
- `SettingsService` and settings table
- `AddForm` and prompt_toolkit usage
- Tag autocomplete API endpoint

- [ ] **Step 3: Update README.md**

Add smart tagging to Features list.

- [ ] **Step 4: Commit**

```bash
git add docs/USER-GUIDE.md docs/DEVELOPER-GUIDE.md README.md
git commit -m "docs: update guides for smart tagging and metadata fields

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```
