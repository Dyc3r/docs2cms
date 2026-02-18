import hashlib
from pathlib import Path
from uuid import UUID

import frontmatter
import pytest

from d2cms.docs import (
    D2CMSFrontmatter,
    _title_to_slug,
    generate_doc_hash,
    generate_template_doc,
    read_directory,
    reparent_and_relocate_children,
    to_html,
    update_frontmatter,
)

DOC_KEY = UUID("00000001-0000-7000-8000-000000000000")
PARENT_KEY = UUID("ffffffff-ffff-7fff-bfff-ffffffffffff")


class TestTitleToSlug:
    def test_replaces_spaces_with_hyphens(self):
        assert _title_to_slug("Hello World") == "hello-world"

    def test_lowercases_input(self):
        assert _title_to_slug("UPPERCASE TITLE") == "uppercase-title"

    def test_strips_surrounding_whitespace(self):
        assert _title_to_slug("  padded  ") == "padded"

    def test_already_a_slug(self):
        assert _title_to_slug("already-a-slug") == "already-a-slug"

    def test_mixed_case_with_spaces(self):
        assert _title_to_slug("My New Feature") == "my-new-feature"


class TestGenerateDocHash:
    def test_returns_sha256_hex_digest(self):
        post = frontmatter.loads("---\ntitle: Test\n---\nHello world")
        expected = hashlib.sha256(b"Hello world").hexdigest()
        assert generate_doc_hash(post) == expected

    def test_consistent_for_same_content(self):
        post = frontmatter.loads("---\ntitle: Test\n---\nSame content")
        assert generate_doc_hash(post) == generate_doc_hash(post)

    def test_different_for_different_content(self):
        post_a = frontmatter.loads("---\ntitle: Test\n---\nContent A")
        post_b = frontmatter.loads("---\ntitle: Test\n---\nContent B")
        assert generate_doc_hash(post_a) != generate_doc_hash(post_b)

    def test_empty_content_returns_empty_sha256(self):
        post = frontmatter.loads("---\ntitle: Test\n---\n")
        assert generate_doc_hash(post) == hashlib.sha256(b"").hexdigest()

    def test_hash_ignores_frontmatter_changes(self):
        # Changing only frontmatter should not change the content hash
        post_a = frontmatter.loads("---\ntitle: A\n---\nShared content")
        post_b = frontmatter.loads("---\ntitle: B\n---\nShared content")
        assert generate_doc_hash(post_a) == generate_doc_hash(post_b)


class TestD2CMSFrontmatterIsChild:
    def test_is_child_when_parent_key_set(self):
        fm = D2CMSFrontmatter(
            document_key=DOC_KEY,
            content_type="docs",
            title="Child",
            slug="child",
            parent_key=PARENT_KEY,
        )
        assert fm.is_child is True

    def test_not_child_by_default(self):
        fm = D2CMSFrontmatter(
            document_key=DOC_KEY,
            content_type="docs",
            title="Root",
            slug="root",
        )
        assert fm.is_child is False

    def test_not_child_when_parent_key_none(self):
        fm = D2CMSFrontmatter(
            document_key=DOC_KEY,
            content_type="docs",
            title="Root",
            slug="root",
            parent_key=None,
        )
        assert fm.is_child is False


class TestGenerateTemplateDoc:
    def test_creates_file_at_slug_derived_path(self, tmp_path):
        result = generate_template_doc(tmp_path, tmp_path, "My Document", None)
        assert result == tmp_path / "my-document.md"
        assert result.exists()

    def test_raises_if_file_already_exists(self, tmp_path):
        generate_template_doc(tmp_path, tmp_path, "My Doc", None)
        with pytest.raises(FileExistsError):
            generate_template_doc(tmp_path, tmp_path, "My Doc", None)

    def test_creates_intermediate_directories(self, tmp_path):
        subdir = tmp_path / "a" / "b"
        result = generate_template_doc(tmp_path, subdir, "Nested", None)
        assert result.exists()

    def test_no_parent_key_at_root(self, tmp_path):
        result = generate_template_doc(tmp_path, tmp_path, "Root Doc", None)
        post = frontmatter.load(result)
        assert not post.metadata.get("parent_key")

    def test_sets_parent_key_from_sibling_md_file(self, tmp_path):
        # Create a parent document file: docs_root/section.md
        parent_file = tmp_path / "section.md"
        parent_file.write_text(
            f"---\ndocument_key: {PARENT_KEY}\ntitle: Section\n---\n"
        )
        # Child lives under docs_root/section/child.md
        child_dir = tmp_path / "section"
        result = generate_template_doc(tmp_path, child_dir, "Child Doc", None)
        post = frontmatter.load(result)
        assert str(post.metadata.get("parent_key")) == str(PARENT_KEY)

    def test_no_parent_key_when_parent_file_absent(self, tmp_path):
        child_dir = tmp_path / "orphan"
        result = generate_template_doc(tmp_path, child_dir, "Orphan", None)
        post = frontmatter.load(result)
        assert not post.metadata.get("parent_key")

    def test_writes_tags_as_yaml_list(self, tmp_path):
        result = generate_template_doc(tmp_path, tmp_path, "Tagged", ["python", "cms"])
        post = frontmatter.load(result)
        assert post.metadata["tags"] == ["python", "cms"]

    def test_multi_word_tags_round_trip(self, tmp_path):
        result = generate_template_doc(tmp_path, tmp_path, "Tasty", ["apple pie", "tacos", "pizza"])
        post = frontmatter.load(result)
        assert post.metadata["tags"] == ["apple pie", "tacos", "pizza"]

    def test_empty_tags_writes_empty_yaml_list(self, tmp_path):
        result = generate_template_doc(tmp_path, tmp_path, "No Tags", [])
        post = frontmatter.load(result)
        assert post.metadata["tags"] == []

    def test_none_tags_treated_as_empty(self, tmp_path):
        result = generate_template_doc(tmp_path, tmp_path, "No Tags", None)
        post = frontmatter.load(result)
        assert post.metadata["tags"] == []

    def test_default_content_type_is_docs(self, tmp_path):
        result = generate_template_doc(tmp_path, tmp_path, "My Doc", None)
        post = frontmatter.load(result)
        assert post.metadata.get("content_type") == "docs"

    def test_custom_content_type_pages(self, tmp_path):
        result = generate_template_doc(tmp_path, tmp_path, "A Page", None, content_type="pages")
        post = frontmatter.load(result)
        assert post.metadata.get("content_type") == "pages"

    def test_custom_content_type_posts(self, tmp_path):
        result = generate_template_doc(tmp_path, tmp_path, "A Post", None, content_type="posts")
        post = frontmatter.load(result)
        assert post.metadata.get("content_type") == "posts"

    def test_generated_document_key_is_unique(self, tmp_path):
        result_a = generate_template_doc(tmp_path, tmp_path, "Doc A", None)
        result_b = generate_template_doc(tmp_path, tmp_path, "Doc B", None)
        key_a = frontmatter.load(result_a).metadata["document_key"]
        key_b = frontmatter.load(result_b).metadata["document_key"]
        assert str(key_a) != str(key_b)

    def test_title_written_to_frontmatter(self, tmp_path):
        result = generate_template_doc(tmp_path, tmp_path, "Cool Title", None)
        post = frontmatter.load(result)
        assert post.metadata.get("title") == "Cool Title"


class TestUpdateFrontmatter:
    @pytest.fixture
    def doc_file(self, tmp_path) -> Path:
        f = tmp_path / "test.md"
        f.write_text(
            "---\ntitle: Test\nwordpress_id: \ndocument_hash: \n---\n\nContent here\n"
        )
        return f

    def test_updates_wordpress_id(self, doc_file):
        update_frontmatter(doc_file, wordpress_id=42, document_hash=None)
        post = frontmatter.load(doc_file)
        assert post.metadata["wordpress_id"] == 42

    def test_updates_document_hash(self, doc_file):
        update_frontmatter(doc_file, wordpress_id=None, document_hash="abc123")
        post = frontmatter.load(doc_file)
        assert post.metadata["document_hash"] == "abc123"

    def test_updates_both_fields(self, doc_file):
        update_frontmatter(doc_file, wordpress_id=99, document_hash="deadbeef")
        post = frontmatter.load(doc_file)
        assert post.metadata["wordpress_id"] == 99
        assert post.metadata["document_hash"] == "deadbeef"

    def test_does_not_overwrite_with_none(self, doc_file):
        update_frontmatter(doc_file, wordpress_id=10, document_hash="abc")
        update_frontmatter(doc_file, wordpress_id=None, document_hash=None)
        post = frontmatter.load(doc_file)
        assert post.metadata["wordpress_id"] == 10
        assert post.metadata["document_hash"] == "abc"

    def test_preserves_existing_content_body(self, doc_file):
        original_content = frontmatter.load(doc_file).content
        update_frontmatter(doc_file, wordpress_id=1, document_hash="x")
        assert frontmatter.load(doc_file).content == original_content

    def test_preserves_other_frontmatter_fields(self, doc_file):
        update_frontmatter(doc_file, wordpress_id=1, document_hash="x")
        post = frontmatter.load(doc_file)
        assert post.metadata["title"] == "Test"

    def test_sets_parent_key_when_provided(self, tmp_path):
        f = tmp_path / "child.md"
        f.write_text("---\ntitle: C\nparent_key: \ndocument_hash: \n---\n\nContent\n")
        update_frontmatter(f, parent_key=PARENT_KEY)
        assert frontmatter.load(f).metadata["parent_key"] == str(PARENT_KEY)

    def test_clears_parent_key_when_none_passed(self, tmp_path):
        f = tmp_path / "child.md"
        f.write_text(f"---\ntitle: C\nparent_key: {PARENT_KEY}\ndocument_hash: abc\n---\n\nC\n")
        update_frontmatter(f, parent_key=None)
        assert frontmatter.load(f).metadata["parent_key"] == ""

    def test_clears_document_hash_when_parent_key_provided(self, tmp_path):
        f = tmp_path / "child.md"
        f.write_text("---\ntitle: C\nparent_key: \ndocument_hash: oldhash\n---\n\nC\n")
        update_frontmatter(f, parent_key=PARENT_KEY)
        assert frontmatter.load(f).metadata["document_hash"] == ""

    def test_does_not_touch_parent_key_when_omitted(self, doc_file):
        # doc_file has no parent_key field — calling without parent_key should not add it
        update_frontmatter(doc_file, wordpress_id=1)
        assert "parent_key" not in frontmatter.load(doc_file).metadata


GRANDPARENT_KEY = UUID("00000003-0000-7000-8000-000000000000")


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

    def test_clears_document_hash_on_children(self, tmp_path):
        doc = self._make_parent_doc(tmp_path, "section.md", GRANDPARENT_KEY)
        sibling = tmp_path / "section"
        sibling.mkdir()
        self._make_child_doc(sibling, "child.md")
        reparent_and_relocate_children(doc)
        post = frontmatter.load(tmp_path / "child.md")
        assert post.metadata["document_hash"] == ""

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


class TestToHtml:
    def test_renders_bold_markdown(self):
        post = frontmatter.loads("---\ntitle: Test\n---\nHello **world**")
        assert "<strong>world</strong>" in to_html(post)

    def test_renders_paragraph(self):
        post = frontmatter.loads("---\ntitle: Test\n---\nJust a paragraph.")
        assert "<p>" in to_html(post)

    def test_strips_leading_h1_matching_title(self):
        post = frontmatter.loads("---\ntitle: My Doc\n---\n# My Doc\n\nParagraph here")
        html = to_html(post)
        assert "<h1>" not in html
        assert "Paragraph here" in html

    def test_keeps_h1_not_matching_title(self):
        post = frontmatter.loads("---\ntitle: My Doc\n---\n# Different Heading\n\nContent")
        assert "<h1>" in to_html(post)

    def test_keeps_h1_when_no_title_in_frontmatter(self):
        post = frontmatter.loads("---\n---\n# Heading\n\nContent")
        assert "<h1>" in to_html(post)

    def test_handles_empty_content(self):
        post = frontmatter.loads("---\ntitle: Empty\n---\n")
        assert to_html(post).strip() == ""

    def test_renders_unordered_list(self):
        post = frontmatter.loads("---\ntitle: Test\n---\n- item1\n- item2")
        html = to_html(post)
        assert "<li>" in html
        assert "item1" in html

    def test_renders_inline_code(self):
        post = frontmatter.loads("---\ntitle: Test\n---\nUse `foo()` here")
        assert "<code>" in to_html(post)

    def test_content_after_stripped_h1_is_preserved(self):
        post = frontmatter.loads(
            "---\ntitle: Guide\n---\n# Guide\n\nFirst para\n\nSecond para"
        )
        html = to_html(post)
        assert "First para" in html
        assert "Second para" in html

    def test_strips_md_extension_from_internal_links(self):
        post = frontmatter.loads("---\ntitle: Test\n---\n[Other](./other.md)")
        assert 'href="./other"' in to_html(post)
        assert ".md" not in to_html(post)

    def test_strips_md_extension_from_relative_path_links(self):
        post = frontmatter.loads("---\ntitle: Test\n---\n[Deep](../section/page.md)")
        assert 'href="../section/page"' in to_html(post)

    def test_does_not_strip_md_from_external_links(self):
        post = frontmatter.loads("---\ntitle: Test\n---\n[Ext](https://example.com/readme.md)")
        assert "readme.md" in to_html(post)

    def test_strips_md_from_multiple_links(self):
        post = frontmatter.loads(
            "---\ntitle: Test\n---\n[A](./a.md) and [B](./b.md)"
        )
        html = to_html(post)
        assert 'href="./a"' in html
        assert 'href="./b"' in html


class TestReadDirectory:
    def test_empty_directory_returns_empty_lists(self, tmp_path):
        files, dirs = read_directory(tmp_path)
        assert files == []
        assert dirs == []

    def test_returns_files_separately_from_directories(self, tmp_path):
        (tmp_path / "doc.md").write_text("content")
        (tmp_path / "subdir").mkdir()
        files, dirs = read_directory(tmp_path)
        assert len(files) == 1
        assert len(dirs) == 1
        assert files[0].name == "doc.md"
        assert dirs[0].name == "subdir"

    def test_only_files(self, tmp_path):
        (tmp_path / "a.md").write_text("")
        (tmp_path / "b.md").write_text("")
        files, dirs = read_directory(tmp_path)
        assert len(files) == 2
        assert dirs == []

    def test_only_directories(self, tmp_path):
        (tmp_path / "child1").mkdir()
        (tmp_path / "child2").mkdir()
        files, dirs = read_directory(tmp_path)
        assert files == []
        assert len(dirs) == 2

    def test_does_not_recurse(self, tmp_path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "nested.md").write_text("")
        files, dirs = read_directory(tmp_path)
        assert files == []
        assert len(dirs) == 1
