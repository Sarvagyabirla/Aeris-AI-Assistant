import pytest

from aeris.tools.downloads import DownloadTools


def test_download_url_requires_http_and_blocks_private_addresses(tmp_path):
    tools = DownloadTools(tmp_path, ("*",))
    with pytest.raises(ValueError):
        tools._validate_url("file:///secret.txt")
    with pytest.raises(ValueError):
        tools._validate_url("http://127.0.0.1/file.zip")
    with pytest.raises(ValueError):
        tools._validate_url("http://192.168.1.2/file.zip")


def test_download_domain_allowlist_and_embedded_credentials(tmp_path):
    tools = DownloadTools(tmp_path, ("example.com",))
    assert tools._validate_url("https://files.example.com/file.zip")
    with pytest.raises(ValueError):
        tools._validate_url("https://other.test/file.zip")
    with pytest.raises(ValueError):
        tools._validate_url("https://user:pass@example.com/file.zip")


def test_download_filename_is_sanitized_and_never_overwritten(tmp_path):
    tools = DownloadTools(tmp_path, ("*",))
    assert tools._safe_filename("../../unsafe?.zip") == "unsafe_.zip"
    existing = tmp_path / "file.zip"
    existing.write_bytes(b"existing")
    assert tools._destination_for("file.zip").name == "file (1).zip"
