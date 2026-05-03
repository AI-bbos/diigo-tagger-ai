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

### Task 2: Fix domain-name fallback in BookmarkService

**File:** `diigo_tagger/services/bookmark_service.py`

- [ ] Remove `urlparse(url).netloc` fallback from line 300. If no title is available, use the URL itself (more informative than just the domain) or leave empty for user to fill in during confirmation step
- [ ] When no title can be determined, flag it in the result so the CLI/web can prompt the user
- [ ] Write tests for the empty-metadata scenario

### Task 3: Update tests

**Files:** `tests/unit/test_metadata_fetcher.py`, `tests/unit/test_bookmark_service.py`

- [ ] Test MetadataFetcher with og:title fallback
- [ ] Test MetadataFetcher with h1 fallback
- [ ] Test BookmarkService no longer produces domain-name titles
- [ ] Test BookmarkService flags missing title in result
