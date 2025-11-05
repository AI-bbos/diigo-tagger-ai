# ABOUTME: OpenAI API client for tag generation (now wraps LLMRouter)
# ABOUTME: Backward-compatible wrapper around LLMRouter for multi-provider support

from typing import List
import logging

from .llm_router import LLMRouter

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Client for LLM-based tag generation.

    DEPRECATED: This class now wraps LLMRouter for backward compatibility.
    New code should use LLMRouter directly for multi-provider support.

    Maintains the same interface (returns List[str]) but uses LLMRouter
    internally with automatic provider fallback.
    """

    def __init__(self, api_key: str | None, model: str = "gpt-4o-mini"):
        """
        Initialize LLM client.

        Args:
            api_key: OpenAI API key for authentication
            model: Model to use (default: gpt-4o-mini) - ignored, LLMRouter chooses

        Raises:
            ValueError: If API key is missing
        """
        if not api_key:
            raise ValueError("API key is required for OpenAI client")

        self.api_key = api_key
        self.model = model

        # Use LLMRouter internally
        self.router = LLMRouter(openai_api_key=api_key)
        logger.info("OpenAIClient initialized (using LLMRouter)")

    def generate_tags(
        self, title: str, description: str, url: str, max_tags: int = 8
    ) -> List[str]:
        """
        Generate tags for a bookmark using LLM.

        Uses LLMRouter internally with automatic provider fallback.
        Maintains backward compatibility by returning List[str].

        Args:
            title: Bookmark title
            description: Bookmark description/notes
            url: Bookmark URL
            max_tags: Maximum number of tags to generate

        Returns:
            List of generated tag strings

        Raises:
            ValueError: If suspicious input detected (prompt injection)
            Exception: On API errors (rate limit, network errors)

        Note:
            This method now uses LLMRouter internally for multi-provider support.
            The full response (including provider, model, fallback status) is logged.
        """
        # Use LLMRouter to generate tags
        result = self.router.generate_tags(
            title=title,
            description=description,
            url=url,
            max_tags=max_tags
        )

        # Log provider transparency info
        logger.info(
            f"Generated {len(result['tags'])} tags using {result['provider']} "
            f"(model: {result['model']}, fallback: {result['fallback']})"
        )

        # Return just the tags for backward compatibility
        return result["tags"]
