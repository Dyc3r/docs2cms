import json
from pathlib import Path

import frontmatter
import httpx
import respx

from d2cms.docs import generate_doc_hash
from d2cms.wordpress import _sync_document
from tests.wordpress._helpers import (
    DOC_KEY,
    PARENT_KEY,
    WP_BASE,
    _existing_doc,
    _new_doc,
    _synced_doc,
    _write_doc,
)


class TestSyncDocument:
    def test_creates_new_document_and_updates_frontmatter(self, tmp_path, cfg, report):
        doc_file = _new_doc(tmp_path)
        with respx.mock:
            respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(201, json={"id": 101, "slug": "test-document"})
            )
            _sync_document(doc_file, cfg, report)
        post = frontmatter.load(doc_file)
        assert post.metadata["wordpress_id"] == 101

    def test_updates_existing_document_via_item_route(self, tmp_path, cfg, report):
        doc_file = _existing_doc(tmp_path, wp_id=42, stored_hash="stale-hash")
        with respx.mock:
            route = respx.post(f"{WP_BASE}wp/v2/docs/42").mock(
                return_value=httpx.Response(200, json={"id": 42})
            )
            _sync_document(doc_file, cfg, report)
        assert route.called

    def test_skips_sync_when_hash_matches(self, tmp_path, cfg, report):
        doc_file = _synced_doc(tmp_path, wp_id=5)
        # No routes registered — any HTTP request would raise ConnectError
        with respx.mock:
            _sync_document(doc_file, cfg, report)

    def test_force_bypasses_hash_check(self, tmp_path, cfg, report):
        doc_file = _synced_doc(tmp_path, wp_id=5)
        with respx.mock:
            route = respx.post(f"{WP_BASE}wp/v2/docs/5").mock(
                return_value=httpx.Response(200, json={"id": 5})
            )
            _sync_document(doc_file, cfg, report, force=True)
        assert route.called

    def test_updates_document_hash_in_frontmatter(self, tmp_path, cfg, report):
        doc_file = _new_doc(tmp_path)
        expected_hash = generate_doc_hash(frontmatter.load(doc_file), Path("test.md"))
        with respx.mock:
            respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(201, json={"id": 101})
            )
            _sync_document(doc_file, cfg, report)
        post = frontmatter.load(doc_file)
        assert post.metadata["document_hash"] == expected_hash

    def test_deletes_deprecated_document(self, tmp_path, cfg, report):
        doc_file = _write_doc(
            tmp_path,
            f"---\ndocument_key: {DOC_KEY}\ntitle: Old\nslug: old\ncontent_type: docs\n"
            "wordpress_id: 99\ndeprecated: true\n---\nOld content\n",
        )
        with respx.mock:
            respx.delete(f"{WP_BASE}wp/v2/docs/99").mock(
                return_value=httpx.Response(200, json={"deleted": True})
            )
            _sync_document(doc_file, cfg, report)
        assert not doc_file.exists()

    def test_deprecated_doc_never_synced_is_just_removed_locally(self, tmp_path, cfg, report):
        doc_file = _write_doc(
            tmp_path,
            f"---\ndocument_key: {DOC_KEY}\ntitle: Ghost\nslug: ghost\ncontent_type: docs\n"
            "wordpress_id: \ndeprecated: true\n---\nContent\n",
        )
        # No HTTP mock needed — file should vanish without a network call
        with respx.mock:
            _sync_document(doc_file, cfg, report)
        assert not doc_file.exists()

    def test_syncs_tags_for_new_document(self, tmp_path, cfg, report):
        doc_file = _write_doc(
            tmp_path,
            f"---\ndocument_key: {DOC_KEY}\ntitle: Tagged\nslug: tagged\ncontent_type: docs\n"
            "parent_key: \ntags: [python, cms]\nwordpress_id: \n"
            "document_hash: \ndeprecated: false\n---\n\nContent\n",
        )
        with respx.mock:
            respx.get(f"{WP_BASE}wp/v2/tags").mock(
                return_value=httpx.Response(200, json=[{"id": 3, "name": "python"}])
            )
            post_route = respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(201, json={"id": 50})
            )
            _sync_document(doc_file, cfg, report)
        assert post_route.called
        body = json.loads(post_route.calls[0].request.content)
        assert 3 in body["tags"]

    def test_records_http_error_in_report(self, tmp_path, cfg, report):
        doc_file = _new_doc(tmp_path)
        with respx.mock:
            respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(401, json={"code": "rest_not_logged_in"})
            )
            _sync_document(doc_file, cfg, report)
        assert report.has_failures
        assert report.failure_count == 1

    def test_records_parent_not_found_in_report(self, tmp_path, cfg, report):
        doc_file = _write_doc(
            tmp_path,
            f"---\ndocument_key: {DOC_KEY}\ntitle: Child\nslug: child\ncontent_type: docs\n"
            f"parent_key: {PARENT_KEY}\ntags: []\nwordpress_id: \n"
            "document_hash: \ndeprecated: false\n---\n\nChild content\n",
        )
        with respx.mock:
            respx.get(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(200, json=[])
            )
            _sync_document(doc_file, cfg, report)
        assert report.has_failures
        assert report.failure_count == 1

    def test_deprecated_delete_failure_records_in_report_and_keeps_file(self, tmp_path, cfg, report):
        doc_file = _write_doc(
            tmp_path,
            f"---\ndocument_key: {DOC_KEY}\ntitle: Old\nslug: old\ncontent_type: docs\n"
            "wordpress_id: 99\ndeprecated: true\n---\nOld content\n",
        )
        with respx.mock:
            respx.delete(f"{WP_BASE}wp/v2/docs/99").mock(
                return_value=httpx.Response(403, json={"code": "rest_forbidden"})
            )
            _sync_document(doc_file, cfg, report)
        assert report.has_failures
        assert doc_file.exists()

    def test_resolves_parent_before_posting(self, tmp_path, cfg, report):
        doc_file = _write_doc(
            tmp_path,
            f"---\ndocument_key: {DOC_KEY}\ntitle: Child\nslug: child\ncontent_type: docs\n"
            f"parent_key: {PARENT_KEY}\ntags: []\nwordpress_id: \n"
            "document_hash: \ndeprecated: false\n---\n\nChild content\n",
        )
        with respx.mock:
            respx.get(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(200, json=[{"id": 10}])
            )
            post_route = respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(201, json={"id": 20})
            )
            _sync_document(doc_file, cfg, report)
        body = json.loads(post_route.calls[0].request.content)
        assert body["parent"] == 10

    def test_posts_with_published_status(self, tmp_path, cfg, report):
        doc_file = _new_doc(tmp_path)
        with respx.mock:
            post_route = respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(201, json={"id": 101})
            )
            _sync_document(doc_file, cfg, report)
        body = json.loads(post_route.calls[0].request.content)
        assert body["status"] == "publish"

    def test_posts_menu_order(self, tmp_path, cfg, report):
        doc_file = _write_doc(
            tmp_path,
            f"---\ndocument_key: {DOC_KEY}\ntitle: Ordered\nslug: ordered\ncontent_type: docs\n"
            "parent_key: \ntags: []\norder: 3\nwordpress_id: \n"
            "document_hash: \ndeprecated: false\n---\n\nContent\n",
        )
        with respx.mock:
            post_route = respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(201, json={"id": 101})
            )
            _sync_document(doc_file, cfg, report)
        body = json.loads(post_route.calls[0].request.content)
        assert body["menu_order"] == 3

    def test_menu_order_defaults_to_zero(self, tmp_path, cfg, report):
        doc_file = _new_doc(tmp_path)
        with respx.mock:
            post_route = respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(201, json={"id": 101})
            )
            _sync_document(doc_file, cfg, report)
        body = json.loads(post_route.calls[0].request.content)
        assert body["menu_order"] == 0

    def test_failure_includes_doc_metadata_in_report(self, tmp_path, cfg, report):
        doc_file = _existing_doc(tmp_path, wp_id=42, stored_hash="stale-hash")
        with respx.mock:
            respx.post(f"{WP_BASE}wp/v2/docs/42").mock(
                return_value=httpx.Response(500, json={"code": "internal_error"})
            )
            _sync_document(doc_file, cfg, report)
        assert report.has_failures
        failure = report._failures[0]
        assert failure.content_type == "docs"
        assert failure.wordpress_id == 42
        assert failure.doc_path == "test.md"
