import logging
from pathlib import Path

import frontmatter
from frontmatter import Post
from httpx import Client

from . import docs
from .config import D2CMSConfig
from .docs import (
    ContentType,
    D2CMSFrontmatter,
    content_type_from_path,
    generate_doc_hash,
    to_html,
    update_frontmatter,
)
from .http import make_client
from .report import SyncReport

logger = logging.getLogger(__name__)


class ParentNotFoundError(FileNotFoundError):
    """Raised when a parent_key does not match an existing content object in the remote DB"""


def _find_parent_id(metadata: D2CMSFrontmatter, content_type: ContentType, client: Client) -> int | None:
    """Find the WordPress ID of the parent document, if any"""
    if metadata.parent_key:
        response = client.get(f"wp/v2/{content_type}", params={
            "meta_key": "document_key",
            "meta_value": metadata.parent_key
        }, follow_redirects=True)
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
        response = client.get("wp/v2/tags", params={"name": name}, follow_redirects=True)
        existing = response.json()

        if existing:
            tag_ids.append(existing[0]['id'])
        else:
            logger.debug("Creating tag: %s", name)
            response = client.post("wp/v2/tags", json={"name": name})
            response.raise_for_status()
            tag_ids.append(response.json()['id'])

    return tag_ids


def _handle_delete(document: Post, file_path: Path, cfg: D2CMSConfig) -> None:
    """Delete post from WordPress and remove local file."""
    wordpress_id = document.metadata.get("wordpress_id")
    post_title = document.metadata.get("title")

    logger.info("[delete] %s", file_path)

    if not wordpress_id:
        logger.info("[delete] %s was never synced — removing local file only", post_title)
        file_path.unlink()
        return

    with make_client(cfg) as client:
        content_type = content_type_from_path(file_path, cfg.docs_dir)

        logger.debug("[delete] DELETE wp/v2/%s/%s", content_type, wordpress_id)
        response = client.delete(f"wp/v2/{content_type}/{wordpress_id}")
        response.raise_for_status()

        logger.info("[delete] %s removed from WordPress (id=%s)", post_title, wordpress_id)
        file_path.unlink()


def _sync_directory(directory: Path, cfg: D2CMSConfig, report: SyncReport, force: bool = False) -> None:
    """Sync all documents in a directory to WordPress"""
    logger.debug("[sync] scanning directory: %s", directory)
    files, directories = docs.read_directory(directory)

    for file_path in files:
        _sync_document(file_path, cfg, report, force=force)

    for child_dir in directories:
        if child_dir.exists() and child_dir.name != "d2cms-sync-results":
            _sync_directory(child_dir, cfg, report, force=force)


def _sync_document(file_path: Path, cfg: D2CMSConfig, report: SyncReport, force: bool = False) -> None:
    """Sync a single document to WordPress"""
    logger.debug("[sync] processing: %s", file_path)

    document = frontmatter.load(file_path)
    metadata = document.metadata

    content_type: ContentType | None = None
    try:
        content_type = content_type_from_path(file_path, cfg.docs_dir)
        current_hash = generate_doc_hash(document, file_path.relative_to(cfg.docs_dir))

        if metadata.get("deprecated"):
            _handle_delete(document, file_path, cfg)
            return

        if not force and metadata.get("document_hash") == current_hash:
            logger.info("[sync] skipping (no changes): %s", file_path)
            return

        with make_client(cfg) as client:
            wordpress_id = metadata.get("wordpress_id")
            if wordpress_id:
                logger.info("[sync] updating: %s (id=%s)", file_path, wordpress_id)
                api_route = f"wp/v2/{content_type}/{wordpress_id}"
            else:
                logger.info("[sync] creating: %s", file_path)
                api_route = f"wp/v2/{content_type}"

            logger.debug("[sync] POST %s", client.build_request("POST", api_route).url)
            fm_kwargs = {k: v for k, v in metadata.items() if k != "content_type"}
            response = client.post(api_route, json={
                "slug": metadata.get("slug"),
                "title": metadata.get("title"),
                "status": "publish",
                "menu_order": metadata.get("order") or 0,
                "content": to_html(document),
                "meta": {
                    "document_key": str(metadata.get("document_key")),
                    "document_hash": current_hash,
                },
                "parent": _find_parent_id(D2CMSFrontmatter(**fm_kwargs), content_type, client),
                "tags": _get_or_create_tag_ids(metadata.get("tags") or [], client)
            })
            response.raise_for_status()

            wp_data = response.json()

        logger.info("[sync] done: %s (wp_id=%s)", file_path, wp_data['id'])
        update_frontmatter(file_path, wordpress_id=wp_data['id'], document_hash=current_hash)

    except Exception as e:
        logger.error("[sync] failed: %s — %s", file_path, e)
        report.record_failure(
            doc_path=str(file_path.relative_to(cfg.docs_dir)),
            content_type=content_type,
            wordpress_id=metadata.get("wordpress_id") or None,
            error=e,
        )


def sync(cfg: D2CMSConfig, force: bool = False, path: Path | None = None) -> SyncReport:
    report = SyncReport()
    _sync_directory(path if path is not None else cfg.docs_dir, cfg, report, force=force)
    return report