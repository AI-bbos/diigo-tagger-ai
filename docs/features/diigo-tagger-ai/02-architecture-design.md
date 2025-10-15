# System Architecture Design: Diigo Tagger AI

**Project**: diigo-tagger-ai
**Designed**: October 2025
**System Architect**: Claude
**Status**: Ready for Data Engineering
**Input**: `01-bsa-analysis.md`

---

## Executive Summary

**Purpose**: AI-powered CLI tool to automate Diigo bookmark saving with intelligent tag management, semantic search, and tag consistency enforcement.

**Core Architecture**:
- **Pattern**: Layered architecture with CLI → Service → Data layers
- **Database**: SQLite with FTS5 for wildcard search and optional embeddings for semantic search
- **LLM Integration**: Provider-agnostic with OpenAI primary, Anthropic fallback
- **CLI Framework**: Click with Rich terminal UI
- **Tag Reconciliation**: Three-tier matching (exact → fuzzy → semantic)

**Key Decisions**:
1. SQLite with FTS5 over external vector DB (simplicity for thousands of tags)
2. Click over argparse (better developer experience, Rich integration)
3. Alembic for schema migrations (maintainability)
4. Local sentence-transformers over OpenAI embeddings API (cost efficiency)
5. File-based configuration (.env) over OS keychain (portability)

---

## Architecture Decision Records (ADRs)

### ADR-001: SQLite with FTS5 for Tag Storage

**Context**: Need to store thousands of tags with wildcard and semantic search capabilities.

**Decision**: Use SQLite with FTS5 extension for full-text search and optional BLOB column for embeddings.

**Rationale**:
- **Simplicity**: Single file database, no external service dependencies
- **Performance**: FTS5 provides < 50ms wildcard search for thousands of tags
- **Embeddings**: Cosine similarity O(n) is acceptable for thousands (< 500ms)
- **Portability**: Database is a single file in `~/.diigo/tags.db`
- **Tooling**: Native Python sqlite3 support, SQLAlchemy ORM, Alembic migrations

**Alternatives Considered**:
- ❌ **PostgreSQL with pgvector**: Overkill for single-user, thousands of tags
- ❌ **ChromaDB/Weaviate**: External service complexity not justified for this scale
- ❌ **JSON file**: No wildcard search, no fuzzy matching, poor performance

**Consequences**:
- ✅ Zero configuration for users (no Docker, no external DB)
- ✅ Backup is simple (copy one file)
- ⚠️ Limited to ~1M tags (acceptable for personal use)
- ⚠️ Embeddings stored as BLOBs (not indexed, must scan all for semantic search)

**Status**: Accepted

---

### ADR-002: Click CLI Framework with Rich UI

**Context**: Need a CLI framework that's easy to use, well-documented, and integrates with modern terminal UI libraries.

**Decision**: Use Click for CLI commands and Rich for terminal formatting.

**Rationale**:
- **Click**:
  - Most popular Python CLI framework (17k GitHub stars)
  - Auto-generated help text from docstrings
  - Built-in parameter validation and type conversion
  - Composable command groups (`diigo tags:sync`, `diigo tags:search`)
- **Rich**:
  - Beautiful terminal output (tables, progress bars, colors)
  - Zero configuration, works out of the box
  - Graceful degradation on terminals without color support

**Alternatives Considered**:
- ❌ **argparse**: Verbose, manual help text, no Rich integration
- ❌ **Typer**: Newer, less mature, smaller ecosystem
- ❌ **Fire**: Too magical, unclear CLI interface from code

**Consequences**:
- ✅ Professional CLI UX matching modern tools (poetry, docker)
- ✅ Rich tables for tag search results
- ✅ Progress bars for tag sync
- ⚠️ Click is opinionated (good for consistency, limits flexibility)

**Status**: Accepted

---

### ADR-003: Alembic for Database Migrations

**Context**: Database schema will evolve (adding embedding columns, new indexes, performance optimizations).

**Decision**: Use Alembic for schema migrations with manual migration files (not auto-generate).

**Rationale**:
- **Industry standard**: Alembic is the Python equivalent of Liquibase/Flyway
- **Version control**: Migration files in git for reproducibility
- **Rollback support**: Can downgrade schema if needed
- **Manual control**: Auto-generate often produces incorrect migrations for SQLite

**Alternatives Considered**:
- ❌ **SQLAlchemy auto-create**: No migration history, can't evolve schema safely
- ❌ **Custom SQL scripts**: Reinventing the wheel, no version tracking
- ❌ **Alembic auto-generate**: Doesn't handle SQLite limitations (column renames, constraints)

**Consequences**:
- ✅ Safe schema evolution (users can upgrade without data loss)
- ✅ Clear migration history in git
- ⚠️ Requires discipline (must create migration for every schema change)
- ⚠️ Learning curve for team unfamiliar with Alembic

**Migration Strategy**:
```
alembic/
  versions/
    001_initial_schema.py       # Tags table, FTS5, indexes
    002_add_embeddings.py        # Add embedding BLOB column
    003_add_source_column.py     # Add source field (user|master|system)
```

**Status**: Accepted

---

### ADR-004: Local Embeddings (sentence-transformers) over API

**Context**: Semantic tag search requires vector embeddings. Options: generate locally or use OpenAI embeddings API.

**Decision**: Use sentence-transformers with MiniLM model (80MB) for local embedding generation.

**Rationale**:
- **Cost**: Zero ongoing cost (vs $0.0001 per 1k tokens for OpenAI)
- **Privacy**: Tag names stay local (no external API calls for embeddings)
- **Speed**: ~100 tags/sec on CPU, one-time generation
- **Offline**: Works without internet after initial download

**Alternatives Considered**:
- ❌ **OpenAI embeddings API**: $0.01-0.05 per month for thousands of tags (low but recurring)
- ❌ **Larger local models (SBERT)**: 500MB+, slower, diminishing returns for tag matching
- ❌ **No semantic search**: Limits discoverability (user might not find "version-control" when searching "git")

**Consequences**:
- ✅ One-time 80MB download (acceptable for modern systems)
- ✅ ~1 second load time on first semantic search
- ⚠️ Requires ~200MB RAM when model loaded
- ⚠️ User must approve download on first semantic search

**Model Details**:
- **Name**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384 (float32 = 1.5KB per tag)
- **Performance**: ~100 embeddings/sec on CPU
- **Storage**: 80MB model + ~3MB for 2000 tags (384 × 4 bytes × 2000)

**Status**: Accepted

---

### ADR-005: Provider-Agnostic LLM with Fallback Chain

**Context**: LLM inference for tag generation should support multiple providers for reliability and cost optimization.

**Decision**: Use LangChain with provider abstraction and fallback chain (OpenAI → Anthropic → Local).

**Rationale**:
- **Reliability**: If OpenAI API is down, fallback to Anthropic
- **Cost optimization**: Route expensive queries to cheaper models
- **Flexibility**: Easy to add Ollama/local models for offline use
- **LangChain benefits**: Unified interface, built-in retry logic, prompt templates

**Alternatives Considered**:
- ❌ **OpenAI SDK only**: Vendor lock-in, no fallback
- ❌ **Custom abstraction**: Reinventing the wheel, no retry/caching
- ❌ **LiteLLM**: Simpler but less ecosystem support than LangChain

**Configuration** (`~/.diigo-tagger.yml`):
```yaml
llm_providers:
  - provider: openai
    model: gpt-4o-mini
    priority: 1
    temperature: 0.2
  - provider: anthropic
    model: claude-3-haiku-20240307
    priority: 2
    temperature: 0.2
  - provider: ollama
    model: llama3.2
    priority: 3
    temperature: 0.2
```

**Fallback Logic**:
1. Try primary provider (priority 1)
2. If 429 rate limit or 5xx error, try next priority
3. If all providers fail, use rule-based heuristic (keyword matching from title)

**Consequences**:
- ✅ Resilience to API outages
- ✅ User can customize provider order
- ⚠️ Complexity: need API keys for multiple providers
- ⚠️ LangChain adds dependency weight (~10 packages)

**Status**: Accepted

---

### ADR-006: Three-Tier Tag Reconciliation Strategy

**Context**: LLM may propose tags that are similar to existing tags (typos, plurals, different separators).

**Decision**: Implement three-tier reconciliation: exact → fuzzy (Levenshtein) → semantic (cosine similarity).

**Rationale**:
- **Exact match**: Fast (O(1) hash lookup), catches perfect matches
- **Fuzzy match**: Catches typos and minor variations (git-workflow vs gitworkflow)
- **Semantic match**: Catches synonyms and related concepts (version-control → git-workflow)

**Algorithm**:
```python
def reconcile_tag(proposed: str, db: TagDatabase) -> tuple[str, str]:
    """
    Returns: (canonical_tag, match_type)
    Match types: "exact" | "fuzzy" | "semantic" | "new"
    """
    # Step 1: Exact match (case-insensitive)
    if exact := db.find_exact(proposed.lower()):
        return (exact, "exact")

    # Step 2: Fuzzy match (Levenshtein distance ≤ 2)
    if fuzzy := db.find_fuzzy(proposed, max_distance=2):
        return (fuzzy, "fuzzy")

    # Step 3: Semantic match (cosine similarity > 0.75)
    if semantic := db.find_semantic(proposed, threshold=0.75):
        return (semantic, "semantic")

    # No match: propose as new tag
    return (proposed, "new")
```

**Thresholds**:
- **Fuzzy**: Levenshtein distance ≤ 2 (allows 2 character edits)
- **Semantic**: Cosine similarity > 0.75 (high confidence only)

**User Experience**:
```
Reconciled tags:
  ✅ ai-agent           [exact match]
  ✅ git-workflow       [fuzzy: gitworkflow → git-workflow]
  ✅ version-control    [semantic: "vcs" → version-control]

Unknown tags (require approval):
  ⚠️ niche-topic
     Similar: topic-modeling (0.68), topic-analysis (0.65)
```

**Consequences**:
- ✅ Prevents tag drift automatically
- ✅ User learns correct tag names through reconciliation feedback
- ⚠️ Semantic matching requires embeddings (not available until first semantic search)
- ⚠️ High threshold (0.75) may miss valid matches (user can lower in config)

**Status**: Accepted

---

### ADR-007: File-Based Configuration (.env) over OS Keychain

**Context**: Need to store Diigo and OpenAI API credentials securely.

**Decision**: Use `.env` file in project root with file permissions 600, gitignored.

**Rationale**:
- **Simplicity**: No platform-specific code (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- **Portability**: Works on any platform where user can create files
- **Developer experience**: Standard practice in Python ecosystem (python-dotenv)
- **CI/CD friendly**: Easy to inject secrets via environment variables

**Security Measures**:
- `.env` added to `.gitignore` (prevent accidental commit)
- File permissions set to 600 (owner read/write only)
- Validation on startup (fail fast if credentials missing)
- Never log credentials or include in error messages

**Example `.env`**:
```bash
DIIGO_USER=brooke
DIIGO_PASS=your_password_here
DIIGO_API_KEY=your_api_key_here
OPENAI_API_KEY=sk-...
```

**Alternatives Considered**:
- ❌ **OS Keychain**: Platform-specific, complex API, harder to debug
- ❌ **Hardcoded in config file**: Insecure, easily committed to git
- ❌ **Prompt user on each run**: Tedious for daily use

**Consequences**:
- ✅ Standard Python practice (easy onboarding)
- ✅ Works on all platforms
- ⚠️ Credentials in plain text (user responsible for file security)
- ⚠️ Must remind users to never commit `.env` to git

**Status**: Accepted

---

## System Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                           │
│  (Click commands: save, tags:sync, tags:search, etc.)       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ BookmarkSvc  │  │ TagService   │  │ LLMService   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ DiigoClient  │  │ TagDatabase  │  │ LLMProvider  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                       Data Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  SQLite DB   │  │  Embeddings  │  │  HTTP APIs   │      │
│  │  (tags.db)   │  │  (in memory) │  │ (Diigo, LLM) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**CLI Layer** (`cli/`):
- Command parsing and validation (Click)
- User interaction and prompts (Rich)
- Progress bars and error formatting
- Configuration loading (.env, YAML)

**Service Layer** (`services/`):
- **BookmarkService**: Orchestrates save workflow (fetch → analyze → reconcile → save)
- **TagService**: Tag database operations (search, reconcile, merge)
- **LLMService**: Provider abstraction, fallback logic, prompt templates

**Data Layer** (`data/`):
- **TagDatabase**: SQLAlchemy ORM, Alembic migrations, FTS5 queries
- **DiigoClient**: Diigo API client (GET bookmarks, POST bookmark)
- **LLMProvider**: Provider-specific implementations (OpenAI, Anthropic, Ollama)

---

## Database Schema Design

### Tags Table (Primary Storage)

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,          -- Normalized tag name (lowercase, hyphens)
    count INTEGER DEFAULT 0,             -- Usage frequency
    last_used TIMESTAMP,                 -- Last time this tag was used
    source TEXT NOT NULL,                -- 'user' | 'master' | 'system'
    embedding BLOB,                      -- 384-dim float32 array (optional)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_tags_count ON tags(count DESC);
CREATE INDEX idx_tags_last_used ON tags(last_used DESC);
CREATE INDEX idx_tags_source ON tags(source);

-- FTS5 virtual table for wildcard search
CREATE VIRTUAL TABLE tags_fts USING fts5(
    name,
    content=tags,
    content_rowid=id
);

-- Triggers to keep FTS5 in sync
CREATE TRIGGER tags_ai AFTER INSERT ON tags BEGIN
    INSERT INTO tags_fts(rowid, name) VALUES (new.id, new.name);
END;

CREATE TRIGGER tags_ad AFTER DELETE ON tags BEGIN
    DELETE FROM tags_fts WHERE rowid = old.id;
END;

CREATE TRIGGER tags_au AFTER UPDATE ON tags BEGIN
    UPDATE tags_fts SET name = new.name WHERE rowid = old.id;
END;
```

### Tag Sources Explained

- **`user`**: Tags created by user (either manually or approved from LLM suggestions)
- **`master`**: Tags synced from Diigo (pre-existing taxonomy)
- **`system`**: Auto-generated tags (`source:*`, `author:*`)

### Embedding Storage Format

**Format**: BLOB containing 384 float32 values (1536 bytes per tag)

**Why BLOB**:
- SQLite doesn't support array types
- NumPy `tobytes()` for efficient serialization
- No index needed (cosine similarity requires full scan anyway)

**Memory Efficiency**:
- 2000 tags × 1.5KB = 3MB in database
- Loaded into memory for semantic search (~200MB with model)

---

## Data Flow Diagrams

### Bookmark Save Workflow

```
┌────────┐
│  User  │ diigo save <url>
└───┬────┘
    │
    ▼
┌────────────────┐
│ Fetch URL      │ requests.get(url)
│ Extract HTML   │ BeautifulSoup
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Parse Metadata │ title, author, desc, text sample
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ LLM Tag Gen    │ OpenAI → Anthropic → Ollama → Fallback
│ (provider      │ Input: metadata + 2000 chars
│  fallback)     │ Output: [tag1, tag2, ...]
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Tag Reconcile  │ For each tag:
│ (3-tier match) │   exact → fuzzy → semantic → new
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Add System Tags│ source:{domain}, author:{slug}
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Interactive    │ Show bookmark preview
│ Review         │ [Y/n/e] prompt (unless --no-interactive)
└───┬────────────┘
    │ (if edit)
    │ ┌────────────┐
    └─┤ User edits │ Reconcile again
      └────────────┘
    │ (if yes)
    ▼
┌────────────────┐
│ Save to Diigo  │ POST /api/v2/bookmarks
│                │ Retry 3x with backoff
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Update Tag DB  │ Increment count, update last_used
└────────────────┘
```

### Tag Sync Workflow

```
┌────────┐
│  User  │ diigo tags:sync --user brooke
└───┬────┘
    │
    ▼
┌────────────────┐
│ Paginate API   │ GET /api/v2/bookmarks?user=brooke&count=100
│ (100/page)     │ Loop until no more results
└───┬────────────┘
    │ [progress bar: 547/2134 bookmarks]
    ▼
┌────────────────┐
│ Aggregate Tags │ Deduplicate, count usage per tag
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Save to DB     │ Batch insert/update
│                │ Mark source='master'
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Generate       │ (if semantic search enabled)
│ Embeddings     │ sentence-transformers for all tags
└────────────────┘
```

### Semantic Tag Search Workflow

```
┌────────┐
│  User  │ diigo tags:similar "version control"
└───┬────┘
    │
    ▼
┌────────────────┐
│ Load Model     │ (if first time: download 80MB, ask user)
│ (lazy load)    │ sentence-transformers/all-MiniLM-L6-v2
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Embed Query    │ "version control" → [0.12, -0.45, ...]
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Load All       │ SELECT embedding FROM tags
│ Embeddings     │ WHERE embedding IS NOT NULL
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Cosine         │ For each tag:
│ Similarity     │   score = dot(query_emb, tag_emb) / (norm(q) * norm(t))
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Sort & Filter  │ threshold > 0.75, top 10 results
└───┬────────────┘
    │
    ▼
┌────────────────┐
│ Display Table  │ Rich table: tag | score | count | last_used
└────────────────┘
```

---

## API Integration Design

### Diigo API Client

**Endpoints**:
```python
class DiigoClient:
    def __init__(self, user: str, password: str, api_key: str):
        self.base_url = "https://secure.diigo.com/api/v2"
        self.auth = HTTPBasicAuth(user, password)
        self.api_key = api_key

    def get_bookmarks(self, user: str, count: int = 100, start: int = 0) -> list[dict]:
        """Paginate through user's bookmarks."""
        params = {"user": user, "count": count, "start": start, "key": self.api_key}
        resp = requests.get(f"{self.base_url}/bookmarks", auth=self.auth, params=params)
        resp.raise_for_status()
        return resp.json()

    def create_bookmark(self, url: str, title: str, tags: list[str], desc: str = "", shared: str = "no") -> dict:
        """Save bookmark to Diigo (idempotent)."""
        data = {
            "key": self.api_key,
            "url": url,
            "title": title,
            "tags": ",".join(tags),  # CSV format
            "desc": desc,
            "shared": shared
        }
        resp = requests.post(f"{self.base_url}/bookmarks", auth=self.auth, data=data)
        resp.raise_for_status()
        return resp.json()
```

**Error Handling**:
- **Retry logic**: 3 attempts with exponential backoff (1s, 2s, 4s)
- **Rate limiting**: Detect 429, wait and retry
- **Network errors**: Catch `requests.RequestException`, show friendly message
- **Invalid credentials**: Fail fast on 401/403 with clear instructions

### LLM Provider Abstraction

**LangChain Integration**:
```python
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage

class LLMService:
    def __init__(self, config: dict):
        self.providers = self._init_providers(config)

    def generate_tags(self, title: str, author: str, description: str, content_sample: str) -> list[str]:
        """Generate tags using provider fallback chain."""
        prompt = self._build_prompt(title, author, description, content_sample)

        for provider in self.providers:
            try:
                response = provider.invoke(prompt)
                return self._parse_tags(response.content)
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue

        # All providers failed, use fallback heuristic
        return self._heuristic_fallback(title)

    def _build_prompt(self, title, author, desc, sample) -> list[Message]:
        system = SystemMessage(content="""
        You are a bookmark tagging assistant. Generate 5-10 relevant tags for this content.
        Rules:
        - Use lowercase with hyphens (e.g., machine-learning)
        - Prefer existing tags when possible
        - Include technical topics, frameworks, concepts
        - Return comma-separated list only, no explanation
        """)

        user = HumanMessage(content=f"""
        Title: {title}
        Author: {author}
        Description: {desc}
        Content sample: {sample[:2000]}

        Tags:
        """)

        return [system, user]

    def _parse_tags(self, response: str) -> list[str]:
        """Parse LLM response into tag list."""
        # Handle various formats: "tag1, tag2, tag3" or "- tag1\n- tag2"
        tags = re.split(r'[,\n]', response)
        return [t.strip().strip('-').strip() for t in tags if t.strip()]

    def _heuristic_fallback(self, title: str) -> list[str]:
        """Rule-based tag generation when all LLMs fail."""
        # Extract keywords from title (simple TF-IDF or keyword matching)
        # Better than nothing, but inferior to LLM
        pass
```

**Provider Configuration**:
```yaml
# ~/.diigo-tagger.yml
llm_providers:
  - provider: openai
    model: gpt-4o-mini
    priority: 1
    temperature: 0.2
    max_tokens: 150

  - provider: anthropic
    model: claude-3-haiku-20240307
    priority: 2
    temperature: 0.2
    max_tokens: 150
```

---

## Performance & Scalability Analysis

### Tag Storage Scaling

**Current Design (SQLite + FTS5)**:

| Tags Count | DB Size | FTS5 Index | Embeddings | Wildcard Search | Semantic Search |
|------------|---------|------------|------------|-----------------|-----------------|
| 1,000      | 50KB    | 20KB       | 1.5MB      | < 10ms          | < 100ms         |
| 10,000     | 500KB   | 200KB      | 15MB       | < 50ms          | < 500ms         |
| 100,000    | 5MB     | 2MB        | 150MB      | < 100ms         | < 2s            |
| 1,000,000  | 50MB    | 20MB       | 1.5GB      | < 500ms         | < 10s           |

**Bottlenecks**:
- **Semantic search**: O(n) cosine similarity (no vector index)
  - Acceptable for < 100k tags (< 2s)
  - Would need specialized vector DB (ChromaDB, Weaviate) for > 100k
- **Embedding storage**: 1.5KB per tag (1.5GB for 1M tags)
  - Acceptable for modern systems (8GB+ RAM)

**Why This is Sufficient**:
- **Target use case**: Thousands of tags (Brooke's scale)
- **Personal tool**: Not multi-tenant, not serving millions of users
- **Graceful degradation**: If user has > 100k tags, semantic search becomes slow but still works

### LLM Inference Performance

**Latency Breakdown** (95th percentile):
```
Fetch URL:           500ms  (network)
Parse HTML:          100ms  (BeautifulSoup)
LLM inference:       2000ms (OpenAI API)
Tag reconciliation:  50ms   (exact + fuzzy + semantic)
Save to Diigo:       500ms  (network)
Update tag DB:       10ms   (SQLite write)
──────────────────────────
Total:               ~3.2s
```

**Optimization Strategies**:
- **Caching**: Cache LLM responses for same URL (TTL: 24 hours)
- **Async I/O**: Fetch URL and load embedding model in parallel
- **Batch mode**: `--no-interactive` skips user review (save ~2s UX time)

### Concurrency & Thread Safety

**Current Design**: Single-threaded (acceptable for CLI tool)

**Future Enhancements** (if needed):
- SQLite WAL mode for concurrent reads
- Process pool for batch bookmark processing
- Async LLM calls (aiohttp + asyncio)

---

## Security Architecture

### Threat Model

**Assets to Protect**:
1. Diigo credentials (username, password, API key)
2. OpenAI API key
3. User's bookmark data (URLs, titles, tags)
4. Tag database (intellectual property)

**Threat Actors**:
1. **Accidental exposure**: User commits `.env` to public GitHub repo
2. **Local file access**: Malicious script reads `.env` or `tags.db`
3. **Network interception**: Man-in-the-middle attack on API calls
4. **Prompt injection**: Malicious HTML in fetched page tricks LLM

### Security Controls

**Credential Protection**:
- ✅ `.env` in `.gitignore` (prevent accidental commit)
- ✅ File permissions 600 (owner read/write only)
- ✅ Validate on startup (fail fast if missing)
- ✅ Never log credentials or include in error messages
- ⚠️ Plain text storage (user responsible for file security)
- ❌ No OS keychain integration (future enhancement)

**API Security**:
- ✅ HTTPS only (reject HTTP)
- ✅ Bearer token for OpenAI (industry standard)
- ✅ HTTP Basic Auth for Diigo (per Diigo spec)
- ⚠️ No certificate pinning (trust OS cert store)

**Data Privacy**:
- ✅ Local database only (no sync to cloud)
- ✅ LLM context limited to 2000 chars (no full HTML)
- ✅ Tag names only in DB (no bookmark content)
- ⚠️ LLM providers see metadata (title, author, sample)

**Prompt Injection Mitigation**:
- ✅ Structured prompts with clear delimiters
- ✅ System message enforces output format (tags only)
- ✅ Temperature 0.2 (reduces hallucination)
- ⚠️ No content filtering (assume fetched URLs are trusted)

### Dependency Security

**Supply Chain**:
- ✅ Poetry lock file (pinned versions)
- ✅ `poetry audit` in CI/CD
- ✅ Official PyPI only (no custom repos)
- ⚠️ No SBOM generation (future enhancement)

**Vulnerability Scanning**:
```bash
# Run on every commit
poetry audit
# Run weekly
poetry update --dry-run  # Check for updates
```

---

## Open Questions & Handoff

### Resolved Questions

1. ✅ **Database location**: `~/.diigo/tags.db` (simple, user-writable)
2. ✅ **Embedding storage format**: BLOB with NumPy `tobytes()` (efficient, standard)
3. ✅ **Migration strategy**: Alembic with manual migrations (control + safety)

### New Questions for Data Engineer

1. **Alembic auto-generate or manual?**
   - Recommendation: Manual (SQLite has limitations, auto-generate often fails)
   - Data Engineer should validate this recommendation

2. **WAL mode for SQLite?**
   - Recommendation: Enable WAL (better concurrency, safer writes)
   - Data Engineer should benchmark performance impact

3. **Embedding re-generation strategy?**
   - When user updates to better embedding model, how to migrate?
   - Recommendation: Add `embedding_version` column, background migration task

### For Security Engineer

4. **Credential rotation policy?**
   - How often should user rotate API keys?
   - Should tool warn if keys are > 90 days old?

5. **OS keychain integration?**
   - Worth the complexity for v1.0, or defer to v1.1?
   - Recommendation: Defer (simplicity for MVP)

### For QAS Engineer

6. **Test data generation?**
   - Need synthetic bookmark dataset for E2E tests
   - Should we scrape real Diigo data (Brooke's bookmarks) or generate fake data?

---

## Next Steps

### Data Engineer Tasks

1. **Create Alembic migrations**:
   - `001_initial_schema.py`: Tags table, FTS5, indexes
   - `002_add_embeddings.py`: Add embedding BLOB column
   - Test upgrade/downgrade paths

2. **Benchmark SQLite performance**:
   - FTS5 wildcard search with 10k tags
   - Semantic search with 10k embeddings
   - Write performance (batch insert 1k tags)

3. **Design backup strategy**:
   - Recommend users add `~/.diigo/tags.db` to Time Machine/cloud backup
   - Add `diigo tags:export` command to dump CSV for manual backup

### Handoff

- **Input file**: `docs/features/diigo-tagger-ai/01-bsa-analysis.md` (BSA analysis)
- **Output file**: `docs/features/diigo-tagger-ai/02-architecture-design.md` (this file)
- **Ready for**: Data Engineer
- **Next agent should produce**: `docs/features/diigo-tagger-ai/03-data-engineering-plan.md`

---

**System Architect Sign-off**: Architecture design is complete, scalable to target use case (thousands of tags), secure for single-user personal tool. Core decisions documented in ADRs. Ready for data engineering implementation.
