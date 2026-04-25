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

# Resolve venv Python path
VENV_PYTHON="$(cd "$REPO_DIR" && poetry env info -e 2>/dev/null || echo "")"
if [ -z "$VENV_PYTHON" ]; then
    echo "WARNING: Could not detect virtualenv. Run 'poetry install' first."
    echo "         The wrapper will fall back to 'poetry env info' at runtime (slower)."
    VENV_PYTHON="__VENV_PYTHON__"  # Leave placeholder for runtime fallback
fi

# Copy wrapper with placeholders replaced
sed -e "s|__DIIGO_HOME__|$REPO_DIR|g" \
    -e "s|__VENV_PYTHON__|$VENV_PYTHON|g" \
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
