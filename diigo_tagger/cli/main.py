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
from ..api.diigo_client import DiigoClient
from ..api.openai_client import OpenAIClient
from ..services.tag_reconciliation import TagReconciliationService

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


def _fetch_bookmarks_until_new_tags(client, target_new_tags, session, fetch_all=False):
    """
    Fetch bookmarks and process tags until we find target number of new tags.

    Args:
        client: DiigoClient instance
        target_new_tags: Number of new unique tags to find (or None for --all)
        session: Database session
        fetch_all: If True, fetch all bookmarks regardless of new tag count

    Returns:
        Tuple of (bookmarks_processed, tags_added, tags_updated)
    """
    start = 0
    batch_size = 100  # API max per request

    bookmarks_processed = 0
    tags_added = 0
    tags_updated = 0

    while True:
        # Fetch next batch
        batch = client.fetch_bookmarks(count=batch_size, start=start)
        if not batch:
            break

        bookmarks_processed += len(batch)

        # Process tags from this batch
        for bookmark in batch:
            for tag_name in bookmark.tags:
                # Normalize tag name
                tag_name = tag_name.strip().lower()
                if not tag_name:
                    continue

                # Get or create tag
                tag = session.query(Tag).filter_by(name=tag_name).first()
                if tag:
                    tag.count += 1
                    tags_updated += 1
                else:
                    tag = Tag(name=tag_name, count=1, source="user")
                    session.add(tag)
                    tags_added += 1

        # Commit this batch
        session.commit()

        # Show progress
        click.echo(f"  Processed {bookmarks_processed} bookmarks, found {tags_added} new tags, updated {tags_updated} existing tags")

        # Check stopping conditions
        if not fetch_all and tags_added >= target_new_tags:
            click.echo(f"✓ Reached target of {target_new_tags} new tags")
            break

        # If we got less than batch_size, we've reached the end
        if len(batch) < batch_size:
            click.echo(f"✓ Reached end of bookmarks")
            break

        start += batch_size

    return bookmarks_processed, tags_added, tags_updated


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

    # Fetch and process bookmarks
    if fetch_all:
        click.echo("Fetching all bookmarks from Diigo (paginating)...")
        target_msg = "all bookmarks"
    else:
        click.echo(f"Fetching bookmarks until {count} new tags found...")
        target_msg = f"{count} new tags"

    with db_session_manager(db_path) as session:
        bookmarks_processed, tags_added, tags_updated = _fetch_bookmarks_until_new_tags(
            client, count, session, fetch_all
        )

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
    with db_session_manager(db_path) as session:
        service = TagReconciliationService(session)

        if semantic:
            # Semantic search using embeddings
            click.echo(f"Searching for tags similar to '{query}'...")
            results = service.find_similar_tags(query, threshold=threshold, limit=limit)
        else:
            # Wildcard search using FTS5
            click.echo(f"Searching for tags matching '{query}'...")
            results = service.wildcard_search(query, limit=limit)

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
@handle_cli_errors
def generate(title: str, description: str, url: str, max_tags: int):
    """Generate tag suggestions using AI (GPT-4o-mini)."""
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        click.echo("✗ Error: OPENAI_API_KEY environment variable not set", err=True)
        raise click.Abort()

    # Initialize OpenAI client
    client = OpenAIClient(api_key=api_key)

    # Generate tags
    click.echo(f"Generating tags for: {title}")
    tags = client.generate_tags(
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
        # Build query
        query = session.query(Tag)
        if source:
            query = query.filter_by(source=source)

        # Apply sorting
        if sort == 'count':
            query = query.order_by(Tag.count.desc())
        elif sort == 'name':
            query = query.order_by(Tag.name.asc())
        elif sort == 'created':
            query = query.order_by(Tag.created_at.desc())

        # Get tags with limit
        tags = query.limit(limit).all()

        if not tags:
            click.echo("No tags found")
        else:
            click.echo(f"\nShowing {len(tags)} tags:\n")
            click.echo(f"{'Tag':<30} {'Count':<10} {'Source':<10}")
            click.echo("-" * 50)
            for tag in tags:
                click.echo(f"{tag.name:<30} {tag.count:<10} {tag.source:<10}")


if __name__ == "__main__":
    cli()
