# ABOUTME: Application-wide constants and configuration values
# ABOUTME: Centralizes magic numbers, limits, and defaults for maintainability

"""
Constants module for Diigo Tagger AI.

This module defines all magic numbers, limits, and default values used throughout
the application. Centralizing these values improves maintainability and makes it
easier to understand why specific values were chosen.
"""

# Security - Prompt Injection Detection
PROMPT_INJECTION_MAX_LENGTH = 10000
"""Maximum allowed length for user input to prevent DoS attacks."""

# Security - API Key Redaction
API_KEY_SHORT_THRESHOLD = 4
"""Minimum characters to show for very short API keys."""

API_KEY_SHORT_VISIBLE_CHARS = 4
"""Number of characters to show for keys < 20 chars."""

API_KEY_LONG_THRESHOLD = 20
"""Length threshold between short and long API keys."""

API_KEY_LONG_VISIBLE_CHARS = 8
"""Number of characters to show for keys >= 20 chars."""

# Tag Model - Embedding
EMBEDDING_DIMENSION = 384
"""Dimensionality of sentence-transformers/all-MiniLM-L6-v2 embeddings."""

EMBEDDING_DTYPE = "float32"
"""Data type for storing embeddings (numpy dtype)."""

EMBEDDING_VERSION = 1
"""Current version of embedding model (for future migrations)."""

# CLI - Default Values
DEFAULT_SYNC_COUNT = 100
"""Default number of bookmarks to fetch from Diigo API."""

DEFAULT_SEARCH_LIMIT = 20
"""Default number of search results to return."""

DEFAULT_SEARCH_THRESHOLD = 0.8
"""Default similarity threshold for semantic search (0.0-1.0)."""

DEFAULT_LIST_LIMIT = 50
"""Default number of tags to display in list command."""

DEFAULT_MAX_TAGS = 8
"""Default maximum number of tags to generate with AI."""

# CLI - Input Validation Ranges
SYNC_COUNT_MIN = 1
SYNC_COUNT_MAX = 1000
"""Valid range for --count parameter in sync command."""

SEARCH_LIMIT_MIN = 1
SEARCH_LIMIT_MAX = 1000
"""Valid range for --limit parameter in search command."""

SEARCH_THRESHOLD_MIN = 0.0
SEARCH_THRESHOLD_MAX = 1.0
"""Valid range for --threshold parameter in semantic search."""

GENERATE_MAX_TAGS_MIN = 1
GENERATE_MAX_TAGS_MAX = 20
"""Valid range for --max-tags parameter in generate command."""

LIST_LIMIT_MIN = 1
LIST_LIMIT_MAX = 10000
"""Valid range for --limit parameter in list command."""

# API - Timeouts
DIIGO_API_TIMEOUT = 30
"""Timeout in seconds for Diigo API requests."""

OPENAI_API_TIMEOUT = 60
"""Timeout in seconds for OpenAI API requests."""

# API - Tag Generation
OPENAI_MODEL = "gpt-4o-mini"
"""Default OpenAI model for tag generation."""

OPENAI_TEMPERATURE = 0.3
"""Temperature for LLM generation (lower = more deterministic)."""

OPENAI_MAX_TOKENS = 100
"""Maximum tokens for LLM response."""

# Database - SQLite Version
SQLITE_MIN_VERSION = (3, 35, 0)
"""Minimum SQLite version required for FTS5 support."""
