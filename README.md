# docs2cms

A CLI utility for publishing git-managed markdown files to WordPress via its REST API.

Markdown files live in your repository. `d2cms` reads their YAML frontmatter to track WordPress IDs and content hashes, then creates or updates posts/pages/docs only when content has changed.

## Claude Code Experiment
This is a proof of concept for leveraging Claude as a productivity booster.

## How it works

1. Each markdown file carries a YAML frontmatter block with a stable UUID, WordPress post ID, and a content hash.
2. On sync, `d2cms` computes the current hash and skips the file if nothing changed.
3. New or modified files are converted to HTML and upserted into WordPress via its REST API.
4. Frontmatter is written back with the updated WordPress ID and hash.

## Setup

**Requirements:** Python 3.14+

```bash
cd python
pip install -e ".[dev]"
```

Copy the example environment file and fill in your values:

```bash
cp python/src/.env.example python/src/.env
```

| Variable | Description |
|---|---|
| `D2CMS_WP_API_ROOT` | WordPress REST API root (e.g. `https://example.com/wp-json`) |
| `D2CMS_WP_API_KEY` | Bearer token or password |
| `D2CMS_WP_API_USER` | WordPress username |
| `D2CMS_DOCS_DIR` | Path to directory containing your markdown files |
| `D2CMS_AUTH_MODE` | `token` (default) or `basic` |

## Commands

### `add`

Generate a template markdown document with a pre-populated frontmatter block:

```bash
d2cms add "My Document Title"
```

The file is written to `D2CMS_DOCS_DIR` by default. Use `--path` to write into a subdirectory relative to `D2CMS_DOCS_DIR`. If a markdown file exists at that path (e.g. `guides.md`), its `document_key` is automatically used as the `parent_key` of the new document:

```bash
d2cms add "My Document Title" --path guides
```

Additional options:

```bash
# Set the WordPress content type (default: docs)
d2cms add "My Document Title" --content-type pages

# Assign tags (comma-delimited, supports multi-word tags)
d2cms add "My Document Title" --tags "guide,getting started,tutorial"
```

### `deprecate`

Mark a document as deprecated and relocate its children up one directory level:

```bash
d2cms deprecate guides/old-page.md
```

The path is relative to `D2CMS_DOCS_DIR`. This command sets `deprecated: true` in the file's frontmatter and updates the `parent_key` of any children to inherit the deprecated document's own parent. The next `sync` will remove the document from WordPress and delete the local file.

### `sync`

Sync all documents in `D2CMS_DOCS_DIR` to WordPress:

```bash
d2cms sync
```

Files whose content hash matches the stored `document_hash` are skipped. New files are created, changed files are updated, and files marked `deprecated: true` are deleted from WordPress and removed locally.


## Local WordPress environment

A Docker Compose setup is included for local development:

```bash
cd wordpress
docker compose up -d
# WordPress available at http://localhost:8080
```

The `mu-plugins/` directory registers a custom `docs` post type and a bearer token auth handler.

> **Warning:** The bearer token auth plugin (`d2cms-auth.php`) is for local development only and must not be used in production.

## Development

```bash
mypy          # type checking
ruff check .  # lint
ruff format . # format
pytest        # tests
```