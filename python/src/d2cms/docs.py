import hashlib
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, get_args
from uuid import UUID, uuid7

import frontmatter
import yaml
from frontmatter import Post
from markdown_it import MarkdownIt

ContentType = Literal["posts", "pages", "docs"]


def content_type_from_path(file_path: Path, docs_dir: Path) -> ContentType:
    """Derive the WordPress content type from the file's top-level directory."""
    relative = file_path.relative_to(docs_dir)
    top = relative.parts[0] if relative.parts else ""
    if top not in get_args(ContentType):
        raise ValueError(
            f"File is not inside a content type directory (docs/pages/posts): {file_path}"
        )
    return top  # type: ignore[return-value]


@dataclass
class D2CMSFrontmatter:
    document_key: UUID # tool-generated unique ID
    title: str # Post title
    slug: str # Post slug (used in URL & doc file name)
    order: int = 0
    wordpress_id: int | None = None # WordPress generated ID
    document_hash: str | None = None # hashed value of the doc for identifying diffs
    parent_key: UUID | None = None # the document_key of the parent object
    tags: list[str] = field(default_factory = list)
    deprecated: bool = False

    @property
    def is_child(self) -> bool:
        return self.parent_key is not None
    


def _title_to_slug(title: str) -> str:
    return title.lower().strip().replace(" ", "-")



def generate_doc_hash(post: Post, relative_path: Path) -> str:
    metadata_for_hash = {k: v for k, v in post.metadata.items() if k != "document_hash"}
    hash_input = "\n".join([
        str(relative_path),
        yaml.dump(metadata_for_hash, sort_keys=True, default_flow_style=False),
        post.content,
    ])
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()



def generate_template_doc(
        docs_root: Path,
        document_path: Path,
        title: str,
        tags: list[str] | None,
) -> Path:

    document_path.mkdir(parents=True, exist_ok=True)

    slug = _title_to_slug(title)
    file_path = document_path / f"{slug}.md"

    if file_path.exists():
        raise FileExistsError(f"Specified file already exists: {file_path}")

    parent_key: UUID | None = None
    if document_path != docs_root:
        parent_file = Path(f"{file_path.parent}.md")
        if parent_file.exists():
            parent_post = frontmatter.load(parent_file)
            key = parent_post.metadata.get("document_key")
            parent_key = UUID(str(key)) if key else None
        
    fm = D2CMSFrontmatter(
        document_key=uuid7(),
        title=title,
        slug=slug,
        parent_key=parent_key,
        tags=tags or []
    )

    content = f"""---
document_key: {fm.document_key}
title: {fm.title}
slug: {fm.slug}
order: {fm.order}
parent_key: {fm.parent_key or ''}
tags: [{', '.join(fm.tags)}]
wordpress_id: {fm.wordpress_id or ''}
document_hash: {fm.document_hash or ''}
---

# {fm.title}

Doc content here
"""

    file_path.write_text(content)
    return file_path



def read_directory(doc_path: Path):
    files = []
    directories = []

    for entry in doc_path.iterdir():
        if entry.is_dir():
            directories.append(entry)
        else:
            files.append(entry)

    return files, directories



class _NotProvided:
    pass


_NOT_PROVIDED = _NotProvided()


def update_frontmatter(
    file_path: Path,
    wordpress_id: int | None = None,
    document_hash: str | None = None,
    parent_key: UUID | None | _NotProvided = _NOT_PROVIDED,
) -> None:
    post = frontmatter.load(file_path)

    if wordpress_id is not None:
        post.metadata["wordpress_id"] = wordpress_id

    if document_hash is not None:
        post.metadata["document_hash"] = document_hash

    if not isinstance(parent_key, _NotProvided):
        post.metadata["parent_key"] = str(parent_key) if parent_key is not None else ""

    with file_path.open("w") as f:
        f.write(frontmatter.dumps(post))


def reparent_and_relocate_children(doc_path: Path) -> None:
    """Move sibling directory contents up one level and update their parent_key."""
    sibling_dir = doc_path.parent / doc_path.stem
    if not sibling_dir.is_dir():
        return

    deleted_post = frontmatter.load(doc_path)
    raw_key = deleted_post.metadata.get("parent_key")
    inherited_parent_key: UUID | None = UUID(str(raw_key)) if raw_key else None

    for child in sibling_dir.iterdir():
        if child.is_file() and child.suffix == ".md":
            update_frontmatter(child, parent_key=inherited_parent_key)

    for item in list(sibling_dir.iterdir()):
        shutil.move(str(item), str(doc_path.parent / item.name))

    sibling_dir.rmdir()



def to_html(document: Post, file_path: Path, docs_dir: Path) -> str:
    md = MarkdownIt("commonmark").enable("table")

    title = document.metadata.get("title")
    content = document.content

    lines = content.split("\n")
    if lines and title and lines[0].strip() == f"# {title}":
        content = "\n".join(lines[1:]).lstrip()

    # Resolve relative .md links to root-relative URLs so WordPress page hierarchy
    # doesn't cause ../foo.md to resolve to the wrong URL (e.g. /parent/parent).
    def _rewrite_md_link(match: re.Match) -> str:  # type: ignore[type-arg]
        link_path = match.group(1)
        target = (file_path.parent / (link_path + ".md")).resolve()
        try:
            parts = list(target.relative_to(docs_dir).with_suffix("").parts)
            # posts/ and pages/ are not part of the WordPress URL; docs/ is
            if len(parts) > 1 and parts[0] in ("posts", "pages"):
                parts = parts[1:]
            return f"](/{'/'.join(parts)})"
        except ValueError:
            return f"]({link_path})"
    content = re.sub(r']\(([./]*[\w/-]+)\.md\)', _rewrite_md_link, content)

    return md.render(content)