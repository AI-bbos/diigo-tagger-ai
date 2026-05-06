# Plan: Open Source Release & Marketing

## 1. License & Open Source

### Tasks
- [x] Add `LICENSE` file with AGPL-3.0 text
- [x] Add license header reference to `pyproject.toml` (`license = "AGPL-3.0-or-later"`)
- [x] Audit repo for secrets/credentials (ensure `.env` is gitignored, no hardcoded keys)
- [x] Review commit history for any accidentally committed secrets
- [x] Update README.md with license badge and "what is this" summary for public audience
- [x] Audit all 31 direct dependencies against PyPI + blocklist (all clean)
- [ ] Make repo public on GitHub

### Why AGPL-3.0
- Covers the network loophole (GPL doesn't protect web services)
- Anyone can use, modify, learn — but hosting a modified version requires sharing source
- Establishes Brooke as original author via full git history
- Standard, respected license in the open source community

## 2. PyPI Distribution

### Tasks
- [x] Verify `pyproject.toml` has correct metadata (description, author, URLs, classifiers)
- [ ] Create PyPI account at pypi.org (if not already)
- [ ] Configure Poetry for PyPI publishing (`poetry config pypi-token.pypi <token>`)
- [ ] Test with TestPyPI first (`poetry publish --repository testpypi`)
- [ ] Publish to PyPI (`poetry publish --build`)
- [ ] Verify `pip install diigo-tagger-ai` works in a clean virtualenv

### Ongoing
- Publish new versions on each milestone release (semver)
- Add GitHub Action for automated PyPI publishing on tag push (future)

## 3. dev.to Article

### Title Options
- "Building an AI-Powered Bookmark Manager — Architecture Decisions That AI Can't Make For You"
- "What 9,600 Bookmarks Taught Me About Tag Management (And Why I Built an AI For It)"
- "AI-Augmented Engineering: Directing Claude Code Like a Senior Engineer Directs a Team"

### Outline

**Hook:** "I have 9,600 bookmarks in Diigo. Tagging them manually was a nightmare. So I built an AI-powered system that doesn't just suggest tags — it understands my taxonomy."

**Section 1: The Problem**
- Manual tagging doesn't scale
- LLM-generated tags are generic without context
- The real challenge: making AI suggestions fit YOUR vocabulary, not generic categories

**Section 2: Architecture That Matters**
- Thin UI / thick service pattern — why it matters for testability and flexibility
- Prepare/submit split — preview before committing to Diigo
- Multi-provider LLM with automatic fallback — not locked to OpenAI
- SQLite + FTS5 over PostgreSQL — simplicity wins for personal tools

**Section 3: Smart Tag Matching (the interesting bit)**
- The problem: LLM suggests "women-empowerment" but you have "women_empowerment"
- String similarity with confidence tiers (auto-accept, confirm, new)
- Ranked dropdown showing alternatives by usage count — user decides, AI suggests
- Why this beats "just use the LLM's output"

**Section 4: Category Inference via LCA**
- The cold-start problem: new users have no tags to match against
- Solution: cluster content tags, find Lowest Common Ancestor via LLM
- No maintained ontology — the LLM's internal knowledge IS the ontology
- Existing users get vocabulary reinforcement, new users get hierarchy bootstrapping

**Section 5: What AI Can't Do**
- UX iteration — the tag pills went through 3 redesigns based on real usage
- Edge cases — Medium's 403 blocks, Python's `.title()` capitalizing after digits
- Product decisions — should tags auto-add or be suggestions? (We went back and forth)
- Domain knowledge — knowing that `rating=7_10` format matters to the user's workflow

**Section 6: The Stack**
- Python 3.10+, FastAPI, HTMX, Tailwind, SQLite FTS5, LangChain
- Why HTMX over React — server-rendered is simpler for personal tools
- 340+ tests, 71% coverage

**Closing:** "AI didn't build this. I did, with AI as a tool. The difference is the same as the difference between a senior engineer and a junior — both write code, but one makes the decisions that make the code worth writing."

### Suggested Screenshots for Article
1. The full preview page with all sections visible (hero image)
2. Tag similarity dropdown — the money shot showing ranked alternatives
3. Before/after: "medium.com" title vs proper title extraction
4. Related bookmarks section showing tag inheritance

### Publishing
- [ ] Draft on dev.to (supports markdown, code blocks, images)
- [ ] Cross-post to Hashnode and LinkedIn article
- [ ] Share on LinkedIn feed with shorter summary
- [ ] Post to relevant subreddits: r/Python, r/selfhosted, r/webdev

## 4. LinkedIn Presence

### Profile Updates
- [ ] Add project to LinkedIn Featured section
- [ ] Update headline/summary to reflect AI-augmented engineering capability
- [ ] Pin a post about the project

### Framing
Position as "Senior Software Engineer" — not "AI Coder" or "Prompt Engineer." The narrative:
- Directed AI as a tool, like directing a team
- Made architecture and design decisions that require experience
- Iterative product thinking based on real-world usage
- The AI accelerated execution; the engineering judgment is human

### Post Ideas
- "I built an AI bookmark manager in a weekend. Here's what the AI couldn't do." (thread format)
- "340 tests, 20 issues, 28 PRs — and my AI assistant wrote most of the code. Here's why that makes me MORE valuable, not less."
- Share the dev.to article with a personal take

## 5. GitHub Profile

### Tasks
- [ ] Pin diigo-tagger-ai repo once public
- [ ] Add topic tags: `python`, `fastapi`, `ai`, `bookmarks`, `diigo`, `llm`, `htmx`
- [ ] Add "About" description: "AI-powered bookmark management for Diigo — smart tagging, similarity matching, and category inference"
- [ ] Ensure issue tracker and PR history are clean (they are — 20 closed issues, 28 merged PRs)

## Timeline

| Week | Action |
|------|--------|
| 1 | License, audit, make public, PyPI publish |
| 2 | Draft dev.to article, take screenshots |
| 3 | Publish article, LinkedIn posts |
| Ongoing | Phase 4 development, new releases |
