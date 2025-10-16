# ABOUTME: Security utilities for Diigo Tagger AI
# ABOUTME: Provides API key redaction, HTTPS validation, and prompt injection detection

import re
from dataclasses import dataclass
from urllib.parse import urlparse


def redact_api_key(api_key: str | None) -> str:
    """
    Redact API key for safe logging.

    Shows first 4 characters for short keys (< 20 chars) or first 8 characters
    for long keys, replacing the rest with ***.

    Args:
        api_key: API key to redact, or None

    Returns:
        Redacted string safe for logging

    Examples:
        >>> redact_api_key("sk-1234567890")
        'sk-1***'
        >>> redact_api_key("sk-proj-1234567890abcdefghijklmnop")
        'sk-proj-***'
    """
    if api_key is None or api_key == "":
        return "***"

    if len(api_key) < 4:
        return "***"

    if len(api_key) < 20:
        return f"{api_key[:4]}***"

    return f"{api_key[:8]}***"


def is_valid_https_url(url: str | None) -> bool:
    """
    Validate that URL uses HTTPS protocol.

    Args:
        url: URL to validate, or None

    Returns:
        True if URL is valid HTTPS, False otherwise

    Examples:
        >>> is_valid_https_url("https://api.openai.com/v1/chat")
        True
        >>> is_valid_https_url("http://insecure.com")
        False
    """
    if url is None or url == "":
        return False

    try:
        parsed = urlparse(url)
        # Must have HTTPS scheme and a valid netloc (domain)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except Exception:
        return False


@dataclass
class InjectionDetectionResult:
    """
    Result of prompt injection detection.

    Attributes:
        is_suspicious: True if suspicious patterns detected
        patterns_detected: List of pattern types found
        confidence: Confidence score (0.0-1.0)
    """

    is_suspicious: bool
    patterns_detected: list[str]
    confidence: float = 0.0


def detect_prompt_injection(text: str | None) -> InjectionDetectionResult:
    """
    Detect potential prompt injection attempts.

    Scans input for common prompt injection patterns including:
    - System instruction override attempts
    - Role manipulation
    - Delimiter/escape sequence injection
    - Command execution attempts
    - Excessive length

    Args:
        text: User input to scan, or None

    Returns:
        InjectionDetectionResult with detection findings

    Examples:
        >>> result = detect_prompt_injection("Ignore previous instructions")
        >>> result.is_suspicious
        True
    """
    if text is None or text == "":
        return InjectionDetectionResult(
            is_suspicious=False, patterns_detected=[], confidence=0.0
        )

    patterns_detected = []
    text_lower = text.lower()

    # Pattern 1: System override attempts
    system_override_patterns = [
        r"ignore\s+(previous|all|prior)\s+instructions",
        r"disregard\s+(previous|all|prior)\s+instructions",
        r"forget\s+(previous|all|prior)\s+instructions",
        r"override\s+system",
        r"system\s*:\s*ignore",
    ]
    for pattern in system_override_patterns:
        if re.search(pattern, text_lower):
            patterns_detected.append("system_override")
            break

    # Pattern 2: Role manipulation
    role_manipulation_patterns = [
        r"you\s+are\s+now",
        r"act\s+as\s+a\s+different",
        r"pretend\s+to\s+be",
        r"you\s+are\s+a\s+different",
        r"switch\s+to\s+developer\s+mode",
        r"enable\s+developer\s+mode",
    ]
    for pattern in role_manipulation_patterns:
        if re.search(pattern, text_lower):
            patterns_detected.append("role_manipulation")
            break

    # Pattern 3: Delimiter injection (escaped newlines, special chars)
    delimiter_patterns = [
        r"\\n\\n(system|user|assistant)\s*:",
        r"\\n\\nsystem\s*:",
        r"\]\]\>",  # Common in XML/template injection
        r"\<\!\-\-",  # Comment injection
    ]
    for pattern in delimiter_patterns:
        if re.search(pattern, text_lower):
            patterns_detected.append("delimiter_injection")
            break

    # Pattern 4: Command injection attempts
    command_patterns = [
        r"exec\s*\(",
        r"eval\s*\(",
        r"__import__\s*\(",
        r"os\.system",
        r"subprocess\.",
        r"`;",  # Shell command separator
        r"\$\(",  # Shell command substitution
    ]
    for pattern in command_patterns:
        if re.search(pattern, text):  # Case-sensitive for code
            patterns_detected.append("command_injection")
            break

    # Pattern 5: Excessive length (potential DoS or hidden injection)
    if len(text) > 10000:
        patterns_detected.append("excessive_length")

    # Calculate confidence based on number of patterns
    confidence = min(len(patterns_detected) / 3.0, 1.0)

    return InjectionDetectionResult(
        is_suspicious=len(patterns_detected) > 0,
        patterns_detected=patterns_detected,
        confidence=confidence,
    )
