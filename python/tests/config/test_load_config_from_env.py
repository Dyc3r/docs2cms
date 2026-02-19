import pytest

from d2cms.config import ConfigError, load_config_from_env


class TestLoadConfigFromEnv:
    @pytest.fixture
    def valid_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("D2CMS_WP_API_ROOT", "https://example.com/wp-json")
        monkeypatch.setenv("D2CMS_WP_API_KEY", "test-token")
        monkeypatch.setenv("D2CMS_WP_API_USER", "admin")
        monkeypatch.setenv("D2CMS_DOCS_DIR", str(tmp_path))
        monkeypatch.setenv("D2CMS_AUTH_MODE", "token")
        return tmp_path

    def test_loads_all_fields(self, valid_env):
        cfg = load_config_from_env()
        assert cfg.wp_api_root == "https://example.com/wp-json/"
        assert cfg.wp_api_key == "test-token"
        assert cfg.wp_api_user == "admin"
        assert cfg.docs_dir == valid_env
        assert cfg.auth_mode == "token"

    def test_default_auth_mode_is_basic(self, valid_env, monkeypatch):
        monkeypatch.delenv("D2CMS_AUTH_MODE", raising=False)
        cfg = load_config_from_env()
        assert cfg.auth_mode == "basic"

    def test_auth_mode_normalised_to_lowercase(self, valid_env, monkeypatch):
        monkeypatch.setenv("D2CMS_AUTH_MODE", "TOKEN")
        cfg = load_config_from_env()
        assert cfg.auth_mode == "token"

    def test_raises_for_invalid_auth_mode(self, valid_env, monkeypatch):
        monkeypatch.setenv("D2CMS_AUTH_MODE", "oauth")
        with pytest.raises(ConfigError, match='"token" or "basic"'):
            load_config_from_env()

    def test_raises_when_docs_dir_does_not_exist(self, valid_env, monkeypatch, tmp_path):
        monkeypatch.setenv("D2CMS_DOCS_DIR", str(tmp_path / "nonexistent"))
        with pytest.raises(ConfigError, match="does not exist"):
            load_config_from_env()

    def test_raises_when_docs_dir_is_a_file(self, valid_env, monkeypatch, tmp_path):
        f = tmp_path / "not_a_dir.md"
        f.write_text("content")
        monkeypatch.setenv("D2CMS_DOCS_DIR", str(f))
        with pytest.raises(ConfigError, match="not a directory"):
            load_config_from_env()

    def test_raises_when_api_root_missing(self, valid_env, monkeypatch):
        monkeypatch.delenv("D2CMS_WP_API_ROOT")
        with pytest.raises(ConfigError):
            load_config_from_env()

    def test_raises_when_api_key_missing(self, valid_env, monkeypatch):
        monkeypatch.delenv("D2CMS_WP_API_KEY")
        with pytest.raises(ConfigError):
            load_config_from_env()

    def test_raises_when_api_user_missing(self, valid_env, monkeypatch):
        monkeypatch.delenv("D2CMS_WP_API_USER")
        with pytest.raises(ConfigError):
            load_config_from_env()

    def test_raises_when_docs_dir_missing(self, valid_env, monkeypatch):
        monkeypatch.delenv("D2CMS_DOCS_DIR")
        with pytest.raises(ConfigError):
            load_config_from_env()

    def test_api_root_trailing_slash_normalised(self, valid_env, monkeypatch):
        monkeypatch.setenv("D2CMS_WP_API_ROOT", "https://example.com/wp-json")
        cfg = load_config_from_env()
        assert cfg.wp_api_root.endswith("/")

    def test_config_is_frozen(self, valid_env):
        cfg = load_config_from_env()
        with pytest.raises((AttributeError, TypeError)):
            cfg.wp_api_key = "new-key"  # type: ignore[misc]

    def test_docs_dir_resolved_to_absolute(self, valid_env, monkeypatch, tmp_path):
        monkeypatch.setenv("D2CMS_DOCS_DIR", str(tmp_path))
        cfg = load_config_from_env()
        assert cfg.docs_dir.is_absolute()
