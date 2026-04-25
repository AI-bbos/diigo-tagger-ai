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
