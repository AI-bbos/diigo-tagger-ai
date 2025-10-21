#!/bin/bash
# ABOUTME: Shell setup script for Diigo Tagger AI development
# ABOUTME: Sources this file to activate venv and create convenient aliases

# Get the Poetry virtual environment path
VENV_PATH=$(poetry env info --path 2>/dev/null)

if [ -z "$VENV_PATH" ]; then
    echo "❌ Error: Poetry virtual environment not found."
    echo "   Run 'poetry install' first to create the environment."
    return 1 2>/dev/null || exit 1
fi

# Activate the virtual environment
echo "✓ Activating Poetry virtual environment..."
source "$VENV_PATH/bin/activate"

# Create convenient alias for diigo command
alias diigo='poetry run diigo'

# Create aliases for common development tasks
alias diigo-test='poetry run pytest'
alias diigo-coverage='poetry run pytest --cov=diigo_tagger --cov-report=term-missing'
alias diigo-lint='poetry run ruff check diigo_tagger'
alias diigo-format='poetry run black diigo_tagger'

echo "✓ Environment activated!"
echo ""
echo "Available commands:"
echo "  diigo              - Run diigo CLI (via poetry run)"
echo "  diigo-test         - Run test suite"
echo "  diigo-coverage     - Run tests with coverage report"
echo "  diigo-lint         - Run linter (ruff)"
echo "  diigo-format       - Format code (black)"
echo ""
echo "Examples:"
echo "  diigo init"
echo "  diigo --help"
echo "  diigo-test"
echo ""
echo "To deactivate when done: deactivate"
