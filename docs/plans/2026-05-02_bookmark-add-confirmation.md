# Bookmark Add Confirmation Step

**Goal:** Show a preview of the bookmark (title, description, tags, URL) before submitting to Diigo, giving the user a chance to review and confirm or cancel.

**Motivation:** Currently, `diigo add` submits directly to Diigo without showing the user what will be sent. This is fine for conflicts (which already have a review step), but new bookmarks get submitted blind.

---

## Current Flow (CLI)

1. User runs `diigo add --url <url>`
2. Service fetches metadata, generates LLM tags
3. If conflict → interactive resolution prompt (existing)
4. If new → **immediately submits to Diigo** ← problem

## Proposed Flow (CLI)

1. User runs `diigo add --url <url>`
2. Service fetches metadata, generates LLM tags
3. If conflict → existing resolution prompt (unchanged)
4. If new → **show preview, prompt for confirmation**
   - Display: URL, title, description (truncated), tags
   - Options: `[Y]es / [e]dit / [c]ancel`
   - `Yes`: submit as shown
   - `Edit`: open fields for inline editing (title, description, tags)
   - `Cancel`: abort without submitting
5. Submit to Diigo

## Proposed Flow (Web UI)

The web UI add form already shows fields before submission — this is primarily a CLI issue. However, the web flow should also show a "review" state after LLM suggestions are generated, before final submit.

---

## Implementation

### Task 1: Refactor BookmarkService.add_bookmark to separate prepare from submit

**Files:** `diigo_tagger/services/bookmark_service.py`

Split `add_bookmark()` into two phases:
1. `prepare_bookmark()` — fetches metadata, generates LLM suggestions, checks for conflicts. Returns a preview dict without submitting to Diigo.
2. `submit_bookmark()` — takes the prepared data and submits to Diigo + saves to DB.

This keeps the service layer clean and lets both CLI and web UI implement their own confirmation UX.

- [ ] Write tests for `prepare_bookmark()` returning preview without side effects
- [ ] Write tests for `submit_bookmark()` creating the bookmark
- [ ] Implement `prepare_bookmark()` by extracting lines 275-350 from `add_bookmark()`
- [ ] Implement `submit_bookmark()` by extracting lines 409-479 from `add_bookmark()`
- [ ] Keep `add_bookmark()` as a convenience wrapper that calls both (backward compat)

### Task 2: Add confirmation prompt to CLI add command

**Files:** `diigo_tagger/cli/main.py`

- [ ] After calling `prepare_bookmark()`, display preview:
  ```
  📋 Bookmark Preview:
    URL:         https://medium.com/...
    Title:       Claude Code Hooks Explained...
    Description: The missing layer between...
    Tags:        claude-code, hooks, ai, development

  Submit? [Y]es / [e]dit / [c]ancel:
  ```
- [ ] `Y` (default): call `submit_bookmark()` with prepared data
- [ ] `e`: prompt for edits to title, description, tags (pre-filled with current values)
- [ ] `c`: abort
- [ ] Add `--yes` / `-y` flag to skip confirmation (for scripting)

### Task 3: Tests

**Files:** `tests/unit/test_bookmark_service.py`, `tests/unit/test_cli_add.py`

- [ ] Test `prepare_bookmark()` returns correct preview for new URL
- [ ] Test `prepare_bookmark()` returns conflict info for existing URL
- [ ] Test `submit_bookmark()` creates bookmark in DB and calls Diigo API
- [ ] Test CLI add with `--yes` flag skips confirmation
