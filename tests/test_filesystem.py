import pytest

from aeris.tools.filesystem import FilesystemTools, PathGuard


def test_path_guard_accepts_allowed_path(tmp_path):
    guard = PathGuard((tmp_path,))
    assert guard.resolve("notes.txt") == (tmp_path / "notes.txt").resolve()


def test_path_guard_rejects_traversal(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    guard = PathGuard((allowed,))
    with pytest.raises(PermissionError):
        guard.resolve("../outside.txt")


def test_find_files_only_returns_matches(tmp_path):
    (tmp_path / "resume.pdf").write_bytes(b"pdf")
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    result = FilesystemTools((tmp_path,)).find_files({"query": "resume"})
    assert result.success
    assert len(result.data["matches"]) == 1
    assert result.data["matches"][0].endswith("resume.pdf")


def test_read_text_file(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello Aeris", encoding="utf-8")
    result = FilesystemTools((tmp_path,)).read_text({"path": str(path)})
    assert result.success
    assert result.data["content"] == "hello Aeris"


def test_read_blocks_unapproved_extension(tmp_path):
    path = tmp_path / "program.exe"
    path.write_bytes(b"not really an exe")
    result = FilesystemTools((tmp_path,)).read_text({"path": str(path)})
    assert not result.success
    assert result.error == "unsupported_file_type"


def test_open_blocks_executable_before_os_call(tmp_path):
    path = tmp_path / "program.exe"
    path.write_bytes(b"binary")
    result = FilesystemTools((tmp_path,)).open_file({"path": str(path)})
    assert not result.success
    assert result.error == "dangerous_file_type"


def test_create_copy_and_move_do_not_overwrite(tmp_path):
    tools = FilesystemTools((tmp_path,))
    created = tools.write_text({"path": "notes.txt", "text": "hello"})
    assert created.success

    duplicate = tools.write_text({"path": "notes.txt", "text": "replacement"})
    assert not duplicate.success
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello"

    copied = tools.copy_file({"source": "notes.txt", "destination": "copy.txt"})
    assert copied.success
    moved = tools.move_file({"source": "copy.txt", "destination": "archive/moved.txt"})
    assert moved.success
    assert not (tmp_path / "copy.txt").exists()
    assert (tmp_path / "archive" / "moved.txt").read_text(encoding="utf-8") == "hello"
