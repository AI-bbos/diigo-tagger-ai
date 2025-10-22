# ABOUTME: Main CLI commands for Diigo Tagger AI
# ABOUTME: Click-based interface for sync, search, merge, generate, and list operations

import os
import click
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from dotenv import load_dotenv

from ..db import init_db, get_session
from ..models import Tag
from ..clients.diigo_client import DiigoClient
from ..clients.openai_client import OpenAIClient
from ..services.tag_reconciliation import TagReconciliationService
from ..services.bookmark_service import BookmarkService
from ..services.tag_service import TagService

# Load environment variables from .env file
load_dotenv()


@contextmanager
def db_session_manager(db_path: Optional[str] = None):
    """
    Context manager for database sessions.

    Ensures proper session lifecycle: creation, commit on success,
    rollback on error, and cleanup in all cases.

    Args:
        db_path: Optional custom database path

    Yields:
        SQLAlchemy Session instance

    Examples:
        >>> with db_session_manager() as session:
        ...     tags = session.query(Tag).all()
    """
    db_path_obj = Path(db_path) if db_path else None
    session = get_session(db_path_obj)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def handle_cli_errors(func):
    """
    Decorator for CLI commands to handle errors consistently.

    Catches exceptions, displays user-friendly error messages,
    and aborts with proper exit code.

    Examples:
        >>> @cli.command()
        ... @handle_cli_errors
        ... def my_command():
        ...     # command implementation
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except click.Abort:
            # Already handled, just re-raise
            raise
        except ValueError as e:
            # Validation or security errors
            click.echo(f"✗ Error: {e}", err=True)
            raise click.Abort()
        except Exception as e:
            # Unexpected errors
            click.echo(f"✗ Unexpected error: {e}", err=True)
            raise click.Abort()

    return wrapper


@click.group()
def cli():
    """Diigo Tagger AI - AI-powered bookmark tagging tool."""
    pass


@cli.command()
@click.option("--db-path", type=click.Path(), help="Path to database file")
def init(db_path: Optional[str]):
    """Initialize database with schema."""
    db_path_obj = Path(db_path) if db_path else None

    try:
        engine = init_db(db_path_obj)
        click.echo(f"✓ Database initialized successfully")
        if db_path:
            click.echo(f"  Location: {db_path}")
    except Exception as e:
        click.echo(f"✗ Error initializing database: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--all", "fetch_all", is_flag=True, help="Fetch all bookmarks (paginate through entire collection)")
@click.option("--count", default=500, type=click.IntRange(1, 100000), help="Number of NEW tags to find (default: 500)")
@click.option("--db-path", type=click.Path(), help="Path to database file")
@handle_cli_errors
def sync(fetch_all: bool, count: int, db_path: Optional[str]):
    """Sync bookmarks from Diigo and update tag database.

    Fetches bookmarks in batches of 100 and extracts tags. Stops when:
    - --all: All bookmarks have been fetched
    - --count N: N new/unique tags have been found (default: 500)

    Note: Existing tags get their counts updated but don't count toward --count target.
    """
    # Get credentials from environment
    api_key = os.getenv("DIIGO_API_KEY")
    username = os.getenv("DIIGO_USERNAME")
    password = os.getenv("DIIGO_PASSWORD")

    if not api_key:
        click.echo("✗ Error: DIIGO_API_KEY environment variable not set", err=True)
        raise click.Abort()

    if not username:
        click.echo("✗ Error: DIIGO_USERNAME environment variable not set", err=True)
        raise click.Abort()

    if not password:
        click.echo("✗ Error: DIIGO_PASSWORD environment variable not set", err=True)
        raise click.Abort()

    # Initialize Diigo client
    client = DiigoClient(api_key=api_key, username=username, password=password)

    # Display starting message
    if fetch_all:
        click.echo("Fetching all bookmarks from Diigo (paginating)...")
    else:
        click.echo(f"Fetching bookmarks until {count} new tags found...")

    # Progress callback to show updates
    def progress_callback(bookmarks_processed, tags_added, tags_updated):
        click.echo(f"  Processed {bookmarks_processed} bookmarks, found {tags_added} new tags, updated {tags_updated} existing tags")

    # Use service to sync
    with db_session_manager(db_path) as session:
        service = BookmarkService(session, client)
        bookmarks_processed, tags_added, tags_updated = service.sync(
            target_new_tags=count,
            fetch_all=fetch_all,
            progress_callback=progress_callback
        )

    # Display completion messages
    if fetch_all:
        click.echo("✓ Reached end of bookmarks")
    else:
        click.echo(f"✓ Reached target of {count} new tags")

    click.echo(f"\n✓ Summary:")
    click.echo(f"  Bookmarks processed: {bookmarks_processed}")
    click.echo(f"  New tags added: {tags_added}")
    click.echo(f"  Existing tags updated: {tags_updated}")


@cli.command()
@click.argument("query")
@click.option("--semantic", is_flag=True, help="Use semantic similarity search")
@click.option("--threshold", default=0.8, type=click.FloatRange(0.0, 1.0), help="Similarity threshold (0.0-1.0)")
@click.option("--limit", default=20, type=click.IntRange(1, 1000), help="Maximum results to return (1-1000)")
@click.option("--db-path", type=click.Path(), help="Path to database file")
@handle_cli_errors
def search(query: str, semantic: bool, threshold: float, limit: int, db_path: Optional[str]):
    """Search for tags using wildcard or semantic similarity."""
    # Display search type
    if semantic:
        click.echo(f"Searching for tags similar to '{query}'...")
    else:
        click.echo(f"Searching for tags matching '{query}'...")

    # Use service to search
    with db_session_manager(db_path) as session:
        service = TagReconciliationService(session)
        results = service.search_tags(
            query=query,
            semantic=semantic,
            threshold=threshold,
            limit=limit
        )

    # Display results
    if not results:
        click.echo("No tags found")
    else:
        click.echo(f"\nFound {len(results)} tags:\n")
        for tag in results:
            click.echo(f"  {tag.name:30} (used {tag.count} times)")


@cli.command()
@click.option("--source", multiple=True, required=True, help="Source tag to merge (can specify multiple)")
@click.option("--target", required=True, help="Target tag to merge into")
@click.option("--db-path", type=click.Path(), help="Path to database file")
@handle_cli_errors
def merge(source: tuple, target: str, db_path: Optional[str]):
    """Merge multiple tags into a single canonical tag."""
    if not source:
        click.echo("✗ Error: Must specify at least one --source tag", err=True)
        raise click.Abort()

    with db_session_manager(db_path) as session:
        service = TagReconciliationService(session)
        click.echo(f"Merging {list(source)} → '{target}'...")
        service.merge_tags(source_tags=list(source), target_tag=target)
        click.echo(f"✓ Tags merged successfully")


@cli.command()
@click.option("--title", required=True, help="Bookmark title")
@click.option("--description", default="", help="Bookmark description")
@click.option("--url", required=True, help="Bookmark URL")
@click.option("--max-tags", default=8, type=click.IntRange(1, 20), help="Maximum number of tags to generate (1-20)")
@click.option("--db-path", type=click.Path(), help="Path to database file")
@handle_cli_errors
def generate(title: str, description: str, url: str, max_tags: int, db_path: Optional[str]):
    """Generate tag suggestions using AI (GPT-4o-mini)."""
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        click.echo("✗ Error: OPENAI_API_KEY environment variable not set", err=True)
        raise click.Abort()

    # Initialize OpenAI client
    client = OpenAIClient(api_key=api_key)

    # Use service to generate tags
    click.echo(f"Generating tags for: {title}")
    with db_session_manager(db_path) as session:
        service = TagService(session, client)
        tags = service.generate_tags(
            title=title,
            description=description,
            url=url,
            max_tags=max_tags
        )

    click.echo(f"\n✓ Generated {len(tags)} tags:\n")
    for tag in tags:
        click.echo(f"  {tag}")


@cli.command()
@click.option("--limit", default=50, type=click.IntRange(1, 10000), help="Maximum number of tags to display (1-10000)")
@click.option("--source", type=click.Choice(['user', 'master', 'system'], case_sensitive=False), help="Filter by source")
@click.option("--sort", type=click.Choice(['count', 'name', 'created'], case_sensitive=False), default='count', help="Sort by: count (default), name, or created")
@click.option("--db-path", type=click.Path(), help="Path to database file")
@handle_cli_errors
def list(limit: int, source: Optional[str], sort: str, db_path: Optional[str]):
    """List all tags in the database."""
    with db_session_manager(db_path) as session:
        service = TagService(session)
        tags = service.list_tags(limit=limit, source=source, sort_by=sort)

        if not tags:
            click.echo("No tags found")
        else:
            click.echo(f"\nShowing {len(tags)} tags:\n")
            click.echo(f"{'Tag':<30} {'Count':<10} {'Source':<10}")
            click.echo("-" * 50)
            for tag in tags:
                click.echo(f"{tag.name:<30} {tag.count:<10} {tag.source:<10}")


@cli.command()
@click.option("--url", required=True, help="Bookmark URL")
@click.option("--title", help="Bookmark title (LLM generates if not provided)")
@click.option("--description", help="Bookmark description (LLM generates if not provided)")
@click.option("--tags", help="Comma-separated tags (supplements LLM-generated tags)")
@click.option("--outline", help="Diigo outliner content")
@click.option("--groups", help="Comma-separated Diigo group names")
@click.option("--shared/--private", default=True, help="Make bookmark public (default) or private")
@click.option("--db-path", type=click.Path(), help="Path to database file")
@handle_cli_errors
def add(url: str, title: Optional[str], description: Optional[str], tags: Optional[str],
        outline: Optional[str], groups: Optional[str], shared: bool, db_path: Optional[str]):
    """Add bookmark to Diigo with LLM-powered defaults.

    If title/description not provided, LLM generates them from URL.
    If provided, format is "User Input (LLM Suggestion)".
    Tags are checked for similarity and combined smartly.
    """
    # Get credentials from environment
    diigo_api_key = os.getenv("DIIGO_API_KEY")
    diigo_username = os.getenv("DIIGO_USERNAME")
    diigo_password = os.getenv("DIIGO_PASSWORD")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not diigo_api_key or not diigo_username or not diigo_password:
        click.echo("✗ Error: DIIGO_API_KEY, DIIGO_USERNAME, and DIIGO_PASSWORD must be set", err=True)
        raise click.Abort()

    # Initialize clients
    diigo_client = DiigoClient(api_key=diigo_api_key, username=diigo_username, password=diigo_password)
    openai_client = OpenAIClient(api_key=openai_api_key) if openai_api_key else None

    if not openai_client:
        click.echo("⚠ Warning: OPENAI_API_KEY not set. LLM features disabled.", err=True)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(',')] if tags else None

    # Use service to add bookmark
    click.echo(f"Adding bookmark: {url}")
    with db_session_manager(db_path) as session:
        service = BookmarkService(session, diigo_client, openai_client)
        result = service.add_bookmark(
            url=url,
            title=title,
            description=description,
            tags=tag_list,
            outline=outline,
            groups=groups,
            shared=shared
        )

    # Display results
    click.echo(f"\n✓ Bookmark added successfully!")
    click.echo(f"  Display ID: {result['display_id']}")
    click.echo(f"  Title: {result['title']}")
    if result.get('description'):
        click.echo(f"  Description: {result['description'][:100]}...")
    click.echo(f"  Tags: {', '.join(result['tags'])}")

    if openai_client and result.get('llm_suggestions'):
        click.echo(f"\n  LLM Suggestions:")
        click.echo(f"    Title: {result['llm_suggestions'].get('title')}")
        click.echo(f"    Tags: {', '.join(result['llm_suggestions'].get('tags', []))}")


@cli.command()
@click.argument("identifiers", nargs=-1, required=False)  # Can be URL or display IDs
@click.option("--url", help="Look up by URL")
@click.option("--verbose", "-v", is_flag=True, help="Show full bookmark details")
@click.option("--db-path", type=click.Path(), help="Path to database file")
@handle_cli_errors
def lookup(identifiers: tuple, url: Optional[str], verbose: bool, db_path: Optional[str]):
    """Look up bookmarks by URL or display ID.

    Usage:
        diigo lookup https://example.com          # Look up by URL
        diigo lookup a3f2b8c1                     # Look up by display ID
        diigo lookup a3f2b8c1 b4d7e9f2           # Multiple display IDs
        diigo lookup --url https://example.com    # Explicit URL lookup
        diigo lookup -v a3f2b8c1                  # Verbose mode

    Brief mode shows: display_id, URL, title, tags, similar count
    Verbose mode shows: all fields including description, groups, outlines, dates
    """
    # Get credentials
    diigo_api_key = os.getenv("DIIGO_API_KEY")
    diigo_username = os.getenv("DIIGO_USERNAME")
    diigo_password = os.getenv("DIIGO_PASSWORD")

    if not diigo_api_key or not diigo_username or not diigo_password:
        click.echo("✗ Error: DIIGO_API_KEY, DIIGO_USERNAME, and DIIGO_PASSWORD must be set", err=True)
        raise click.Abort()

    diigo_client = DiigoClient(api_key=diigo_api_key, username=diigo_username, password=diigo_password)

    # Build identifier list
    identifier_list = [url] if url else list(identifiers) if identifiers else []

    if not identifier_list:
        click.echo("✗ Error: Provide URL or display IDs to look up", err=True)
        raise click.Abort()

    # Use service to lookup all identifiers
    with db_session_manager(db_path) as session:
        service = BookmarkService(session, diigo_client)
        results = service.lookup_by_identifiers(identifier_list)

    # Display results
    for result in results:
        if result['type'] == 'url':
            _display_lookup_results(result, verbose)
        else:
            # display_id lookup
            if result['exact_match']:
                _display_bookmark(result['exact_match'], verbose)
            else:
                click.echo(f"✗ No bookmark found with display ID: {result['identifier']}")


def _display_lookup_results(result: dict, verbose: bool):
    """Display lookup results from service."""
    if result['exact_match']:
        click.echo("\n✓ Exact match found:")
        _display_bookmark(result['exact_match'], verbose)
    elif result['similar_matches']:
        click.echo(f"\n⚠ No exact match. Found {result['similar_count']} bookmarks on similar domain:")
        for bookmark in result['similar_matches'][:5]:  # Show top 5
            _display_bookmark(bookmark, verbose=False)  # Brief for similar matches
        if result['similar_count'] > 5:
            click.echo(f"\n  ... and {result['similar_count'] - 5} more. Use display IDs with -v for details.")
    else:
        click.echo("\n✗ No bookmarks found")


def _display_bookmark(bookmark, verbose: bool):
    """Display a single bookmark (brief or verbose)."""
    import json

    # Get tags as list of strings
    tag_names = [tag.name for tag in bookmark.tags] if bookmark.tags else []

    if verbose:
        # Verbose: show everything as JSON
        data = {
            "display_id": bookmark.display_id,
            "url": bookmark.url,
            "title": bookmark.title,
            "description": bookmark.description,
            "tags": tag_names,
            "shared": bookmark.shared,
            "outline": bookmark.outline,
            "groups": bookmark.groups,
            "diigo_created_at": str(bookmark.diigo_created_at) if bookmark.diigo_created_at else None,
            "diigo_updated_at": str(bookmark.diigo_updated_at) if bookmark.diigo_updated_at else None,
            "created_at": str(bookmark.created_at),
            "updated_at": str(bookmark.updated_at)
        }
        click.echo(json.dumps(data, indent=2))
    else:
        # Brief: one-line summary
        tags_str = ', '.join(tag_names[:3])
        if len(tag_names) > 3:
            tags_str += f" (+{len(tag_names) - 3} more)"

        click.echo(f"  [{bookmark.display_id}] {bookmark.title or 'Untitled'}")
        click.echo(f"      {bookmark.url}")
        if tag_names:
            click.echo(f"      Tags: {tags_str}")
        click.echo()


if __name__ == "__main__":
    cli()
