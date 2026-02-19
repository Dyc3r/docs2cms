import frontmatter
import pytest

from d2cms.docs import generate_template_doc
from tests.docs._constants import PARENT_KEY


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

    def test_sets_parent_key_from_parent_directory_md_file(self, tmp_path):
        parent_file = tmp_path / "section.md"
        parent_file.write_text(f"---\ndocument_key: {PARENT_KEY}\ntitle: Section\n---\n")
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
