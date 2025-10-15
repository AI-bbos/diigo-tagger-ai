# BSA Analysis: Diigo CLI (LLM-Assisted Bookmark Tool)

## Business Context

- **Need**: Automate and standardize the process of saving bookmarks to Diigo with consistent, reusable tagging to avoid tag drift and improve bookmark discoverability
- **Stakeholders**:
  - Primary: Individual knowledge workers who extensively use Diigo for bookmark management (user: oehmsmith)
  - Secondary: Anyone working with large bookmark collections requiring disciplined taxonomy
- **Success Metric**:
  - Maximize tag reuse from existing personal tag vocabulary (desired but not always possible - new tags acceptable if no existing tags fit)
  - Zero manual tag entry for URL, title, author, description extraction
  - Sub-30-second workflow from URL to saved bookmark

## Technical Requirements

### Data Requirements

**Input Data:**
- URL or free-text prompt (required)
- Optional: custom description override
- User credentials: Diigo username, password, API key
- OpenAI API key for LLM-assisted extraction

**Data to Extract/Generate:**
- Page title (from HTML `<meta>` or `<title>`)
- Author name (from `<meta name="author">` or article byline)
- Description (from `<meta name="description">` or first paragraph, max 300 chars)
- Content sample (first 2000 chars for LLM context)
- Proposed tags (via LLM using master tag list + cached user tags)

**Data to Store:**
- Local cache: `~/.config/diigo/cache/` (tag cache - SQLite database for quick queries and/or VectorDB for similarity/context searches)
- Config: `~/.config/diigo/config.yml` (master tags, aliases, rules, LLM provider preferences)
- LLM model registry: `~/.config/diigo/models.json` (provider/model catalog synced from APIs, last updated timestamp)

**Tag Schema:**
- Content tags: from master list (e.g., `ai-agent`, `git-workflow`, `conventional_commits`)
- System tags: `source:<domain>` (always added if URL present)
- System tags: `author:<slug>` (always added if author detected, slugified as `author:firstname-lastname`)
- Metadata tag: `created-by-diigo-tagger-ai` (always added to all bookmarks created with this tool)
- **Tag Format Rules**:
  - **No spaces allowed** in tags
  - **Hyphens (`-`)**: Join compound words (e.g., `ai-agent`, `git-workflow`)
  - **Underscores (`_`)**: Replace spaces in multi-word phrases (e.g., `commit_narrative`, `knowledge_management`)
  - **Both can be combined**: `ai-enhanced_devops` (compound words hyphenated, space-words underscored)
  - All tags: lowercase, special chars stripped except `:`, `-`, `_`

### API Requirements

**Diigo API Integration:**

1. **POST /api/v2/bookmarks** (save bookmark)
   - Auth: HTTP Basic Auth (username:password) + API key as query param
   - Request body (form-encoded):
     - `url`: string (required)
     - `title`: string (required)
     - `tags`: comma-separated string
     - `desc`: string (optional)
     - `shared`: "yes"|"no" (default "no")
   - Response: 200 OK with JSON (created/updated status)
   - Error handling: 401/403 (auth), 429 (rate limit with retry), 5xx (retry with backoff)

2. **GET /api/v2/bookmarks** (fetch user's bookmarks for tag sync)
   - Auth: Same as above
   - Query params:
     - `user`: username (required)
     - `key`: API key (required)
     - `start`: offset for pagination (0-indexed)
     - `count`: batch size (max 100)
     - `filter`: "public"|"all" (default "all")
   - Response: JSON array of bookmark objects
   - Pagination: iterate with `start` += `count` until empty batch

**LLM API Integration (via LangChain - Provider Agnostic):**

3. **ChatCompletion** (LLM-assisted tag generation with multi-provider fallback)
   - **Architecture**: Use LangChain abstractions for provider independence
   - **Providers**: ChatGPT (OpenAI), Gemini (Google), Claude (Anthropic)
   - **Model Selection**: Dynamic lookup from model registry (no hardcoded models)
   - **Model Registry**:
     - Scheduled sync from provider APIs (OpenAI, Anthropic, Google) every 7 days (configurable)
     - Query provider APIs for available models (names, capabilities, pricing)
     - Merge with local preference rankings (cheapest → most expensive)
     - Store in `~/.config/diigo/models.json`
   - **Fallback Chain**: Attempt providers/models in preference order on failures
     1. Try cheapest model from preferred provider
     2. On failure (API error, rate limit, auth failure), cycle to next provider/model
     3. Continue through preference list until success or exhaustion
   - **Temperature**: 0.2 (deterministic)
   - **System prompt**: Enforce tagging rules (reuse master tags, add source:/author:, lowercase, hyphen/underscore rules)
   - **User prompt**: URL, domain, title, author, content sample, master tag list
   - **Response**: CSV or JSON array of proposed tags
   - **Ultimate Fallback**: If all LLM providers fail or no API keys configured, use heuristic (keyword matching against master tags)

### UI Requirements

**CLI Interface:**

```bash
# Primary command: save bookmark
diigo save <URL or text> [--desc "..."] [--dry-run] [--no-interactive] [--allow-new-tags]

# Tag management commands
diigo tags:show [--show latest|top|chrono[logical]] [-n N]  # Display tags (N=0 for ALL)
diigo tags:sync --user <username> [--scope all|public]       # Fetch all user tags (auto first-time, scheduled weekly)
diigo tags:normalize                                          # Find/transform contextual duplicate tags (later phase)

# Help
diigo --help
```

**Tag Display Options:**
- `--show latest`: Show most recently used tags (default)
- `--show top`: Show most frequently used tags
- `--show chrono` or `--show chronological`: Show tags in chronological order (oldest first)
- `-n N`: Show N tags (N=0 shows ALL tags)

**Interactive Workflow (default):**
1. Display extracted metadata:
   - URL
   - Title
   - Author
   - Description
   - Proposed tags (validated against master+cache)
   - Unknown tags (blocked, shown separately)
2. Prompt: `Save to Diigo? [Y/n/e]:`
   - `Y` or Enter → save
   - `n` → cancel
   - `e` → edit tags (enter comma-separated list, recompute, prompt again)

**Non-Interactive Mode (`--no-interactive`):**
- Skip confirmation, save immediately

**Dry-Run Mode (`--dry-run`):**
- Print exact API payload without calling Diigo API

**WebUI (Later Phase):**
- Browser-based interface for bookmark management
- Calls REST API endpoints (not service layer directly)
- Same functionality as CLI but with visual interface
- Implementation in later development phase after CLI is stable

### Architecture Requirements

**Layered Design (per CLAUDE.md - SOLID principles, GoF patterns, TDD mandatory):**

```
┌─────────────────────────────────────────────────────┐
│                  UI Layer                           │
│  ┌──────────────┐              ┌─────────────────┐ │
│  │     CLI      │              │     WebUI       │ │
│  │  (stateless) │              │   (stateless)   │ │
│  └──────┬───────┘              └────────┬────────┘ │
│         │                               │          │
│         │ direct method calls           │ HTTP     │
│         │                               │          │
└─────────┼───────────────────────────────┼──────────┘
          │                               │
          │                               │
          │                   ┌───────────▼──────────┐
          │                   │   REST API Layer     │
          │                   │ (HTTP endpoints for  │
          │                   │   WebUI only)        │
          │                   │    (stateless)       │
          │                   └───────────┬──────────┘
          │                               │
          │ method calls                  │ method calls
          │                               │
┌─────────▼───────────────────────────────▼──────────┐
│                 Service Layer                      │
│          (Business Logic - shared)                 │
│  ┌──────────────┐  ┌──────────────┐               │
│  │   Bookmark   │  │     Tag      │               │
│  │   Service    │  │   Service    │  (etc.)       │
│  └──────┬───────┘  └──────┬───────┘               │
└─────────┼──────────────────┼────────────────────────┘
          │                  │
          │ method calls     │
          │                  │
┌─────────▼──────────────────▼────────────────────────┐
│         Repository/Client Layer                     │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │   Diigo    │  │    LLM     │  │    Cache     │  │
│  │   Client   │  │  Provider  │  │  (SQLite/    │  │
│  │ (REST API) │  │ (LangChain)│  │  VectorDB)   │  │
│  └────────────┘  └────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Design Principles:**
- **CLI → Services**: Direct method calls (no HTTP overhead, stateless, local)
- **WebUI → REST API → Services**: HTTP via REST API for remote access
- **Service Layer**: Shared business logic used by both CLI and WebUI
- **Separation of Concerns**: Each layer has single responsibility
- **No MCP**: Decided against Model Context Protocol - LLM doesn't need direct Diigo access
- **Clean REST/API Client Layer**: Diigo interaction through well-defined client interface
- **TDD**: Comprehensive test coverage for all layers per CLAUDE.md requirements

### Security Requirements

**Authentication:**
- Diigo credentials stored in environment variables (`.env` file, never committed)
- OpenAI API key stored in environment variables
- HTTP Basic Auth over HTTPS for Diigo API
- No credential persistence in code or config files checked into version control

**Input Validation:**
- URL validation (must start with `http://` or `https://`)
- Tag normalization (strip special chars, lowercase, hyphenate)
- Author slugification (alphanumeric + hyphens only)

**Data Privacy:**
- No logging of passwords or API keys
- Bookmark data only sent to Diigo API (user's own account)
- LLM receives: URL, title, author, content sample (no sensitive data beyond what's publicly accessible)

**Rate Limiting:**
- Respect Diigo API rate limits (429 responses trigger exponential backoff)
- Max 3 retries on 5xx errors with backoff (1s, 2s, 4s)

**Audit Logging:**
- Print all API responses (success/failure) to stdout
- Tag cache timestamps (last sync time in ISO format)

### Performance Requirements

**Response Time:**
- Page fetch: < 5 seconds (timeout at 15s)
- LLM tag generation: < 10 seconds (gpt-4o-mini is fast)
- Diigo API save: < 3 seconds (timeout at 15s)
- End-to-end (URL to saved): < 30 seconds total

**Tag Sync (One-Time Operation):**
- Fetch all bookmarks: ~5-10 seconds per 1000 bookmarks (100/batch, 20s timeout per request)
- Expected scale: 1000-10000 bookmarks typical for active users
- Cache write: < 1 second

**Concurrency:**
- Single-user CLI (no concurrent requests needed)
- Sequential API calls (fetch page → LLM → save to Diigo)

**Storage:**
- Tag cache file size: ~10-50 KB for 1000-5000 unique tags
- No disk space concerns

## Acceptance Criteria

### AC1: URL-Based Bookmark Extraction
```
GIVEN a valid URL
WHEN user runs `diigo save "https://example.com/article"`
THEN the tool fetches the page
AND extracts title from <title> or og:title
AND extracts author from <meta name="author"> or byline
AND extracts description from <meta name="description"> or first paragraph
AND generates tags using LLM + master tag list
AND adds source:example.com tag
AND adds author:<slug> tag if author found
AND displays interactive confirmation with all metadata
```

### AC2: Tag Reuse from Cache
```
GIVEN user has synced tags once with `diigo tags:sync --user oehmsmith`
WHEN LLM proposes tags for a new bookmark
THEN ALL proposed tags are validated against (master_tags + cached tags)
AND any tag NOT in the combined list is marked as "unknown"
AND unknown tags are blocked unless --allow-new-tags flag is used
AND user sees "Unknown (blocked): <tag1>, <tag2>" message
```

### AC3: Tag Cache Sync
```
GIVEN valid Diigo credentials in environment
WHEN user runs `diigo tags:sync --user oehmsmith --scope all`
THEN the tool paginates through ALL bookmarks (100 per batch)
AND extracts comma-separated tags from each bookmark
AND computes tag counts (frequency across all bookmarks)
AND writes JSON to ~/.diigo_tags: {"tags": [...], "counts": {...}, "last_sync": "2025-10-15T..."}
AND prints "✅ Tag cache written to ~/.diigo_tags"
```

### AC4: Interactive Tag Editing
```
GIVEN user runs `diigo save <URL>` (interactive mode, default)
WHEN tool displays proposed tags
AND user enters "e" at the prompt
THEN tool prompts "Enter comma-separated tags:\n> "
AND user types custom tags
AND tool re-validates against master+cache
AND displays recomputed tags
AND prompts "Save now? [Y/n]:"
```

### AC5: Dry-Run Mode
```
GIVEN any bookmark save command
WHEN user adds `--dry-run` flag
THEN tool performs all extraction (fetch page, LLM tagging, validation)
AND prints "DRY RUN: Would send to Diigo:"
AND prints exact payload dict: {"url": "...", "title": "...", "tags": "...", "desc": "...", "shared": "no"}
AND does NOT call Diigo API
AND exits
```

### AC6: System Tag Generation
```
GIVEN URL "https://hyperdev.matsuoka.com/p/article" and author "Robert Matsuoka"
WHEN bookmark is saved
THEN tags include "source:hyperdev.matsuoka.com"
AND tags include "author:robert-matsuoka"
AND both system tags appear in final tag list
```

### AC7: Fallback Without OpenAI Key
```
GIVEN OPENAI_API_KEY is not set in environment
WHEN user runs `diigo save <URL>`
THEN tool fetches page metadata (title, author, desc)
AND uses heuristic tagging (keyword match against master tags from title+content sample)
AND produces a smaller tag set (2-6 tags typical)
AND still enforces master tag validation
AND still adds source: and author: tags
AND proceeds with save as normal
```

### AC8: Error Handling - Missing Prerequisites
```
GIVEN DIIGO_USER, DIIGO_PASS, or DIIGO_API_KEY is missing from .env
WHEN user runs any command requiring Diigo API
THEN CLI prints "⚠️ Missing credentials in .env: DIIGO_USER, DIIGO_PASS, DIIGO_API_KEY"
AND CLI exits with error code (no crash)
AND WebUI displays error message with instructions

GIVEN tag cache does not exist at ~/.config/diigo/cache/
WHEN user runs `diigo save <URL>`
THEN CLI prints "⚠️ Tag cache missing. Please run: diigo tags:sync --user <username>"
AND CLI exits with error code
AND WebUI displays error message with sync instructions
```

### AC9: Error Handling - API Failures
```
GIVEN Diigo API returns 429 (rate limit exceeded)
WHEN tool attempts to save bookmark
THEN tool prints "⚠️ Attempt 1 failed: 429 Too Many Requests, retrying in 1s..."
AND retries up to 3 times with exponential backoff (1s, 2s, 4s)
AND if all attempts fail, prints "❌ Error 429: <response text>"
AND exits with error
```

### AC10: Tag Display
```
GIVEN user runs `diigo tags:show --show top -n 20`
WHEN tag cache exists at ~/.config/diigo/cache/
THEN tool prints "Master tags:" followed by top 20 most frequently used tags
AND displays each tag on separate line with usage count
AND respects display options: latest (default), top (frequency), chronological (oldest first)
AND -n 0 displays ALL tags
```

### AC11: Tag Normalization (Later Phase)
```
GIVEN user runs `diigo tags:normalize`
WHEN tag cache contains contextual duplicates (e.g., "ai_agent" with 1 use, "ai-agent" with 50 uses)
THEN tool uses NLP/semantic similarity algorithm to detect variants
AND identifies canonical form (highest usage count)
AND prompts user: "Transform 'ai_agent' (1 use) → 'ai-agent' (50 uses)? [Y/n]"
AND on confirmation, calls Diigo API to update all bookmarks with low-usage tag
AND updates local cache to reflect transformation
AND prints summary: "✅ Normalized 3 tags across 12 bookmarks"

NOTE: Requires verification that Diigo API supports absolute tag list replacement
```

## Dependencies

### Infrastructure
- ✅ Python 3.10+ environment (VALIDATED: Standard requirement)
- ✅ Internet connectivity (VALIDATED: Required for API calls)
- ⚠️ Diigo account with API access (UNVALIDATED: User must have API key - needs confirmation that key is available)

### Services
- ✅ Diigo API (VALIDATED: Documented at https://www.diigo.com/api_dev/docs)
  - Endpoint: https://secure.diigo.com/api/v2/bookmarks
  - Auth: HTTP Basic + API key
  - Rate limits: Not specified in docs (needs monitoring)
- ⚠️ OpenAI API (UNVALIDATED: Optional but recommended - user must have valid API key)
  - Fallback exists if missing (heuristic tagging)

### Python Dependencies
- ✅ requests (VALIDATED: HTTP client for Diigo API)
- ✅ beautifulsoup4 (VALIDATED: HTML parsing for metadata extraction)
- ✅ langchain (VALIDATED: LLM orchestration)
- ✅ openai (VALIDATED: OpenAI API client)
- ✅ tiktoken (VALIDATED: Token counting for LLM)
- ✅ python-dotenv (VALIDATED: Environment variable loading)
- ✅ pyyaml (VALIDATED: Config file parsing)
- ✅ pytest, black, ruff (VALIDATED: Dev/test tools)

### Data Prerequisites
- ❌ ~/.config/diigo/cache/ tag cache (BLOCKER: Must run `tags:sync` once before first use to populate cache)
  - Auto-sync on first run (prompts user)
  - Scheduled weekly sync thereafter (configurable)
  - CLI exits with error if missing; WebUI displays error message
- ❌ .env file with credentials (BLOCKER: User must create from .env.example before first use)
  - CLI exits with error if missing; WebUI displays error message
- ⚠️ ~/.config/diigo/models.json model registry (UNVALIDATED: Auto-created on first LLM call, synced every 7 days)

### Feature Dependencies
- ✅ If implementing within existing project: Poetry for dependency management (VALIDATED: pyproject.toml provided)
- ⚠️ If using in other contexts: Could package as standalone script with pip-installable dependencies

## Assumptions

### Technical Assumptions
- ✅ **User has Python 3.10+** (VALIDATED: Specified in pyproject.toml)
- ✅ **Diigo API uses HTTP Basic Auth** (VALIDATED: Confirmed in API docs)
- ⚠️ **Diigo API returns 200 OK for both create and update** (UNVALIDATED: Docs suggest this but needs testing)
- ⚠️ **Bookmark deduplication is URL-based** (UNVALIDATED: Assuming Diigo treats POST to existing URL as update - needs confirmation)
- ✅ **gpt-4o-mini is sufficient for tag generation** (VALIDATED: Designed for lightweight extraction tasks)
- ⚠️ **User's Diigo account has API access enabled** (UNVALIDATED: Some Diigo accounts may not have API keys)

### Business Assumptions
- ✅ **User wants to minimize manual tagging** (VALIDATED: Explicitly stated goal in document)
- ✅ **Tag consistency is more important than tag diversity** (VALIDATED: Enforces limited master set)
- ⚠️ **User prefers command-line workflow over browser bookmarklet** (UNVALIDATED: CLI-first design - may need browser integration later)
- ⚠️ **One-time tag sync is acceptable** (UNVALIDATED: Assumes manual re-sync when needed - could automate with periodic refresh)
- ✅ **Interactive confirmation is desired by default** (VALIDATED: Requirement specifies interactive mode with --no-interactive opt-out)

### Scope Assumptions
- ✅ **Single-user tool** (VALIDATED: No multi-user features in design)
- ✅ **English-language content primary target** (VALIDATED: LLM prompts in English, no i18n)
- ⚠️ **Bookmarks are articles/pages with standard HTML metadata** (UNVALIDATED: May fail on PDFs, videos, non-standard pages)
- ❌ **No offline mode needed** (BLOCKER: Requires internet for all operations - if offline use is required, this is out of scope)
- ⚠️ **No bulk import from other bookmark services** (UNVALIDATED: One-at-a-time workflow only)

### Resource Assumptions
- ✅ **OpenAI API costs are acceptable** (VALIDATED: Using gpt-4o-mini for cost efficiency, ~$0.00015 per request)
- ✅ **Diigo API has no cost** (VALIDATED: Free API for personal use)
- ⚠️ **Local disk space sufficient for tag cache** (UNVALIDATED: ~50 KB for 5000 tags - should be fine but not verified)

## Risks & Concerns

### Technical Risks
- **🔴 HIGH: Diigo API rate limiting**
  - If user saves many bookmarks rapidly, 429 errors likely
  - Mitigation: Exponential backoff implemented, but no rate limit documentation found
  - Impact: Could block user workflow for minutes/hours
- **🟡 MEDIUM: HTML metadata extraction reliability**
  - Not all pages have proper `<meta>` tags or structured author info
  - Mitigation: Multiple fallback selectors (og:title, byline patterns)
  - Impact: Some bookmarks may have poor title/author extraction
- **🟡 MEDIUM: LLM tagging quality**
  - gpt-4o-mini may hallucinate tags or ignore master list guidance
  - Mitigation: Strict validation against master+cache, interactive review
  - Impact: User may need to manually edit tags frequently
- **🟢 LOW: Tag cache staleness**
  - User must manually re-run tags:sync to refresh cache
  - Mitigation: Document manual sync process, show last_sync timestamp
  - Impact: New tags added via web won't appear in CLI suggestions until sync

### Security Risks
- **🟡 MEDIUM: Credentials in environment variables**
  - .env file readable by any process running as user
  - Mitigation: Warn user not to commit .env, add to .gitignore
  - Impact: Local credential compromise if system is breached
- **🟢 LOW: OpenAI API sees bookmark content**
  - Sends URL, title, author, 2000-char sample to OpenAI
  - Mitigation: User can opt out by not setting OPENAI_API_KEY (fallback to heuristic)
  - Impact: Privacy concern for confidential/proprietary content

### Business Risks
- **🟡 MEDIUM: User workflow friction**
  - Multi-step setup (install, credentials, tag sync, then use)
  - Mitigation: Clear README with quickstart, example .env
  - Impact: User may abandon tool before first successful bookmark
- **🟢 LOW: Tag drift over time**
  - If user doesn't sync cache regularly, CLI and web tags diverge
  - Mitigation: Print last_sync date in tags:show, remind to sync
  - Impact: Duplicate tags with slight variations (e.g., "ai-agent" vs "ai-agents")

### Schedule Risks
- **🟢 LOW: LangChain version compatibility**
  - LangChain 0.2.x API may change (rapidly evolving library)
  - Mitigation: Pin versions in pyproject.toml
  - Impact: May need updates to extractor.py if API breaks

## Open Questions

### Resolved Questions (from Brooke)

1. **What happens if Diigo API returns duplicate tag error?** ✅ RESOLVED
   - **Decision**: Don't think Diigo cares, but run test to verify behavior
   - Action: Test sending "AI-Agent,ai-agent,AI_AGENT" in same request during implementation

2. **Should we support batch bookmark import from CSV/JSON?** ✅ RESOLVED
   - **Decision**: Low priority, later phase
   - Scope: Focus on one-at-a-time workflow for initial release

3. **How to handle bookmarks with no detectable author?** ✅ RESOLVED
   - **Decision**: Not an error - keep accessible log explaining missing metadata
   - Current approach: Skip author: tag entirely (no "author:unknown")

4. **Should tags:sync be automatic on first run?** ✅ RESOLVED
   - **Decision**: Error if cache missing, auto-sync on first time (with prompt), scheduled weekly syncs thereafter
   - UX: CLI exits with error and instructions; WebUI displays error message with sync button

5. **What's the maximum acceptable tag count per bookmark?** ✅ RESOLVED
   - **Decision**: No hard limit but suggest 12 as realistic
   - LLM will propose reasonable number, user can edit if needed

6. **Should we cache fetched page HTML locally to avoid re-fetching?** ✅ RESOLVED
   - **Decision**: Don't worry about it - too complex for initial release
   - Fetch page every time (performance is acceptable with <5s target)

7. **Do we need tags:top/latest/chrono commands?** ✅ RESOLVED
   - **Decision**: Implemented as `--show latest|top|chrono[logical] -n N` flags on tags:show
   - See AC10 for full specification

### Remaining Open Questions

8. **Tag normalization algorithm complexity** (Engineering/AI)
   - NLP/semantic detection for hyphen vs underscore distinction - how complex is this?
   - Fallback: Preserve hyphens, convert spaces to underscores if NLP too complex

9. **Does Diigo API support absolute tag replacement?** (Diigo API/Engineering)
   - Required for `tags:normalize` feature to transform tags across bookmarks
   - Need to test: Can we replace tag "ai_agent" with "ai-agent" across all bookmarks atomically?

10. **SQLite vs VectorDB for tag cache?** (Architecture/Engineering)
    - SQLite: Fast queries, familiar, lightweight
    - VectorDB: Similarity/context searches for better tag matching
    - Decision needed in architecture phase: Use both? Just SQLite initially?

## Next Steps

### Immediate Actions
1. ✅ **Create this BSA analysis file** (docs/features/diigo-cli-llm-assisted/01-bsa-analysis.md) - COMPLETED
2. ✅ **Update BSA with all stakeholder feedback** - COMPLETED
3. ⚠️ **Verify Diigo API key is available** (Brooke: check Diigo account settings)
4. ⚠️ **Verify LLM provider API keys available** (Brooke: check OpenAI/Anthropic/Google accounts)

### File Handoff
- **File saved**: `docs/features/diigo-cli-llm-assisted/01-bsa-analysis.md`
- **Handoff to**: System Architect (reads this file for architecture design)
- **Next file**: `02-architecture-design.md` (schema, API contracts, component design, database design)

### Key Architectural Decisions to Detail in 02-architecture-design.md
- SQLite schema for tag cache (or VectorDB, or both)
- LLM provider fallback implementation (LangChain abstractions)
- Model registry structure and sync mechanism
- Tag normalization algorithm (NLP/semantic detection)
- Service layer contracts (BookmarkService, TagService, etc.)
- REST API endpoints for WebUI
- Clean Diigo client interface (no MCP)

### Implementation Readiness
- ✅ Requirements are clear and testable (11 acceptance criteria with GIVEN-WHEN-THEN)
- ✅ All stakeholder questions resolved (7/7 answered)
- ✅ Dependencies identified and validated
- ✅ Architecture approach confirmed (layered design, SOLID, TDD)
- ⚠️ Some technical details need validation (Diigo API duplicate behavior, tag replacement support)
- ✅ Risks are manageable (no blockers, mitigations exist for HIGH/MEDIUM risks)
- **READY TO PROCEED** to architecture design phase (02-architecture-design.md)
