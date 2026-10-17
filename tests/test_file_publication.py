"""Publication races and cancellation through the registered production tools."""
import ctypes
import os
import time
from dataclasses import replace
from email.message import Message
from pathlib import Path

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.core.file_publication import HeldSource, _FileDispositionInfo
from aeris.models import ActionRequest
from aeris.state import CancellationToken
from aeris.tools import filesystem
from aeris.tools.downloads import DownloadTools

TRANSFER_TOOLS = ["files.copy", pytest.param("files.move", marks=pytest.mark.skipif(
    os.name != "nt", reason="Identity-preserving source deletion requires Windows"))]


@pytest.fixture
def assistant(tmp_path):
    config = make_config(tmp_path, dry_run=False)
    config.download_dir = tmp_path / "downloads"
    instance = AerisAssistant(config)
    try:
        yield instance
    finally:
        instance.close()


@pytest.mark.parametrize("tool", TRANSFER_TOOLS)
def test_competing_destination_is_never_overwritten(assistant, tmp_path, monkeypatch, tool):
    source, destination = tmp_path / "source.txt", tmp_path / "destination.txt"
    source.write_bytes(b"original")
    exists = Path.exists
    raced = False

    def competing_exists(path):
        nonlocal raced
        if path == destination and not raced:
            raced = True
            destination.write_bytes(b"competing document")
            return False
        return exists(path)

    monkeypatch.setattr(Path, "exists", competing_exists)
    result = assistant.registry.execute(ActionRequest(tool, {
        "source": str(source), "destination": str(destination),
    }), lambda *_: True)
    assert not result.success
    assert result.error == "already_exists"
    assert destination.read_bytes() == b"competing document"
    assert source.read_bytes() == b"original"
    assert not list(tmp_path.glob(".aeris-transfer-*"))


class CancelBeforeCommit(CancellationToken):
    def commit(self, effect):
        self.cancel()
        return super().commit(effect)


class CancelAfterCommit(CancellationToken):
    def commit(self, effect):
        result = super().commit(effect)
        self.cancel()
        return result


@pytest.mark.parametrize("tool", TRANSFER_TOOLS)
def test_cancel_before_publication_retains_source_only(assistant, tmp_path, tool):
    source, destination = tmp_path / "source.txt", tmp_path / "destination.txt"
    source.write_bytes(b"original")
    result = assistant.registry.execute(ActionRequest(tool, {
        "source": str(source), "destination": str(destination),
    }), lambda *_: True, CancelBeforeCommit())
    assert not result.success and result.error == "cancelled"
    assert not destination.exists()
    assert source.read_bytes() == b"original"
    assert not list(tmp_path.glob(".aeris-transfer-*"))


@pytest.mark.parametrize("tool", TRANSFER_TOOLS)
def test_cancel_after_publication_has_retained_effect_receipt(assistant, tmp_path, tool):
    source, destination = tmp_path / "source.txt", tmp_path / "destination.txt"
    source.write_bytes(b"original")
    result = assistant.registry.execute(ActionRequest(tool, {
        "source": str(source), "destination": str(destination),
    }), lambda *_: True, CancelAfterCommit())
    assert not result.success and result.error == "cancelled_after_publication"
    assert result.data["published"] is True
    assert result.data["destination"] == str(destination)
    assert result.data["source_removed"] is False
    assert destination.read_bytes() == source.read_bytes() == b"original"


class Response:
    def __init__(self):
        self.headers = Message()
        self.headers["Content-Length"] = "7"
        self.content = iter([b"fixture", b""])

    def geturl(self):
        return "https://example.com/fixture.txt"

    def read(self, _limit):
        return next(self.content)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def fake_download(assistant, monkeypatch, before_open=lambda: None, response_factory=Response):
    tools = assistant.registry._tools["downloads.download"].handler.__self__
    monkeypatch.setattr(tools, "_validate_url", lambda value, **_: value)
    monkeypatch.setattr(tools, "_defender_scan", lambda *_, **__: "not_available")

    class Opener:
        def open(self, *_args, **_kwargs):
            before_open()
            return response_factory()

    monkeypatch.setattr("aeris.tools.downloads.urllib.request.build_opener", lambda *_: Opener())
    return tools


def test_download_never_removes_a_partial_it_did_not_create(assistant, monkeypatch):
    directory = assistant.config.download_dir
    directory.mkdir()
    competing = directory / "fixture.txt.aeris.part"
    fake_download(assistant, monkeypatch, lambda: competing.write_bytes(b"another download"))
    result = assistant.registry.execute(ActionRequest("downloads.download", {
        "url": "https://example.com/fixture.txt",
    }), lambda *_: True)
    assert competing.exists() and competing.read_bytes() == b"another download"
    assert result.success and result.data["published"] is True


def test_download_receipt_survives_verification_failure(assistant, monkeypatch):
    tools = fake_download(assistant, monkeypatch)

    def failed_scan(*_, **__):
        raise OSError("fixture scan unavailable")

    monkeypatch.setattr(tools, "_defender_scan", failed_scan)
    result = assistant.registry.execute(ActionRequest("downloads.download", {
        "url": "https://example.com/fixture.txt",
    }), lambda *_: True)
    assert not result.success and result.error == "verification_incomplete"
    assert result.data["published"] is True
    assert Path(result.data["path"]).read_bytes() == b"fixture"


def test_download_cancel_before_publication_leaves_no_owned_stage(assistant, monkeypatch):
    fake_download(assistant, monkeypatch)
    result = assistant.registry.execute(ActionRequest("downloads.download", {
        "url": "https://example.com/fixture.txt",
    }), lambda *_: True, CancelBeforeCommit())
    assert not result.success and result.error == "cancelled"
    assert not list(assistant.config.download_dir.iterdir())


@pytest.mark.parametrize("tool", TRANSFER_TOOLS)
def test_changed_source_before_handle_open_is_rejected(assistant, tmp_path, monkeypatch, tool):
    source, destination = tmp_path / "source.txt", tmp_path / "destination.txt"
    source.write_bytes(b"original")
    original = filesystem._HeldSource

    def replaced(path, **kwargs):
        replacement = tmp_path / "replacement.txt"
        replacement.write_bytes(b"replacement")
        os.replace(replacement, source)
        return original(path, **kwargs)

    monkeypatch.setattr(filesystem, "_HeldSource", replaced)
    result = assistant.registry.execute(ActionRequest(tool, {
        "source": str(source), "destination": str(destination),
    }), lambda *_: True)
    assert result.error == "stale_source"
    assert source.read_bytes() == b"replacement"
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows native sharing/deletion contract")
@pytest.mark.parametrize("tool", TRANSFER_TOOLS)
def test_opened_source_cannot_be_replaced_before_publication(assistant, tmp_path, monkeypatch, tool):
    source, replacement = tmp_path / "source.txt", tmp_path / "replacement.txt"
    source.write_bytes(b"original")
    replacement.write_bytes(b"replacement")
    publish = filesystem.publish_exclusive

    def raced(staged, destination, token=None):
        with pytest.raises(PermissionError):
            os.replace(replacement, source)
        with pytest.raises(PermissionError):
            with source.open("wb"):
                pytest.fail("An outside writer opened the held source")
        publish(staged, destination, token)

    monkeypatch.setattr(filesystem, "publish_exclusive", raced)
    result = assistant.registry.execute(ActionRequest(tool, {
        "source": str(source), "destination": str(tmp_path / "destination.txt"),
    }), lambda *_: True)
    assert result.success
    assert (tmp_path / "destination.txt").read_bytes() == b"original"
    assert replacement.read_bytes() == b"replacement"


@pytest.mark.skipif(os.name != "nt", reason="Windows native sharing/deletion contract")
def test_move_removal_failure_retains_both_paths_and_uncertain_receipt(assistant, tmp_path, monkeypatch):
    source, destination = tmp_path / "source.txt", tmp_path / "destination.txt"
    source.write_bytes(b"original")

    def failed_remove(_self):
        raise OSError("fixture handle deletion failure")

    monkeypatch.setattr(filesystem._HeldSource, "delete_owned", failed_remove)
    result = assistant.registry.execute(ActionRequest("files.move", {
        "source": str(source), "destination": str(destination),
    }), lambda *_: True)
    assert result.error == "source_removal_unverified"
    assert result.data["published"] and result.data["outcome_uncertain"]
    assert not result.data["source_removed"]
    assert source.read_bytes() == destination.read_bytes() == b"original"


@pytest.mark.skipif(os.name != "nt", reason="Windows native sharing/deletion contract")
def test_move_cancel_after_owned_source_deletion_reports_both_effects(assistant, tmp_path):
    source, destination = tmp_path / "source.txt", tmp_path / "destination.txt"
    source.write_bytes(b"original")

    class CancelAfterDelete(CancellationToken):
        calls = 0

        def commit(self, effect):
            result = super().commit(effect)
            self.calls += 1
            if self.calls == 2:
                self.cancel()
            return result

    result = assistant.registry.execute(ActionRequest("files.move", {
        "source": str(source), "destination": str(destination),
    }), lambda *_: True, CancelAfterDelete())
    assert result.error == "cancelled_after_publication"
    assert result.data["published"] and result.data["source_removed"]
    assert not source.exists() and destination.read_bytes() == b"original"


@pytest.mark.parametrize("tool", TRANSFER_TOOLS)
def test_transfer_hardlink_unavailable_fails_closed(assistant, tmp_path, monkeypatch, tool):
    source, destination = tmp_path / "source.txt", tmp_path / "destination.txt"
    source.write_bytes(b"original")

    def unsupported(*_args, **_kwargs):
        raise PermissionError("fixture filesystem has no links")

    monkeypatch.setattr("aeris.core.file_publication.os.link", unsupported)
    result = assistant.registry.execute(ActionRequest(tool, {
        "source": str(source), "destination": str(destination),
    }), lambda *_: True)
    assert not result.success and result.error == "transfer_unavailable"
    assert source.read_bytes() == b"original"
    assert not destination.exists() and not list(tmp_path.glob(".aeris-transfer-*"))


def test_download_destination_created_at_publication_is_retained(assistant, monkeypatch):
    fake_download(assistant, monkeypatch)
    from aeris.tools import downloads
    publish = downloads.publish_exclusive

    def competing(staged, destination, token=None):
        destination.write_bytes(b"competing document")
        publish(staged, destination, token)

    monkeypatch.setattr(downloads, "publish_exclusive", competing)
    result = assistant.registry.execute(ActionRequest("downloads.download", {
        "url": "https://example.com/fixture.txt",
    }), lambda *_: True)
    assert not result.success and result.error == "already_exists"
    assert (assistant.config.download_dir / "fixture.txt").read_bytes() == b"competing document"
    assert not list(assistant.config.download_dir.glob(".aeris-download-*"))


def test_download_missing_after_scan_is_reported_with_publication_receipt(assistant, monkeypatch):
    tools = fake_download(assistant, monkeypatch)

    def removed_during_scan(path, **_):
        path.unlink()
        return "completed"

    monkeypatch.setattr(tools, "_defender_scan", removed_during_scan)
    result = assistant.registry.execute(ActionRequest("downloads.download", {
        "url": "https://example.com/fixture.txt",
    }), lambda *_: True)
    assert not result.success and result.error == "download_unavailable_after_scan"
    assert result.data["published"] and not result.data["file_present"]


@pytest.mark.parametrize("tool", ["files.copy", "downloads.download"])
def test_stage_cleanup_failure_never_discards_publication_receipt(assistant, tmp_path, monkeypatch, tool):
    if tool == "files.copy":
        source = tmp_path / "source.txt"
        source.write_bytes(b"fixture")
        arguments = {"source": str(source), "destination": str(tmp_path / "destination.txt")}
    else:
        fake_download(assistant, monkeypatch)
        arguments = {"url": "https://example.com/fixture.txt"}
    if os.name == "nt":
        original_delete = HeldSource.delete_owned

        def fail_owned_stage(self):
            if self.path.name.startswith((".aeris-transfer-", ".aeris-download-")):
                raise PermissionError("fixture staging cleanup denied")
            return original_delete(self)

        monkeypatch.setattr(HeldSource, "delete_owned", fail_owned_stage)
    else:
        unlink = Path.unlink

        def fail_stage(path, *args, **kwargs):
            if path.name.startswith((".aeris-transfer-", ".aeris-download-")):
                raise PermissionError("fixture staging cleanup denied")
            return unlink(path, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", fail_stage)
    result = assistant.registry.execute(ActionRequest(tool, arguments), lambda *_: True)
    assert result.error == "cleanup_incomplete"
    assert result.data["published"] and result.data["staging_cleanup_incomplete"]
    assert Path(result.data["staging_path"]).read_bytes() == b"fixture"


def test_native_disposition_boolean_uses_one_byte():
    assert ctypes.sizeof(_FileDispositionInfo) == 1


@pytest.mark.parametrize("failure", ["fdopen", "fstat"])
def test_held_source_construction_failure_closes_descriptor(tmp_path, monkeypatch, failure):
    source = tmp_path / "source.txt"
    source.write_bytes(b"fixture")
    observed = []
    real_fstat = os.fstat

    def fail(descriptor, *_args, **_kwargs):
        observed.append(descriptor)
        raise OSError("fixture constructor failure")

    monkeypatch.setattr("aeris.core.file_publication.os." + failure, fail)
    with pytest.raises(OSError):
        HeldSource(source, move=False)
    with pytest.raises(OSError):
        real_fstat(observed[0])


@pytest.mark.skipif(os.name != "nt", reason="Windows protected publication handle")
def test_move_destination_change_before_binding_retains_source(assistant, tmp_path, monkeypatch):
    source, destination = tmp_path / "source.txt", tmp_path / "destination.txt"
    replacement = tmp_path / "replacement.txt"
    source.write_bytes(b"original")
    replacement.write_bytes(b"competing")
    publish = filesystem.publish_exclusive

    def raced(staged, target, token=None):
        publish(staged, target, token)
        with pytest.raises(PermissionError):
            target.write_bytes(b"competing")
        os.replace(replacement, target)

    monkeypatch.setattr(filesystem, "publish_exclusive", raced)
    result = assistant.registry.execute(ActionRequest("files.move", {
        "source": str(source), "destination": str(destination),
    }), lambda *_: True)
    assert result.error == "published_destination_changed"
    assert result.data["published"] and not result.data["source_removed"]
    assert source.read_bytes() == b"original" and destination.read_bytes() == b"competing"


@pytest.mark.skipif(os.name != "nt", reason="Windows protected destination handle")
def test_bound_move_destination_blocks_mutation_through_source_deletion(assistant, tmp_path, monkeypatch):
    source, destination = tmp_path / "source.txt", tmp_path / "destination.txt"
    replacement = tmp_path / "replacement.txt"
    source.write_bytes(b"original")
    replacement.write_bytes(b"competing")
    delete = HeldSource.delete_owned

    def raced_delete(self):
        if self.path == source:
            with pytest.raises(PermissionError):
                destination.write_bytes(b"competing")
            with pytest.raises(PermissionError):
                os.replace(replacement, destination)
        delete(self)

    monkeypatch.setattr(HeldSource, "delete_owned", raced_delete)
    result = assistant.registry.execute(ActionRequest("files.move", {
        "source": str(source), "destination": str(destination),
    }), lambda *_: True)
    assert result.success and result.data["source_removed"]
    assert not source.exists() and destination.read_bytes() == b"original"
    assert replacement.read_bytes() == b"competing"


@pytest.mark.skipif(os.name != "nt", reason="Windows delete-by-owned-handle cleanup")
@pytest.mark.parametrize("tool", ["files.copy", "downloads.download"])
def test_new_stage_entry_when_protected_reader_closes_is_never_deleted(assistant, tmp_path, monkeypatch, tool):
    if tool == "files.copy":
        source = tmp_path / "source.txt"
        source.write_bytes(b"fixture")
        arguments = {"source": str(source), "destination": str(tmp_path / "destination.txt")}
    else:
        fake_download(assistant, monkeypatch)
        arguments = {"url": "https://example.com/fixture.txt"}
    close = HeldSource.close
    replacements = []

    def competing_close(self):
        close(self)
        if not self.delete_access and self.path.name.startswith((".aeris-transfer-", ".aeris-download-")):
            replacement = self.path.with_name("outside.tmp")
            replacement.write_bytes(b"outside replacement")
            os.replace(replacement, self.path)
            replacements.append(self.path)

    monkeypatch.setattr(HeldSource, "close", competing_close)
    result = assistant.registry.execute(ActionRequest(tool, arguments), lambda *_: True)
    assert result.error == "cleanup_incomplete" and result.data["published"]
    assert len(replacements) == 1 and replacements[0].read_bytes() == b"outside replacement"


def aged_partial(directory, name):
    directory.mkdir(exist_ok=True)
    path = directory / name
    path.write_bytes(b"partial fixture")
    past = time.time() - 25 * 3600
    os.utime(path, (past, past))
    return path


def test_partial_cleanup_only_removes_aged_owned_namespace(assistant):
    directory = assistant.config.download_dir
    old = aged_partial(directory, ".aeris-download-old.aeris.part")
    foreign = aged_partial(directory, "unrelated.aeris.part")
    legacy = aged_partial(directory, "fixture.txt.aeris.part")
    fresh = directory / ".aeris-download-fresh.aeris.part"
    fresh.write_bytes(b"new download")
    result = assistant.registry.execute(ActionRequest("downloads.clear_partial"), lambda *_: True)
    assert result.success and result.data["removed_paths"] == [str(old)]
    assert not old.exists()
    assert foreign.exists() and legacy.exists() and fresh.exists()


@pytest.mark.parametrize("token,expected", [(CancelBeforeCommit, "cancelled"),
                                            (CancelAfterCommit, "cancelled_after_cleanup")])
def test_partial_cleanup_cancellation_preserves_effect_receipt(assistant, token, expected):
    old = aged_partial(assistant.config.download_dir, ".aeris-download-old.aeris.part")
    result = assistant.registry.execute(ActionRequest("downloads.clear_partial"), lambda *_: True, token())
    assert result.error == expected
    if expected == "cancelled":
        assert old.exists() and not result.data["removed_paths"]
    else:
        assert not old.exists() and result.data["removed_paths"] == [str(old)]


def test_partial_cleanup_cannot_remove_active_stage_even_if_aged(assistant, monkeypatch):
    directory = assistant.config.download_dir
    observed = []
    other_instance = DownloadTools(directory, ("example.com",))
    assistant.registry._tools["downloads.clear_partial"] = replace(
        assistant.registry._tools["downloads.clear_partial"], handler=other_instance.clear_partial_downloads)

    class ActiveResponse(Response):
        def read(self, limit):
            if not observed:
                stage = next(directory.glob(".aeris-download-*.aeris.part"))
                past = time.time() - 25 * 3600
                os.utime(stage, (past, past))
                result = assistant.registry.execute(ActionRequest("downloads.clear_partial"), lambda *_: True)
                observed.append(result)
                assert stage.exists()
            return super().read(limit)

    fake_download(assistant, monkeypatch, response_factory=ActiveResponse)
    result = assistant.registry.execute(ActionRequest("downloads.download", {
        "url": "https://example.com/fixture.txt",
    }), lambda *_: True)
    assert result.success
    assert observed[0].success and not observed[0].data["removed_paths"]
    assert observed[0].data["skipped"] == 1


def test_partial_cleanup_rechecks_folder_at_final_gate(assistant, tmp_path, monkeypatch):
    directory = assistant.config.download_dir
    old = aged_partial(directory, ".aeris-download-old.aeris.part")
    resolve = Path.resolve
    calls = 0

    def changed(path, *args, **kwargs):
        nonlocal calls
        if path == directory:
            calls += 1
            if calls >= 2:
                return tmp_path / "outside"
        return resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", changed)
    result = assistant.registry.execute(ActionRequest("downloads.clear_partial"), lambda *_: True)
    assert result.error == "cleanup_incomplete"
    assert old.exists() and not result.data["removed_paths"]


def test_download_provider_exception_body_is_sanitized(assistant, monkeypatch):
    class FailedResponse(Response):
        def read(self, _limit):
            raise RuntimeError("FAKE_PRIVATE_PROVIDER_BODY https://user:secret@example.com/private")

    fake_download(assistant, monkeypatch, response_factory=FailedResponse)
    result = assistant.registry.execute(ActionRequest("downloads.download", {
        "url": "https://example.com/fixture.txt",
    }), lambda *_: True)
    assert result.error == "download_failed"
    assert "FAKE_PRIVATE_PROVIDER_BODY" not in result.message + str(result.data)
    assert not list(assistant.config.download_dir.iterdir())


@pytest.mark.parametrize("tool", ["files.copy", "downloads.download"])
def test_stage_byte_mutation_with_restored_metadata_is_rejected(assistant, tmp_path, monkeypatch, tool):
    def changed_stage(path, **kwargs):
        if path.name.startswith((".aeris-transfer-", ".aeris-download-")):
            before = path.stat()
            path.write_bytes(b"changed")
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        return HeldSource(path, **kwargs)

    if tool == "files.copy":
        source = tmp_path / "source.txt"
        source.write_bytes(b"fixture")
        arguments = {"source": str(source), "destination": str(tmp_path / "destination.txt")}
        monkeypatch.setattr(filesystem, "_HeldSource", changed_stage)
    else:
        fake_download(assistant, monkeypatch)
        arguments = {"url": "https://example.com/fixture.txt"}
        monkeypatch.setattr("aeris.tools.downloads.HeldSource", changed_stage)
    result = assistant.registry.execute(ActionRequest(tool, arguments), lambda *_: True)
    assert not result.success and not result.data["published"]
    assert result.error == ("stale_stage" if tool == "files.copy" else "download_failed")
    assert not list(tmp_path.glob(".aeris-transfer-*"))
    assert not list(assistant.config.download_dir.glob(".aeris-download-*"))
