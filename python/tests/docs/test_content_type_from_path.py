import pytest

from d2cms.docs import content_type_from_path


class TestContentTypeFromPath:
    def test_returns_docs_for_docs_subdir(self, tmp_path):
        file = tmp_path / "docs" / "guide.md"
        assert content_type_from_path(file, tmp_path) == "docs"

    def test_returns_pages_for_pages_subdir(self, tmp_path):
        file = tmp_path / "pages" / "about.md"
        assert content_type_from_path(file, tmp_path) == "pages"

    def test_returns_posts_for_posts_subdir(self, tmp_path):
        file = tmp_path / "posts" / "hello.md"
        assert content_type_from_path(file, tmp_path) == "posts"

    def test_raises_for_file_directly_in_docs_dir(self, tmp_path):
        file = tmp_path / "readme.md"
        with pytest.raises(ValueError):
            content_type_from_path(file, tmp_path)

    def test_raises_for_unknown_top_level_directory(self, tmp_path):
        file = tmp_path / "other" / "file.md"
        with pytest.raises(ValueError):
            content_type_from_path(file, tmp_path)

    def test_works_for_deeply_nested_files(self, tmp_path):
        file = tmp_path / "docs" / "section" / "child.md"
        assert content_type_from_path(file, tmp_path) == "docs"

    def test_error_message_includes_file_path(self, tmp_path):
        file = tmp_path / "unknown" / "file.md"
        with pytest.raises(ValueError, match="docs/pages/posts"):
            content_type_from_path(file, tmp_path)
