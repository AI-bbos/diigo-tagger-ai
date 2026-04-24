# ABOUTME: Tests for grouped CLI help output
# ABOUTME: Verifies commands are organized into labeled sections

import pytest
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

    @pytest.mark.skip(reason="Server commands added in Task 2")
    def test_help_shows_server_group(self):
        """Should show Server group header."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "Server:" in result.output

    @pytest.mark.skip(reason="Server commands added in Task 2")
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
