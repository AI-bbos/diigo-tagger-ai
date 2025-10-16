# Diigo Tagger AI

AI-powered CLI tool for Diigo bookmark tagging with semantic search.

## Features

- 🤖 Automated tag generation using GPT-4o-mini
- 🔍 Wildcard tag search with SQLite FTS5
- 🧠 Semantic tag search with embeddings (requires pre-stored embeddings)
- 📊 Tag database sync from Diigo bookmarks
- 🔀 Tag merge for duplicate cleanup (local database only)
- 🔒 Security hardening (credential protection, API key redaction, prompt injection detection)

## Installation

```bash
pip install diigo-tagger-ai
```

## Quick Start

### 1. Set up environment variables

Create a `.env` file:

```bash
DIIGO_API_KEY=your_diigo_api_key
OPENAI_API_KEY=sk-your_openai_key
```

### 2. Initialize database

```bash
diigo init
```

### 3. Sync tags from Diigo

```bash
diigo sync --count 100
```

### 4. Generate tag suggestions

```bash
diigo generate --title "Article Title" --url "https://example.com/article"
```

**Note**: v1.0 generates tag suggestions only. Tags are NOT automatically saved to Diigo.

### 5. Search tags

```bash
# Wildcard search
diigo search "*python*"

# Semantic search (requires embeddings)
diigo search "machine learning" --semantic
```

## Commands

- `diigo init` - Initialize database
- `diigo sync` - Sync bookmarks from Diigo
- `diigo search` - Search tags (wildcard or semantic)
- `diigo merge` - Merge duplicate tags
- `diigo generate` - Generate tag suggestions with AI
- `diigo list` - List all tags

For detailed documentation, see [User Documentation](docs/features/diigo-tagger-ai/05-user-documentation.md)

## Development

```bash
# Clone repository
git clone https://github.com/yourusername/diigo-tagger-ai.git
cd diigo-tagger-ai

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run CLI
poetry run diigo --help
```

## Documentation

- [User Guide](docs/features/diigo-tagger-ai/05-user-documentation.md)
- [Architecture](docs/features/diigo-tagger-ai/02-architecture-design.md)
- [Security Audit](docs/features/diigo-tagger-ai/04-security-audit.md)
- [Test Plan](docs/features/diigo-tagger-ai/06-test-plan.md)

## License

MIT
