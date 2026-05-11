# ABOUTME: Unit tests for tag hierarchy API endpoints (GET and POST /api/v1/tags/hierarchy)
# ABOUTME: Tests tree response structure, parent assignment, removal, and circular reference prevention

import pytest
from unittest.mock import MagicMock, patch

from diigo_tagger.api.routes.bookmarks import get_tag_hierarchy, set_tag_parent, SetParentRequest
from diigo_tagger.models import Tag


class TestGetTagHierarchy:
    """Tests for GET /api/v1/tags/hierarchy."""

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_empty_hierarchy(self, mock_get_session):
        """Empty database returns empty tags list."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_session.query.return_value.outerjoin.return_value.group_by.return_value.order_by.return_value.all.return_value = []

        result = await get_tag_hierarchy()
        assert result == {"tags": []}

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_hierarchy_returns_tree(self, mock_get_session):
        """Tags with parent-child relationships are nested correctly."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Simulate: development(id=1, parent=None), python(id=2, parent=1), javascript(id=3, parent=None)
        mock_session.query.return_value.outerjoin.return_value.group_by.return_value.order_by.return_value.all.return_value = [
            (1, "development", None, 100),
            (2, "python", 1, 50),
            (3, "javascript", None, 30),
        ]

        result = await get_tag_hierarchy()

        root_names = {t["name"] for t in result["tags"]}
        assert "development" in root_names
        assert "javascript" in root_names
        assert "python" not in root_names

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_hierarchy_nesting_depth(self, mock_get_session):
        """Verify two levels of nesting: development -> python -> flask."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_session.query.return_value.outerjoin.return_value.group_by.return_value.order_by.return_value.all.return_value = [
            (1, "development", None, 100),
            (2, "python", 1, 50),
            (3, "flask", 2, 10),
        ]

        result = await get_tag_hierarchy()

        dev = next(t for t in result["tags"] if t["name"] == "development")
        assert len(dev["children"]) == 1
        assert dev["children"][0]["name"] == "python"

        py = dev["children"][0]
        assert len(py["children"]) == 1
        assert py["children"][0]["name"] == "flask"
        assert py["children"][0]["children"] == []

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_hierarchy_node_structure(self, mock_get_session):
        """Each node has id, name, parent_id, count, and children."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_session.query.return_value.outerjoin.return_value.group_by.return_value.order_by.return_value.all.return_value = [
            (1, "development", None, 100),
        ]

        result = await get_tag_hierarchy()

        tag = result["tags"][0]
        assert tag["id"] == 1
        assert tag["name"] == "development"
        assert tag["parent_id"] is None
        assert tag["count"] == 100
        assert tag["children"] == []

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_root_tags_sorted_by_count_descending(self, mock_get_session):
        """Root tags are sorted by bookmark count, highest first."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_session.query.return_value.outerjoin.return_value.group_by.return_value.order_by.return_value.all.return_value = [
            (1, "alpha", None, 10),
            (2, "beta", None, 50),
            (3, "gamma", None, 30),
        ]

        result = await get_tag_hierarchy()

        names = [t["name"] for t in result["tags"]]
        assert names == ["beta", "gamma", "alpha"]


class TestSetTagParent:
    """Tests for POST /api/v1/tags/hierarchy."""

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_set_parent(self, mock_get_session):
        """Assign a parent to a tag."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        tag = MagicMock(spec=Tag)
        tag.name = "python"
        tag.id = 2
        tag.parent_id = None

        parent = MagicMock(spec=Tag)
        parent.name = "development"
        parent.id = 1
        parent.parent_id = None

        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=tag)),       # tag lookup
            MagicMock(first=MagicMock(return_value=parent)),    # parent lookup
        ]

        request = SetParentRequest(tag_name="python", parent_name="development")
        result = await set_tag_parent(request)

        assert result["tag"] == "python"
        assert result["parent_id"] == 1
        assert tag.parent_id == 1
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_remove_parent(self, mock_get_session):
        """Set parent_name to null to make a tag top-level."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        tag = MagicMock(spec=Tag)
        tag.name = "python"
        tag.id = 2
        tag.parent_id = 1

        mock_session.query.return_value.filter_by.return_value.first.return_value = tag

        request = SetParentRequest(tag_name="python", parent_name=None)
        result = await set_tag_parent(request)

        assert result["tag"] == "python"
        assert result["parent_id"] is None
        assert tag.parent_id is None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_set_parent_tag_not_found(self, mock_get_session):
        """Return 404 when the tag to modify does not exist."""
        from fastapi import HTTPException

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        request = SetParentRequest(tag_name="nonexistent", parent_name="development")

        with pytest.raises(HTTPException) as exc_info:
            await set_tag_parent(request)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "TAG_NOT_FOUND"

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_set_parent_parent_not_found(self, mock_get_session):
        """Return 404 when the desired parent does not exist."""
        from fastapi import HTTPException

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        tag = MagicMock(spec=Tag)
        tag.name = "python"
        tag.id = 2

        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=tag)),     # tag found
            MagicMock(first=MagicMock(return_value=None)),    # parent not found
        ]

        request = SetParentRequest(tag_name="python", parent_name="nonexistent")

        with pytest.raises(HTTPException) as exc_info:
            await set_tag_parent(request)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "PARENT_TAG_NOT_FOUND"

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_self_parent_rejected(self, mock_get_session):
        """Cannot set a tag as its own parent."""
        from fastapi import HTTPException

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        tag = MagicMock(spec=Tag)
        tag.name = "python"
        tag.id = 2

        # Both lookups return the same tag
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=tag)),
            MagicMock(first=MagicMock(return_value=tag)),
        ]

        request = SetParentRequest(tag_name="python", parent_name="python")

        with pytest.raises(HTTPException) as exc_info:
            await set_tag_parent(request)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "CIRCULAR_HIERARCHY"

    @pytest.mark.asyncio
    @patch("diigo_tagger.api.routes.bookmarks.get_session")
    async def test_circular_hierarchy_rejected(self, mock_get_session):
        """Cannot create a cycle: flask -> python -> dev, then set dev -> flask."""
        from fastapi import HTTPException

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # development (id=1, parent=None) wants parent=flask (id=3, parent=python(id=2, parent=dev(id=1)))
        dev_tag = MagicMock(spec=Tag)
        dev_tag.name = "development"
        dev_tag.id = 1
        dev_tag.parent_id = None

        flask_tag = MagicMock(spec=Tag)
        flask_tag.name = "flask"
        flask_tag.id = 3
        flask_tag.parent_id = 2  # parent is python

        python_tag = MagicMock(spec=Tag)
        python_tag.name = "python"
        python_tag.id = 2
        python_tag.parent_id = 1  # parent is development — this creates the cycle!

        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=dev_tag)),    # tag lookup: development
            MagicMock(first=MagicMock(return_value=flask_tag)),  # parent lookup: flask
        ]
        # Walking up: flask.parent_id=2, get(2)=python, python.parent_id=1 == dev_tag.id -> circular!
        mock_session.query.return_value.get.side_effect = [python_tag]

        request = SetParentRequest(tag_name="development", parent_name="flask")

        with pytest.raises(HTTPException) as exc_info:
            await set_tag_parent(request)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "CIRCULAR_HIERARCHY"
