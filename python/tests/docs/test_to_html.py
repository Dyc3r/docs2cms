import frontmatter

from d2cms.docs import to_html


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
        assert "<p>First para</p>" in html
        assert "<p>Second para</p>" in html

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

    def test_renders_table_as_html_table(self):
        post = frontmatter.loads("---\ntitle: Test\n---\n| A | B |\n|---|---|\n| 1 | 2 |")
        html = to_html(post)
        assert "<table>" in html
        assert "<th>A</th>" in html
        assert "<td>1</td>" in html

    def test_strips_md_from_multiple_links(self):
        post = frontmatter.loads(
            "---\ntitle: Test\n---\n[A](./a.md) and [B](./b.md)"
        )
        html = to_html(post)
        assert 'href="./a"' in html
        assert 'href="./b"' in html
