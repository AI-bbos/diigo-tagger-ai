# Phase 3: Smart Tagging and Metadata Fields

**Created**: 2026-04-25
**Status**: Approved
**Milestone**: Phase 3: Smart Tagging and Metadata Fields
**Issue**: https://github.com/AI-bbos/diigo-tagger-ai/issues/10

---

## Summary

Enhance bookmark tagging with auto-detected metadata tags, a rating system, configurable prefix tag autocomplete, and tag similarity matching. Upgrade the CLI add flow to use `prompt_toolkit` for interactive form navigation. Extend the web UI with corresponding fields.

---

## 1. Auto-Detected Metadata Tags

A `MetadataTagDetector` service that takes a URL + fetched metadata and returns detected tags. These are presented in a **separate section** from LLM suggestions — "Detected metadata tags" — where the user can accept or reject each individually.

### format: tags

Detected by URL pattern and metadata:

| Pattern | Tag |
|---------|-----|
| YouTube, Vimeo, Dailymotion, etc. | `format:video` |
| URLs ending in `.pdf` | `format:pdf` |
| GitHub/GitLab repo URLs (not file/blob URLs) | `format:repository` |
| Standard web pages with `<article>` element or article-type meta tags | `format:article` |

Detection uses URL patterns first, falls back to metadata content type / HTML structure.

### source: tags

Extracted from the URL domain — no curation, always applied:

- `source:youtube.com`
- `source:github.com`
- `source:bbc.co.uk`
- `source:medium.com`

Uses the registered domain (not full hostname), so `www.youtube.com` → `source:youtube.com`.

### Implementation

New file: `diigo_tagger/services/metadata_tag_detector.py`

```python
class MetadataTagDetector:
    """Detect format: and source: tags from URL and metadata."""

    def detect(self, url: str, metadata: dict) -> list[dict]:
        """Return list of {'tag': str, 'type': 'format'|'source', 'confidence': float}."""
```

No external dependencies. Pure logic based on URL parsing and metadata dict inspection.

---

## 2. Rating

Tag format: `rating=x_10` (note: equals sign, not colon).

- Prompted **last**, after all other tag work
- Single keypress: 1-9 for those values, 0 for 10, enter to skip
- No confirmation needed — keypress immediately sets it
- Stored as a regular tag on the bookmark

### CLI

`prompt_toolkit` captures single keypress without requiring enter.

### Web UI

Row of 10 clickable buttons (1-10) plus a "Skip" button. Styled as a rating widget.

---

## 3. Configurable Prefix Tags

Tag prefixes that get special autocomplete treatment when adding bookmarks. Prefixes are user-configurable and stored in the database settings table.

### Default prefixes

- `reference:` — where you heard about it (e.g., `reference:peter-zeihan`, `reference:hacker-news`)

Users can add more via CLI or settings (e.g., `project:`, `topic:`).

### Prompt flow

For each configured prefix:
1. Show existing tags with that prefix as autocomplete options
2. User can type to filter, select an existing one, or create a new one
3. Enter with empty input skips the prefix

### CLI

`prompt_toolkit` with `WordCompleter` or `FuzzyCompleter` populated from existing tags with that prefix.

### Web UI

Input field per prefix with HTMX-powered autocomplete. Fetches suggestions from `/api/v1/tags/autocomplete?prefix=reference:&q=pet`.

---

## 4. Tag Similarity Matching

Before presenting LLM tag suggestions, match each against existing tags in the database.

- **>80% string similarity** → substitute the existing tag (e.g., LLM suggests `java-script` but `javascript` exists → use `javascript`)
- **<80% similarity** → suggest as a new tag
- Uses `difflib.SequenceMatcher` for string similarity (stdlib, no new dependencies)

### Implementation

Add a `match_existing_tags()` method to `TagReconciliationService` (or `TagService`):

```python
def match_existing_tags(self, suggested_tags: list[str], threshold: float = 0.8) -> list[dict]:
    """Match suggested tags against existing ones.

    Returns list of {'suggested': str, 'matched': str|None, 'similarity': float}.
    If matched is not None, the existing tag should be used instead.
    """
```

Called in `BookmarkService.add_bookmark()` after LLM generates tags, before presenting to user.

---

## 5. CLI Form Flow (prompt_toolkit)

Add `prompt_toolkit` as a dependency. Create a new interactive add-bookmark form.

### New file: `diigo_tagger/cli/add_form.py`

Encapsulates the multi-field form logic, keeping `main.py` thin.

### Flow

1. **URL** — standard input, triggers metadata fetch
2. **Title** — pre-filled from metadata. Enter to accept, type to replace. Left/right arrows position cursor.
3. **Description** — same as title
4. **LLM tag suggestions** — list shown, accept/reject each (y/n keypress or enter to accept)
5. **Detected metadata tags** — separate section, same accept/reject UX
6. **Prefix tag prompts** — one per configured prefix. Autocomplete dropdown from existing tags. Enter to skip, type to filter/create.
7. **Rating** — "Rate? (1-9, 0=10, enter to skip)". Single keypress, no enter needed.
8. **Confirm** — show summary, enter to submit, 'q' to cancel

### Keyboard behavior

- **Enter** on any field → accept current value, advance to next field
- **Enter** on final field → submit
- **Arrow keys** in text fields → cursor positioning
- **Any printable character** in text fields → insert at cursor position
- **Single digit** on rating → set rating immediately, advance

### Integration

The existing `add` command in `main.py` delegates to `add_form.py` for the interactive flow. Non-interactive usage (all options passed via flags) bypasses the form.

---

## 6. Web UI

Extend the existing `add_bookmark.html` template. No React — HTMX handles all dynamic behavior.

### New UI elements

- **Detected Tags section** — below LLM suggestions, visually distinct (different color/border). Each tag shown as a chip with accept/reject toggle.
- **Rating widget** — row of 10 buttons (1-10) plus "Skip". Clicking sets the value, highlighted button shows selection.
- **Prefix tag inputs** — one input per configured prefix, with HTMX autocomplete. Fetches from new API endpoint as user types.

### New API endpoint

`GET /api/v1/tags/autocomplete?prefix=reference:&q=pet`

Returns matching tags for autocomplete:

```json
{
    "tags": ["reference:peter-zeihan", "reference:peter-attia"],
    "prefix": "reference:"
}
```

### Settings API

`GET /api/v1/settings/tag-prefixes` — returns configured prefixes
`PUT /api/v1/settings/tag-prefixes` — update prefix list

---

## 7. Database Changes

### New: settings table

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Initial data:

```sql
INSERT INTO settings (key, value) VALUES ('tag_prefixes', '["reference:"]');
```

Value is JSON-encoded. Simple key-value store, extensible for future settings.

### Alembic migration

New migration file to create the `settings` table and insert defaults.

### No changes to existing models

All new tags (`format:video`, `source:youtube.com`, `rating=7_10`, `reference:peter-zeihan`) are regular tags stored in the existing `tags` table via the existing `bookmark_tags` association.

---

## 8. File Changes Summary

### New files

| File | Purpose |
|------|---------|
| `diigo_tagger/services/metadata_tag_detector.py` | Detect format: and source: tags from URL/metadata |
| `diigo_tagger/cli/add_form.py` | prompt_toolkit interactive add-bookmark form |
| (added to `diigo_tagger/models.py`) | Settings ORM model added to existing models file |
| `alembic/versions/004_add_settings_table.py` | Migration for settings table |
| `tests/unit/test_metadata_tag_detector.py` | Tests for metadata tag detection |
| `tests/unit/test_tag_similarity.py` | Tests for tag similarity matching |
| `tests/unit/test_add_form.py` | Tests for CLI form flow |

### Modified files

| File | Changes |
|------|---------|
| `diigo_tagger/services/bookmark_service.py` | Call MetadataTagDetector and tag similarity matching during add |
| `diigo_tagger/services/tag_service.py` or `tag_reconciliation.py` | Add match_existing_tags() method |
| `diigo_tagger/cli/main.py` | Delegate add command to add_form.py |
| `diigo_tagger/api/routes/bookmarks.py` | Add tag autocomplete endpoint, settings endpoints |
| `diigo_tagger/web/templates/add_bookmark.html` | Detected tags section, rating widget, prefix inputs |
| `diigo_tagger/models.py` | Add Settings model |
| `pyproject.toml` | Add prompt_toolkit dependency |

---

## 9. Out of Scope (Separate Issues)

- **Subpath URL matching** — https://github.com/AI-bbos/diigo-tagger-ai/issues/8
- **Context-aware hierarchical tag inference** — https://github.com/AI-bbos/diigo-tagger-ai/issues/9
- **Vercel deployment / Turso migration** — deferred from Phase 2
