from unittest.mock import ANY, patch

import httpx
import respx

from d2cms.report import SyncReport
from d2cms.wordpress import sync
from tests.wordpress._helpers import WP_BASE, _new_doc


class TestSync:
    def test_sync_calls_sync_directory_with_docs_dir(self, cfg):
        with patch("d2cms.wordpress._sync_directory") as mock_dir:
            sync(cfg)
        mock_dir.assert_called_once_with(cfg.docs_dir, cfg, ANY, force=False)

    def test_sync_uses_custom_path_when_provided(self, tmp_path, cfg):
        subdir = tmp_path / "section"
        subdir.mkdir()
        with patch("d2cms.wordpress._sync_directory") as mock_dir:
            sync(cfg, path=subdir)
        mock_dir.assert_called_once_with(subdir, cfg, ANY, force=False)

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
