import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid7

import frontmatter
from frontmatter import Post
from markdown_it import MarkdownIt

ContentType = Literal["posts", "pages", "docs"]


@dataclass
class D2CMSFrontmatter:
    document_key: UUID # tool-generated unique ID
    content_type: ContentType # the WP content type this doc represents
    title: str # Post title
    slug: str # Post slug (used in URL & doc file name)
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



def generate_doc_hash(post: Post):
    return hashlib.sha256(post.content.encode("utf-8")).hexdigest()



def generate_template_doc(
        docs_root: Path,
        document_path: Path,
        title: str,
        tags: list[str] | None,
        content_type: ContentType = "docs",
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
        content_type=content_type,
        title=title,
        slug=slug,
        parent_key=parent_key,
        tags=tags or []
    )

    content = f"""---
document_key: {fm.document_key}
title: {fm.title}
slug: {fm.slug}
content_type: {fm.content_type}
parent_key: {fm.parent_key or ''}
tags: {', '.join(fm.tags)}
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



def update_frontmatter(file_path: Path, wordpress_id: int | None, document_hash: str | None) -> None:
    post = frontmatter.load(file_path)

    if wordpress_id is not None:
        post.metadata["wordpress_id"] = wordpress_id

    if document_hash is not None:
        post.metadata["document_hash"] = document_hash

    with file_path.open('w') as f:
        f.write(frontmatter.dumps(post))



def to_html(document: Post) -> str:
    md = MarkdownIt("commonmark")

    title = document.metadata.get("title")
    content = document.content

    lines = content.split("\n")
    if lines and title and lines[0].strip() == f"# {title}":
        content = "\n".join(lines[1:]).lstrip()

    # Strip .md extension from internal links
    content = re.sub(r']\(([./]*[\w/-]+)\.md\)', r'](\1)', content)

    return md.render(content)