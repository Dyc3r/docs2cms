import pytest

from d2cms.config import ConfigError, _normalize_api_root


class TestNormalizeApiRoot:
    def test_adds_trailing_slash(self):
        assert _normalize_api_root("https://example.com/wp-json") == "https://example.com/wp-json/"

    def test_preserves_existing_trailing_slash(self):
        assert _normalize_api_root("https://example.com/wp-json/") == "https://example.com/wp-json/"

    def test_strips_surrounding_whitespace(self):
        assert _normalize_api_root("  https://example.com/wp-json  ") == "https://example.com/wp-json/"

    def test_accepts_http_scheme(self):
        assert _normalize_api_root("http://localhost:8080/wp-json") == "http://localhost:8080/wp-json/"

    def test_accepts_https_scheme(self):
        assert _normalize_api_root("https://example.com") == "https://example.com/"

    def test_raises_for_no_scheme(self):
        with pytest.raises(ConfigError, match="valid scheme"):
            _normalize_api_root("example.com/wp-json")

    def test_raises_for_ftp_scheme(self):
        with pytest.raises(ConfigError, match="valid scheme"):
            _normalize_api_root("ftp://example.com/wp-json")

    def test_raises_for_empty_string(self):
        with pytest.raises(ConfigError, match="valid scheme"):
            _normalize_api_root("")

    def test_raises_for_relative_path(self):
        with pytest.raises(ConfigError, match="valid scheme"):
            _normalize_api_root("/wp-json/")
