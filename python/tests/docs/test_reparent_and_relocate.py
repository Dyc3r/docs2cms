from pathlib import Path
from uuid import UUID

import frontmatter

from d2cms.docs import reparent_and_relocate_children
from tests.docs._constants import DOC_KEY, GRANDPARENT_KEY, PARENT_KEY


class TestReparentAndRelocate:
    def _make_parent_doc(
        self, parent_dir: Path, name: str, parent_key: UUID | None = None
    ) -> Path:
        f = parent_dir / name
        pk = str(parent_key) if parent_key else ""
        f.write_text(
            f"---\ntitle: Parent\ndocument_key: {DOC_KEY}\nparent_key: {pk}\n"
            "document_hash: oldhash\ndeprecated: true\n---\n\nContent\n"
        )
        return f

    def _make_child_doc(self, child_dir: Path, name: str) -> Path:
        f = child_dir / name
        f.write_text(
            f"---\ntitle: Child\ndocument_key: {PARENT_KEY}\nparent_key: {DOC_KEY}\n"
            "document_hash: childhash\ndeprecated: false\n---\n\nChild content\n"
        )
        return f

    def test_no_op_when_no_sibling_dir(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        reparent_and_relocate_children(doc)
        assert doc.exists()

    def test_no_op_when_sibling_is_a_file_not_dir(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        (tmp_path / "section").write_text("not a dir")
        reparent_and_relocate_children(doc)
        assert doc.exists()

    def test_moves_child_md_files_to_parent_dir(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        sibling = tmp_path / "section"
        sibling.mkdir()
        self._make_child_doc(sibling, "child-a.md")
        reparent_and_relocate_children(doc)
        assert (tmp_path / "child-a.md").exists()
        assert not (sibling / "child-a.md").exists()

    def test_moves_subdirectories_to_parent_dir(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        sibling = tmp_path / "section"
        sibling.mkdir()
        nested = sibling / "nested"
        nested.mkdir()
        (nested / "grandchild.md").write_text("content")
        reparent_and_relocate_children(doc)
        assert (tmp_path / "nested").is_dir()
        assert (tmp_path / "nested" / "grandchild.md").exists()

    def test_removes_sibling_dir_after_relocation(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        sibling = tmp_path / "section"
        sibling.mkdir()
        self._make_child_doc(sibling, "child.md")
        reparent_and_relocate_children(doc)
        assert not sibling.exists()

    def test_moves_multiple_files_and_dirs(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        sibling = tmp_path / "section"
        sibling.mkdir()
        self._make_child_doc(sibling, "child-a.md")
        self._make_child_doc(sibling, "child-b.md")
        (sibling / "nested").mkdir()
        reparent_and_relocate_children(doc)
        assert (tmp_path / "child-a.md").exists()
        assert (tmp_path / "child-b.md").exists()
        assert (tmp_path / "nested").is_dir()
        assert not sibling.exists()

    def test_children_inherit_deleted_docs_parent_key(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        sibling = tmp_path / "section"
        sibling.mkdir()
        self._make_child_doc(sibling, "child.md")
        reparent_and_relocate_children(doc)
        post = frontmatter.load(tmp_path / "child.md")
        assert post.metadata["parent_key"] == str(GRANDPARENT_KEY)

    def test_children_get_empty_parent_key_when_deleted_doc_was_root(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", parent_key=None)
        sibling = tmp_path / "section"
        sibling.mkdir()
        self._make_child_doc(sibling, "child.md")
        reparent_and_relocate_children(doc)
        post = frontmatter.load(tmp_path / "child.md")
        assert post.metadata["parent_key"] == ""

    def test_preserves_document_hash_on_reparented_children(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        sibling = tmp_path / "section"
        sibling.mkdir()
        self._make_child_doc(sibling, "child.md")
        reparent_and_relocate_children(doc)
        post = frontmatter.load(tmp_path / "child.md")
        # Hash is intentionally not cleared — path change makes it naturally stale
        assert post.metadata["document_hash"] == "childhash"

    def test_does_not_update_files_in_nested_subdirs(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        sibling = tmp_path / "section"
        sibling.mkdir()
        nested = sibling / "nested"
        nested.mkdir()
        grandchild = nested / "grandchild.md"
        grandchild.write_text(
            f"---\ntitle: GC\nparent_key: {PARENT_KEY}\ndocument_hash: gchash\n---\n\nC\n"
        )
        reparent_and_relocate_children(doc)
        post = frontmatter.load(tmp_path / "nested" / "grandchild.md")
        assert str(post.metadata["parent_key"]) == str(PARENT_KEY)

    def test_does_not_modify_deleted_doc_itself(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        sibling = tmp_path / "section"
        sibling.mkdir()
        self._make_child_doc(sibling, "child.md")
        original_text = doc.read_text()
        reparent_and_relocate_children(doc)
        assert doc.read_text() == original_text
