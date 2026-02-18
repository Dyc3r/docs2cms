import argparse
import sys

from dotenv import load_dotenv

from d2cms.config import ConfigError, load_config_from_env
from d2cms.docs import generate_template_doc


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


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(prog="d2cms", description="Sync markdown docs to WordPress")
    subparsers = parser.add_subparsers(dest="command")

    add_doc = subparsers.add_parser("add-doc", help="Generate a template markdown document")
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

    args = parser.parse_args()

    if args.command == "add-doc":
        _cmd_add_doc(args)
    else:
        parser.print_help()
