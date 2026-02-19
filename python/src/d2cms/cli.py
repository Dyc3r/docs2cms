import argparse
import logging
import sys
from datetime import datetime

import frontmatter
from dotenv import load_dotenv

from d2cms.config import ConfigError, load_config_from_env
from d2cms.docs import ContentType, generate_template_doc, reparent_and_relocate_children
from d2cms.wordpress import sync


def _cmd_add_doc(args: argparse.Namespace) -> None:
    try:
        config = load_config_from_env()
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    content_type: ContentType = args.content_type or "docs"
    
    if args.path:
        doc_path = config.docs_dir / content_type / args.path
    else:
        doc_path = config.docs_dir / content_type
    
    try:
        created = generate_template_doc(
            docs_root=config.docs_dir,
            document_path=doc_path,
            title=args.title,
            tags=[t.strip() for t in args.tags.split(",")] if args.tags else [],
        )
        print(f"Created: {created}")
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_deprecate(args: argparse.Namespace) -> None:
    try:
        config = load_config_from_env()
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    file_path = config.docs_dir / args.path

    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    post = frontmatter.load(file_path)
    post.metadata["deprecated"] = True
    with file_path.open("w") as f:
        f.write(frontmatter.dumps(post))

    reparent_and_relocate_children(file_path)
    print(f"Deprecated: {file_path}")


def _cmd_sync(args: argparse.Namespace) -> None:
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")

    try:
        config = load_config_from_env()
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    path = config.docs_dir / args.path if args.path else None
    report = sync(config, force=args.force, path=path)


    if report.has_failures:
        print(f"{report.failure_count} document(s) failed to sync.", file=sys.stderr)
        
        report_dir = config.docs_dir / "d2cms-sync-results"
        report_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        report_path = report_dir / f"{timestamp}.csv"
        report.write_csv(report_path)
    
        print(f"Sync report written to {report_path}")
        sys.exit(1)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(prog="d2cms", description="Sync markdown docs to WordPress")
    subparsers = parser.add_subparsers(dest="command")

    add_doc = subparsers.add_parser("add", help="Generate a template markdown document")
    add_doc.add_argument("title", help="Document title")
    add_doc.add_argument(
        "--content-type",
        default="docs",
        choices=["posts", "pages", "docs"],
        help="WordPress content type (default: docs)",
    )
    add_doc.add_argument(
        "--path",
        help="Subdirectory relative to the content type directory inside the D2CMS_DOCS_DIR root (e.g. 'guides/intro')",
    )
    add_doc.add_argument("--tags", metavar="TAGS", help="Comma-delimited list of tags to assign to the document")

    deprecate_cmd = subparsers.add_parser(
        "deprecate", help="Mark a document as deprecated and relocate its children"
    )
    deprecate_cmd.add_argument(
        "path", help="Path to the document relative to D2CMS_DOCS_DIR"
    )

    sync_cmd = subparsers.add_parser("sync", help="Sync all documents in D2CMS_DOCS_DIR to WordPress")
    sync_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")
    sync_cmd.add_argument("--force", action="store_true", help="Sync all documents regardless of content hash")
    sync_cmd.add_argument("--path", help="Subdirectory relative to D2CMS_DOCS_DIR to sync")

    args = parser.parse_args()

    if args.command == "add":
        _cmd_add_doc(args)
    elif args.command == "deprecate":
        _cmd_deprecate(args)
    elif args.command == "sync":
        _cmd_sync(args)
    else:
        parser.print_help()
