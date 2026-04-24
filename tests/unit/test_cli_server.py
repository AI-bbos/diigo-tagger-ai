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
