from pathlib import Path

import frontmatter
from frontmatter import Post
from httpx import Client

from .config import D2CMSConfig
from .docs import D2CMSFrontmatter, generate_doc_hash, to_html, update_frontmatter
from .http import make_client


class ParentNotFoundError(FileNotFoundError):
    """Raised when a parent_key does not match an existing content object in the remote DB"""


def _find_parent_id(metadata: D2CMSFrontmatter, client: Client) -> int | None:
    """Find the WordPress ID of the parent document, if any"""
    if metadata.parent_key:
        content_type = metadata.content_type

        response = client.get(f"wp/v2/{content_type}", params={
            "meta_key": "document_key",
            "meta_value": metadata.parent_key
        })
        response.raise_for_status()

        parent_data = response.json()
        if not parent_data:
            raise ParentNotFoundError(f"The specified parent document does not exist: {metadata.parent_key}")
        return parent_data[0]['id']
    else:
        return None


def _get_or_create_tag_ids(tags: list[str], client: Client) -> list[int]:
    """Get or create WordPress tag IDs for the given list of tag names"""
    tag_ids = []

    for name in tags:
        response = client.get("wp/v2/tags", params={ "name": name })
        existing = response.json()

        if existing:
            tag_ids.append(existing[0]['id'])
        else:
            response = client.post("wp/v2/tags", json={ "name": name })
            response.raise_for_status()
            tag_ids.append(response.json()['id'])

    return tag_ids


def _handle_delete(document: Post, file_path: Path, cfg: D2CMSConfig) -> None:
    """Delete post from WordPress and remove local file."""
    wordpress_id = document.metadata.get("wordpress_id")
    post_title = document.metadata.get("title")

    print(f"{post_title} is deprecated. Preparing to delete")

    if not wordpress_id:
        print(f"{post_title} was never synced. Removing local document")
        file_path.unlink()
        return

    with make_client(cfg) as client:
        content_type = document.metadata.get("content_type")

        response = client.delete(f"wp/v2/{content_type}/{wordpress_id}")
        response.raise_for_status()

        print(f"{post_title} was successfully removed from WordPress. Removing local document")
        file_path.unlink()


def sync_document(file_path: Path, cfg: D2CMSConfig) -> None:
    """Sync a single document to WordPress"""
    document = frontmatter.load(file_path)
    metadata = document.metadata
    current_hash = generate_doc_hash(document)

    if metadata.get("deprecated"):
        # If the document is deprecated, remove it
        _handle_delete(document, file_path, cfg)
        return

    
    if document.metadata.get("document_hash") == current_hash:
        print(f"No changes detected. Skipping: {document.metadata.get("title")}")
        return
    
    with make_client(cfg) as client:
        content_type = document.metadata.get("content_type")
        wordpress_id = document.metadata.get("wordpress_id")
        if wordpress_id:
            api_route = f"wp/v2/{content_type}/{wordpress_id}"
        else:
            api_route = f"wp/v2/{content_type}"

        response = client.post(api_route, json={
            "slug": document.metadata.get("slug"),
            "title": document.metadata.get("title"),
            "content": to_html(document),
            "meta": {
                "document_key": str(document.metadata.get("document_key")),
                "document_hash": current_hash,
            },
            "parent": _find_parent_id(D2CMSFrontmatter(**metadata), client),
            "tags": _get_or_create_tag_ids(metadata.get("tags", []), client)
        })
        response.raise_for_status()

        wp_data = response.json()

    update_frontmatter(file_path, wordpress_id=wp_data['id'], hash=current_hash)