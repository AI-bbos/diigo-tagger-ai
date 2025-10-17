# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Error handling decorator for consistent CLI error messages
- Constants module for centralized configuration values
- Comprehensive input validation for all CLI commands

### Changed
- Improved session management with context manager pattern
- Refactored CLI commands to use error handling decorator
- Extracted magic numbers to constants module for maintainability

## [1.0.0] - 2025-10-17

### Added
- Initial release of Diigo Tagger AI
- SQLite database with FTS5 full-text search support
- Tag model with embedding support (384-dim float32)
- Cross-platform config directory support (platformdirs)
- Database initialization and migration with Alembic
- Security utilities:
  - API key redaction for safe logging
  - HTTPS-only URL validation
  - Prompt injection detection (5 pattern types)
- API clients:
  - Diigo API client for bookmark fetching
  - OpenAI API client for tag generation (GPT-4o-mini)
- Tag reconciliation service:
  - Tag normalization (lowercase, trim)
  - Deduplication (case-insensitive)
  - Wildcard search using FTS5
  - Semantic similarity search using embeddings
  - Tag merging (combine counts, preserve timestamps)
- CLI commands:
  - `init`: Initialize database with schema
  - `sync`: Sync bookmarks from Diigo
  - `search`: Search tags (wildcard or semantic)
  - `merge`: Merge duplicate tags
  - `generate`: Generate tag suggestions with AI
  - `list`: List all tags
- Comprehensive test suite (79/80 tests passing, 87% coverage)
- User documentation with quick start guide
- Security best practices documentation
- `.env.example` template for configuration

### Security
- All API calls enforce HTTPS
- API keys redacted in logs and error messages
- Prompt injection detection before LLM calls
- Input validation on all user-facing functions
- No secrets committed to repository
- SQL injection prevention via parameterized queries

### Performance
- Module-level engine caching (prevents connection pool waste)
- Session factory caching (reduces overhead)
- FTS5 full-text search (< 50ms for thousands of tags)
- Optimized database indexes on frequently queried columns

### Technical Details
- Python 3.10+ required
- SQLite 3.35.0+ required (for FTS5)
- WAL mode enabled for better concurrency
- Platform-specific config directories:
  - macOS: `~/Library/Application Support/diigo-tagger`
  - Linux: `~/.config/diigo-tagger`
  - Windows: `%LOCALAPPDATA%\diigo-tagger`

## [0.1.0] - 2025-10-15

### Added
- Project scaffolding
- Initial architecture design
- Planning documentation (7-agent workflow)
- BSA analysis
- Security audit
- Test plan

[Unreleased]: https://github.com/yourusername/diigo-tagger-ai/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/diigo-tagger-ai/releases/tag/v1.0.0
[0.1.0]: https://github.com/yourusername/diigo-tagger-ai/releases/tag/v0.1.0
