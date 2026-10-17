from pathlib import Path

import pytest

from aeris.state import CancellationToken, CancelledError
from aeris.tools.filesystem import FilesystemTools


def test_note_publication_race_never_overwrites_competing_file(tmp_path, monkeypatch):
    tools = FilesystemTools((tmp_path,))
    destination = tmp_path / "note.txt"
    exists = Path.exists
    def raced_exists(path):
        if path == destination:
            destination.write_bytes(b"competing user edit")
            return False
        return exists(path)
    monkeypatch.setattr(Path, "exists", raced_exists)
    result = tools.write_text({"path": "note.txt", "text": "assistant text"})
    assert not result.success and result.error == "already_exists"
    assert destination.read_bytes() == b"competing user edit"
    assert not list(tmp_path.glob(".aeris-note-*"))


def test_note_cancelled_during_final_resolve_preserves_absence(tmp_path, monkeypatch):
    tools = FilesystemTools((tmp_path,))
    resolve = tools.guard.resolve
    token = CancellationToken()
    calls = []
    def cancel(value):
        calls.append(value)
        if len(calls) == 2:
            token.cancel()
        return resolve(value)
    monkeypatch.setattr(tools.guard, "resolve", cancel)
    result = tools.write_text({"path": "note.txt", "text": "fixture"}, token)
    assert result.error == "cancelled"
    assert not (tmp_path / "note.txt").exists()
    assert not list(tmp_path.glob(".aeris-note-*"))


def test_find_has_deadline_and_honors_cancel(tmp_path, monkeypatch):
    tools = FilesystemTools((tmp_path,))
    token = CancellationToken()
    token.cancel()
    with pytest.raises(CancelledError):
        tools.find_files({"query": "absent"}, token=token)
    now = iter([0.0, 3.0])
    monkeypatch.setattr("aeris.tools.filesystem.time.monotonic", lambda: next(now))
    result = tools.find_files({"query": "absent"})
    assert result.data["truncated"]
