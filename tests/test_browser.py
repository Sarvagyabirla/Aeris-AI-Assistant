import pytest

from aeris.tools.browser import BrowserTools


def test_url_normalization_adds_https():
    tools = BrowserTools(("*",))
    assert tools._normalize_url("example.com") == "https://example.com"


def test_only_http_protocols_are_allowed():
    tools = BrowserTools(("*",))
    with pytest.raises(ValueError):
        tools._normalize_url("file:///etc/passwd")


def test_domain_allowlist():
    tools = BrowserTools(("youtube.com",))
    assert tools._normalize_url("https://www.youtube.com/watch?v=1")
    with pytest.raises(ValueError):
        tools._normalize_url("https://example.com")
