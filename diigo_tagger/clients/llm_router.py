# ABOUTME: Multi-provider LLM router using LangChain
# ABOUTME: Supports OpenAI, Anthropic, Google with automatic fallback and transparency

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropicMessages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..security import detect_prompt_injection

logger = logging.getLogger(__name__)


@dataclass
class LLMProvider:
    """
    Represents an LLM provider configuration.

    Attributes:
        name: Provider name (e.g., "openai", "anthropic")
        client: LangChain chat client instance
        model: Model identifier
        available: Whether provider is available
    """
    name: str
    client: Any
    model: str
    available: bool = True


class LLMRouter:
    """
    Multi-provider LLM router with automatic fallback.

    Routes LLM requests to available providers (OpenAI, Anthropic, Google)
    with automatic fallback on errors. Provides provider transparency in responses.

    Example:
        >>> router = LLMRouter(
        ...     openai_api_key="sk-...",
        ...     anthropic_api_key="sk-ant-..."
        ... )
        >>> result = router.generate_tags(
        ...     title="Learn Python",
        ...     description="Beginner tutorial",
        ...     url="https://example.com"
        ... )
        >>> result
        {
            "tags": ["python", "tutorial", "programming"],
            "provider": "anthropic",
            "model": "claude-3-haiku-20240307",
            "fallback": False
        }
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
    ):
        """
        Initialize LLM router with available providers.

        Args:
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key
            google_api_key: Google API key

        Raises:
            ValueError: If no API keys provided
        """
        self.providers: List[LLMProvider] = []

        # Initialize providers in priority order (cheapest first)
        # Priority: Anthropic (Haiku) > OpenAI (GPT-4o-mini) > Google (Gemini)

        if anthropic_api_key:
            try:
                client = ChatAnthropicMessages(
                    api_key=anthropic_api_key,
                    model_name="claude-3-haiku-20240307",
                    temperature=0.3,
                    max_tokens=100,
                )
                self.providers.append(LLMProvider(
                    name="anthropic",
                    client=client,
                    model="claude-3-haiku-20240307",
                    available=True
                ))
                logger.info("Initialized Anthropic provider")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic: {e}")

        if openai_api_key:
            try:
                client = ChatOpenAI(
                    api_key=openai_api_key,
                    model="gpt-4o-mini",
                    temperature=0.3,
                    max_tokens=100,
                )
                self.providers.append(LLMProvider(
                    name="openai",
                    client=client,
                    model="gpt-4o-mini",
                    available=True
                ))
                logger.info("Initialized OpenAI provider")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")

        if google_api_key:
            try:
                client = ChatGoogleGenerativeAI(
                    google_api_key=google_api_key,
                    model="gemini-pro",
                    temperature=0.3,
                    max_output_tokens=100,
                )
                self.providers.append(LLMProvider(
                    name="google",
                    client=client,
                    model="gemini-pro",
                    available=True
                ))
                logger.info("Initialized Google provider")
            except Exception as e:
                logger.warning(f"Failed to initialize Google: {e}")

        if not self.providers:
            raise ValueError(
                "At least one LLM provider API key must be provided "
                "(openai_api_key, anthropic_api_key, or google_api_key)"
            )

        logger.info(f"LLMRouter initialized with {len(self.providers)} provider(s)")

    def generate_tags(
        self,
        title: str,
        description: str,
        url: str,
        max_tags: int = 8
    ) -> Dict[str, Any]:
        """
        Generate tags using available LLM providers with fallback.

        Args:
            title: Bookmark title
            description: Bookmark description
            url: Bookmark URL
            max_tags: Maximum number of tags to generate

        Returns:
            Dict containing:
                - tags: List of generated tag strings
                - provider: Provider name used (e.g., "openai")
                - model: Model identifier used
                - fallback: Whether fallback was used (boolean)

        Raises:
            ValueError: If suspicious input detected (prompt injection)
            Exception: If all providers fail
        """
        # Security: Detect prompt injection attempts
        combined_input = f"{title} {description} {url}"
        detection_result = detect_prompt_injection(combined_input)

        if detection_result.is_suspicious:
            raise ValueError(
                f"Suspicious input detected. Patterns: {', '.join(detection_result.patterns_detected)}"
            )

        # Build prompts
        system_prompt = (
            "You are a tag generation assistant for bookmark organization. "
            "Generate relevant, concise tags based on the bookmark content. "
            "Return ONLY comma-separated tags, no explanations. "
            "Use lowercase, hyphenated format (e.g., 'web-development', 'python'). "
            f"Maximum {max_tags} tags."
        )

        user_prompt = f"""Title: {title}
Description: {description}
URL: {url}

Generate relevant tags for this bookmark."""

        # Try providers in order
        errors = []
        providers_attempted = 0

        for provider in self.providers:
            if not provider.available:
                continue

            try:
                logger.debug(f"Attempting tag generation with {provider.name}")

                # Create messages for LangChain
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]

                # Invoke LLM
                response = provider.client.invoke(messages)

                # Parse response
                content = response.content.strip()

                # Extract tags from response
                tags = [tag.strip().lower() for tag in content.split(",")]
                # Filter out empty tags and limit to max_tags
                tags = [tag for tag in tags if tag][:max_tags]

                logger.info(
                    f"Successfully generated {len(tags)} tags using {provider.name}"
                )

                # Fallback used if we had failures before this success
                fallback_used = providers_attempted > 0

                return {
                    "tags": tags,
                    "provider": provider.name,
                    "model": provider.model,
                    "fallback": fallback_used
                }

            except Exception as e:
                error_msg = f"{provider.name}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Provider {provider.name} failed: {e}")
                providers_attempted += 1

                # Continue to next provider
                continue

        # All providers failed
        error_summary = "; ".join(errors)
        raise Exception(
            f"All LLM providers failed. Errors: {error_summary}"
        )
