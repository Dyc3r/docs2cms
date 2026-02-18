# docs2cms

A CLI utility for publishing git-managed markdown files to WordPress via its REST API.

Markdown files live in your repository. `d2cms` reads their YAML frontmatter to track WordPress IDs and content hashes, then creates or updates posts/pages/docs only when content has changed.

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
