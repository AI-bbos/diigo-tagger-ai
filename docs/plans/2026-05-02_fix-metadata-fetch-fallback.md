# Fix: Metadata Fetch Falls Back to Domain Name

**Goal:** Fix the bug where bookmark title/description becomes just the domain name (e.g., "medium.com") when metadata fetching fails or returns empty results.

**Root Cause:** Two compounding issues:

1. **MetadataFetcher uses a basic User-Agent** (`Mozilla/5.0 (compatible; DiigoTagger/1.0)`) that gets blocked by sites like Medium, returning empty title/description.

2. **BookmarkService has a bad fallback** at line 300: `llm_title = title or fetched_title or urlparse(url).netloc`. When fetched_title is empty, the domain name becomes the bookmark title — which is useless as a title.

---

## Fix Plan

### Task 1: Improve MetadataFetcher User-Agent and title extraction

**File:** `diigo_tagger/clients/metadata_fetcher.py`

- [ ] Change User-Agent to a realistic browser string (Chrome on macOS) — sites like Medium serve full content to real browsers but block bots
- [ ] Add `og:title` extraction as a title fallback (many sites set og:title even when `<title>` is generic)
- [ ] Add `<h1>` extraction as a secondary title fallback
- [ ] Add `og:description` check before generic meta description (already partially done but order matters)
- [ ] Write/update tests for Medium-style pages with og: tags

### Task 2: Add URL-path title extraction as fallback

**File:** `diigo_tagger/clients/metadata_fetcher.py`

Sites like Medium and Substack encode the article title in the URL slug (e.g., `claude-code-hooks-explained-the-missing-layer-between-prompts-and-production-d0e3d1509278`). This is a better fallback than the domain name when HTML parsing fails.

- [ ] Add `_title_from_url_path(url)` method:
  1. Take the last meaningful path segment (ignore trailing hash suffixes like hex IDs)
  2. Replace hyphens with spaces
  3. Title-case the result
  4. Strip trailing hex/UUID suffixes (common on Medium: 12+ hex chars at end)
- [ ] Insert this in the fallback chain: `<title>` → `og:title` → `<h1>` → URL path slug
- [ ] Write tests with Medium and Substack URLs

### Task 3: Fix domain-name fallback in BookmarkService

**File:** `diigo_tagger/services/bookmark_service.py`

- [ ] Replace `urlparse(url).netloc` fallback on line 300 with a call to MetadataFetcher's URL-path extraction (or leave empty and let the confirmation step handle it)
- [ ] When no title can be determined, flag it in the result so the CLI/web can prompt the user
- [ ] Write tests for the empty-metadata scenario

### Task 4: Update tests

**Files:** `tests/unit/test_metadata_fetcher.py`, `tests/unit/test_bookmark_service.py`

- [ ] Test MetadataFetcher with og:title fallback
- [ ] Test MetadataFetcher with h1 fallback
- [ ] Test URL-path title extraction (Medium, Substack, generic slugs)
- [ ] Test BookmarkService no longer produces domain-name titles
- [ ] Test BookmarkService flags missing title in result
