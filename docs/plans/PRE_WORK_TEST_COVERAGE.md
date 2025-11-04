# Pre-work: Test Coverage & Fixes

**Project**: Diigo Tagger AI - Web UI Pre-work
**Created**: 2025-11-04
**Last Updated**: 2025-11-04
**Branch**: `feat/web-ui`
**Status**: Required Before Phase 0
**Duration**: 2-3 days

---

## Current Status

**Coverage**: 76% (Target: >80%)
**Failing Tests**: 14
**Passing Tests**: 103
**Skipped Tests**: 5

---

## Coverage Breakdown

```
diigo_tagger/cli/main.py                        346     99    71%
diigo_tagger/clients/diigo_client.py             83     56    33%  ← Low
diigo_tagger/clients/metadata_fetcher.py         70     35    50%  ← Low
diigo_tagger/clients/openai_client.py            28     17    39%  ← Low
diigo_tagger/services/bookmark_service.py       179     27    85%  ← Good
diigo_tagger/services/tag_reconciliation.py      87      9    90%  ← Good
diigo_tagger/services/tag_service.py             38      0   100%  ← Excellent
```

**Problem Areas:**
1. **CLI** (71%) - Many commands not tested
2. **Clients** (33-50%) - API clients under-tested
3. **Services** (85-100%) - Good coverage ✓

---

## Failing Tests (14)

### API Clients (11 failures)
- `test_api_clients.py::TestDiigoClient::test_initialization_validates_https`
- `test_api_clients.py::TestDiigoClient::test_fetch_bookmarks_success`
- `test_api_clients.py::TestDiigoClient::test_fetch_bookmarks_handles_empty_tags`
- `test_api_clients.py::TestDiigoClient::test_fetch_bookmarks_rate_limit_error`
- `test_api_clients.py::TestDiigoClient::test_fetch_bookmarks_auth_error`
- `test_api_clients.py::TestDiigoClient::test_fetch_bookmarks_uses_pagination`
- `test_api_clients.py::TestOpenAIClient::test_generate_tags_success`
- `test_api_clients.py::TestOpenAIClient::test_generate_tags_handles_malformed_response`
- `test_api_clients.py::TestOpenAIClient::test_generate_tags_detects_prompt_injection`
- `test_api_clients.py::TestOpenAIClient::test_generate_tags_rate_limit_handling`
- `test_api_clients.py::TestOpenAIClient::test_generate_tags_uses_correct_model`

### CLI Tests (3 failures)
- `test_cli.py::TestCLISearch::test_search_wildcard`
- `test_cli.py::TestCLISearch::test_search_semantic`
- `test_cli.py::TestCLIAdd::test_add_bookmark_without_openai`

---

## Action Plan

### Task 1: Fix Failing Tests (Day 1)

**Priority 1: API Client Tests (11 tests)**
- Likely issue: Mocking strategy changed after code refactoring
- Action: Review and update mocks to match current implementation
- Files: `tests/unit/test_api_clients.py`

**Priority 2: CLI Tests (3 tests)**
- Search tests may need updated fixtures
- Add bookmark test needs OpenAI mock fix
- Files: `tests/unit/test_cli.py`

**Deliverable**: All tests passing ✅

---

### Task 2: Increase Coverage to >80% (Day 2)

**Target Areas:**

1. **CLI Coverage 71% → 80%**
   - Add tests for uncovered commands
   - Test error paths
   - Missing coverage: lines 77-78, 100-122, 142-144, etc.

2. **DiigoClient 33% → 75%**
   - Test create_bookmark with merge parameter
   - Test error handling paths
   - Missing coverage: lines 68, 91-149, 180-244

3. **MetadataFetcher 50% → 75%**
   - Test YouTube metadata extraction
   - Test webpage scraping
   - Test error handling
   - Missing coverage: lines 60, 63-65, 83-133, etc.

4. **OpenAIClient 39% → 75%**
   - Test tag generation with various inputs
   - Test error handling (rate limits, API failures)
   - Missing coverage: lines 56-108

**Deliverable**: >80% overall coverage ✅

---

### Task 3: Write Missing Tests for New Features (Day 2-3)

**New Code Not Yet Tested:**

1. **Metadata Fetcher** (`metadata_fetcher.py`)
   - YouTube URL detection
   - YouTube metadata extraction (yt-dlp)
   - Webpage metadata extraction (BeautifulSoup)
   - Error handling for both paths

2. **Updated Bookmark Service**
   - Early duplicate detection (skip LLM)
   - Metadata integration
   - No-changes response

**Test Files to Create/Extend:**
- `tests/unit/test_metadata_fetcher.py` (new)
- Extend `tests/unit/test_bookmark_service.py`

**Deliverable**: New features tested ✅

---

## Success Criteria

- ✅ **All tests passing** (0 failures)
- ✅ **>80% coverage** (currently 76%)
- ✅ **No regressions** (existing functionality works)
- ✅ **CI/CD ready** (tests run in automation)

---

## Estimated Timeline

| Day | Tasks | Hours |
|-----|-------|-------|
| Day 1 | Fix 14 failing tests | 4-6 hours |
| Day 2 | Increase coverage to 80%: CLI, clients | 4-6 hours |
| Day 3 | Write tests for new features (metadata) | 3-4 hours |
| **Total** | **Pre-work complete** | **11-16 hours** |

---

## After Pre-work

Once complete, proceed to:
1. ✅ Get plan approval from Brooke
2. System Architect: Design REST API structure
3. Phase 0: Foundation (FastAPI + LangChain)

---

**Blocker**: Web UI work cannot start until pre-work is complete and tests pass with >80% coverage.
