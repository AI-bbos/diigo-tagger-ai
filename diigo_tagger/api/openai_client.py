# ABOUTME: OpenAI API client for tag generation
# ABOUTME: Uses GPT-4o-mini with prompt injection detection and error handling

from typing import List
from openai import OpenAI

from ..security import detect_prompt_injection, redact_api_key


class OpenAIClient:
    """
    Client for OpenAI API tag generation.

    Uses GPT-4o-mini to generate relevant tags from bookmark content.
    Includes prompt injection detection for security.
    """

    def __init__(self, api_key: str | None, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI API client.

        Args:
            api_key: OpenAI API key for authentication
            model: Model to use (default: gpt-4o-mini)

        Raises:
            ValueError: If API key is missing
        """
        if not api_key:
            raise ValueError("API key is required for OpenAI client")

        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def generate_tags(
        self, title: str, description: str, url: str, max_tags: int = 8
    ) -> List[str]:
        """
        Generate tags for a bookmark using GPT-4o-mini.

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
        """
        # Security: Detect prompt injection attempts
        combined_input = f"{title} {description} {url}"
        detection_result = detect_prompt_injection(combined_input)

        if detection_result.is_suspicious:
            raise ValueError(
                f"Suspicious input detected. Patterns: {', '.join(detection_result.patterns_detected)}"
            )

        # Build prompt
        system_prompt = (
            "You are a tag generation assistant for bookmark organization. "
            "Generate relevant, concise tags based on the bookmark content. "
            "Return ONLY comma-separated tags, no explanations. "
            "Use lowercase, hyphenated format (e.g., 'web-development', 'python'). "
            f"Maximum {max_tags} tags."
        )

        user_prompt = f"""
Title: {title}
Description: {description}
URL: {url}

Generate relevant tags for this bookmark.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=100,
            )

            # Parse response
            content = response.choices[0].message.content.strip()

            # Extract tags from response (handle various formats)
            # Split by comma and clean up
            tags = [tag.strip().lower() for tag in content.split(",")]
            # Filter out empty tags and limit to max_tags
            tags = [tag for tag in tags if tag][:max_tags]

            return tags

        except Exception as e:
            # Re-raise with better error message
            error_msg = str(e)
            if "rate limit" in error_msg.lower():
                raise Exception(f"Rate limit exceeded for OpenAI API: {e}")
            raise
