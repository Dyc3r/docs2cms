import frontmatter
import httpx
import pytest
import respx

from d2cms.wordpress import _handle_delete
from tests.wordpress._helpers import WP_BASE, _write_doc


class TestHandleDelete:
    def test_removes_local_file_when_never_synced(self, tmp_path, cfg):
        doc_file = _write_doc(
            tmp_path,
            "---\ntitle: Ghost\nwordpress_id: \ncontent_type: docs\ndeprecated: true\n---\nContent\n",
        )
        doc = frontmatter.load(doc_file)
        _handle_delete(doc, doc_file, cfg)
        assert not doc_file.exists()

    def test_deletes_from_wordpress_and_removes_local(self, tmp_path, cfg):
        doc_file = _write_doc(
            tmp_path,
            "---\ntitle: Old Doc\nwordpress_id: 42\ncontent_type: docs\ndeprecated: true\n---\nContent\n",
        )
        doc = frontmatter.load(doc_file)
        with respx.mock:
            respx.delete(f"{WP_BASE}wp/v2/docs/42").mock(
                return_value=httpx.Response(200, json={"deleted": True, "previous": {}})
            )
            _handle_delete(doc, doc_file, cfg)
        assert not doc_file.exists()

    def test_raises_on_wordpress_http_error(self, tmp_path, cfg):
        doc_file = _write_doc(
            tmp_path,
            "---\ntitle: Old Doc\nwordpress_id: 42\ncontent_type: docs\ndeprecated: true\n---\nContent\n",
        )
        doc = frontmatter.load(doc_file)
        with respx.mock:
            respx.delete(f"{WP_BASE}wp/v2/docs/42").mock(
                return_value=httpx.Response(403, json={"code": "rest_forbidden"})
            )
            with pytest.raises(httpx.HTTPStatusError):
                _handle_delete(doc, doc_file, cfg)
        # File should NOT have been deleted when the HTTP call failed
        assert doc_file.exists()

    def test_uses_correct_content_type_in_delete_url(self, tmp_path, cfg):
        doc_file = _write_doc(
            tmp_path,
            "---\ntitle: A Page\nwordpress_id: 7\ncontent_type: pages\ndeprecated: true\n---\nContent\n",
        )
        doc = frontmatter.load(doc_file)
        with respx.mock:
            route = respx.delete(f"{WP_BASE}wp/v2/pages/7").mock(
                return_value=httpx.Response(200, json={"deleted": True})
            )
            _handle_delete(doc, doc_file, cfg)
        assert route.called
