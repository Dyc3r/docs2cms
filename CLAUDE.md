# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**docs2cms (d2cms)** syncs git-managed markdown files to WordPress via its REST API. Documents store metadata (WordPress ID, content hash, UUID) in YAML frontmatter, enabling hash-based change detection to skip unnecessary API calls.

## Development Commands

All commands run from the `python/` directory.

```bash
# Install dependencies (editable + dev)
pip install -e ".[dev]"

# Type checking (strict mode)
mypy

# Lint
ruff check .

# Format
ruff format .

# Run all tests
pytest

# Run a single test file
pytest tests/test_foo.py

# Run a single test by name
pytest -k "test_name"
```

## WordPress Dev Environment

```bash
# Start WordPress (from wordpress/)
docker compose up -d

# WordPress is available at http://localhost:8080
# REST API root: http://localhost:8080/wp-json
```

## Architecture

```
cli.py  →  config.py  →  docs.py  →  wordpress.py
                                          ↑
                               http.py (client factory)
```

- **config.py**: Frozen dataclass loaded from env vars (`.env` file via python-dotenv). Validates auth mode (`token` or `basic`), normalizes API root URL.
- **docs.py**: Parses markdown frontmatter (`D2CMSFrontmatter` dataclass), converts markdown to HTML via markdown-it-py, computes SHA256 content hashes, reads/writes frontmatter.
- **http.py**: Factory creating a configured `httpx.Client` with auth headers/credentials, 10s timeout, `Accept: application/json`.
- **wordpress.py**: REST API integration — syncs documents, manages tags, resolves parent-child relationships by UUID, handles deletions.

## Key Design Decisions

- **Document identity**: Each doc has a `document_key` UUIDv7 stored in frontmatter and as WordPress post meta — used as stable cross-system identifier.
- **Change detection**: `generate_doc_hash()` SHA256s document content; sync is skipped if the hash matches the stored `frontmatter_hash`.
- **Content types**: Supports `posts`, `pages`, and `docs` WordPress content types (the latter registered by `wordpress/mu-plugins/d2cms-docs.php`).
- **Auth**: Bearer token (`D2CMS_AUTH_MODE=token`) or HTTP Basic (`D2CMS_AUTH_MODE=basic`). Dev environment uses a bearer token via `wordpress/mu-plugins/d2cms-auth.php`.
- **Parent resolution**: `_find_parent_id()` queries WordPress meta to find a parent by UUID; raises `ParentNotFoundError` if not found.

## Environment Variables

See `python/src/.env.example`:

```
D2CMS_WP_API_ROOT      # WordPress REST API root URL
D2CMS_WP_API_KEY       # Bearer token or password
D2CMS_WP_API_USER      # WordPress username (used in basic auth)
D2CMS_DOCS_DIR         # Local directory containing markdown files
D2CMS_AUTH_MODE        # "token" or "basic" (default: "basic")
```

## Code Style

- Python 3.14+, strict MyPy, ruff with rules E, F, I, B, UP, SIM
- 100-character line length, double quotes
- Dataclasses with `frozen=True` for immutable config/data structures
