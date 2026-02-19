import argparse
from unittest.mock import patch

import pytest

from d2cms.config import ConfigError
from d2cms.report import SyncReport


def _make_args(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


class TestCmdSync:
    def test_calls_sync_with_config(self, cfg):
        from d2cms.cli import _cmd_sync

        with (
            patch("d2cms.cli.load_config_from_env", return_value=cfg),
            patch("d2cms.cli.sync", return_value=SyncReport()) as mock_sync,
        ):
            _cmd_sync(_make_args(debug=False, force=False, path=None))

        mock_sync.assert_called_once_with(cfg, force=False, path=None)

    def test_exits_with_error_when_config_invalid(self, capsys):
        from d2cms.cli import _cmd_sync

        with (
            patch("d2cms.cli.load_config_from_env", side_effect=ConfigError("bad config")),
            pytest.raises(SystemExit) as exc_info,
        ):
            _cmd_sync(_make_args(debug=False, force=False, path=None))

        assert exc_info.value.code == 1

    def test_prints_config_error_to_stderr(self, capsys):
        from d2cms.cli import _cmd_sync

        with (
            patch("d2cms.cli.load_config_from_env", side_effect=ConfigError("missing env")),
            pytest.raises(SystemExit),
        ):
            _cmd_sync(_make_args(debug=False, force=False, path=None))

        assert "missing env" in capsys.readouterr().err
