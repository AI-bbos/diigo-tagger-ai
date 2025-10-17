# ABOUTME: Main CLI commands for Diigo Tagger AI
# ABOUTME: Click-based interface for sync, search, merge, generate, and list operations

import os
import click
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from ..db import init_db, get_session
from ..models import Tag
from ..api.diigo_client import DiigoClient
from ..api.openai_client import OpenAIClient
from ..services.tag_reconciliation import TagReconciliationService


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
@click.option("--count", default=100, type=click.IntRange(1, 1000), help="Number of bookmarks to fetch (1-1000)")
@click.option("--db-path", type=click.Path(), help="Path to database file")
def sync(count: int, db_path: Optional[str]):
    """Sync bookmarks from Diigo and update tag database."""
    # Get API key from environment
    api_key = os.getenv("DIIGO_API_KEY")
    if not api_key:
        click.echo("✗ Error: DIIGO_API_KEY environment variable not set", err=True)
        raise click.Abort()

    try:
        # Initialize Diigo client
        client = DiigoClient(api_key=api_key)

        # Fetch bookmarks
        click.echo(f"Fetching {count} bookmarks from Diigo...")
        bookmarks = client.fetch_bookmarks(count=count)
        click.echo(f"✓ Fetched {len(bookmarks)} bookmarks")

        # Update tag database with proper session management
        tags_added = 0
        tags_updated = 0

        with db_session_manager(db_path) as session:
            for bookmark in bookmarks:
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

        click.echo(f"✓ Added {tags_added} new tags, updated {tags_updated} existing tags")

    except Exception as e:
        click.echo(f"✗ Error syncing bookmarks: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("query")
@click.option("--semantic", is_flag=True, help="Use semantic similarity search")
@click.option("--threshold", default=0.8, type=click.FloatRange(0.0, 1.0), help="Similarity threshold (0.0-1.0)")
@click.option("--limit", default=20, type=click.IntRange(1, 1000), help="Maximum results to return (1-1000)")
@click.option("--db-path", type=click.Path(), help="Path to database file")
def search(query: str, semantic: bool, threshold: float, limit: int, db_path: Optional[str]):
    """Search for tags using wildcard or semantic similarity."""
    try:
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

    except Exception as e:
        click.echo(f"✗ Error searching tags: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--source", multiple=True, required=True, help="Source tag to merge (can specify multiple)")
@click.option("--target", required=True, help="Target tag to merge into")
@click.option("--db-path", type=click.Path(), help="Path to database file")
def merge(source: tuple, target: str, db_path: Optional[str]):
    """Merge multiple tags into a single canonical tag."""
    if not source:
        click.echo("✗ Error: Must specify at least one --source tag", err=True)
        raise click.Abort()

    try:
        with db_session_manager(db_path) as session:
            service = TagReconciliationService(session)
            click.echo(f"Merging {list(source)} → '{target}'...")
            service.merge_tags(source_tags=list(source), target_tag=target)
            click.echo(f"✓ Tags merged successfully")

    except Exception as e:
        click.echo(f"✗ Error merging tags: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--title", required=True, help="Bookmark title")
@click.option("--description", default="", help="Bookmark description")
@click.option("--url", required=True, help="Bookmark URL")
@click.option("--max-tags", default=8, type=click.IntRange(1, 20), help="Maximum number of tags to generate (1-20)")
def generate(title: str, description: str, url: str, max_tags: int):
    """Generate tag suggestions using AI (GPT-4o-mini)."""
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        click.echo("✗ Error: OPENAI_API_KEY environment variable not set", err=True)
        raise click.Abort()

    try:
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

    except ValueError as e:
        # Prompt injection detected
        click.echo(f"✗ Security error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ Error generating tags: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--limit", default=50, type=click.IntRange(1, 10000), help="Maximum number of tags to display (1-10000)")
@click.option("--source", type=click.Choice(['user', 'master', 'system'], case_sensitive=False), help="Filter by source")
@click.option("--db-path", type=click.Path(), help="Path to database file")
def list(limit: int, source: Optional[str], db_path: Optional[str]):
    """List all tags in the database."""
    try:
        with db_session_manager(db_path) as session:
            # Build query
            query = session.query(Tag)
            if source:
                query = query.filter_by(source=source)

            # Get tags ordered by count
            tags = query.order_by(Tag.count.desc()).limit(limit).all()

            if not tags:
                click.echo("No tags found")
            else:
                click.echo(f"\nShowing {len(tags)} tags:\n")
                click.echo(f"{'Tag':<30} {'Count':<10} {'Source':<10}")
                click.echo("-" * 50)
                for tag in tags:
                    click.echo(f"{tag.name:<30} {tag.count:<10} {tag.source:<10}")

    except Exception as e:
        click.echo(f"✗ Error listing tags: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
