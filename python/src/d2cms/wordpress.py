from pathlib import Path

import frontmatter
from httpx import Client

from .config import D2CMSConfig
from .docs import D2CMSFrontmatter, generate_doc_hash, to_html, update_frontmatter
from .http import make_client


def _find_parent_id(frontmatter: D2CMSFrontmatter, client: Client) -> int | None:
    if frontmatter.parent_key:
        content_type = frontmatter.content_type

        response = client.get(f"wp/v2/{content_type}", params={
            "meta_key": "document_key",
            "meta_value": frontmatter.parent_key
        })
        response.raise_for_status()

        parent_data = response.json()
        return parent_data['id']
    else:
        return None


def _get_or_create_tag_ids(tags: list[str], client: Client) -> list[int]:
    tag_ids = []

    for name in tags:
        response = client.get("wp/v2/tags", params={ "name": name })
        existing = response.json()

        if existing:
            tag_ids.append(existing[0]['id'])
        else:
            response = client.post("wp/v2/tags", jason={ "name": name })
            response.raise_for_status()
            tag_ids.append(response.json()['id'])

    return tag_ids


def sync_document(file_path: Path, cfg: D2CMSConfig) -> None:
    document = frontmatter.load(file_path)
    metadata = document.metadata
    current_hash = generate_doc_hash(document)

    
    if document.metadata.get("document_hash") == current_hash:
        print(f"No changes detected. Skipping: {document.metadata.get["title"]}")
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
                "document_key": document.metadata.get("document_key"),
                "document_hash": current_hash,
            },
            "parent": _find_parent_id(D2CMSFrontmatter(**metadata), client),
            "tags": _get_or_create_tag_ids(metadata.get("tags"))
        })
        response.raise_for_status()

        wp_data = response.json()

    update_frontmatter(file_path, wordpress_id=wp_data['id'], hash=current_hash)