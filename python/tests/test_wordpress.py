"""
WordPress sync tests — HTTP calls are intercepted by respx, which raises
httpx.ConnectError for any request that doesn't match a registered route.
This makes it easy to assert that no HTTP traffic occurs in skip/short-circuit paths.
"""

from pathlib import Path
from unittest.mock import ANY, patch
from uuid import UUID

import frontmatter
import httpx
import pytest
import respx

from d2cms.config import D2CMSConfig
from d2cms.docs import D2CMSFrontmatter, generate_doc_hash, update_frontmatter
from d2cms.report import SyncReport
from d2cms.wordpress import (
    ParentNotFoundError,
    _find_parent_id,
    _get_or_create_tag_ids,
    _handle_delete,
    _sync_directory,
    _sync_document,
    sync,
)

WP_BASE = "http://test-wp.test/wp-json/"
DOC_KEY = "00000001-0000-7000-8000-000000000000"
PARENT_KEY = "ffffffff-ffff-7fff-bfff-ffffffffffff"


@pytest.fixture
def cfg(tmp_path: Path) -> D2CMSConfig:
    return D2CMSConfig(
        wp_api_root=WP_BASE,
        wp_api_key="test-token",
        wp_api_user="admin",
        docs_dir=tmp_path,
        auth_mode="token",
    )


@pytest.fixture
def report() -> SyncReport:
    return SyncReport()


def _write_doc(tmp_path: Path, content: str, name: str = "test.md") -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


def _new_doc(tmp_path: Path, name: str = "test.md") -> Path:
    """A doc that has never been synced (no wordpress_id, no hash)."""
    return _write_doc(
        tmp_path,
        f"---\ndocument_key: {DOC_KEY}\ntitle: Test Document\nslug: test-document\n"
        "content_type: docs\nparent_key: \ntags: []\nwordpress_id: \n"
        "document_hash: \ndeprecated: false\n---\n\nContent here\n",
        name,
    )


def _existing_doc(tmp_path: Path, wp_id: int, stored_hash: str, name: str = "test.md") -> Path:
    """A doc that was previously synced, with a (possibly stale) hash."""
    return _write_doc(
        tmp_path,
        f"---\ndocument_key: {DOC_KEY}\ntitle: Test Document\nslug: test-document\n"
        f"content_type: docs\nparent_key: \ntags: []\nwordpress_id: {wp_id}\n"
        f"document_hash: {stored_hash}\ndeprecated: false\n---\n\nContent here\n",
        name,
    )


def _synced_doc(tmp_path: Path, wp_id: int, name: str = "test.md") -> Path:
    """A doc whose stored hash matches its current content (sync should be skipped)."""
    doc_file = _new_doc(tmp_path, name)
    real_hash = generate_doc_hash(frontmatter.load(doc_file))
    update_frontmatter(doc_file, wordpress_id=wp_id, document_hash=real_hash)
    return doc_file


# ---------------------------------------------------------------------------
# _find_parent_id
# ---------------------------------------------------------------------------


class TestFindParentId:
    def _metadata(self, *, parent_key: str | None = None) -> D2CMSFrontmatter:
        return D2CMSFrontmatter(
            document_key=UUID(DOC_KEY),
            content_type="docs",
            title="Doc",
            slug="doc",
            parent_key=UUID(parent_key) if parent_key else None,
        )

    def test_returns_none_when_no_parent_key(self):
        client = httpx.Client(base_url=WP_BASE)
        result = _find_parent_id(self._metadata(), client)
        assert result is None

    def test_returns_parent_id_when_found(self):
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(200, json=[{"id": 55}])
            )
            result = _find_parent_id(self._metadata(parent_key=PARENT_KEY), client)
        assert result == 55

    def test_raises_parent_not_found_error(self):
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(200, json=[])
            )
            with pytest.raises(ParentNotFoundError):
                _find_parent_id(self._metadata(parent_key=PARENT_KEY), client)

    def test_queries_correct_content_type_endpoint(self):
        metadata = D2CMSFrontmatter(
            document_key=UUID(DOC_KEY),
            content_type="pages",
            title="Child Page",
            slug="child-page",
            parent_key=UUID(PARENT_KEY),
        )
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            route = respx.get(f"{WP_BASE}wp/v2/pages").mock(
                return_value=httpx.Response(200, json=[{"id": 10}])
            )
            _find_parent_id(metadata, client)
        assert route.called

    def test_raises_http_error_on_failed_response(self):
        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(500, json={"error": "server error"})
            )
            with pytest.raises(httpx.HTTPStatusError):
                _find_parent_id(self._metadata(parent_key=PARENT_KEY), client)


# ---------------------------------------------------------------------------
# _get_or_create_tag_ids
# ---------------------------------------------------------------------------


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

    def test_returns_ids_in_input_order(self):
        tag_store = {"alpha": 1, "beta": 2, "gamma": 3}

        def _tag_lookup(request: httpx.Request) -> httpx.Response:
            name = request.url.params.get("name")
            if name in tag_store:
                return httpx.Response(200, json=[{"id": tag_store[name], "name": name}])
            return httpx.Response(200, json=[])

        with respx.mock, httpx.Client(base_url=WP_BASE) as client:
            respx.get(f"{WP_BASE}wp/v2/tags").mock(side_effect=_tag_lookup)
            result = _get_or_create_tag_ids(["gamma", "alpha", "beta"], client)
        assert result == [3, 1, 2]

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


# ---------------------------------------------------------------------------
# _handle_delete
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# _sync_document
# ---------------------------------------------------------------------------


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
        expected_hash = generate_doc_hash(frontmatter.load(doc_file))
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
        # Verify the POST body contained tag IDs
        assert post_route.called
        request_body = post_route.calls[0].request
        import json
        body = json.loads(request_body.content)
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
        import json
        body = json.loads(post_route.calls[0].request.content)
        assert body["parent"] == 10

    def test_posts_with_published_status(self, tmp_path, cfg, report):
        doc_file = _new_doc(tmp_path)
        with respx.mock:
            post_route = respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(201, json={"id": 101})
            )
            _sync_document(doc_file, cfg, report)
        import json
        body = json.loads(post_route.calls[0].request.content)
        assert body["status"] == "publish"

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


# ---------------------------------------------------------------------------
# _sync_directory
# ---------------------------------------------------------------------------


class TestSyncDirectory:
    def test_syncs_each_file_in_directory(self, tmp_path, cfg, report):
        (tmp_path / "a.md").write_text("content a")
        (tmp_path / "b.md").write_text("content b")
        with patch("d2cms.wordpress._sync_document") as mock_sync:
            _sync_directory(tmp_path, cfg, report)
        assert mock_sync.call_count == 2

    def test_recurses_into_subdirectories(self, tmp_path, cfg, report):
        subdir = tmp_path / "section"
        subdir.mkdir()
        (tmp_path / "root.md").write_text("root")
        (subdir / "child.md").write_text("child")
        with patch("d2cms.wordpress._sync_document") as mock_sync:
            _sync_directory(tmp_path, cfg, report)
        assert mock_sync.call_count == 2

    def test_empty_directory_makes_no_sync_calls(self, tmp_path, cfg, report):
        with patch("d2cms.wordpress._sync_document") as mock_sync:
            _sync_directory(tmp_path, cfg, report)
        mock_sync.assert_not_called()

    def test_passes_cfg_and_report_to_sync_document(self, tmp_path, cfg, report):
        doc = tmp_path / "doc.md"
        doc.write_text("content")
        with patch("d2cms.wordpress._sync_document") as mock_sync:
            _sync_directory(tmp_path, cfg, report)
        mock_sync.assert_called_once_with(doc, cfg, report, force=False)

    def test_deeply_nested_structure(self, tmp_path, cfg, report):
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "deep.md").write_text("deep content")
        with patch("d2cms.wordpress._sync_document") as mock_sync:
            _sync_directory(tmp_path, cfg, report)
        assert mock_sync.call_count == 1

    def test_skips_nonexistent_child_dir_during_recursion(self, tmp_path, cfg, report):
        """Guard: a child dir deleted during file processing does not crash recursion."""
        subdir = tmp_path / "section"
        subdir.mkdir()
        parent_doc = tmp_path / "section.md"
        parent_doc.write_text("content")

        def delete_subdir(path: Path, *_: object, **__: object) -> None:
            if path == parent_doc:
                import shutil
                shutil.rmtree(subdir)

        with patch("d2cms.wordpress._sync_document", side_effect=delete_subdir):
            _sync_directory(tmp_path, cfg, report)  # should not raise

    def test_parent_doc_synced_before_subdirectory(self, tmp_path, cfg, report):
        subdir = tmp_path / "section"
        subdir.mkdir()
        parent_doc = tmp_path / "section.md"
        parent_doc.write_text("parent")
        child_doc = subdir / "child.md"
        child_doc.write_text("child")
        call_order: list[Path] = []
        with patch(
            "d2cms.wordpress._sync_document",
            side_effect=lambda path, *_, **__: call_order.append(path),
        ):
            _sync_directory(tmp_path, cfg, report)
        assert call_order.index(parent_doc) < call_order.index(child_doc)

    def test_skips_sync_results_directory(self, tmp_path, cfg, report):
        sync_results = tmp_path / "d2cms-sync-results"
        sync_results.mkdir()
        (sync_results / "20260219T120000.csv").write_text("doc_path,error\n")
        with patch("d2cms.wordpress._sync_document") as mock_sync:
            _sync_directory(tmp_path, cfg, report)
        mock_sync.assert_not_called()

    def test_continues_syncing_after_document_failure(self, tmp_path, cfg):
        """A failure in one document does not abort the rest of the directory."""
        _new_doc(tmp_path, "a.md")
        _new_doc(tmp_path, "b.md")
        report = SyncReport()
        with respx.mock:
            respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(500, json={"code": "internal_error"})
            )
            _sync_directory(tmp_path, cfg, report)
        assert report.failure_count == 2


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------


class TestSync:
    def test_sync_calls_sync_directory_with_docs_dir(self, cfg):
        with patch("d2cms.wordpress._sync_directory") as mock_dir:
            sync(cfg)
        mock_dir.assert_called_once_with(cfg.docs_dir, cfg, ANY, force=False)

    def test_sync_returns_report(self, cfg):
        with patch("d2cms.wordpress._sync_directory"):
            result = sync(cfg)
        assert isinstance(result, SyncReport)

    def test_sync_report_contains_failures(self, tmp_path, cfg):
        _new_doc(tmp_path)
        with respx.mock:
            respx.post(f"{WP_BASE}wp/v2/docs").mock(
                return_value=httpx.Response(503, json={"code": "service_unavailable"})
            )
            report = sync(cfg)
        assert report.has_failures
