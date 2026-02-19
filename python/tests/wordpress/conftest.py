from pathlib import Path

import pytest

from d2cms.config import D2CMSConfig
from d2cms.report import SyncReport

WP_BASE = "http://test-wp.test/wp-json/"


@pytest.fixture
def cfg(tmp_path: Path) -> D2CMSConfig:
    return D2CMSConfig(
        wp_api_root=WP_BASE,
        wp_api_key="test-token",
        wp_api_user="admin",
        docs_dir=tmp_path,
        auth_mode="token",
    )


@pytest.fixture
def report() -> SyncReport:
    return SyncReport()
