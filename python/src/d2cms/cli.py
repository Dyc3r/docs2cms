import argparse
import logging
import sys

import frontmatter
from dotenv import load_dotenv

from d2cms.config import ConfigError, load_config_from_env
from d2cms.docs import generate_template_doc, reparent_and_relocate_children
from d2cms.wordpress import sync


def _cmd_add_doc(args: argparse.Namespace) -> None:
    try:
        config = load_config_from_env()
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    doc_path = config.docs_dir / args.path if args.path else config.docs_dir

    try:
        created = generate_template_doc(
            docs_root=config.docs_dir,
            document_path=doc_path,
            title=args.title,
            tags=[t.strip() for t in args.tags.split(",")] if args.tags else [],
            content_type=args.content_type,
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

    sync(config)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(prog="d2cms", description="Sync markdown docs to WordPress")
    subparsers = parser.add_subparsers(dest="command")

    add_doc = subparsers.add_parser("add", help="Generate a template markdown document")
    add_doc.add_argument("title", help="Document title")
    add_doc.add_argument(
        "--path",
        help="Subdirectory relative to D2CMS_DOCS_DIR to create the document in",
    )
    add_doc.add_argument("--tags", metavar="TAGS", help="Comma-delimited list of tags to assign to the document")
    add_doc.add_argument(
        "--content-type",
        choices=["posts", "pages", "docs"],
        default="docs",
        help="WordPress content type (default: docs)",
    )

    deprecate_cmd = subparsers.add_parser(
        "deprecate", help="Mark a document as deprecated and relocate its children"
    )
    deprecate_cmd.add_argument(
        "path", help="Path to the document relative to D2CMS_DOCS_DIR"
    )

    sync_cmd = subparsers.add_parser("sync", help="Sync all documents in D2CMS_DOCS_DIR to WordPress")
    sync_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.command == "add":
        _cmd_add_doc(args)
    elif args.command == "deprecate":
        _cmd_deprecate(args)
    elif args.command == "sync":
        _cmd_sync(args)
    else:
        parser.print_help()
