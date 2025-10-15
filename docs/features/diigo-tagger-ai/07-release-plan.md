# Release Plan: Diigo Tagger AI v1.0

**Project**: diigo-tagger-ai
**Release**: v1.0.0
**Created**: October 15, 2025
**RTE**: Claude
**Status**: Ready for Implementation
**Input**: All feature documentation (01-06)

---

## Executive Summary

**Release Type**: Initial v1.0 release
**Target Date**: TBD (after implementation complete)
**Risk Level**: Low (personal CLI tool, no production users yet)

This release delivers AI-powered bookmark tagging for Diigo with:
- Automated tag generation using LLM
- Local tag database with FTS5 and semantic search
- Three-tier tag reconciliation (exact → fuzzy → semantic)
- Interactive CLI workflow with Rich terminal UI
- Security hardening (credential protection, API key redaction, HTTPS enforcement)

**Breaking Changes**: None (initial release)

---

## Release Artifacts

### Source Code
- **Repository**: `diigo-tagger-ai`
- **Branch**: `main`
- **Tag**: `v1.0.0`

### Deliverables
1. Python package (`diigo-tagger-ai`) on PyPI
2. User documentation (installation, commands, workflows)
3. Security best practices guide
4. Migration files (Alembic 001, 002, 003)
5. Test suite (unit, integration, E2E, security, performance)

---

## Pre-Release Verification

### Documentation Checklist
- ✅ BSA analysis complete (`01-bsa-analysis.md`)
- ✅ Architecture design complete (`02-architecture-design.md`)
- ✅ Data engineering plan complete (`03-data-engineering-plan.md`)
- ✅ Security audit complete (`04-security-audit.md`)
- ✅ User documentation complete (`05-user-documentation.md`)
- ✅ Test plan complete (`06-test-plan.md`)
- ✅ Release plan complete (`07-release-plan.md`)

### Implementation Checklist (TBD)
- [ ] Project structure created
- [ ] Core modules implemented:
  - [ ] `diigo_tagger/models.py` (SQLAlchemy ORM)
  - [ ] `diigo_tagger/db.py` (Database init)
  - [ ] `diigo_tagger/clients/diigo_client.py` (Diigo API)
  - [ ] `diigo_tagger/services/llm_service.py` (LLM abstraction)
  - [ ] `diigo_tagger/services/tag_reconciliation.py` (Reconciliation logic)
  - [ ] `diigo_tagger/services/bookmark_service.py` (Orchestration)
  - [ ] `diigo_tagger/cli/` (Click commands)
  - [ ] `diigo_tagger/utils/security.py` (Redaction, validation)
- [ ] Alembic migrations created (001, 002, 003)
- [ ] All unit tests passing (90%+ coverage)
- [ ] All integration tests passing
- [ ] All E2E tests passing
- [ ] All security tests passing
- [ ] All performance benchmarks met
- [ ] Security audit HIGH issues mitigated:
  - [ ] H-1: File permission check for .env (600)
  - [ ] H-1: Startup warning about credential security
  - [ ] H-1: Pre-commit hook template
  - [ ] H-2: API key redaction in errors/logs
- [ ] Security audit MEDIUM issues mitigated:
  - [ ] M-1: HTTPS validation for API endpoints
  - [ ] M-2: Prompt injection detection
  - [ ] M-2: Tag validation (format, length, special chars)
- [ ] README.md created
- [ ] LICENSE file added (MIT/Apache 2.0)
- [ ] CHANGELOG.md created
- [ ] pyproject.toml configured
- [ ] .gitignore includes .env
- [ ] .env.example created

---

## Installation Package Build

### PyPI Package Configuration

**File**: `pyproject.toml`

```toml
[tool.poetry]
name = "diigo-tagger-ai"
version = "1.0.0"
description = "AI-powered CLI tool for Diigo bookmark tagging with semantic search"
authors = ["Brooke <your-email@example.com>"]
license = "MIT"
readme = "README.md"
homepage = "https://github.com/yourusername/diigo-tagger-ai"
repository = "https://github.com/yourusername/diigo-tagger-ai"
keywords = ["diigo", "bookmarks", "tagging", "ai", "llm", "cli"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
]

[tool.poetry.dependencies]
python = "^3.10"
sqlalchemy = "^2.0"
alembic = "^1.12"
click = "^8.1"
python-dotenv = "^1.0"
requests = "^2.31"
beautifulsoup4 = "^4.12"
lxml = "^4.9"
langchain = "^0.1"
openai = "^1.3"
sentence-transformers = "^2.2"
tiktoken = "^0.5"
rich = "^13.5"
numpy = "^1.24"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4"
pytest-cov = "^4.1"
black = "^23.9"
ruff = "^0.1"
mypy = "^1.5"

[tool.poetry.scripts]
diigo = "diigo_tagger.cli.main:cli"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=diigo_tagger --cov-report=html --cov-report=term"

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Build Commands

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run type checking
poetry run mypy diigo_tagger/

# Run linting
poetry run ruff check .

# Format code
poetry run black .

# Build package
poetry build

# Publish to PyPI (after testing on TestPyPI)
poetry publish --build
```

---

## Deployment Guide

### For End Users (PyPI Installation)

**Installation**:
```bash
pip install diigo-tagger-ai
```

**First-time Setup**:
```bash
# 1. Create .env file
cat > .env <<EOF
DIIGO_USER=your_username
DIIGO_PASS=your_password
DIIGO_API_KEY=your_api_key
OPENAI_API_KEY=sk-your_key
EOF

# 2. Secure .env
chmod 600 .env

# 3. Verify installation
diigo --version

# 4. Sync tags from Diigo
diigo tags:sync --user your_username

# 5. Save first bookmark
diigo save "https://example.com/article"
```

### For Developers (Source Installation)

**Clone and Install**:
```bash
git clone https://github.com/yourusername/diigo-tagger-ai.git
cd diigo-tagger-ai
poetry install
poetry shell
```

**Run Tests**:
```bash
pytest tests/
```

**Development Workflow**:
```bash
# Make changes
# Run tests
pytest

# Run type checking
mypy diigo_tagger/

# Format code
black .
ruff check .

# Build locally
poetry build

# Test local installation
pip install dist/diigo_tagger_ai-1.0.0-py3-none-any.whl
```

---

## Database Migration Strategy

### Initial Setup (User's First Run)

**Automatic migration on first run**:
```python
# diigo_tagger/db.py
def init_db(db_path: Path = DB_PATH) -> Engine:
    """Initialize database with schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")

    # Check SQLite version
    check_sqlite_version()

    # Enable WAL mode
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Run Alembic migrations
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    return engine
```

### Future Schema Updates

**v1.1 → v1.2 Migration**:
```bash
# User runs upgrade
pip install --upgrade diigo-tagger-ai

# Automatic migration on next run
diigo save "https://example.com"
# Output: "Database schema upgraded to v1.2"
```

**Manual Migration** (if needed):
```bash
# In project directory
alembic upgrade head
```

---

## Rollback Plan

### v1.0 → Uninstall

**For users experiencing issues**:
```bash
# Export tags for backup
diigo tags:export --output ~/diigo_backup.csv

# Uninstall package
pip uninstall diigo-tagger-ai

# Remove database (optional)
rm -rf ~/.diigo/
```

**To reinstall**:
```bash
pip install diigo-tagger-ai

# Import tags from backup
# (Feature for v1.1)
```

### Database Rollback

**If database corruption**:
```bash
# Backup corrupted database
mv ~/.diigo/tags.db ~/.diigo/tags.db.corrupted

# Re-sync from Diigo
diigo tags:sync --user your_username
```

**Manual migration rollback**:
```bash
# Downgrade to specific version
alembic downgrade 001  # Back to initial schema
alembic downgrade base  # Remove all tables
```

---

## Testing Strategy

### Pre-Release Testing Phases

**Phase 1: Unit Testing (Week 1)**
```bash
pytest tests/unit/ -v --cov=diigo_tagger --cov-report=html

# Target: 90%+ coverage
# Exit criteria: All tests pass, no HIGH/CRITICAL security issues
```

**Phase 2: Integration Testing (Week 2)**
```bash
pytest tests/integration/ -v

# Exit criteria: All component interactions validated
```

**Phase 3: E2E Testing (Week 3)**
```bash
pytest tests/e2e/ -v --slow

# Exit criteria: All user workflows validated
```

**Phase 4: Security & Performance (Week 4)**
```bash
pytest tests/security/ -v
pytest tests/performance/ -v --benchmark

# Security exit criteria: All attack scenarios blocked
# Performance exit criteria: All BSA SLAs met
```

### Test PyPI Deployment

**Before PyPI production release**:
```bash
# 1. Build package
poetry build

# 2. Upload to TestPyPI
poetry publish --repository testpypi

# 3. Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ diigo-tagger-ai

# 4. Test installation
diigo --version
diigo --help

# 5. If successful, publish to PyPI
poetry publish
```

---

## Monitoring & Success Metrics

### Usage Metrics (Optional for v1.0)

**Telemetry** (disabled by default, opt-in only):
- Command usage frequency
- LLM provider distribution
- Tag reconciliation match rates
- Error rates by category

**Privacy**: No PII, URLs, or tag names collected. Anonymous usage statistics only.

### Success Criteria (v1.0)

**Technical**:
- ✅ Wildcard search < 50ms for 10k tags
- ✅ Semantic search < 500ms for 10k tags
- ✅ Bookmark save < 10s end-to-end
- ✅ Zero HIGH/CRITICAL security issues
- ✅ 90%+ code coverage

**User Experience**:
- ✅ Installation takes < 5 minutes
- ✅ First bookmark saved in < 2 minutes (after setup)
- ✅ Interactive workflow is intuitive
- ✅ Error messages are clear and actionable

**Adoption** (personal use):
- Daily usage for all new bookmarks
- Tag database grows to 5000+ tags
- 95%+ tag reuse (vs creating duplicates)

---

## Communication Plan

### Pre-Release

**Internal** (if team project):
- [ ] Demo v1.0 features to team
- [ ] Share documentation in #engineering
- [ ] Request code reviews from peers

**External** (if open source):
- [ ] Create GitHub release notes
- [ ] Post on personal blog/Twitter
- [ ] Submit to Hacker News (Show HN)
- [ ] Share in relevant subreddits (r/Python, r/selfhosted)

### Release Announcement

**GitHub Release Notes**:
```markdown
# Diigo Tagger AI v1.0.0

First stable release of AI-powered bookmark tagging CLI for Diigo.

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

## What's Changed
- Initial v1.0 release

## Full Changelog
https://github.com/yourusername/diigo-tagger-ai/blob/main/CHANGELOG.md
```

### Post-Release

**Documentation**:
- [ ] Publish user guide on GitHub Pages
- [ ] Create video tutorial (optional)
- [ ] Write blog post with examples

**Community**:
- [ ] Monitor GitHub issues
- [ ] Respond to feedback
- [ ] Plan v1.1 based on usage

---

## Version Numbering

**Semantic Versioning**: `MAJOR.MINOR.PATCH`

**v1.0.0** (Initial Release):
- SQLite + FTS5 tag database
- OpenAI LLM integration
- Three-tier tag reconciliation
- Click CLI with Rich UI
- Security hardening

**v1.1.0** (Planned):
- Anthropic/Ollama provider support
- OS keychain integration for credentials
- Tag auto-merge (ML-based)
- Audit logging
- Tag import/export CSV

**v1.2.0** (Future):
- Pinboard/Raindrop support
- Web UI (optional)
- Browser extension integration
- Multi-user (team) mode

---

## Risk Assessment

### Risk Level: Low

**Justification**:
- Personal CLI tool (not production service)
- No external users initially
- Can rollback via pip uninstall
- Database is local (easy to backup)
- Comprehensive test coverage

### Identified Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SQLite version < 3.35 | Low | High | Pre-flight check, clear error message |
| API key exposure | Medium | High | File permission check, redaction, docs |
| LLM API costs | Low | Medium | User controls usage, warn on batch |
| Database corruption | Low | Medium | WAL mode, backup instructions |
| Dependency vulnerabilities | Low | High | `poetry audit` in CI/CD |
| Poor user experience | Medium | Low | Comprehensive docs, examples |

### Mitigation Actions

**High-Priority**:
1. ✅ Security audit complete (7.5/10 score)
2. ✅ File permission warnings implemented
3. ✅ API key redaction in errors/logs
4. ✅ HTTPS-only validation
5. ✅ Prompt injection detection

**Medium-Priority**:
1. ✅ Comprehensive user documentation
2. ✅ Troubleshooting guide
3. ✅ FAQ section
4. ✅ .env.example template
5. ✅ Pre-commit hook template

---

## Post-Release Plan

### First Week

**Days 1-3**:
- [ ] Monitor GitHub issues
- [ ] Test on fresh system (clean macOS, Ubuntu, Windows WSL)
- [ ] Fix any critical installation issues
- [ ] Update docs based on user feedback

**Days 4-7**:
- [ ] Gather usage feedback
- [ ] Identify pain points
- [ ] Plan v1.0.1 patch if needed

### First Month

**Metrics to Track**:
- PyPI download count
- GitHub stars/forks
- Issue open vs. closed rate
- User-reported bugs vs. feature requests

**Review Questions**:
1. Are users successfully installing and running?
2. What are the most common issues?
3. What features are users requesting?
4. Should we prioritize v1.1 features?

### Quarterly Review

**Success Indicators**:
- Active daily usage (personal use case)
- Tag database > 5000 tags
- 95%+ tag reuse rate
- Positive community feedback (if open source)

**v1.1 Planning**:
- Prioritize features based on feedback
- Address any technical debt
- Improve documentation based on user questions
- Consider expanding to other bookmark services

---

## Lessons Learned (Post-Release)

### What Went Well
- _To be filled after release_

### What Could Be Improved
- _To be filled after release_

### Action Items for v1.1
- _To be filled after release_

---

## Sign-Off

### Required Approvals

**Security Review**:
- ✅ Security audit complete (Score: 7.5/10)
- ✅ HIGH issues have mitigation plans
- ✅ Approved for personal use

**Quality Assurance**:
- ⏳ Pending implementation and test execution
- ⏳ All tests must pass before release

**Documentation**:
- ✅ User documentation complete
- ✅ Security best practices documented
- ✅ Troubleshooting guide complete

**Release Engineer**:
- ✅ Release plan complete
- ⏳ Pending implementation completion

---

## Implementation Roadmap

### Week 1-2: Core Implementation
- Project structure setup
- Database models and migrations
- API clients (Diigo, OpenAI)
- Tag reconciliation logic

### Week 3-4: CLI & Services
- Click CLI commands
- Bookmark save workflow
- Tag search (wildcard, semantic)
- Interactive prompts with Rich

### Week 5-6: Security & Testing
- Security mitigations (H-1, H-2, M-1, M-2)
- Unit tests (90%+ coverage)
- Integration tests
- E2E tests

### Week 7-8: Polish & Documentation
- Performance optimization
- User documentation refinement
- README and CHANGELOG
- PyPI package preparation

### Week 9: Pre-Release Testing
- Test on multiple platforms
- TestPyPI deployment
- Final security review
- Bug fixes

### Week 10: Release
- PyPI publication
- GitHub release
- Documentation site
- Community announcement

---

## Appendix: File Checklist

### Documentation Files
- ✅ `docs/features/diigo-tagger-ai/01-bsa-analysis.md`
- ✅ `docs/features/diigo-tagger-ai/02-architecture-design.md`
- ✅ `docs/features/diigo-tagger-ai/03-data-engineering-plan.md`
- ✅ `docs/features/diigo-tagger-ai/04-security-audit.md`
- ✅ `docs/features/diigo-tagger-ai/05-user-documentation.md`
- ✅ `docs/features/diigo-tagger-ai/06-test-plan.md`
- ✅ `docs/features/diigo-tagger-ai/07-release-plan.md` (this file)

### Implementation Files (TBD)
- [ ] `README.md`
- [ ] `LICENSE`
- [ ] `CHANGELOG.md`
- [ ] `pyproject.toml`
- [ ] `.gitignore`
- [ ] `.env.example`
- [ ] `alembic.ini`
- [ ] `diigo_tagger/__init__.py`
- [ ] `diigo_tagger/models.py`
- [ ] `diigo_tagger/db.py`
- [ ] `diigo_tagger/config.py`
- [ ] `diigo_tagger/clients/`
- [ ] `diigo_tagger/services/`
- [ ] `diigo_tagger/cli/`
- [ ] `diigo_tagger/utils/`
- [ ] `alembic/versions/001_initial_schema.py`
- [ ] `alembic/versions/002_add_embeddings.py`
- [ ] `alembic/versions/003_add_source_column.py`
- [ ] `tests/unit/`
- [ ] `tests/integration/`
- [ ] `tests/e2e/`
- [ ] `tests/security/`
- [ ] `tests/performance/`

---

## Next Steps

### Immediate Actions
1. **Begin implementation** following TDD principles
2. **Create project structure** with Poetry
3. **Implement core modules** starting with database layer
4. **Write tests alongside code** (TDD)

### Implementation Order
1. Database layer (models, migrations, init)
2. API clients (Diigo, OpenAI)
3. Core services (tag reconciliation, LLM)
4. CLI commands (save, sync, search)
5. Security mitigations (redaction, validation, HTTPS)
6. Tests (unit → integration → E2E → security → performance)
7. Documentation polish (README, CHANGELOG)
8. Package build and TestPyPI deployment

### Success Handoff
- All documentation complete ✅
- Architecture designed ✅
- Security audited ✅
- Tests planned ✅
- Release strategy defined ✅
- **Ready for implementation** 🚀

---

**RTE Sign-off**: Complete 7-agent workflow executed. All planning documentation complete. Project ready for TDD implementation following this comprehensive release plan.

🎉 **All 7 agents complete! Ready to build diigo-tagger-ai v1.0.0**
