import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

AuthMode = Literal["token", "basic"]



class ConfigError(ValueError):
    """Raised when runtime config is missing or invalid"""



def _getenv_required(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ConfigError(f"Missing required environment variable: {name}")
    
    return value.strip()



def _normalize_api_root(url: str) -> str:
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ConfigError("API root URL must start with a valid scheme")
    
    
    return url if url.endswith("/") else url + "/"



@dataclass(frozen=True)
class D2CMSConfig:
    wp_api_root: str
    wp_api_key: str
    wp_api_user: str
    docs_dir: Path
    auth_mode: AuthMode
    

def load_config_from_env() -> D2CMSConfig:
    auth_mode_raw = os.getenv("D2CMS_AUTH_MODE", "basic").strip().lower()
    if auth_mode_raw not in ("token", "basic"):
        raise ConfigError('D2CMS_AUTH_MODE must be either "token" or "basic"')
    
    
    docs_dir = Path(_getenv_required("D2CMS_DOCS_DIR")).expanduser().resolve()
    if not docs_dir.exists():
        raise ConfigError(f"D2CMS_DOCS_DIR does not exist: {docs_dir}")
    if not docs_dir.is_dir():
        raise ConfigError(f"D2CMS_DOCS_DIR is not a directory: {docs_dir}")
    

    return D2CMSConfig(
        wp_api_root = _normalize_api_root(_getenv_required("D2CMS_WP_API_ROOT")),
        wp_api_key = _getenv_required("D2CMS_WP_API_KEY"),
        wp_api_user = _getenv_required("D2CMS_WP_API_USER"),
        docs_dir = docs_dir,
        auth_mode = auth_mode_raw
    )