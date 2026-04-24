# CLI Wrapper & Server Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an installable CLI wrapper and four server/deployment commands with grouped help output.

**Architecture:** Bash wrapper installed via `scripts/install.sh` delegates to `poetry run diigo`. New Click commands (`dev`, `build`, `deploy`, `promote`) added to the existing CLI. `HelpfulGroup` extended to render commands in labeled groups.

**Tech Stack:** Bash, Click 8.1, uvicorn, Poetry

**Spec:** `docs/plans/2026-04-24_cli-wrapper-and-vercel-deploy.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `bin/diigo` | Bash wrapper template — exports `DIIGO_HOME`, delegates to `poetry run diigo` |
| `scripts/install.sh` | Installer — replaces placeholder, copies wrapper to user's bin dir |
| `diigo_tagger/cli/main.py` | Extended with grouped help + 4 new commands |
| `tests/unit/test_cli_server.py` | Tests for `dev`, `build`, `deploy`, `promote` commands |
| `tests/unit/test_cli_help.py` | Tests for grouped help output |

---

### Task 1: Grouped Help in HelpfulGroup

**Files:**
- Modify: `diigo_tagger/cli/main.py:87-128` (HelpfulGroup class + cli group)
- Create: `tests/unit/test_cli_help.py`

- [ ] **Step 1: Write failing tests for grouped help**

Create `tests/unit/test_cli_help.py`:

```python
# ABOUTME: Tests for grouped CLI help output
# ABOUTME: Verifies commands are organized into labeled sections

from click.testing import CliRunner
from diigo_tagger.cli.main import cli


class TestGroupedHelp:
    """Test that --help output organizes commands into groups."""

    def test_help_shows_bookmarks_group(self):
        """Should show Bookmarks group header."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "Bookmarks:" in result.output

    def test_help_shows_database_group(self):
        """Should show Database group header."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "Database:" in result.output

    def test_help_shows_tags_group(self):
        """Should show Tags group header."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "Tags:" in result.output

    def test_help_shows_server_group(self):
        """Should show Server group header."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "Server:" in result.output

    def test_help_group_order(self):
        """Should show groups in order: Bookmarks, Database, Tags, Server."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        output = result.output
        bookmarks_pos = output.index("Bookmarks:")
        database_pos = output.index("Database:")
        tags_pos = output.index("Tags:")
        server_pos = output.index("Server:")
        assert bookmarks_pos < database_pos < tags_pos < server_pos

    def test_help_bookmarks_contains_expected_commands(self):
        """Should list bookmark commands under Bookmarks group."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        lines = result.output.split("\n")
        # Find lines between "Bookmarks:" and next group header
        in_bookmarks = False
        bookmark_commands = []
        for line in lines:
            if line.strip() == "Bookmarks:":
                in_bookmarks = True
                continue
            if in_bookmarks:
                if line.strip() and line.strip().endswith(":") and not line.startswith(" "):
                    break
                stripped = line.strip()
                if stripped:
                    bookmark_commands.append(stripped.split()[0])
        assert "add" in bookmark_commands
        assert "sync" in bookmark_commands
        assert "search-bookmarks" in bookmark_commands

    def test_help_exits_zero(self):
        """Should exit 0 on --help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/unit/test_cli_help.py -v`
Expected: FAIL — no group headers in current help output

- [ ] **Step 3: Implement grouped help in HelpfulGroup**

In `diigo_tagger/cli/main.py`, replace the `HelpfulGroup` class and update the `@click.group` decorator. Also add a helper function `grouped_command` for assigning groups to commands.

Replace the existing `HelpfulGroup` class (lines 87-122) with:

```python
# Group ordering for --help display
COMMAND_GROUPS = ["Bookmarks", "Database", "Tags", "Server"]

# Map each command name to its group
COMMAND_GROUP_MAP = {
    "add": "Bookmarks",
    "lookup": "Bookmarks",
    "search": "Bookmarks",
    "search-bookmarks": "Bookmarks",
    "sync": "Bookmarks",
    "init": "Database",
    "generate": "Tags",
    "list": "Tags",
    "merge": "Tags",
    "dev": "Server",
    "build": "Server",
    "deploy": "Server",
    "promote": "Server",
}


class HelpfulGroup(click.Group):
    """
    Custom Click Group with grouped help output and helpful error messages.

    Commands are organized into labeled sections (Bookmarks, Database,
    Tags, Server) in the --help output. Invalid options trigger suggestions
    for the correct subcommand.
    """

    def format_commands(self, ctx, formatter):
        """Override to display commands in labeled groups."""
        commands_by_group = {}
        for group_name in COMMAND_GROUPS:
            commands_by_group[group_name] = []

        for cmd_name in self.list_commands(ctx):
            cmd = self.get_command(ctx, cmd_name)
            if cmd is None or cmd.hidden:
                continue
            help_text = cmd.get_short_help_str(limit=150)
            group_name = COMMAND_GROUP_MAP.get(cmd_name, "Other")
            if group_name not in commands_by_group:
                commands_by_group[group_name] = []
            commands_by_group[group_name].append((cmd_name, help_text))

        for group_name in COMMAND_GROUPS:
            cmds = commands_by_group.get(group_name, [])
            if not cmds:
                continue
            with formatter.section(group_name):
                formatter.write_dl(sorted(cmds))

        # Any ungrouped commands
        ungrouped = commands_by_group.get("Other", [])
        if ungrouped:
            with formatter.section("Other"):
                formatter.write_dl(sorted(ungrouped))

    def parse_args(self, ctx, args):
        """Override to provide helpful error messages."""
        try:
            return super().parse_args(ctx, args)
        except click.exceptions.NoSuchOption as e:
            click.echo(f"Error: {e.message}\n", err=True)

            option_name = e.option_name
            suggestion = None
            if option_name == '--url':
                suggestion = "add"
            elif option_name in ['--query', '--pattern']:
                suggestion = "search"
            elif option_name in ['--limit', '--sort']:
                suggestion = "list"

            if suggestion:
                click.echo(f"Did you mean: diigo {suggestion} {option_name} ...\n", err=True)

            click.echo("Available commands:", err=True)
            formatter = ctx.make_formatter()
            self.format_commands(ctx, formatter)
            click.echo(formatter.getvalue(), err=True)
            click.echo("\nFor command-specific options, try: diigo <command> --help", err=True)
            ctx.exit(2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_cli_help.py -v`
Expected: PASS (all 7 tests). Note: the Server group test will fail until Task 2 adds the server commands. That's expected — skip that one assertion for now by marking it `@pytest.mark.skip(reason="Server commands added in Task 2")`.

Actually, add the skip decorator to `test_help_shows_server_group` and `test_help_group_order` now, and remove them in Task 2.

- [ ] **Step 5: Run existing CLI tests to check for regressions**

Run: `poetry run pytest tests/unit/test_cli.py -v`
Expected: Same pass/fail count as before this change (no new failures)

- [ ] **Step 6: Commit**

```bash
git add diigo_tagger/cli/main.py tests/unit/test_cli_help.py
git commit -m "feat: add grouped help output to CLI

Organizes --help into Bookmarks, Database, Tags sections.
Server group added when server commands are implemented."
```

---

### Task 2: Add dev Command

**Files:**
- Modify: `diigo_tagger/cli/main.py` (add `dev` command after existing commands)
- Create: `tests/unit/test_cli_server.py`

- [ ] **Step 1: Write failing test for dev command**

Create `tests/unit/test_cli_server.py`:

```python
# ABOUTME: Tests for CLI server and deployment commands (dev, build, deploy, promote)
# ABOUTME: Tests Click command interface with mocked subprocess calls

import os
import json
from unittest.mock import patch, call
from click.testing import CliRunner
from diigo_tagger.cli.main import cli


class TestDevCommand:
    """Test the dev server command."""

    @patch("diigo_tagger.cli.main.subprocess.run")
    def test_dev_starts_uvicorn(self, mock_run):
        """Should start uvicorn with reload on default port."""
        runner = CliRunner()
        result = runner.invoke(cli, ["dev"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args = mock_run.call_args
        cmd = args[0][0]
        assert "uvicorn" in cmd
        assert "diigo_tagger.api.main:app" in cmd
        assert "--reload" in cmd
        assert "--port" in cmd
        assert "8000" in cmd

    @patch("diigo_tagger.cli.main.subprocess.run")
    def test_dev_custom_port(self, mock_run):
        """Should start uvicorn on specified port."""
        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "--port", "3000"])

        assert result.exit_code == 0
        args = mock_run.call_args
        cmd = args[0][0]
        assert "3000" in cmd

    @patch("diigo_tagger.cli.main.subprocess.run")
    def test_dev_shows_startup_message(self, mock_run):
        """Should print startup message with URL."""
        runner = CliRunner()
        result = runner.invoke(cli, ["dev"])

        assert "http://localhost:8000" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/test_cli_server.py::TestDevCommand -v`
Expected: FAIL — no `dev` command

- [ ] **Step 3: Implement dev command**

Add to `diigo_tagger/cli/main.py`, after the existing imports at the top, add:

```python
import subprocess
```

Then add the command after the last existing command (before `if __name__ == "__main__":`):

```python
@cli.command()
@click.option("--port", default=8000, type=click.IntRange(1, 65535), help="Port to run on (default: 8000)")
def dev(port: int):
    """Start local development server."""
    click.echo(f"Starting development server at http://localhost:{port}")
    click.echo("Press Ctrl+C to stop\n")
    subprocess.run([
        "uvicorn",
        "diigo_tagger.api.main:app",
        "--reload",
        "--port", str(port),
    ])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_cli_server.py::TestDevCommand -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Remove skip from Server group help tests**

In `tests/unit/test_cli_help.py`, remove the `@pytest.mark.skip` decorators from `test_help_shows_server_group` and `test_help_group_order`.

- [ ] **Step 6: Run all help tests**

Run: `poetry run pytest tests/unit/test_cli_help.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 7: Commit**

```bash
git add diigo_tagger/cli/main.py tests/unit/test_cli_server.py tests/unit/test_cli_help.py
git commit -m "feat: add dev command to start local web server

Runs uvicorn with --reload on configurable port (default 8000)."
```

---

### Task 3: Add build Command

**Files:**
- Modify: `diigo_tagger/cli/main.py` (add `build` command)
- Modify: `tests/unit/test_cli_server.py` (add build tests)

- [ ] **Step 1: Write failing tests for build command**

Add to `tests/unit/test_cli_server.py`:

```python
class TestBuildCommand:
    """Test the build command for Vercel deployment preparation."""

    @patch("diigo_tagger.cli.main.subprocess.run")
    def test_build_exports_requirements(self, mock_run):
        """Should run poetry export to create requirements.txt."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            os.environ["DIIGO_HOME"] = os.getcwd()
            result = runner.invoke(cli, ["build"])
            del os.environ["DIIGO_HOME"]

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "poetry" in cmd
        assert "export" in cmd

    @patch("diigo_tagger.cli.main.subprocess.run")
    def test_build_creates_api_index(self, mock_run):
        """Should create api/index.py entry point."""
        mock_run.return_value = type("Result", (), {"returncode": 0})()
        runner = CliRunner()
        with runner.isolated_filesystem():
            os.environ["DIIGO_HOME"] = os.getcwd()
            result = runner.invoke(cli, ["build"])
            del os.environ["DIIGO_HOME"]

            assert os.path.exists("api/index.py")
            with open("api/index.py") as f:
                content = f.read()
            assert "from diigo_tagger.api.main import app" in content

    @patch("diigo_tagger.cli.main.subprocess.run")
    def test_build_creates_vercel_json(self, mock_run):
        """Should create vercel.json config."""
        mock_run.return_value = type("Result", (), {"returncode": 0})()
        runner = CliRunner()
        with runner.isolated_filesystem():
            os.environ["DIIGO_HOME"] = os.getcwd()
            result = runner.invoke(cli, ["build"])
            del os.environ["DIIGO_HOME"]

            assert os.path.exists("vercel.json")
            with open("vercel.json") as f:
                config = json.load(f)
            assert "builds" in config
            assert "routes" in config

    @patch("diigo_tagger.cli.main.subprocess.run")
    def test_build_prints_summary(self, mock_run):
        """Should print summary of generated files."""
        mock_run.return_value = type("Result", (), {"returncode": 0})()
        runner = CliRunner()
        with runner.isolated_filesystem():
            os.environ["DIIGO_HOME"] = os.getcwd()
            result = runner.invoke(cli, ["build"])
            del os.environ["DIIGO_HOME"]

        assert "requirements.txt" in result.output
        assert "api/index.py" in result.output
        assert "vercel.json" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/unit/test_cli_server.py::TestBuildCommand -v`
Expected: FAIL — no `build` command

- [ ] **Step 3: Implement build command**

Add to `diigo_tagger/cli/main.py` before `if __name__ == "__main__":`:

```python
@cli.command()
def build():
    """Prepare project for Vercel deployment."""
    project_dir = Path(os.environ.get("DIIGO_HOME", Path(__file__).parent.parent.parent))

    # Export requirements.txt
    click.echo("Exporting requirements.txt from Poetry...")
    subprocess.run(
        ["poetry", "export", "-f", "requirements.txt",
         "--output", str(project_dir / "requirements.txt"),
         "--without-hashes"],
        cwd=str(project_dir),
    )

    # Create api/index.py
    api_dir = project_dir / "api"
    api_dir.mkdir(exist_ok=True)
    index_file = api_dir / "index.py"
    index_file.write_text(
        '# ABOUTME: Vercel serverless function entry point\n'
        '# ABOUTME: Imports the FastAPI app for Vercel to serve\n'
        '\n'
        'from diigo_tagger.api.main import app  # noqa: F401\n'
    )

    # Create vercel.json
    vercel_config = {
        "builds": [{"src": "api/index.py", "use": "@vercel/python"}],
        "routes": [{"src": "/(.*)", "dest": "api/index.py"}],
    }
    vercel_file = project_dir / "vercel.json"
    vercel_file.write_text(json.dumps(vercel_config, indent=2) + "\n")

    click.echo("\nBuild complete:")
    click.echo(f"  requirements.txt  — exported from Poetry")
    click.echo(f"  api/index.py      — Vercel entry point")
    click.echo(f"  vercel.json       — Vercel routing config")
```

Also add `import json` to the imports at the top of the file if not already present.

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_cli_server.py::TestBuildCommand -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add diigo_tagger/cli/main.py tests/unit/test_cli_server.py
git commit -m "feat: add build command for Vercel deployment prep

Exports requirements.txt, creates api/index.py entry point
and vercel.json routing config."
```

---

### Task 4: Add deploy and promote Commands (Scaffolded)

**Files:**
- Modify: `diigo_tagger/cli/main.py` (add `deploy` and `promote` commands)
- Modify: `tests/unit/test_cli_server.py` (add tests)

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_cli_server.py`:

```python
class TestDeployCommand:
    """Test the deploy command (scaffolded)."""

    def test_deploy_shows_not_configured(self):
        """Should print not-configured message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["deploy"])

        assert result.exit_code == 0
        assert "not yet configured" in result.output.lower()

    def test_deploy_mentions_turso(self):
        """Should mention database migration requirement."""
        runner = CliRunner()
        result = runner.invoke(cli, ["deploy"])

        assert "Turso" in result.output


class TestPromoteCommand:
    """Test the promote command (scaffolded)."""

    def test_promote_shows_not_configured(self):
        """Should print not-configured message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["promote"])

        assert result.exit_code == 0
        assert "not yet configured" in result.output.lower()

    def test_promote_mentions_turso(self):
        """Should mention database migration requirement."""
        runner = CliRunner()
        result = runner.invoke(cli, ["promote"])

        assert "Turso" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/unit/test_cli_server.py::TestDeployCommand tests/unit/test_cli_server.py::TestPromoteCommand -v`
Expected: FAIL — no `deploy` or `promote` commands

- [ ] **Step 3: Implement deploy and promote commands**

Add to `diigo_tagger/cli/main.py` before `if __name__ == "__main__":`:

```python
@cli.command()
def deploy():
    """Deploy preview to Vercel."""
    click.echo("Vercel deployment not yet configured. Database migration to Turso required first.")


@cli.command()
def promote():
    """Promote latest preview to production."""
    click.echo("Vercel deployment not yet configured. Database migration to Turso required first.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_cli_server.py -v`
Expected: PASS (all tests in file — dev + build + deploy + promote)

- [ ] **Step 5: Run all help tests again**

Run: `poetry run pytest tests/unit/test_cli_help.py -v`
Expected: PASS (all 7 — Server group now has all 4 commands)

- [ ] **Step 6: Commit**

```bash
git add diigo_tagger/cli/main.py tests/unit/test_cli_server.py
git commit -m "feat: add scaffolded deploy and promote commands

Both print not-configured message pending Turso migration."
```

---

### Task 5: Create bin/diigo Wrapper Template

**Files:**
- Create: `bin/diigo`

- [ ] **Step 1: Create the wrapper template**

Create `bin/diigo`:

```bash
#!/bin/bash
# ABOUTME: CLI wrapper for Diigo Tagger AI — delegates to poetry run diigo
# ABOUTME: Installed by scripts/install.sh, __DIIGO_HOME__ replaced at install time
export DIIGO_HOME="__DIIGO_HOME__"
cd "$DIIGO_HOME" || { echo "Error: DIIGO_HOME directory not found: $DIIGO_HOME"; exit 1; }
poetry run diigo "$@"
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x bin/diigo`

- [ ] **Step 3: Verify the placeholder is present**

Run: `grep '__DIIGO_HOME__' bin/diigo`
Expected: Two matches (export line and comment)

- [ ] **Step 4: Commit**

```bash
git add bin/diigo
git commit -m "feat: add CLI wrapper template for install script

Contains __DIIGO_HOME__ placeholder replaced at install time."
```

---

### Task 6: Create scripts/install.sh

**Files:**
- Modify: `scripts/install.sh` (new file in existing `scripts/` directory)

- [ ] **Step 1: Create the install script**

Create `scripts/install.sh`:

```bash
#!/bin/bash
# ABOUTME: Installs the diigo CLI wrapper to a user-specified bin directory
# ABOUTME: Replaces __DIIGO_HOME__ placeholder with the repo's absolute path

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Diigo Tagger AI CLI Installer"
echo "=============================="
echo ""
echo "Repository location: $REPO_DIR"
echo ""

# Ask for install directory
read -p "Install directory [$HOME/bin]: " INSTALL_DIR
INSTALL_DIR="${INSTALL_DIR:-$HOME/bin}"

# Expand tilde
INSTALL_DIR="${INSTALL_DIR/#\~/$HOME}"

# Create install dir if needed
mkdir -p "$INSTALL_DIR"

# Copy wrapper with placeholder replaced
sed -e "s|__DIIGO_HOME__|$REPO_DIR|g" \
    "$REPO_DIR/bin/diigo" > "$INSTALL_DIR/diigo"
chmod +x "$INSTALL_DIR/diigo"

echo ""
echo "Installed diigo to $INSTALL_DIR/diigo"
echo ""
echo "Run 'diigo --help' to get started."
echo "Run 'diigo dev' to start the web server."
echo ""

# Check if install dir is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "WARNING: $INSTALL_DIR is not in your PATH."
    echo "Add this to your shell profile:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
fi
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/install.sh`

- [ ] **Step 3: Verify it works (dry run)**

Run the install to a temp directory to verify:

```bash
echo "/tmp/diigo-test-install" | scripts/install.sh
cat /tmp/diigo-test-install/diigo | head -5
rm -rf /tmp/diigo-test-install
```

Expected: The wrapper should have the repo path replacing `__DIIGO_HOME__`.

- [ ] **Step 4: Commit**

```bash
git add scripts/install.sh
git commit -m "feat: add CLI install script

Installs diigo wrapper to user's bin directory with repo path baked in."
```

---

### Task 7: Update ABOUTME Headers and Final Verification

**Files:**
- Modify: `diigo_tagger/cli/main.py` (update ABOUTME header)

- [ ] **Step 1: Update ABOUTME header in main.py**

Replace the first two lines of `diigo_tagger/cli/main.py`:

```python
# ABOUTME: Main CLI commands for Diigo Tagger AI
# ABOUTME: Click-based interface for bookmark management, tagging, and server operations
```

- [ ] **Step 2: Run full test suite**

Run: `poetry run pytest tests/unit/test_cli_help.py tests/unit/test_cli_server.py -v`
Expected: PASS (all tests)

- [ ] **Step 3: Verify help output manually**

Run: `poetry run diigo --help`
Expected: Grouped output matching the spec — Bookmarks, Database, Tags, Server sections with alphabetized commands.

- [ ] **Step 4: Verify dev command starts (then ctrl-C)**

Run: `poetry run diigo dev --port 9999`
Expected: Prints startup message, starts uvicorn. Ctrl-C to stop.

- [ ] **Step 5: Final commit**

```bash
git add diigo_tagger/cli/main.py
git commit -m "docs: update ABOUTME header in CLI main module"
```
