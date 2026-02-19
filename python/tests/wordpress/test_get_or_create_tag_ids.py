import httpx
import pytest
import respx

from d2cms.wordpress import _get_or_create_tag_ids
from tests.wordpress._helpers import WP_BASE


class TestGetOrCreateTagIds:
    def test_returns_empty_list_for_no_tags(self):
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            result = _get_or_create_tag_ids([], client)
        assert result == []

    def test_returns_existing_tag_id(self):
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/tags").mock(
                return_value=httpx.Response(200, json=[{"id": 7, "name": "python"}])
            )
            result = _get_or_create_tag_ids(["python"], client)
        assert result == [7]

    def test_creates_tag_when_not_found(self):
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/tags").mock(
                return_value=httpx.Response(200, json=[])
            )
            respx.post(f"{WP_BASE}wp/v2/tags").mock(
                return_value=httpx.Response(201, json={"id": 99, "name": "new-tag"})
            )
            result = _get_or_create_tag_ids(["new-tag"], client)
        assert result == [99]

    def test_handles_mix_of_existing_and_new_tags(self):
        def _tag_lookup(request: httpx.Request) -> httpx.Response:
            name = request.url.params.get("name")
            if name == "existing":
                return httpx.Response(200, json=[{"id": 5, "name": "existing"}])
            return httpx.Response(200, json=[])

        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/tags").mock(side_effect=_tag_lookup)
            respx.post(f"{WP_BASE}wp/v2/tags").mock(
                return_value=httpx.Response(201, json={"id": 20, "name": "new"})
            )
            result = _get_or_create_tag_ids(["existing", "new"], client)
        assert result == [5, 20]

    def test_raises_on_failed_tag_creation(self):
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/tags").mock(
                return_value=httpx.Response(200, json=[])
            )
            respx.post(f"{WP_BASE}wp/v2/tags").mock(
                return_value=httpx.Response(403, json={"code": "rest_forbidden"})
            )
            with pytest.raises(httpx.HTTPStatusError):
                _get_or_create_tag_ids(["bad-tag"], client)
