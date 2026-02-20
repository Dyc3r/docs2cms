import frontmatter
import pytest

from d2cms.docs import to_html


class TestToHtml:
    @pytest.fixture
    def paths(self, tmp_path):
        """A default docs_dir and a file_path at posts/page.md."""
        docs_dir = tmp_path
        (docs_dir / "posts").mkdir(parents=True)
        file_path = docs_dir / "posts" / "page.md"
        return file_path, docs_dir

    def test_renders_bold_markdown(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\ntitle: Test\n---\nHello **world**")
        assert "<strong>world</strong>" in to_html(post, file_path, docs_dir)

    def test_renders_paragraph(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\ntitle: Test\n---\nJust a paragraph.")
        assert "<p>" in to_html(post, file_path, docs_dir)

    def test_strips_leading_h1_matching_title(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\ntitle: My Doc\n---\n# My Doc\n\nParagraph here")
        html = to_html(post, file_path, docs_dir)
        assert "<h1>" not in html
        assert "Paragraph here" in html

    def test_keeps_h1_not_matching_title(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\ntitle: My Doc\n---\n# Different Heading\n\nContent")
        assert "<h1>" in to_html(post, file_path, docs_dir)

    def test_keeps_h1_when_no_title_in_frontmatter(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\n---\n# Heading\n\nContent")
        assert "<h1>" in to_html(post, file_path, docs_dir)

    def test_handles_empty_content(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\ntitle: Empty\n---\n")
        assert to_html(post, file_path, docs_dir).strip() == ""

    def test_renders_unordered_list(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\ntitle: Test\n---\n- item1\n- item2")
        html = to_html(post, file_path, docs_dir)
        assert "<li>" in html
        assert "item1" in html

    def test_renders_inline_code(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\ntitle: Test\n---\nUse `foo()` here")
        assert "<code>" in to_html(post, file_path, docs_dir)

    def test_content_after_stripped_h1_is_preserved(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads(
            "---\ntitle: Guide\n---\n# Guide\n\nFirst para\n\nSecond para"
        )
        html = to_html(post, file_path, docs_dir)
        assert "<p>First para</p>" in html
        assert "<p>Second para</p>" in html

    def test_strips_md_extension_from_internal_links(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\ntitle: Test\n---\n[Other](./other.md)")
        assert 'href="/other"' in to_html(post, file_path, docs_dir)

    def test_strips_md_extension_from_relative_path_links(self, tmp_path):
        docs_dir = tmp_path
        (docs_dir / "posts" / "section").mkdir(parents=True)
        file_path = docs_dir / "posts" / "section" / "file.md"
        post = frontmatter.loads("---\ntitle: Test\n---\n[Deep](../page.md)")
        assert 'href="/page"' in to_html(post, file_path, docs_dir)

    def test_does_not_strip_md_from_external_links(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\ntitle: Test\n---\n[Ext](https://example.com/readme.md)")
        assert "readme.md" in to_html(post, file_path, docs_dir)

    def test_renders_table_as_html_table(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads("---\ntitle: Test\n---\n| A | B |\n|---|---|\n| 1 | 2 |")
        html = to_html(post, file_path, docs_dir)
        assert "<table>" in html
        assert "<th>A</th>" in html
        assert "<td>1</td>" in html

    def test_strips_md_from_multiple_links(self, paths):
        file_path, docs_dir = paths
        post = frontmatter.loads(
            "---\ntitle: Test\n---\n[A](./a.md) and [B](./b.md)"
        )
        html = to_html(post, file_path, docs_dir)
        assert 'href="/a"' in html
        assert 'href="/b"' in html

    def test_parent_link_from_posts_child_resolves_correctly(self, tmp_path):
        """../parent.md from posts/parent/child.md should produce /parent, not /parent/parent."""
        docs_dir = tmp_path
        (docs_dir / "posts" / "parent").mkdir(parents=True)
        file_path = docs_dir / "posts" / "parent" / "child.md"
        post = frontmatter.loads("---\ntitle: Child\n---\n[Up](../parent.md)")
        assert 'href="/parent"' in to_html(post, file_path, docs_dir)

    def test_parent_link_from_docs_child_resolves_correctly(self, tmp_path):
        """../parent.md from docs/parent/child.md should produce /docs/parent."""
        docs_dir = tmp_path
        (docs_dir / "docs" / "parent").mkdir(parents=True)
        file_path = docs_dir / "docs" / "parent" / "child.md"
        post = frontmatter.loads("---\ntitle: Child\n---\n[Up](../parent.md)")
        assert 'href="/docs/parent"' in to_html(post, file_path, docs_dir)
