import hashlib
from pathlib import Path

import frontmatter
import yaml

from d2cms.docs import generate_doc_hash


def _make_hash(post: frontmatter.Post, relative_path: Path) -> str:
    metadata_for_hash = {k: v for k, v in post.metadata.items() if k != "document_hash"}
    hash_input = "\n".join([
        str(relative_path),
        yaml.dump(metadata_for_hash, sort_keys=True, default_flow_style=False),
        post.content,
    ])
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


class TestGenerateDocHash:
    def test_returns_sha256_hex_string(self):
        post = frontmatter.loads("---\ntitle: Test\n---\nHello world")
        result = generate_doc_hash(post, Path("test.md"))
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_matches_expected_sha256_of_combined_input(self):
        post = frontmatter.loads("---\ntitle: Test\n---\nHello world")
        path = Path("section/test.md")
        assert generate_doc_hash(post, path) == _make_hash(post, path)

    def test_consistent_for_same_inputs(self):
        post = frontmatter.loads("---\ntitle: Test\n---\nSame content")
        path = Path("test.md")
        assert generate_doc_hash(post, path) == generate_doc_hash(post, path)

    def test_changes_when_content_changes(self):
        path = Path("test.md")
        post_a = frontmatter.loads("---\ntitle: Test\n---\nContent A")
        post_b = frontmatter.loads("---\ntitle: Test\n---\nContent B")
        assert generate_doc_hash(post_a, path) != generate_doc_hash(post_b, path)

    def test_changes_when_path_changes(self):
        post = frontmatter.loads("---\ntitle: Test\n---\nContent")
        assert generate_doc_hash(post, Path("a.md")) != generate_doc_hash(post, Path("b.md"))

    def test_changes_when_frontmatter_changes(self):
        path = Path("test.md")
        post_a = frontmatter.loads("---\ntitle: A\n---\nShared content")
        post_b = frontmatter.loads("---\ntitle: B\n---\nShared content")
        assert generate_doc_hash(post_a, path) != generate_doc_hash(post_b, path)

    def test_document_hash_field_excluded_from_hash(self):
        path = Path("test.md")
        post_a = frontmatter.loads("---\ntitle: T\ndocument_hash: old\n---\nContent")
        post_b = frontmatter.loads("---\ntitle: T\ndocument_hash: new\n---\nContent")
        assert generate_doc_hash(post_a, path) == generate_doc_hash(post_b, path)
