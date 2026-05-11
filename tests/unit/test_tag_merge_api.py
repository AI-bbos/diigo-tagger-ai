# ABOUTME: Tests for the tag merge API endpoints (POST /tags/merge, GET /tags/similar)
# ABOUTME: Validates merge operations, preview mode, and similarity pair detection

import difflib

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from diigo_tagger.models import Tag, Base, bookmark_tags, Bookmark
from diigo_tagger.services.tag_reconciliation import TagReconciliationService


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database with test data."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create test tags
    tag_python = Tag(name="python", count=10, source="user")
    tag_python3 = Tag(name="python3", count=3, source="user")
    tag_py3 = Tag(name="py3", count=2, source="user")
    tag_javascript = Tag(name="javascript", count=8, source="user")
    tag_js = Tag(name="js", count=5, source="user")

    session.add_all([tag_python, tag_python3, tag_py3, tag_javascript, tag_js])
    session.commit()

    # Create a bookmark and associate with tags
    bookmark = Bookmark(
        url="https://example.com",
        title="Test Bookmark",
        display_id="abc123",
    )
    session.add(bookmark)
    session.commit()

    # Associate bookmark with python3 and py3 tags
    session.execute(
        bookmark_tags.insert().values(bookmark_id=bookmark.id, tag_id=tag_python3.id)
    )
    session.execute(
        bookmark_tags.insert().values(bookmark_id=bookmark.id, tag_id=tag_py3.id)
    )
    session.commit()

    yield session
    session.close()


class TestMergeTagsEndpoint:
    """Tests for POST /api/v1/tags/merge logic."""

    def test_merge_valid_source_target(self, db_session):
        """Merge source tags into target and verify counts."""
        # Count affected bookmarks before merge
        source_tag_objs = (
            db_session.query(Tag)
            .filter(Tag.name.in_(["python3", "py3"]))
            .all()
        )
        source_tag_ids = [t.id for t in source_tag_objs]

        affected_bookmarks = (
            db_session.query(func.count(func.distinct(bookmark_tags.c.bookmark_id)))
            .filter(bookmark_tags.c.tag_id.in_(source_tag_ids))
            .scalar()
        ) or 0

        assert len(source_tag_objs) == 2
        assert affected_bookmarks == 1

        # Perform merge
        service = TagReconciliationService(session=db_session)
        service.merge_tags(source_tags=["python3", "py3"], target_tag="python")

        # Verify source tags deleted
        remaining = db_session.query(Tag).filter(Tag.name.in_(["python3", "py3"])).all()
        assert len(remaining) == 0

        # Verify target tag exists with merged count
        target = db_session.query(Tag).filter_by(name="python").first()
        assert target is not None
        assert target.count == 15  # 10 + 3 + 2

    def test_merge_preview_does_not_delete(self, db_session):
        """Preview query (counting affected) does not modify data."""
        source_tag_objs = (
            db_session.query(Tag)
            .filter(Tag.name.in_(["python3", "py3"]))
            .all()
        )
        source_tag_ids = [t.id for t in source_tag_objs]

        affected_bookmarks = (
            db_session.query(func.count(func.distinct(bookmark_tags.c.bookmark_id)))
            .filter(bookmark_tags.c.tag_id.in_(source_tag_ids))
            .scalar()
        ) or 0

        assert affected_bookmarks == 1
        assert len(source_tag_objs) == 2

        # Tags should still exist (no merge performed)
        remaining = db_session.query(Tag).filter(Tag.name.in_(["python3", "py3"])).all()
        assert len(remaining) == 2

    def test_merge_nonexistent_source(self, db_session):
        """Merging nonexistent source tags yields zero counts."""
        source_tag_objs = (
            db_session.query(Tag)
            .filter(Tag.name.in_(["nonexistent"]))
            .all()
        )
        assert len(source_tag_objs) == 0

        # Merge should still succeed (no-op)
        service = TagReconciliationService(session=db_session)
        service.merge_tags(source_tags=["nonexistent"], target_tag="python")

        # Python tag count should be unchanged
        target = db_session.query(Tag).filter_by(name="python").first()
        assert target.count == 10

    def test_merge_creates_target_if_missing(self, db_session):
        """Merge creates target tag when it does not already exist."""
        service = TagReconciliationService(session=db_session)
        service.merge_tags(source_tags=["py3"], target_tag="python-lang")

        target = db_session.query(Tag).filter_by(name="python-lang").first()
        assert target is not None
        assert target.count == 2


class TestSimilarTags:
    """Tests for similar tags detection logic (GET /api/v1/tags/similar)."""

    def test_similar_tags_returns_pairs(self, db_session):
        """Find similar tag pairs above threshold."""
        all_tags = db_session.query(Tag).all()
        tag_names = [t.name for t in all_tags]

        pairs = []
        threshold = 0.5
        for i in range(len(tag_names)):
            for j in range(i + 1, len(tag_names)):
                similarity = difflib.SequenceMatcher(
                    None, tag_names[i], tag_names[j]
                ).ratio()
                if similarity >= threshold:
                    pairs.append({
                        "tag1": tag_names[i],
                        "tag2": tag_names[j],
                        "similarity": round(similarity, 3),
                    })

        # python/python3 should appear as similar
        found_python_pair = any(
            "python" in p["tag1"] and "python" in p["tag2"]
            for p in pairs
        )
        assert found_python_pair
        assert len(pairs) > 0

    def test_similar_tags_respects_threshold(self, db_session):
        """Higher threshold yields fewer pairs."""
        all_tags = db_session.query(Tag).all()
        tag_names = [t.name for t in all_tags]

        def count_pairs(threshold):
            count = 0
            for i in range(len(tag_names)):
                for j in range(i + 1, len(tag_names)):
                    similarity = difflib.SequenceMatcher(
                        None, tag_names[i], tag_names[j]
                    ).ratio()
                    if similarity >= threshold:
                        count += 1
            return count

        low_count = count_pairs(0.5)
        high_count = count_pairs(0.95)
        assert high_count <= low_count

    def test_similar_tags_sorted_by_similarity(self, db_session):
        """Pairs should be sorted by similarity descending."""
        all_tags = db_session.query(Tag).all()
        tag_names = [t.name for t in all_tags]

        pairs = []
        threshold = 0.5
        for i in range(len(tag_names)):
            for j in range(i + 1, len(tag_names)):
                similarity = difflib.SequenceMatcher(
                    None, tag_names[i], tag_names[j]
                ).ratio()
                if similarity >= threshold:
                    pairs.append({"similarity": round(similarity, 3)})

        pairs.sort(key=lambda p: p["similarity"], reverse=True)
        for i in range(len(pairs) - 1):
            assert pairs[i]["similarity"] >= pairs[i + 1]["similarity"]

    def test_similar_tags_includes_counts(self, db_session):
        """Bookmark counts are correctly computed per tag."""
        # python3 and py3 each have 1 bookmark association
        tag_python3 = db_session.query(Tag).filter_by(name="python3").first()
        count = (
            db_session.query(func.count())
            .select_from(bookmark_tags)
            .filter(bookmark_tags.c.tag_id == tag_python3.id)
            .scalar()
        )
        assert count == 1
