from pathlib import Path

import frontmatter

from d2cms.docs import generate_doc_hash, update_frontmatter

WP_BASE = "http://test-wp.test/wp-json/"
DOC_KEY = "00000001-0000-7000-8000-000000000000"
PARENT_KEY = "ffffffff-ffff-7fff-bfff-ffffffffffff"


def _write_doc(tmp_path: Path, content: str, name: str = "test.md") -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


def _new_doc(tmp_path: Path, name: str = "test.md") -> Path:
    """A doc that has never been synced (no wordpress_id, no hash)."""
    return _write_doc(
        tmp_path,
        f"---\ndocument_key: {DOC_KEY}\ntitle: Test Document\nslug: test-document\n"
        "content_type: docs\nparent_key: \ntags: []\nwordpress_id: \n"
        "document_hash: \ndeprecated: false\n---\n\nContent here\n",
        name,
    )


def _existing_doc(tmp_path: Path, wp_id: int, stored_hash: str, name: str = "test.md") -> Path:
    """A doc that was previously synced, with a (possibly stale) hash."""
    return _write_doc(
        tmp_path,
        f"---\ndocument_key: {DOC_KEY}\ntitle: Test Document\nslug: test-document\n"
        f"content_type: docs\nparent_key: \ntags: []\nwordpress_id: {wp_id}\n"
        f"document_hash: {stored_hash}\ndeprecated: false\n---\n\nContent here\n",
        name,
    )


def _synced_doc(tmp_path: Path, wp_id: int, name: str = "test.md") -> Path:
    """A doc whose stored hash matches its current content (sync should be skipped)."""
    doc_file = _new_doc(tmp_path, name)
    real_hash = generate_doc_hash(frontmatter.load(doc_file), Path(name))
    update_frontmatter(doc_file, wordpress_id=wp_id, document_hash=real_hash)
    return doc_file
