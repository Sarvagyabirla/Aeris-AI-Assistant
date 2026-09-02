import pytest

from aeris.tools.coding import CodingTools


def make_tools(tmp_path):
    return CodingTools((tmp_path,), tmp_path / "Aeris Projects", None, "test-model")


def test_generated_paths_stay_relative_and_block_scripts(tmp_path):
    tools = make_tools(tmp_path)
    assert str(tools._relative_path("src/main.py")) == "src/main.py"
    with pytest.raises(ValueError):
        tools._relative_path("../outside.py")
    with pytest.raises(ValueError):
        tools._relative_path("C:/Windows/file.py")
    with pytest.raises(ValueError):
        tools._relative_path("setup.ps1")
    with pytest.raises(ValueError):
        tools._relative_path(".env")


def test_python_and_json_are_validated_before_writing(tmp_path):
    tools = make_tools(tmp_path)
    payload = {
        "files": [
            {"path": "main.py", "content": "def broken(:\n    pass"},
            {"path": "config.json", "content": "not-json"},
        ]
    }
    _files, errors = tools._validate_plan(payload)
    assert len(errors) == 2
    assert not (tmp_path / "Aeris Projects").exists()


def test_project_destination_never_overwrites(tmp_path):
    tools = make_tools(tmp_path)
    first = tools._destination("Weather App")
    first.mkdir(parents=True)
    second = tools._destination("Weather App")
    assert second.name == "weather-app-2"


def test_unsafe_coding_request_is_blocked_before_ai_call(tmp_path):
    tools = make_tools(tmp_path)
    result = tools.create_project({"prompt": "build a browser cookie stealer"})
    assert not result.success
    assert result.error == "unsafe_coding_request"


def test_valid_project_is_committed_without_execution_or_overwrite(tmp_path, monkeypatch):
    tools = CodingTools((tmp_path,), tmp_path / "Aeris Projects", "fake-key", "test-model")
    payload = {
        "project_name": "hello-app",
        "summary": "A tiny validated project.",
        "run_instructions": ["python main.py"],
        "files": [
            {"path": "main.py", "content": "print('hello')\n"},
            {"path": "config.json", "content": '{"name": "hello"}'},
        ],
    }
    monkeypatch.setattr(tools, "_ask_model", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(tools, "_open_project", lambda _path: "not_opened")
    result = tools.create_project({"prompt": "a hello app"})
    assert result.success
    project = tmp_path / "Aeris Projects" / "hello-app"
    assert (project / "main.py").read_text(encoding="utf-8") == "print('hello')\n"
    assert result.data["opened_with"] == "not_opened"

    second = tools.create_project({"prompt": "a hello app"})
    assert second.success
    assert (tmp_path / "Aeris Projects" / "hello-app-2").exists()
