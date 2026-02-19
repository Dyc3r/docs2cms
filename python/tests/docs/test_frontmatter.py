from d2cms.docs import D2CMSFrontmatter, _title_to_slug
from tests.docs._constants import DOC_KEY, PARENT_KEY


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


class TestD2CMSFrontmatterIsChild:
    def test_is_child_when_parent_key_set(self):
        fm = D2CMSFrontmatter(
            document_key=DOC_KEY,
            title="Child",
            slug="child",
            parent_key=PARENT_KEY,
        )
        assert fm.is_child is True

    def test_not_child_by_default(self):
        fm = D2CMSFrontmatter(
            document_key=DOC_KEY,
            title="Root",
            slug="root",
        )
        assert fm.is_child is False

    def test_not_child_when_parent_key_none(self):
        fm = D2CMSFrontmatter(
            document_key=DOC_KEY,
            title="Root",
            slug="root",
            parent_key=None,
        )
        assert fm.is_child is False
