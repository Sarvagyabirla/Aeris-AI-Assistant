import json

import pytest

from aeris.tools.packages import PackageTools


def test_package_aliases_resolve_to_exact_winget_ids(tmp_path):
    catalog = tmp_path / "packages.json"
    catalog.write_text(json.dumps({"vlc": "VideoLAN.VLC"}), encoding="utf-8")
    tools = PackageTools((tmp_path,), catalog)
    assert tools._package_selector("VLC") == ("--id", "VideoLAN.VLC")
    assert tools._package_selector("Git.Git") == ("--id", "Git.Git")
    assert tools._package_selector("Some App") == ("--name", "Some App")


def test_package_query_rejects_control_characters(tmp_path):
    tools = PackageTools((tmp_path,))
    with pytest.raises(ValueError):
        tools._package_selector("safe\nsecond-command")
