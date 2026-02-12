from __future__ import annotations

import httpx

from .config import D2CMSConfig


def make_client(cfg: D2CMSConfig) -> httpx.Client:
    headers = {
        "Accept": "application/json",
        "User-Agent": "d2cms/0.1",
    }

    auth = httpx.BasicAuth(cfg.wp_api_user, cfg.wp_api_key)
    if cfg.auth_mode == "token":
        headers['Authorization'] = f"Bearer {cfg.wp_api_key}"

    client = httpx.Client(
        base_url = cfg.wp_base_url,
        headers = headers,
        timeout = httpx.Timeout(10.0),
        auth = auth if cfg.auth_mode == 'basic' else None
    )

    return client