# ABOUTME: Interactive prompt_toolkit-based form for the CLI add-bookmark workflow
# ABOUTME: Handles rating input, prefix tag entry with autocomplete, and tag accept/reject

from typing import Dict, List, Optional

import click
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import WordCompleter


class AddForm:
    """Interactive form for CLI add-bookmark workflow.

    Wraps prompt_toolkit prompts for rating, prefix tags, and tag
    accept/reject flows. Pure helper methods (_filter_accepted,
    _build_rating_tag, etc.) contain no I/O and are unit-testable
    without mocking.
    """

    def __init__(self, session):
        """Initialize with DB session for autocomplete lookups.

        Args:
            session: SQLAlchemy Session used to query existing tags for
                autocomplete suggestions.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Interactive prompt methods
    # ------------------------------------------------------------------

    def prompt_title(self, default: str) -> str:
        """Show current title and let the user edit or press enter to keep.

        Args:
            default: The current title value shown as pre-filled text.

        Returns:
            The (possibly edited) title string.
        """
        click.echo("Title:")
        result = pt_prompt("  > ", default=default)
        return result.strip() or default

    def prompt_description(self, default: str) -> str:
        """Show a truncated description and let the user edit or keep it.

        Displays only the first 120 characters of the default to avoid
        cluttering the terminal; the full value is still used as the
        editable default.

        Args:
            default: The current description value.

        Returns:
            The (possibly edited) description string.
        """
        truncated = default[:120] + "..." if len(default) > 120 else default
        click.echo(f"Description (showing first 120 chars): {truncated}")
        result = pt_prompt("  > ", default=default)
        return result.strip() or default

    def prompt_tag_list(self, tags: List[str], label: str) -> List[str]:
        """Present each tag for accept/reject and return the accepted subset.

        The user presses Enter to accept a tag or types 'n' (then Enter)
        to reject it.

        Args:
            tags: List of tag strings to review.
            label: Section heading displayed before the tag list.

        Returns:
            Tags that the user accepted.
        """
        if not tags:
            return []

        click.echo(f"\n{label} (Enter=keep, n=reject):")
        accepted: List[str] = []
        for tag in tags:
            response = pt_prompt(f"  {tag}? ").strip().lower()
            if response != "n":
                accepted.append(tag)
        return accepted

    def prompt_metadata_tags(self, detected: List[Dict]) -> List[str]:
        """Present detected metadata tags for accept/reject.

        Args:
            detected: List of dicts in the form
                ``[{"tag": "source:x", "type": "source"}, ...]`` as
                returned by MetadataTagDetector.

        Returns:
            Tag strings that the user accepted.
        """
        if not detected:
            return []

        click.echo("\nDetected metadata tags (Enter=keep, n=reject):")
        accepted: List[str] = []
        for item in detected:
            tag_str = item["tag"]
            tag_type = item.get("type", "")
            response = pt_prompt(f"  [{tag_type}] {tag_str}? ").strip().lower()
            if response != "n":
                accepted.append(tag_str)
        return accepted

    def prompt_prefix_tags(self, prefixes: List[str]) -> List[str]:
        """Prompt for a value for each prefix, with autocomplete from existing tags.

        Uses WordCompleter populated from tags already in the database that
        start with the given prefix.

        Args:
            prefixes: List of prefix strings, e.g. ``["reference:", "author:"]``.

        Returns:
            Complete tag strings like ``["reference:peter-zeihan"]`` for
            each prefix where the user entered a non-empty value.
        """
        result: List[str] = []
        for prefix in prefixes:
            existing = self._fetch_prefix_completions(prefix)
            completer = WordCompleter(existing, sentence=True)
            click.echo(f"\nEnter value for '{prefix}' (Tab for autocomplete, Enter to skip):")
            value = pt_prompt(f"  {prefix}", completer=completer).strip()
            tag = self._build_prefix_tag(prefix, value)
            if tag:
                result.append(tag)
        return result

    def prompt_rating(self) -> Optional[str]:
        """Prompt for a single-keypress rating.

        Keys 1–9 map to ratings 1–9, '0' maps to 10, Enter skips.

        Returns:
            A tag string like ``"rating=7_10"``, or ``None`` if the user
            skipped.
        """
        click.echo("\nRating (1-9, 0=10, Enter=skip):")
        from prompt_toolkit.keys import Keys
        from prompt_toolkit import Application
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import Window
        from prompt_toolkit.layout.controls import FormattedTextControl

        rating_holder: List[Optional[int]] = [None]
        done_holder: List[bool] = [False]

        kb = KeyBindings()

        @kb.add("0")
        @kb.add("1")
        @kb.add("2")
        @kb.add("3")
        @kb.add("4")
        @kb.add("5")
        @kb.add("6")
        @kb.add("7")
        @kb.add("8")
        @kb.add("9")
        def handle_digit(event):
            """Record the digit keypress and exit the application."""
            key = event.key_sequence[0].key
            parsed = self._parse_rating_key(key)
            if parsed > 0:
                rating_holder[0] = parsed
            done_holder[0] = True
            event.app.exit()

        @kb.add("enter")
        @kb.add("c-c")
        def handle_skip(event):
            """Exit without recording a rating (skip)."""
            done_holder[0] = True
            event.app.exit()

        layout = Layout(Window(FormattedTextControl("  Rating: ")))
        app = Application(layout=layout, key_bindings=kb)
        app.run()

        return self._build_rating_tag(rating_holder[0])

    # ------------------------------------------------------------------
    # Pure helper methods (unit-testable without mocking I/O)
    # ------------------------------------------------------------------

    def _filter_accepted(self, tags: List[Dict]) -> List[str]:
        """Return tag strings from dicts where accepted is True.

        Args:
            tags: List of dicts with at minimum ``"tag"`` and
                ``"accepted"`` keys.

        Returns:
            List of ``tag`` strings where ``accepted`` is ``True``.
        """
        return [item["tag"] for item in tags if item.get("accepted") is True]

    def _build_rating_tag(self, rating: Optional[int]) -> Optional[str]:
        """Format a rating integer as a tag string.

        Args:
            rating: Integer 1–10, or ``None`` to skip.

        Returns:
            A string like ``"rating=7_10"``, or ``None`` if rating is
            ``None``.
        """
        if rating is None:
            return None
        return f"rating={rating}_10"

    def _build_prefix_tag(self, prefix: str, value: Optional[str]) -> Optional[str]:
        """Combine a prefix and a value into a complete tag string.

        Args:
            prefix: The prefix including its trailing colon, e.g.
                ``"reference:"``.
            value: The value portion entered by the user.  Empty string
                or ``None`` returns ``None``.

        Returns:
            The combined tag string e.g. ``"reference:peter-zeihan"``,
            or ``None`` if value is falsy.
        """
        if not value:
            return None
        # If the prefix already ends with ':' we don't double it
        if prefix.endswith(":"):
            return f"{prefix}{value}"
        return f"{prefix}:{value}"

    def _parse_rating_key(self, key: str) -> int:
        """Map a keypress character to a rating integer.

        Args:
            key: Single character string from a keypress event.

        Returns:
            Integer 1–10 for digit keys (``"0"`` maps to 10),
            ``-1`` for invalid input, and ``None`` for Enter (represented
            as an empty string ``""``).

        Note:
            The function signature returns ``int`` but may return ``None``
            for the Enter key.  Callers should check for ``None`` before
            using the result numerically.
        """
        if key == "":
            return None  # type: ignore[return-value]
        if key == "0":
            return 10
        if key.isdigit():
            return int(key)
        return -1

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_prefix_completions(self, prefix: str) -> List[str]:
        """Query the database for tag values that start with prefix.

        Args:
            prefix: Tag prefix including colon, e.g. ``"reference:"``.

        Returns:
            List of full tag name strings matching the prefix.
        """
        from diigo_tagger.models import Tag

        try:
            rows = (
                self.session.query(Tag.name)
                .filter(Tag.name.like(f"{prefix}%"))
                .all()
            )
            return [row[0] for row in rows]
        except Exception:
            return []
