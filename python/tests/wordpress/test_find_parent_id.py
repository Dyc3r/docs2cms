from uuid import UUID

import httpx
import pytest
import respx

from d2cms.docs import D2CMSFrontmatter
from d2cms.wordpress import ParentNotFoundError, _find_parent_id
from tests.wordpress._helpers import DOC_KEY, PARENT_KEY, WP_BASE


class TestFindParentId:
    def _metadata(self, *, parent_key: str | None = None) -> D2CMSFrontmatter:
        return D2CMSFrontmatter(
            document_key=UUID(DOC_KEY),
            title="Doc",
            slug="doc",
            parent_key=UUID(parent_key) if parent_key else None,
        )

    def test_returns_none_when_no_parent_key(self):
        client = httpx.Client(base_url=WP_BASE)
        result = _find_parent_id(self._metadata(), "docs", client)
        assert result is None

    def test_returns_parent_id_when_found(self):
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(200, json=[{"id": 55}])
            )
            result = _find_parent_id(self._metadata(parent_key=PARENT_KEY), "docs", client)
        assert result == 55

    def test_raises_parent_not_found_error(self):
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(200, json=[])
            )
            with pytest.raises(ParentNotFoundError):
                _find_parent_id(self._metadata(parent_key=PARENT_KEY), "docs", client)

    def test_queries_correct_content_type_endpoint(self):
        metadata = D2CMSFrontmatter(
            document_key=UUID(DOC_KEY),
            title="Child Page",
            slug="child-page",
            parent_key=UUID(PARENT_KEY),
        )
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            route = respx.get(f"{WP_BASE}wp/v2/pages").mock(
                return_value=httpx.Response(200, json=[{"id": 10}])
            )
            _find_parent_id(metadata, "pages", client)
        assert route.called

    def test_raises_http_error_on_failed_response(self):
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(500, json={"error": "server error"})
            )
            with pytest.raises(httpx.HTTPStatusError):
                _find_parent_id(self._metadata(parent_key=PARENT_KEY), "docs", client)
