import sys
from types import SimpleNamespace

from test_assistant import make_config

from aeris.assistant import AerisAssistant


def test_brightness_reports_actual_values_instead_of_assuming_set_worked(tmp_path, monkeypatch):
    monkeypatch.setattr("aeris.tools.desktop.DesktopTools._require_windows", lambda _: None)
    monkeypatch.setitem(sys.modules, "screen_brightness_control", SimpleNamespace(
        get_brightness=lambda: [50], set_brightness=lambda _: None))
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    try:
        turn = assistant.handle("set brightness to 35")
        assert not turn.success and turn.results[0].error == "verification_failed"
        assert turn.results[0].data["levels"] == [50]
        assert assistant.followup.current is None
    finally:
        assistant.close()


def test_relative_brightness_preserves_each_displays_initial_level(tmp_path, monkeypatch):
    levels = [30, 60]
    def set_value(value):
        if isinstance(value, str):
            levels[:] = [max(0, min(100, current + int(value))) for current in levels]
        else:
            levels[:] = [value] * len(levels)
    monkeypatch.setattr("aeris.tools.desktop.DesktopTools._require_windows", lambda _: None)
    monkeypatch.setitem(sys.modules, "screen_brightness_control", SimpleNamespace(
        get_brightness=lambda: levels[:], set_brightness=set_value))
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    try:
        turn = assistant.handle("increase brightness")
        assert turn.success and levels == [40, 70]
        assert turn.results[0].data["verified"]
    finally:
        assistant.close()
