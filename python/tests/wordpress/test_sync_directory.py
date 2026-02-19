import shutil
from pathlib import Path
from unittest.mock import patch

import httpx
import respx

from d2cms.report import SyncReport
from d2cms.wordpress import _sync_directory
from tests.wordpress._helpers import WP_BASE, _new_doc


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
        """Guard: a subdirectory removed externally mid-sync does not crash recursion."""
        subdir = tmp_path / "section"
        subdir.mkdir()
        parent_doc = tmp_path / "section.md"
        parent_doc.write_text("content")

        def delete_subdir(path: Path, *_: object, **__: object) -> None:
            if path == parent_doc:
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
