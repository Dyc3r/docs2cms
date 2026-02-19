import argparse
from pathlib import Path
from unittest.mock import patch

import frontmatter
import pytest

from d2cms.config import ConfigError

DOC_KEY = "00000001-0000-7000-8000-000000000000"


def _make_args(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def _write_doc(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


class TestCmdDeprecate:
    @pytest.fixture
    def doc_file(self, tmp_path: Path, cfg) -> Path:
        return _write_doc(
            tmp_path / "section.md",
            f"---\ndocument_key: {DOC_KEY}\ntitle: Section\nslug: section\n"
            "content_type: docs\nparent_key: \nwordpress_id: \n"
            "document_hash: \ndeprecated: false\n---\n\nContent here\n",
        )

    def test_sets_deprecated_true_in_frontmatter(self, tmp_path, cfg, doc_file):
        from d2cms.cli import _cmd_deprecate

        with (
            patch("d2cms.cli.load_config_from_env", return_value=cfg),
            patch("d2cms.cli.reparent_and_relocate_children"),
        ):
            _cmd_deprecate(_make_args(path="section.md"))

        assert frontmatter.load(doc_file).metadata["deprecated"] is True

    def test_calls_reparent_and_relocate_children_with_file_path(self, tmp_path, cfg, doc_file):
        from d2cms.cli import _cmd_deprecate

        with (
            patch("d2cms.cli.load_config_from_env", return_value=cfg),
            patch("d2cms.cli.reparent_and_relocate_children") as mock_reparent,
        ):
            _cmd_deprecate(_make_args(path="section.md"))

        mock_reparent.assert_called_once_with(doc_file)

    def test_reparent_called_after_frontmatter_written(self, tmp_path, cfg, doc_file):
        """reparent_and_relocate_children reads the deprecated doc, so it must run after write."""
        from d2cms.cli import _cmd_deprecate

        seen_deprecated: list[bool] = []

        def capture_state(path: Path) -> None:
            seen_deprecated.append(frontmatter.load(path).metadata.get("deprecated", False))

        with (
            patch("d2cms.cli.load_config_from_env", return_value=cfg),
            patch("d2cms.cli.reparent_and_relocate_children", side_effect=capture_state),
        ):
            _cmd_deprecate(_make_args(path="section.md"))

        assert seen_deprecated == [True]

    def test_exits_with_error_when_config_invalid(self, tmp_path):
        from d2cms.cli import _cmd_deprecate

        with (
            patch("d2cms.cli.load_config_from_env", side_effect=ConfigError("bad config")),
            pytest.raises(SystemExit) as exc_info,
        ):
            _cmd_deprecate(_make_args(path="section.md"))

        assert exc_info.value.code == 1

    def test_exits_with_error_when_file_not_found(self, tmp_path, cfg):
        from d2cms.cli import _cmd_deprecate

        with (
            patch("d2cms.cli.load_config_from_env", return_value=cfg),
            pytest.raises(SystemExit) as exc_info,
        ):
            _cmd_deprecate(_make_args(path="nonexistent.md"))

        assert exc_info.value.code == 1

    def test_prints_success_message(self, tmp_path, cfg, doc_file, capsys):
        from d2cms.cli import _cmd_deprecate

        with (
            patch("d2cms.cli.load_config_from_env", return_value=cfg),
            patch("d2cms.cli.reparent_and_relocate_children"),
        ):
            _cmd_deprecate(_make_args(path="section.md"))

        assert "section.md" in capsys.readouterr().out

    def test_prints_config_error_to_stderr(self, tmp_path, capsys):
        from d2cms.cli import _cmd_deprecate

        with (
            patch("d2cms.cli.load_config_from_env", side_effect=ConfigError("missing env")),
            pytest.raises(SystemExit),
        ):
            _cmd_deprecate(_make_args(path="section.md"))

        assert "missing env" in capsys.readouterr().err

    def test_prints_file_not_found_error_to_stderr(self, tmp_path, cfg, capsys):
        from d2cms.cli import _cmd_deprecate

        with (
            patch("d2cms.cli.load_config_from_env", return_value=cfg),
            pytest.raises(SystemExit),
        ):
            _cmd_deprecate(_make_args(path="missing.md"))

        assert "missing.md" in capsys.readouterr().err
