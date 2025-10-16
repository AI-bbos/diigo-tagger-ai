# Diigo Tagger AI - Architecture Design Document

**Project**: diigo-tagger-ai
**Version**: 1.0.0
**Date**: October 2025
**Author**: Claude (with Brooke)
**Status**: Design Phase - Pre-Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Agent Orchestration Architecture](#agent-orchestration-architecture)
4. [Data Architecture](#data-architecture)
5. [Component Design](#component-design)
6. [API Contracts](#api-contracts)
7. [Security & Privacy](#security--privacy)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Strategy](#deployment-strategy)
10. [Future Enhancements](#future-enhancements)

---

## Executive Summary

### Problem Statement
Managing thousands of bookmarks in Diigo with consistent, discoverable tags is manually intensive and error-prone. Users face:
- Tag drift and inconsistency (git-workflow vs gitworkflow vs git_workflow)
- No semantic search for finding related tags
- Manual metadata extraction from URLs
- Difficulty maintaining a coherent taxonomy with thousands of tags

### Solution
An AI-powered CLI tool that:
1. Extracts metadata (title, author, description) from URLs automatically
2. Generates contextually appropriate tags using LLM reasoning
3. Enforces tag consistency through intelligent reconciliation
4. Provides semantic search over thousands of existing tags
5. Validates quality before saving to Diigo

### Key Design Decisions
- **Multi-Agent Architecture**: LangGraph orchestration with specialized agents
- **Hybrid Storage**: SQLite + FTS5 + optional vector embeddings
- **Schema Management**: Alembic migrations for database evolution
- **LLM Strategy**: GPT-4o-mini for speed/cost, with fallback to heuristics
- **Local-First**: Zero external dependencies beyond OpenAI API

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER (CLI)                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                           │
│                      (LangGraph)                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Extraction   │→ │ Tag Intel    │→ │ Interactive  │          │
│  │ Agent        │  │ Agent        │  │ Agent        │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ SQLite DB    │  │ Vector Index │  │ Tag Cache    │          │
│  │ (Tags)       │  │ (Embeddings) │  │ (Session)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                              │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ Diigo API    │  │ OpenAI API   │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Core**:
- Python 3.10+
- SQLAlchemy 2.0 (ORM)
- Alembic (migrations)
- LangGraph (agent orchestration)
- LangChain (LLM abstractions)

**AI/ML**:
- OpenAI GPT-4o-mini (primary LLM)
- sentence-transformers (semantic search, optional)
- tiktoken (token counting)

**Storage**:
- SQLite with FTS5 (full-text search)
- NumPy (embedding storage/comparison)

**CLI/UX**:
- argparse (CLI framework)
- rich (terminal formatting, optional)

**External APIs**:
- Diigo API v2 (bookmark management)
- OpenAI API (LLM inference)

---

## Agent Orchestration Architecture

### Design Philosophy

**Separation of Concerns**: Each agent has a single, well-defined responsibility
**Composability**: Agents can be added/removed without affecting others
**Observability**: State changes are tracked through LangGraph's state management
**Fault Tolerance**: Agent failures don't crash the entire pipeline

### Agent Graph (v1.0)

```python
# State definition
class BookmarkState(TypedDict):
    # Input
    user_input: str                    # URL or free text

    # Extraction Agent outputs
    url: str
    raw_html: str
    page_title: str
    page_author: Optional[str]
    page_description: str
    content_sample: str

    # Tag Intelligence Agent outputs
    proposed_tags: list[str]           # LLM-generated tags
    validated_tags: list[str]          # After reconciliation
    unknown_tags: list[str]            # Not in DB, flagged
    system_tags: list[str]             # source:*, author:*
    similar_tags: dict[str, list[str]] # Semantic matches

    # Interactive Agent outputs
    user_approved: bool
    user_edits: Optional[str]
    final_tags: list[str]

    # QA outputs
    qa_passed: bool
    qa_warnings: list[str]
    qa_errors: list[str]

    # Final payload
    diigo_payload: dict
    save_result: dict
```

### Agent Definitions

#### 1. **Extraction Agent**
**Responsibility**: Fetch and parse content from URL or free text

**Inputs**:
- `user_input`: URL or text prompt

**Outputs**:
- `url`: Canonical URL (empty if free text)
- `raw_html`: Page HTML
- `page_title`: Extracted title
- `page_author`: Detected author (if available)
- `page_description`: Meta description or first paragraph
- `content_sample`: First 2000 chars for LLM context

**Tools**:
- `fetch_url(url) -> html`
- `parse_html(html) -> metadata`
- `extract_author(html) -> author`

**Error Handling**:
- Network errors → Retry 3x with backoff
- Parse errors → Log and use partial data
- Free-text mode → Skip fetch, synthesize metadata

---

#### 2. **Tag Intelligence Agent**
**Responsibility**: Generate, reconcile, and validate tags

**Sub-Tasks**:
1. **Generation**: Call LLM with prompt template
2. **Reconciliation**: Match against existing tags using fuzzy + semantic search
3. **Validation**: Enforce naming conventions and required tags

**Inputs**:
- Extraction Agent outputs (title, author, content, URL)
- Tag database (existing tags with embeddings)
- Master tag list (from config)

**Outputs**:
- `proposed_tags`: Raw LLM output
- `validated_tags`: Matched to existing tags
- `unknown_tags`: Not found in DB (require user approval)
- `system_tags`: Auto-generated `source:domain`, `author:slug`
- `similar_tags`: Semantic alternatives for each unknown tag

**Tools**:
- `generate_tags_llm(context) -> tags`
- `search_tags_fuzzy(pattern) -> matches`
- `search_tags_semantic(query) -> matches`
- `normalize_tag(tag) -> normalized`
- `validate_tag_format(tag) -> bool`

**Reconciliation Algorithm**:
```python
for tag in llm_output:
    normalized = normalize_tag(tag)

    # 1. Exact match
    if normalized in existing_tags:
        validated_tags.append(normalized)
        continue

    # 2. Fuzzy match (Levenshtein distance < 2)
    fuzzy_matches = search_tags_fuzzy(normalized, max_distance=2)
    if len(fuzzy_matches) == 1:
        validated_tags.append(fuzzy_matches[0])
        continue

    # 3. Semantic match (cosine similarity > 0.85)
    semantic_matches = search_tags_semantic(normalized, threshold=0.85)
    if len(semantic_matches) == 1:
        validated_tags.append(semantic_matches[0])
        continue

    # 4. Multiple matches or no matches
    unknown_tags.append(normalized)
    similar_tags[normalized] = fuzzy_matches + semantic_matches
```

---

#### 3. **Interactive Agent** (Optional, default enabled)
**Responsibility**: Human-in-the-loop review and editing

**Inputs**:
- All previous agent outputs
- `--no-interactive` flag (skip if true)

**Outputs**:
- `user_approved`: bool
- `user_edits`: Optional comma-separated tag string
- `final_tags`: Approved tag list

**Modes**:
1. **Display Mode**: Show proposed bookmark, ask [Y/n/e]
2. **Edit Mode**: Accept comma-separated tags, re-run reconciliation
3. **Auto-approve Mode**: Skip if `--no-interactive` or `--force`

**Display Format**:
```
Proposed bookmark:

URL:    https://example.com/article
Title:  How to Train Your AI Agent
Author: Jane Doe
Desc:   A comprehensive guide to...

Tags:   ai-agent, machine-learning, training,
        source:example.com, author:jane-doe

Unknown tags (will be added):
  - training → Similar: ai-training, model-training

Save to Diigo? [Y/n/e]:
```

---

#### 4. **Quality Assurance Agent**
**Responsibility**: Validate before saving to Diigo

**Checks**:
1. **Required Fields**: URL, title, tags not empty
2. **System Tags**: `source:*` matches URL domain
3. **Tag Count**: Warn if <2 or >20 tags
4. **Duplicate Detection**: Check if URL already bookmarked
5. **Format Validation**: Tags match `[a-z0-9:-]+` pattern

**Inputs**:
- `final_tags`, `url`, `title`, `description`

**Outputs**:
- `qa_passed`: bool (proceed to save?)
- `qa_warnings`: list[str] (user should see)
- `qa_errors`: list[str] (block save)

**Error Examples**:
- ❌ Error: "URL is missing"
- ❌ Error: "No tags provided"
- ⚠️  Warning: "Only 1 tag - consider adding more"
- ⚠️  Warning: "URL already bookmarked (2023-05-10)"

---

#### 5. **Save Agent**
**Responsibility**: Save to Diigo API

**Inputs**:
- `final_tags`, `url`, `title`, `description`
- Diigo credentials

**Outputs**:
- `save_result`: {success: bool, message: str, bookmark_id: str}

**Error Handling**:
- 401/403 → Credentials invalid
- 429 → Rate limit, wait and retry
- 5xx → Retry 3x with backoff
- Network error → Retry 3x

---

### Agent Flow

```python
# LangGraph workflow definition
from langgraph.graph import StateGraph, END

workflow = StateGraph(BookmarkState)

# Add agents as nodes
workflow.add_node("extract", extraction_agent)
workflow.add_node("tag_intel", tag_intelligence_agent)
workflow.add_node("interactive", interactive_agent)
workflow.add_node("qa", quality_assurance_agent)
workflow.add_node("save", save_agent)

# Define edges (flow)
workflow.add_edge("extract", "tag_intel")
workflow.add_edge("tag_intel", "interactive")

# Conditional: skip interactive if --no-interactive
workflow.add_conditional_edge(
    "interactive",
    lambda state: "qa" if state["user_approved"] else END,
    {True: "qa", False: END}
)

workflow.add_conditional_edge(
    "qa",
    lambda state: "save" if state["qa_passed"] else END,
    {True: "save", False: END}
)

workflow.add_edge("save", END)
workflow.set_entry_point("extract")

# Compile
app = workflow.compile()
```

---

## Data Architecture

### Database Schema (SQLite + Alembic)

#### **Tags Table**
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,              -- Normalized tag name
    count INTEGER DEFAULT 1,                -- Usage frequency
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'user',             -- 'user' | 'master' | 'system'
    embedding BLOB,                         -- Numpy array (384 dims for MiniLM)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_count ON tags(count DESC);
CREATE INDEX idx_tags_source ON tags(source);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE tags_fts USING fts5(
    name,
    content=tags,
    content_rowid=id
);

-- Triggers to keep FTS in sync
CREATE TRIGGER tags_ai AFTER INSERT ON tags BEGIN
    INSERT INTO tags_fts(rowid, name) VALUES (new.id, new.name);
END;

CREATE TRIGGER tags_au AFTER UPDATE ON tags BEGIN
    UPDATE tags_fts SET name = new.name WHERE rowid = new.id;
END;

CREATE TRIGGER tags_ad AFTER DELETE ON tags BEGIN
    DELETE FROM tags_fts WHERE rowid = old.id;
END;
```

#### **Tag Aliases Table** (Future)
```sql
CREATE TABLE tag_aliases (
    id INTEGER PRIMARY KEY,
    alias TEXT UNIQUE NOT NULL,             -- Alternative name
    canonical_id INTEGER NOT NULL,          -- Points to tags.id
    FOREIGN KEY (canonical_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Example: 'ai-devops' → 'ai-enhanced-devops'
```

#### **Bookmarks Cache Table** (Future - for duplicate detection)
```sql
CREATE TABLE bookmarks_cache (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    diigo_id TEXT                            -- Diigo's bookmark ID
);
```

### Data Models (SQLAlchemy)

```python
# diigo_tagger/models.py
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    count = Column(Integer, default=1, index=True)
    last_used = Column(DateTime, default=func.now(), onupdate=func.now())
    source = Column(String, default='user', index=True)
    embedding = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships (future)
    # aliases = relationship("TagAlias", back_populates="canonical_tag")

    def __repr__(self):
        return f"<Tag(name='{self.name}', count={self.count}, source='{self.source}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'count': self.count,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'source': self.source
        }

class TagAlias(Base):
    __tablename__ = 'tag_aliases'

    id = Column(Integer, primary_key=True)
    alias = Column(String, unique=True, nullable=False)
    canonical_id = Column(Integer, ForeignKey('tags.id', ondelete='CASCADE'))

    # canonical_tag = relationship("Tag", back_populates="aliases")
```

### Alembic Migrations

**Migration 001: Initial Schema**
```python
# alembic/versions/001_initial_schema.py
"""Initial tags schema

Revision ID: 001_initial
Create Date: 2025-10-15
"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create tags table
    op.create_table('tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('count', sa.Integer(), server_default='1'),
        sa.Column('last_used', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('source', sa.String(), server_default='user'),
        sa.Column('embedding', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create indexes
    op.create_index('idx_tags_name', 'tags', ['name'])
    op.create_index('idx_tags_count', 'tags', ['count'], postgresql_ops={'count': 'DESC'})
    op.create_index('idx_tags_source', 'tags', ['source'])

    # Create FTS5 virtual table (SQLite specific)
    op.execute("""
        CREATE VIRTUAL TABLE tags_fts USING fts5(
            name,
            content=tags,
            content_rowid=id
        )
    """)

    # Create triggers
    op.execute("""
        CREATE TRIGGER tags_ai AFTER INSERT ON tags BEGIN
            INSERT INTO tags_fts(rowid, name) VALUES (new.id, new.name);
        END
    """)
    op.execute("""
        CREATE TRIGGER tags_au AFTER UPDATE ON tags BEGIN
            UPDATE tags_fts SET name = new.name WHERE rowid = new.id;
        END
    """)
    op.execute("""
        CREATE TRIGGER tags_ad AFTER DELETE ON tags BEGIN
            DELETE FROM tags_fts WHERE rowid = old.id;
        END
    """)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS tags_ad")
    op.execute("DROP TRIGGER IF EXISTS tags_au")
    op.execute("DROP TRIGGER IF EXISTS tags_ai")
    op.execute("DROP TABLE IF EXISTS tags_fts")
    op.drop_index('idx_tags_source', table_name='tags')
    op.drop_index('idx_tags_count', table_name='tags')
    op.drop_index('idx_tags_name', table_name='tags')
    op.drop_table('tags')
```

---

## Component Design

### Tag Store (`diigo_tagger/tag_store.py`)

**Responsibilities**:
- CRUD operations for tags
- Wildcard search (FTS5)
- Semantic search (embeddings)
- Bulk sync from Diigo API

**Public API**:
```python
class TagStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH)

    # Search
    def search_exact(self, tag_name: str) -> Optional[Tag]
    def search_wildcard(self, pattern: str, limit: int = 50) -> list[Tag]
    def search_fuzzy(self, tag_name: str, max_distance: int = 2) -> list[Tag]
    def search_semantic(self, query: str, threshold: float = 0.85, limit: int = 10) -> list[tuple[Tag, float]]

    # CRUD
    def add_tag(self, name: str, source: str = 'user', embedding: Optional[np.ndarray] = None) -> Tag
    def get_tag(self, tag_id: int) -> Optional[Tag]
    def update_tag_count(self, tag_name: str) -> Tag
    def delete_tag(self, tag_id: int) -> bool

    # Bulk operations
    def bulk_insert(self, tags: list[tuple[str, int]]) -> None
    def get_all_tags(self, min_count: int = 1, source: Optional[str] = None) -> list[Tag]

    # Embeddings
    def generate_embeddings(self, tags: list[str]) -> dict[str, np.ndarray]
    def update_embeddings(self, force: bool = False) -> int  # Returns count updated
```

### Diigo Client (`diigo_tagger/diigo_client.py`)

**Responsibilities**:
- Authenticate with Diigo API
- Fetch user's bookmarks (pagination)
- Save new bookmarks
- Check for duplicates

**Public API**:
```python
class DiigoClient:
    def __init__(self, username: str, password: str, api_key: str)

    def fetch_all_bookmarks(
        self,
        username: str,
        filter_scope: str = 'all',
        progress_callback: Optional[Callable] = None
    ) -> list[dict]

    def save_bookmark(
        self,
        url: str,
        title: str,
        tags: list[str],
        description: str = "",
        shared: str = "no"
    ) -> dict  # {success: bool, bookmark_id: str, message: str}

    def check_duplicate(self, url: str) -> Optional[dict]
```

---

## API Contracts

### Inter-Agent Communication

All agents receive and return `BookmarkState` dict. Key contracts:

**Extraction → Tag Intelligence**:
```python
{
    'url': str,              # Required
    'page_title': str,       # Required
    'page_author': str?,     # Optional
    'content_sample': str    # Required for LLM context
}
```

**Tag Intelligence → Interactive**:
```python
{
    'proposed_tags': list[str],          # LLM output
    'validated_tags': list[str],         # Matched to DB
    'unknown_tags': list[str],           # Flagged for review
    'system_tags': list[str],            # source:*, author:*
    'similar_tags': dict[str, list[str]] # Alternatives
}
```

**Interactive → QA**:
```python
{
    'final_tags': list[str],     # User-approved tags
    'user_approved': bool         # Proceed?
}
```

**QA → Save**:
```python
{
    'qa_passed': bool,
    'qa_warnings': list[str],
    'qa_errors': list[str],
    'diigo_payload': {
        'url': str,
        'title': str,
        'tags': str,              # Comma-separated
        'desc': str,
        'shared': str
    }
}
```

---

## Security & Privacy

### Credential Management
- **Storage**: Environment variables via `.env` file (gitignored)
- **Required**: `DIIGO_USER`, `DIIGO_PASS`, `DIIGO_API_KEY`, `OPENAI_API_KEY`
- **Validation**: Fail fast at startup if missing

### API Security
- **Diigo**: HTTP Basic Auth + API key in query param (per spec)
- **OpenAI**: Bearer token in Authorization header
- **No logging** of credentials or API keys

### Data Privacy
- **Local storage**: All data in `~/.diigo/tags.db` (user-owned)
- **No telemetry**: Zero tracking or analytics
- **Cache**: Only public tag names, no bookmark content

### Dependency Security
- **Lock file**: Use Poetry lock file for reproducible builds
- **Audit**: Run `poetry audit` in CI/CD
- **Pin versions**: All dependencies pinned in `pyproject.toml`

---

## Testing Strategy

### Unit Tests

**Tag Store** (`tests/test_tag_store.py`):
```python
def test_search_exact_match()
def test_search_wildcard_patterns()
def test_search_fuzzy_levenshtein()
def test_search_semantic_similarity()
def test_bulk_insert_deduplication()
def test_embedding_generation()
```

**Tag Intelligence** (`tests/test_tag_intelligence.py`):
```python
def test_normalize_tag()
def test_reconcile_exact_match()
def test_reconcile_fuzzy_match()
def test_reconcile_semantic_match()
def test_system_tags_generation()
```

**Diigo Client** (`tests/test_diigo_client.py`):
```python
def test_fetch_bookmarks_pagination()
def test_save_bookmark_success()
def test_save_bookmark_duplicate()
def test_api_error_retry_logic()
```

### Integration Tests

**Agent Flow** (`tests/test_agent_flow.py`):
```python
def test_full_pipeline_url_input()
def test_full_pipeline_text_input()
def test_interactive_edit_flow()
def test_qa_validation_errors()
def test_save_to_diigo_mock()
```

### Test Fixtures
```python
# tests/conftest.py
@pytest.fixture
def temp_db():
    """Temporary SQLite DB for tests"""

@pytest.fixture
def mock_diigo_api():
    """Mock Diigo API responses"""

@pytest.fixture
def sample_tags():
    """Pre-populated tag database"""
```

---

## Deployment Strategy

### Installation

**Prerequisites**:
- Python 3.10+
- pip or Poetry

**Steps**:
```bash
# Clone repo
git clone https://github.com/user/diigo-tagger-ai.git
cd diigo-tagger-ai

# Install dependencies
poetry install

# Optional: semantic search
poetry install -E semantic

# Setup environment
cp .env.example .env
# Edit .env with credentials

# Run migrations
poetry run alembic upgrade head

# One-time tag sync
poetry run diigo tags:sync --user your_username
```

### Configuration Files

**`.env`** (gitignored):
```bash
DIIGO_USER=your_username
DIIGO_PASS=your_password
DIIGO_API_KEY=your_api_key
OPENAI_API_KEY=sk-...
```

**`~/.diigo-tagger.yml`** (optional):
```yaml
master_tags:
  - ai-agent
  - git-workflow
  - conventional-commits
  # ... more

tag_aliases:
  ai-devops: ai-enhanced-devops

rules:
  ensure_source_tag: true
  ensure_author_tag: true
  max_tags: 20
  min_tags: 2
```

### Database Location
- Default: `~/.diigo/tags.db`
- Migrations: Applied automatically on first run
- Backup: User responsible (future: auto-backup on sync)

---

## Future Enhancements

### v1.1 (3-6 months)
- [ ] Tag aliases and merge tool (`diigo tags:merge`)
- [ ] Batch import from browser bookmarks
- [ ] Rich terminal UI with progress bars
- [ ] Export tags to CSV/JSON

### v1.2 (6-12 months)
- [ ] Tag hierarchy (parent/child relationships)
- [ ] Duplicate bookmark detection with fuzzy URL matching
- [ ] Bookmark search CLI (`diigo search "machine learning"`)
- [ ] Web UI (Flask/FastAPI dashboard)

### v2.0 (12+ months)
- [ ] Multi-user support (team tag taxonomies)
- [ ] Chrome/Firefox extension integration
- [ ] Scheduled tag maintenance agent
- [ ] LLM fine-tuning on user's tag patterns

---

## Open Questions for Brooke

1. **LLM Provider**: Stick with OpenAI, or add Anthropic/local model support?
2. **Tag Merge Strategy**: Auto-merge similar tags, or always ask user?
3. **Embedding Model**: sentence-transformers (80MB) or OpenAI embeddings (API cost)?
4. **CLI Framework**: argparse (stdlib) or Click (richer features)?
5. **Terminal UI**: Plain text or rich library with colors/progress?

---

## Appendix

### Project Structure
```
diigo-tagger-ai/
├── .env.example
├── .gitignore
├── README.md
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
├── diigo_tagger/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── extraction.py
│   │   ├── tag_intelligence.py
│   │   ├── interactive.py
│   │   ├── qa.py
│   │   └── save.py
│   ├── orchestration.py
│   ├── tag_store.py
│   ├── diigo_client.py
│   ├── prompts.py
│   ├── config.py
│   └── utils.py
├── tests/
│   ├── conftest.py
│   ├── test_tag_store.py
│   ├── test_agents.py
│   ├── test_diigo_client.py
│   └── test_integration.py
└── docs/
    ├── ARCHITECTURE_DESIGN.md (this file)
    ├── API.md
    └── USER_GUIDE.md
```

---

**End of Architecture Design Document**

*Ready for implementation review and approval*
