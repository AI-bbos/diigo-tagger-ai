# ABOUTME: Service for detecting format: and source: metadata tags from URLs and page metadata
# ABOUTME: Handles registered-domain extraction (including country-code SLDs) and content format classification

from typing import Dict, List, Optional
from urllib.parse import urlparse


# Second-level domains that appear before a ccTLD (e.g. .co.uk, .com.au)
_COUNTRY_SLDS = {"co", "com", "org", "net", "ac", "gov", "edu"}

# Domains that host video content
_VIDEO_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "vimeo.com",
    "dailymotion.com",
    "twitch.tv",
    "rumble.com",
}

# Path segments that indicate a non-root GitHub/GitLab page (not the repo root)
_NON_REPO_SEGMENTS = {"blob", "tree", "raw", "commit", "issues", "pull", "actions", "wiki"}


class MetadataTagDetector:
    """Detects format: and source: metadata tags from a URL and page metadata dict.

    This service is pure (no I/O, no database). It inspects URL structure and a
    lightweight metadata dict to produce structured tag suggestions that downstream
    code can persist as system-generated tags.
    """

    def detect(self, url: str, metadata: Dict) -> List[Dict[str, str]]:
        """Detect all applicable metadata tags for a bookmark.

        Args:
            url: The bookmark URL.
            metadata: Dict of page metadata keys such as ``has_article_tag``
                (bool) and ``content_type`` (str).

        Returns:
            List of dicts, each with ``tag`` (the full tag string, e.g.
            ``"source:github.com"``) and ``type`` (``"source"`` or ``"format"``).
        """
        results: List[Dict[str, str]] = []

        source_tag = self._detect_source(url)
        if source_tag:
            results.append(source_tag)

        format_tag = self._detect_format(url, metadata)
        if format_tag:
            results.append(format_tag)

        return results

    def _detect_source(self, url: str) -> Optional[Dict[str, str]]:
        """Extract the registered domain from a URL as a source tag.

        Strips subdomains (including www) while preserving country-code
        second-level domains such as .co.uk and .com.au.

        Args:
            url: The bookmark URL.

        Returns:
            Dict with ``tag`` and ``type`` keys, or ``None`` if the domain
            cannot be parsed.
        """
        hostname = urlparse(url).hostname
        if not hostname:
            return None

        registered = _registered_domain(hostname)
        if not registered:
            return None

        return {"tag": f"source:{registered}", "type": "source"}

    def _detect_format(self, url: str, metadata: Dict) -> Optional[Dict[str, str]]:
        """Detect the content format from the URL and page metadata.

        Detection priority (first match wins):
        1. Video platform domain
        2. ``.pdf`` file extension
        3. GitHub/GitLab repository root (exactly 2 path segments, no file-view)
        4. Article signal in metadata

        Args:
            url: The bookmark URL.
            metadata: Dict that may contain ``has_article_tag`` (bool) and/or
                ``content_type`` (str).

        Returns:
            Dict with ``tag`` and ``type`` keys, or ``None`` if no format is
            detected.
        """
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        # Normalise to registered domain for platform matching
        registered = _registered_domain(hostname) or hostname

        # 1. Video platforms
        if registered in _VIDEO_DOMAINS:
            return {"tag": "format:video", "type": "format"}

        # 2. PDF by file extension
        path = parsed.path
        if path.lower().endswith(".pdf"):
            return {"tag": "format:pdf", "type": "format"}

        # 3. Repository root on GitHub / GitLab
        if registered in {"github.com", "gitlab.com"}:
            segments = [s for s in path.split("/") if s]
            if len(segments) == 2 and not (_NON_REPO_SEGMENTS & set(segments)):
                return {"tag": "format:repository", "type": "format"}

        # 4. Article signals from metadata
        if metadata.get("has_article_tag") is True:
            return {"tag": "format:article", "type": "format"}
        if metadata.get("content_type") == "article":
            return {"tag": "format:article", "type": "format"}

        return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _registered_domain(hostname: str) -> Optional[str]:
    """Return the registered domain (eTLD+1) for a hostname.

    Handles common country-code second-level domains (e.g. .co.uk, .com.au)
    by checking whether the second-to-last label is a known SLD before a
    two-letter ccTLD.

    Args:
        hostname: Fully-qualified hostname, e.g. ``"www.bbc.co.uk"``.

    Returns:
        Registered domain string (e.g. ``"bbc.co.uk"``), or ``None`` if the
        hostname has fewer than two labels.
    """
    labels = hostname.rstrip(".").split(".")
    if len(labels) < 2:
        return None

    tld = labels[-1]
    sld = labels[-2]

    # Detect pattern: <name>.<known-sld>.<2-char-ccTLD>
    # e.g. bbc.co.uk, abc.com.au
    if len(tld) == 2 and sld in _COUNTRY_SLDS and len(labels) >= 3:
        # Registered domain is labels[-3].<sld>.<tld>
        return f"{labels[-3]}.{sld}.{tld}"

    # Standard case: registered domain is labels[-2].<tld>
    return f"{sld}.{tld}"
