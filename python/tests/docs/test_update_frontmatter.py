from pathlib import Path

import frontmatter
import pytest

from d2cms.docs import update_frontmatter
from tests.docs._constants import PARENT_KEY


class TestUpdateFrontmatter:
    @pytest.fixture
    def doc_file(self, tmp_path: Path) -> Path:
        f = tmp_path / "test.md"
        f.write_text(
            "---\ntitle: Test\nwordpress_id: \ndocument_hash: \n---\n\nContent here\n"
        )
        return f

    def test_updates_wordpress_id(self, doc_file: Path) -> None:
        update_frontmatter(doc_file, wordpress_id=42, document_hash=None)
        post = frontmatter.load(doc_file)
        assert post.metadata["wordpress_id"] == 42

    def test_updates_document_hash(self, doc_file: Path) -> None:
        update_frontmatter(doc_file, wordpress_id=None, document_hash="abc123")
        post = frontmatter.load(doc_file)
        assert post.metadata["document_hash"] == "abc123"

    def test_updates_both_fields(self, doc_file: Path) -> None:
        update_frontmatter(doc_file, wordpress_id=99, document_hash="deadbeef")
        post = frontmatter.load(doc_file)
        assert post.metadata["wordpress_id"] == 99
        assert post.metadata["document_hash"] == "deadbeef"

    def test_does_not_overwrite_with_none(self, doc_file: Path) -> None:
        update_frontmatter(doc_file, wordpress_id=10, document_hash="abc")
        update_frontmatter(doc_file, wordpress_id=None, document_hash=None)
        post = frontmatter.load(doc_file)
        assert post.metadata["wordpress_id"] == 10
        assert post.metadata["document_hash"] == "abc"

    def test_preserves_existing_content_body(self, doc_file: Path) -> None:
        original_content = frontmatter.load(doc_file).content
        update_frontmatter(doc_file, wordpress_id=1, document_hash="x")
        assert frontmatter.load(doc_file).content == original_content

    def test_preserves_other_frontmatter_fields(self, doc_file: Path) -> None:
        update_frontmatter(doc_file, wordpress_id=1, document_hash="x")
        post = frontmatter.load(doc_file)
        assert post.metadata["title"] == "Test"

    def test_sets_parent_key_when_provided(self, tmp_path: Path) -> None:
        f = tmp_path / "child.md"
        f.write_text("---\ntitle: C\nparent_key: \ndocument_hash: \n---\n\nContent\n")
        update_frontmatter(f, parent_key=PARENT_KEY)
        assert frontmatter.load(f).metadata["parent_key"] == str(PARENT_KEY)

    def test_clears_parent_key_when_none_passed(self, tmp_path: Path) -> None:
        f = tmp_path / "child.md"
        f.write_text(f"---\ntitle: C\nparent_key: {PARENT_KEY}\ndocument_hash: abc\n---\n\nC\n")
        update_frontmatter(f, parent_key=None)
        assert frontmatter.load(f).metadata["parent_key"] == ""

    def test_does_not_touch_parent_key_when_omitted(self, doc_file: Path) -> None:
        # doc_file has no parent_key field — calling without parent_key should not add it
        update_frontmatter(doc_file, wordpress_id=1)
        assert "parent_key" not in frontmatter.load(doc_file).metadata
