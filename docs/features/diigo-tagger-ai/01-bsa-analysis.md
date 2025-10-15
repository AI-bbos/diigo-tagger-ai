# BSA Analysis: Diigo Tagger AI

**Project**: diigo-tagger-ai
**Analyzed**: October 2025
**BSA**: Claude
**Status**: Ready for Architecture Review

---

## Business Context

### Business Need
Managing thousands of bookmarks in Diigo with consistent, discoverable tags is manually intensive and error-prone. Users spend significant time:
- Manually extracting metadata (title, author, description) from URLs
- Deciding which tags to apply from thousands of existing tags
- Dealing with tag drift and inconsistency (git-workflow vs gitworkflow vs git_workflow)
- Unable to find related tags semantically (version-control when they mean git-workflow)

**Solution**: AI-powered CLI tool that automates metadata extraction, enforces tag consistency, and provides semantic tag discovery.

### Stakeholders
- **Primary User**: Brooke (power user with thousands of Diigo bookmarks)
- **Secondary Users**: Future power users managing large bookmark collections
- **Internal**: Development team (maintenance, future enhancements)
- **External**:
  - Diigo API (integration dependency)
  - OpenAI API (LLM inference dependency)

### Success Metrics
- **Time savings**: < 30 seconds from URL to saved bookmark (vs 2-3 minutes manual)
- **Tag consistency**: 95%+ reuse of existing tags (vs creating duplicates)
- **Semantic discovery**: Find related tags in < 1 second
- **Accuracy**: 90%+ of LLM-proposed tags accepted without edits
- **Adoption**: Daily usage for all new bookmarks

---

## Technical Requirements

### Data Requirements

**Tag Database (Local SQLite)**:
- **Storage**: `~/.diigo/tags.db`
- **Schema**: Tags table with FTS5 and optional embeddings
- **Volume**: Thousands of tags initially, growing over time
- **Fields**:
  - `name` (TEXT, unique, normalized)
  - `count` (INTEGER, usage frequency)
  - `last_used` (TIMESTAMP)
  - `source` (TEXT: 'user' | 'master' | 'system')
  - `embedding` (BLOB, 384-dim float32 array, optional)
- **Indexes**:
  - B-tree on name, count
  - FTS5 for wildcard search
  - No index on embeddings (cosine similarity is O(n), acceptable for thousands)
- **Retention**: Permanent (user's personal knowledge base)

**Tag Cache Requirements**:
- One-time bulk sync from Diigo API
- Incremental updates after each save
- No PII or bookmark content (just tag names)

**Session State** (in-memory):
- Current bookmark being processed
- LLM responses
- User edits during interactive review

### API Requirements

**Diigo API Integration**:
- `GET /api/v2/bookmarks` - One-time tag sync
  - Pagination: 100 per page
  - Auth: HTTP Basic + API key
  - Rate limit: Unknown (implement exponential backoff)
  - Response: JSON array of bookmark objects
- `POST /api/v2/bookmarks` - Save new bookmark
  - Auth: HTTP Basic + API key
  - Payload: url, title, tags (CSV), desc, shared
  - Idempotent: Updates if URL exists
  - Response: 200 OK with bookmark object

**OpenAI API Integration**:
- `POST /v1/chat/completions` - Tag generation
  - Model: gpt-4o-mini (primary)
  - Fallback: Local heuristic (keyword matching)
  - Prompt: System + user template with context
  - Temperature: 0.2 (deterministic tags)
  - Max tokens: 150 (tags only)
  - Rate limit: Handle 429 with retry

**Provider-Agnostic LLM** (Future):
- Support multiple providers: OpenAI, Anthropic, Local (Ollama)
- Priority sorting with fallback chain
- Configuration: `~/.diigo-tagger.yml` with provider list

### CLI Requirements

**Framework**: Click (most popular Python CLI, 17k⭐)
- Better than argparse: auto-help, parameter types, validation
- Rich integration: progress bars, colors, tables

**Commands**:
```bash
diigo save <url|text>              # Save bookmark
diigo tags:sync --user <username>  # One-time sync
diigo tags:search <pattern>        # Wildcard search
diigo tags:similar <query>         # Semantic search
diigo tags:show                    # List all tags
diigo tags:merge <from> <to>       # Manual merge (v1.1)
```

**Flags**:
- `--dry-run`: Show payload, don't save
- `--no-interactive`: Skip review (batch mode)
- `--allow-new-tags`: Permit unknown tags
- `--force`: Auto-approve (combine with --no-interactive)
- `--desc <text>`: Override description

### UI Requirements

**Terminal UI** (Rich library):
- **Progress indicators**: Tag sync, LLM inference, save operations
- **Color coding**:
  - Green: Validated tags
  - Yellow: Unknown tags (require approval)
  - Red: Errors
  - Blue: System tags (source:*, author:*)
- **Tables**: Tag search results with count + last used
- **Interactive prompts**: [Y/n/e] with clear instructions
- **Error formatting**: Friendly, actionable error messages

**Interactive Flow**:
```
Proposed bookmark:

URL:    https://example.com/article
Title:  How to Train Your AI
Author: Jane Doe
Desc:   A comprehensive guide...

Tags:   ai-agent, machine-learning, training,
        source:example.com, author:jane-doe

Unknown tags (will be added):
  - training → Similar: ai-training, model-training

Save to Diigo? [Y/n/e]: _
```

### Security Requirements

**Credential Management**:
- **Storage**: `.env` file in project root (gitignored)
- **Required variables**:
  - `DIIGO_USER` (username)
  - `DIIGO_PASS` (password, plain text - Diigo doesn't support hashing)
  - `DIIGO_API_KEY` (from Diigo settings)
  - `OPENAI_API_KEY` (from OpenAI dashboard)
- **Validation**: Fail fast at startup if missing
- **Never log**: Credentials, API keys, or API responses containing them

**API Security**:
- **Diigo**: HTTP Basic Auth + API key in query param (per Diigo spec)
- **OpenAI**: Bearer token in Authorization header
- **HTTPS only**: Reject HTTP endpoints
- **No caching**: Don't cache responses containing auth

**Data Privacy**:
- **Local storage**: All data in `~/.diigo/tags.db` (user-owned, no sync)
- **No telemetry**: Zero usage tracking or analytics
- **Cache contents**: Public tag names only (no bookmark URLs, titles, or content)
- **LLM context**: Send only metadata needed for tagging (title, author, 2000-char sample)
- **Never send**: Full HTML, PII from page content, user's other bookmarks

**Dependency Security**:
- **Lock file**: Poetry lock for reproducible builds
- **Audit**: Run `poetry audit` in CI/CD
- **Pin versions**: All deps pinned in `pyproject.toml`
- **Supply chain**: Verify checksums, use official PyPI only

### Performance Requirements

**Tag Search**:
- **Wildcard** (`*commit*`): < 50ms for thousands of tags (FTS5)
- **Fuzzy** (Levenshtein ≤2): < 100ms
- **Semantic** (cosine similarity): < 500ms (acceptable for interactive use)

**Tag Sync**:
- **Initial sync**: 1-5 minutes for thousands of bookmarks (one-time)
- **Progress**: Real-time progress bar with ETA

**Bookmark Save**:
- **End-to-end**: < 10 seconds (fetch + analyze + LLM + save)
- **LLM inference**: < 3 seconds (gpt-4o-mini is fast)
- **Network**: < 2 seconds per API call (retry on timeout)

**Resource Usage**:
- **Memory**: < 200MB (embeddings in memory if semantic search enabled)
- **Disk**: ~100MB (80MB model + DB)
- **Startup**: < 2 seconds (lazy-load embedding model)

---

## Acceptance Criteria

### AC1: URL-based Bookmark Save
```
GIVEN a valid URL
WHEN user runs `diigo save <url>`
THEN the tool fetches the page, extracts metadata, proposes tags, and saves to Diigo
AND the user sees an interactive review prompt
AND validated tags reuse existing tags from the database
```

### AC2: Tag Sync from Diigo
```
GIVEN Diigo credentials are configured
WHEN user runs `diigo tags:sync --user <username>`
THEN the tool fetches ALL bookmarks via paginated API
AND aggregates all tag names with usage counts
AND saves to SQLite database at ~/.diigo/tags.db
AND displays progress with bookmark count and ETA
```

### AC3: Wildcard Tag Search
```
GIVEN thousands of tags in the database
WHEN user runs `diigo tags:search "*commit*"`
THEN the tool returns matching tags in < 50ms
AND results are sorted by usage count (most frequent first)
AND displays in a formatted table with count and last used date
```

### AC4: Semantic Tag Search
```
GIVEN embeddings are generated for all tags
WHEN user runs `diigo tags:similar "version control"`
THEN the tool returns semantically similar tags (git-workflow, github-issues, etc.)
AND results are sorted by cosine similarity score
AND displays in < 500ms
```

### AC5: Interactive Tag Review
```
GIVEN LLM proposes tags with some unknown tags
WHEN the interactive prompt shows the bookmark
THEN the user can choose [Y]es to save, [n]o to cancel, or [e]dit tags
AND if user edits tags, reconciliation re-runs before saving
AND unknown tags are highlighted with similar alternatives
```

### AC6: Tag Reconciliation
```
GIVEN LLM proposes tag "gitworkflow"
WHEN reconciliation runs
THEN it matches to existing "git-workflow" via fuzzy match (Levenshtein=2)
AND replaces the proposed tag with the existing canonical tag
AND the user never sees the typo version
```

### AC7: System Tags Auto-Generation
```
GIVEN a bookmark with URL "https://example.com/article" and author "Jane Doe"
WHEN tags are prepared for save
THEN system tags are automatically added: "source:example.com" and "author:jane-doe"
AND author slug is normalized (lowercase, hyphens, no special chars)
```

### AC8: Dry Run Mode
```
GIVEN user runs `diigo save <url> --dry-run`
WHEN the workflow completes
THEN the tool shows the exact Diigo API payload
AND does NOT make any API call
AND user can verify tags before actual save
```

### AC9: Batch Mode (Non-Interactive)
```
GIVEN user runs `diigo save <url> --no-interactive --force`
WHEN the workflow completes
THEN tags are auto-approved without user review
AND saves directly to Diigo
AND suitable for automation/scripting
```

### AC10: Error Handling
```
GIVEN network failure or API error occurs
WHEN the tool encounters the error
THEN it retries 3x with exponential backoff
AND shows clear error message if all retries fail
AND does NOT lose user's work (can retry manually)
```

---

## Dependencies

### Infrastructure
- **Local system**: macOS/Linux with Python 3.10+
- **Database**: SQLite 3.35+ (for FTS5)
- **Network**: HTTPS access to Diigo and OpenAI APIs

### External Services
- **Diigo API**: v2, requires account + API key
- **OpenAI API**: GPT-4o-mini, requires API key + credits
- **DNS/CDN**: For fetching bookmark URLs

### Python Dependencies
- **Core**:
  - SQLAlchemy 2.0 (ORM)
  - Alembic (migrations)
  - Click (CLI framework)
  - python-dotenv (env loading)
  - requests (HTTP client)
- **AI/ML**:
  - LangChain (LLM abstractions)
  - OpenAI Python SDK
  - sentence-transformers (optional, for semantic search)
  - tiktoken (token counting)
- **Parsing**:
  - BeautifulSoup4 (HTML parsing)
  - lxml (XML/HTML parser backend)
- **UI**:
  - Rich (terminal formatting, optional but recommended)
- **Dev**:
  - pytest (testing)
  - black (formatting)
  - ruff (linting)

### Data Prerequisites
- **Initial tag sync**: Must run `tags:sync` once before first bookmark save
- **Embeddings**: Generated on-demand when semantic search first used

---

## Assumptions

### Technical Assumptions
- ✅ **SQLite FTS5 available**: Validated - Python 3.10+ includes it
- ✅ **Poetry for dependency management**: Brooke uses Poetry
- ⚠️ **Diigo API has no rate limits**: UNVALIDATED - need to monitor and implement backoff
- ⚠️ **OpenAI API costs acceptable**: UNVALIDATED - estimate $0.01-0.05 per bookmark with gpt-4o-mini
- ⚠️ **sentence-transformers model acceptable**: 80MB download, loads in ~1 sec - need user approval
- ❌ **Multi-provider LLM fallback**: BLOCKER for v1.0 - keep simple, add in v1.1

### Business Assumptions
- ✅ **Brooke has thousands of tags**: Validated from conversation
- ✅ **Tag reuse is critical**: Validated - prevents drift
- ⚠️ **Daily usage expected**: UNVALIDATED - will determine if async/batch features needed
- ⚠️ **Command-line acceptable**: UNVALIDATED - may want web UI later

### Scope Assumptions
- ✅ **Single user (not multi-tenant)**: Validated - personal tool
- ✅ **Read-only on Diigo after sync**: Validated - doesn't delete/modify bookmarks
- ⚠️ **English content only**: UNVALIDATED - may need i18n for tags
- ⚠️ **URLs must be publicly accessible**: UNVALIDATED - what about auth-gated content?

### Resource Assumptions
- ✅ **User has OpenAI API access**: Validated
- ✅ **User has Diigo API key**: Validated
- ⚠️ **Sufficient disk space**: UNVALIDATED - need ~200MB for model + DB

---

## Risks & Concerns

### Technical Risks
- **Diigo API reliability**: No SLA, could break without notice
  - *Mitigation*: Graceful degradation, clear error messages
- **LLM hallucination**: May propose nonsensical tags
  - *Mitigation*: Reconciliation blocks unknown tags by default
- **Tag explosion**: User might accept too many new tags
  - *Mitigation*: Warn if >20 tags, require explicit `--allow-new-tags`
- **Embedding model size**: 80MB download on first run
  - *Mitigation*: Make semantic search optional, warn user
- **Database corruption**: SQLite can corrupt on hard crash
  - *Mitigation*: WAL mode, regular backups (user responsibility)

### Security Risks
- **Plain-text credentials**: .env file contains passwords
  - *Mitigation*: Gitignore, file permissions 600, warn user
- **API key exposure**: Could leak in logs or error messages
  - *Mitigation*: Never log credentials, redact in error output
- **Prompt injection**: Malicious page could inject instructions in HTML
  - *Mitigation*: Limited context (2000 chars), structured prompt templates

### Business Risks
- **Low adoption**: User might prefer manual tagging
  - *Mitigation*: Make it 10x faster than manual, high accuracy
- **Tag taxonomy drift**: User might stop using tags consistently
  - *Mitigation*: Reconciliation enforces consistency by default
- **Vendor lock-in**: Tied to OpenAI and Diigo
  - *Mitigation*: Provider-agnostic LLM in v1.1, Diigo alternatives later

### Schedule Risks
- **Multi-agent coordination complexity**: 7-agent workflow could delay
  - *Mitigation*: Follow agent handoff protocol, file-based state
- **Alembic migration learning curve**: If team unfamiliar
  - *Mitigation*: Comprehensive docs, example migrations
- **LangGraph learning curve**: New orchestration framework
  - *Mitigation*: Start with simple pipeline, add LangGraph if needed

---

## Open Questions

### For Brooke (Product Decisions)
1. **LLM provider priority order**: OpenAI first, then Anthropic, then local? Or different order?
   - *Who can answer*: Brooke (based on API cost vs quality tradeoff)

2. **Tag merge strategy**: Start manual, but when to auto-merge?
   - *Who can answer*: Brooke (after using manual merge for a few weeks)

3. **Max tags per bookmark**: Warn at >20, or hard limit?
   - *Who can answer*: Brooke (what does your Diigo history show as reasonable?)

4. **Auth-gated content**: Support cookies/auth for fetching private URLs?
   - *Who can answer*: Brooke (is this a common use case?)

### For System Architect
5. **Database location**: `~/.diigo/tags.db` or `~/.local/share/diigo-tagger/tags.db` (XDG)?
   - *Who can answer*: System Architect (follow platform conventions)

6. **Embedding storage format**: NumPy binary, or base64 in SQLite?
   - *Who can answer*: System Architect (benchmark performance)

7. **Migration strategy**: Alembic auto-generate or manual?
   - *Who can answer*: Data Engineer (maintainability vs control)

### For Security Engineer
8. **Credential storage**: Plain .env, or OS keychain integration?
   - *Who can answer*: Security Engineer (balance convenience vs security)

9. **API key rotation**: How often should user rotate keys?
   - *Who can answer*: Security Engineer (risk assessment)

---

## Next Steps

### Immediate Actions Required
1. **Confirm OpenAI API budget**: Estimate monthly cost for daily usage
2. **Confirm LLM provider priority**: OpenAI, Anthropic, local - in what order?
3. **Resolve embedding model**: Accept 80MB download, or use OpenAI embeddings API?
4. **Database location**: Choose path convention (Architect decides)

### Handoff
- **File saved**: `docs/features/diigo-tagger-ai/01-bsa-analysis.md`
- **Ready for**: System Architect
- **Architect should read**: This file + existing `docs/ARCHITECTURE_DESIGN.md`
- **Architect should produce**:
  - Refined schema design
  - LangGraph agent orchestration plan
  - Component interaction diagrams
  - File: `docs/features/diigo-tagger-ai/02-architecture-design.md`

---

**BSA Sign-off**: Ready for architecture review. Core requirements are clear, assumptions documented, risks identified. Open questions flagged for appropriate stakeholders.
