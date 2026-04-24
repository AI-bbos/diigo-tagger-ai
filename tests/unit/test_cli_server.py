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
