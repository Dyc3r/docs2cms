import argparse
from unittest.mock import patch

import frontmatter
import pytest

from d2cms.config import ConfigError


def _make_args(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


class TestCmdAdd:
    def test_creates_document_in_docs_dir_when_no_path(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="My Doc", path=None, tags=None, content_type="docs"))

        assert (tmp_path / "docs" / "my-doc.md").exists()

    def test_creates_document_in_subdirectory_when_path_given(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="Child", path="section", tags=None, content_type="docs"))

        assert (tmp_path / "docs" / "section" / "child.md").exists()

    def test_defaults_to_docs_when_content_type_not_provided(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="My Doc", path=None, tags=None, content_type=None))

        assert (tmp_path / "docs" / "my-doc.md").exists()

    def test_pages_content_type_creates_in_pages_dir(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="About", path=None, tags=None, content_type="pages"))

        assert (tmp_path / "pages" / "about.md").exists()

    def test_prints_created_file_path(self, tmp_path, cfg, capsys):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="My Doc", path=None, tags=None, content_type="docs"))

        assert "my-doc.md" in capsys.readouterr().out

    def test_exits_with_error_when_config_invalid(self, capsys):
        from d2cms.cli import _cmd_add_doc

        with (
            patch("d2cms.cli.load_config_from_env", side_effect=ConfigError("bad config")),
            pytest.raises(SystemExit) as exc_info,
        ):
            _cmd_add_doc(_make_args(title="Doc", path=None, tags=None, content_type="docs"))

        assert exc_info.value.code == 1

    def test_prints_config_error_to_stderr(self, capsys):
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

        post = frontmatter.load(tmp_path / "docs" / "tagged.md")
        assert post.metadata["tags"] == ["python", "cms"]

    def test_strips_whitespace_from_tags(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="Tagged", path=None, tags="python, cms", content_type="docs"))

        post = frontmatter.load(tmp_path / "docs" / "tagged.md")
        assert post.metadata["tags"] == ["python", "cms"]

    def test_multi_word_tags_preserved(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(
                _make_args(title="Tagged", path=None, tags="apple pie,tacos,pizza", content_type="docs")
            )

        post = frontmatter.load(tmp_path / "docs" / "tagged.md")
        assert post.metadata["tags"] == ["apple pie", "tacos", "pizza"]

    def test_no_tags_arg_writes_empty_list(self, tmp_path, cfg):
        from d2cms.cli import _cmd_add_doc

        with patch("d2cms.cli.load_config_from_env", return_value=cfg):
            _cmd_add_doc(_make_args(title="No Tags", path=None, tags=None, content_type="docs"))

        post = frontmatter.load(tmp_path / "docs" / "no-tags.md")
        assert post.metadata["tags"] == []
