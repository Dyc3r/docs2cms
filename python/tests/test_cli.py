import argparse
from pathlib import Path
from unittest.mock import patch

import frontmatter
import pytest

from d2cms.config import ConfigError, D2CMSConfig

WP_BASE = "http://test-wp.test/wp-json/"
DOC_KEY = "00000001-0000-7000-8000-000000000000"


@pytest.fixture
def cfg(tmp_path: Path) -> D2CMSConfig:
    return D2CMSConfig(
        wp_api_root=WP_BASE,
        wp_api_key="test-token",
        wp_api_user="admin",
        docs_dir=tmp_path,
        auth_mode="token",
    )


def _make_args(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def _write_doc(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# _cmd_add_doc
# ---------------------------------------------------------------------------


class TestCmdAdd:
    def test_creates_document_at_docs_root_when_no_path(self, tmp_path, cfg, capsys):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="My Doc", path=None, tags=None, content_type="docs"))

        assert (tmp_path / "my-doc.md").exists()

    def test_creates_document_in_subdirectory_when_path_given(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="Child", path="section", tags=None, content_type="docs"))

        assert (tmp_path / "section" / "child.md").exists()

    def test_prints_created_file_path(self, tmp_path, cfg, capsys):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="My Doc", path=None, tags=None, content_type="docs"))

        assert "my-doc.md" in capsys.readouterr().out

    def test_exits_with_error_when_config_invalid(self, tmp_path, capsys):
        from d2cms.cli import _cmd_add_doc

        with (
            patch("d2cms.cli.load_config_from_env", side_effect=ConfigError("bad config")),
            pytest.raises(SystemExit) as exc_info,
        ):
            _cmd_add_doc(_make_args(title="Doc", path=None, tags=None, content_type="docs"))

        assert exc_info.value.code == 1

    def test_prints_config_error_to_stderr(self, tmp_path, capsys):
        from d2cms.cli import _cmd_add_doc

        with (
            patch("d2cms.cli.load_config_from_env", side_effect=ConfigError("missing env")),
            pytest.raises(SystemExit),
        ):
            _cmd_add_doc(_make_args(title="Doc", path=None, tags=None, content_type="docs"))

        assert "missing env" in capsys.readouterr().err

    def test_exits_with_error_when_file_already_exists(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="My Doc", path=None, tags=None, content_type="docs"))
            with pytest.raises(SystemExit) as exc_info:
                _cmd_add_doc(_make_args(title="My Doc", path=None, tags=None, content_type="docs"))

        assert exc_info.value.code == 1

    def test_prints_file_exists_error_to_stderr(self, tmp_path, cfg, capsys):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="My Doc", path=None, tags=None, content_type="docs"))
            capsys.readouterr()  # discard first creation output
            with pytest.raises(SystemExit):
                _cmd_add_doc(_make_args(title="My Doc", path=None, tags=None, content_type="docs"))

        assert "already exists" in capsys.readouterr().err

    def test_splits_comma_separated_tags(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="Tagged", path=None, tags="python,cms", content_type="docs"))

        post = frontmatter.load(tmp_path / "tagged.md")
        assert post.metadata["tags"] == ["python", "cms"]

    def test_strips_whitespace_from_tags(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="Tagged", path=None, tags="python, cms", content_type="docs"))

        post = frontmatter.load(tmp_path / "tagged.md")
        assert post.metadata["tags"] == ["python", "cms"]

    def test_multi_word_tags_preserved(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(
                _make_args(title="Tagged", path=None, tags="apple pie,tacos,pizza", content_type="docs")
            )

        post = frontmatter.load(tmp_path / "tagged.md")
        assert post.metadata["tags"] == ["apple pie", "tacos", "pizza"]

    def test_no_tags_arg_writes_empty_list(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="No Tags", path=None, tags=None, content_type="docs"))

        post = frontmatter.load(tmp_path / "no-tags.md")
        assert post.metadata["tags"] == []

    def test_passes_content_type_to_generated_doc(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="A Page", path=None, tags=None, content_type="pages"))

        post = frontmatter.load(tmp_path / "a-page.md")
        assert post.metadata["content_type"] == "pages"


# ---------------------------------------------------------------------------
# _cmd_deprecate
# ---------------------------------------------------------------------------


class TestCmdDeprecate:
    @pytest.fixture
    def doc_file(self, tmp_path: Path) -> Path:
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


# ---------------------------------------------------------------------------
# _cmd_sync
# ---------------------------------------------------------------------------


class TestCmdSync:
    def test_calls_sync_with_config(self, cfg):
        from d2cms.cli import _cmd_sync
        from d2cms.report import SyncReport

        with (
            patch("d2cms.cli.load_config_from_env", return_value=cfg),
            patch("d2cms.cli.sync", return_value=SyncReport()) as mock_sync,
        ):
            _cmd_sync(_make_args(debug=False, force=False))

        mock_sync.assert_called_once_with(cfg, force=False)

    def test_exits_with_error_when_config_invalid(self, capsys):
        from d2cms.cli import _cmd_sync

        with (
            patch("d2cms.cli.load_config_from_env", side_effect=ConfigError("bad config")),
            pytest.raises(SystemExit) as exc_info,
        ):
            _cmd_sync(_make_args(debug=False, force=False))

        assert exc_info.value.code == 1

    def test_prints_config_error_to_stderr(self, capsys):
        from d2cms.cli import _cmd_sync

        with (
            patch("d2cms.cli.load_config_from_env", side_effect=ConfigError("missing env")),
            pytest.raises(SystemExit),
        ):
            _cmd_sync(_make_args(debug=False, force=False))

        assert "missing env" in capsys.readouterr().err
