import pytest

from d2cms.config import ConfigError, _getenv_required


class TestGetenvRequired:
    def test_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("_D2CMS_TEST_VAR", "some-value")
        assert _getenv_required("_D2CMS_TEST_VAR") == "some-value"

    def test_strips_surrounding_whitespace(self, monkeypatch):
        monkeypatch.setenv("_D2CMS_TEST_VAR", "  padded  ")
        assert _getenv_required("_D2CMS_TEST_VAR") == "padded"

    def test_raises_when_variable_absent(self, monkeypatch):
        monkeypatch.delenv("_D2CMS_TEST_VAR", raising=False)
        with pytest.raises(ConfigError, match="_D2CMS_TEST_VAR"):
            _getenv_required("_D2CMS_TEST_VAR")

    def test_raises_for_empty_string(self, monkeypatch):
        monkeypatch.setenv("_D2CMS_TEST_VAR", "")
        with pytest.raises(ConfigError, match="_D2CMS_TEST_VAR"):
            _getenv_required("_D2CMS_TEST_VAR")

    def test_raises_for_whitespace_only(self, monkeypatch):
        monkeypatch.setenv("_D2CMS_TEST_VAR", "   ")
        with pytest.raises(ConfigError, match="_D2CMS_TEST_VAR"):
            _getenv_required("_D2CMS_TEST_VAR")
