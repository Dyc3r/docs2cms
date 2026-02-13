import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
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

    @property
    def is_child(self) -> bool:
        return self.parent_key is not None
    


def _title_to_slug(title: str) -> str:
    return title.lower().replace(" ", "-")



def generate_doc_hash(post: Post):
    return hashlib.sha256(post.content.encode("utf-8")).hexdigest()



def generate_template_doc(
        document_path: Path,
        title: str,
        parent_key: UUID | None,
        tags: list[str] | None,
        content_type: ContentType = "docs",
) -> None:
    
    document_path.mkdir(parents=True, exist_ok=True)
    
    slug = _title_to_slug(title)
    file_path = document_path / f"{slug}.md"

    if file_path.exists():
        raise FileExistsError(f"Specified file already exists: {file_path}")

    frontmatter = D2CMSFrontmatter(
        document_key=uuid7(),
        content_type=content_type,
        title=title,
        slug=slug,
        parent_key=parent_key,
        tags=tags or []
    )

    content = dedent(f"""---
        document_key: {frontmatter.document_key}
        title: {frontmatter.title}
        slug: {frontmatter.slug}
        content_type: {frontmatter.content_type}
        parent_key: {frontmatter.parent_key}
        tags: {', '.join(frontmatter.tags)}
        wordpress_id: {frontmatter.wordpress_id or ''}
        document_hash: {frontmatter.document_hash or ''}
        ---

        # {frontmatter.title}

        Doc content here
    """).strip()
    
    file_path.write_text(content)



def update_frontmatter(file_path: Path, wordpress_id: int | None, hash: str | None) -> None:
    post = frontmatter.load(file_path)

    if wordpress_id is not None:
        post.metadata["wordpress_id"] = wordpress_id

    if hash is not None:
        post.metadata["document_hash"] = hash

    with file_path.open('w') as f:
        f.write(frontmatter.dumps(post))



def to_html(document: Post) -> str:
    md = MarkdownIt("commonmark")

    title = document.metadata.get("title")
    content = document.content

    lines = content.split("\n")
    if lines and title and lines[0].strip() == f"# {title}":
        content = "\n".join(lines[1:]).lstrip()

    return md.render(content)