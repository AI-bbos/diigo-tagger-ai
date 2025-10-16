# Diigo Tagger AI

AI-powered CLI tool for Diigo bookmark tagging with semantic search.

## Features

- 🤖 Automated tag generation using GPT-4o-mini
- 🔍 Wildcard tag search with SQLite FTS5
- 🧠 Semantic tag search with sentence-transformers
- ✨ Interactive CLI workflow with Rich terminal UI
- 🔒 Security hardening (credential protection, API key redaction)
- 📊 Tag reconciliation (exact → fuzzy → semantic)

## Installation

```bash
pip install diigo-tagger-ai
```

## Quick Start

See [User Documentation](docs/features/diigo-tagger-ai/05-user-documentation.md)

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
